"""Dashboard orang tua: karya, penilaian, dan catatan guru untuk anak dari akun yang login."""
import datetime
import re

from django.db import connection
from django.template import Context, Template
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from accounts.models import Siswa, User
from ruang_kerja.models import AnggotaRuangKerja, CatatanRapor, RuangKerja, SubmisiTugas, Tugas

from .models import DimensiPenilaian, LampiranKarya, RefleksiKarya, SkorDimensi
from .orangtua import BATAS_KARYA, ringkasan_untuk_orangtua
from .tests_alur import DasarKreasi, foto, suara


class DasarOrangTua(DasarKreasi):
    """Tambah pembantu untuk membuat karya; guru, siswa A/B, orang tua A/B, ruang SD 1-3 sudah ada dari DasarKreasi."""
    hari = 0

    def buat_karya(self, siswa=None, ruang=None, judul='Maket rumahku', skor=None, feedback='', link=None,
                   emoji='bangga', ringkasan='', hari=None):
        ruang = ruang or self.ruang
        siswa = siswa or self.s_a
        DasarOrangTua.hari += 1
        tugas = Tugas.objects.create(ruang_kerja=ruang, jenis='kreasi', judul=judul, instruksi='x')
        sub = SubmisiTugas.objects.create(tugas=tugas, siswa=siswa, teks_jawaban=ringkasan, feedback=feedback)
        SubmisiTugas.objects.filter(pk=sub.pk).update(
            dikirim_pada=timezone.now() + datetime.timedelta(days=hari if hari is not None else DasarOrangTua.hari))
        LampiranKarya.objects.create(submisi=sub, tipe='foto', nama_asli='maket.png', file=foto())
        if link:
            LampiranKarya.objects.create(submisi=sub, tipe='link', url=link)
        if emoji:
            RefleksiKarya.objects.create(submisi=sub, tipe='emoji_suara', emoji=emoji, audio=suara('r.webm'))
        for kode, level in (skor or {}).items():
            SkorDimensi.objects.create(submisi=sub, level=level, dinilai_oleh=self.guru,
                                       dimensi=DimensiPenilaian.objects.get(jenjang=ruang.get_jenjang(), kode=kode))
        return sub

    def dashboard(self, user):
        self.client.logout()
        self.client.force_login(user)
        return self.client.get(reverse('accounts:dashboard_orangtua'))


KEB, MOT, LIS = 'keberanian_berekspresi', 'motorik_halus', 'kelancaran_lisan'


class TampilanOrangTuaTest(DasarOrangTua):
    def test_melihat_karya_penilaian_dan_catatan_anaknya(self):
        sub = self.buat_karya(skor={KEB: 3, MOT: 4}, feedback='Hebat, Ani!')
        CatatanRapor.objects.create(ruang_kerja=self.ruang, siswa=self.s_a, catatan='Catatan disimpan guru.',
                                    catatan_fisik_motorik='Motorik disimpan guru.')
        r = self.dashboard(self.ortu_a)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Karya &amp; Perkembangan Ani')
        self.assertContains(r, 'Maket rumahku')
        self.assertContains(r, f'src="{sub.lampiran_karya.get(tipe="foto").url_akses}"')
        self.assertContains(r, 'Merasa bangga')
        self.assertContains(r, 'Penilaian guru')
        self.assertContains(r, 'Keberanian Berekspresi')
        self.assertContains(r, 'Cakap (3/4)')
        self.assertContains(r, 'Ani berani menunjukkan karyanya dan menyampaikan idenya kepada guru dan teman.')
        self.assertContains(r, 'Sangat Baik (4/4)')
        self.assertContains(r, 'Hebat, Ani!')
        self.assertContains(r, 'Catatan guru · Seni')
        self.assertContains(r, 'Catatan disimpan guru.')
        self.assertContains(r, 'Motorik disimpan guru.')

    def test_bagian_lama_dashboard_tetap_ada(self):
        r = self.dashboard(self.ortu_a)
        self.assertContains(r, 'Poin Aktif')
        self.assertContains(r, 'Belum ada karya kreasi atau catatan dari guru.')

    def test_tidak_melihat_karya_anak_lain(self):
        # Judul tugas TIDAK dipakai sebagai penanda privasi: tugas dibuat untuk satu RUANG KELAS
        # (bukan satu siswa), jadi judulnya memang wajar terlihat semua orang tua di kelas yang sama
        # (lihat bagian Tugas). Yang harus tetap tersembunyi adalah isi karya, skor, dan feedback --
        # itulah yang diuji di sini.
        self.buat_karya(judul='Tugas Kreasi Bersama', skor={KEB: 4}, feedback='Pesan khusus untuk Ani')
        CatatanRapor.objects.create(ruang_kerja=self.ruang, siswa=self.s_a, catatan='Catatan pribadi Ani.')
        r = self.dashboard(self.ortu_b)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Tugas Kreasi Bersama')                 # judul tugas: wajar terlihat (kelas bersama)
        for teks in ['Pesan khusus untuk Ani', 'Catatan pribadi Ani.', 'Perkembangan Ani', 'maket.png']:
            self.assertNotContains(r, teks)                             # isi karya/skor/catatan: harus tersembunyi
        self.assertContains(r, 'Karya &amp; Perkembangan Budi')
        self.assertContains(r, 'Belum ada karya kreasi atau catatan dari guru.')

    def test_draf_otomatis_tidak_pernah_tampil(self):
        self.buat_karya(skor={KEB: 4, MOT: 3, LIS: 3})           # narasi otomatis bisa dibuat, tapi belum disimpan guru
        r = self.dashboard(self.ortu_a)
        self.assertNotContains(r, 'Catatan guru ·')
        self.assertNotContains(r, 'telah menyelesaikan')
        self.assertNotContains(r, 'Draft')
        CatatanRapor.objects.create(ruang_kerja=self.ruang, siswa=self.s_a, catatan='   ', catatan_disiplin='')
        self.assertNotContains(self.dashboard(self.ortu_a), 'Catatan guru ·')

    def test_karya_belum_dinilai(self):
        self.buat_karya()
        self.assertContains(self.dashboard(self.ortu_a), 'Belum dinilai oleh guru.')

    def test_dimensi_nonaktif_tidak_tampil(self):
        self.buat_karya(skor={KEB: 3, MOT: 4})
        DimensiPenilaian.objects.filter(kode=MOT).update(aktif=False)
        r = self.dashboard(self.ortu_a)
        self.assertNotContains(r, 'Motorik Halus')
        self.assertContains(r, 'Keberanian Berekspresi')

    def _bagian_karya(self, response):
        """Isi bagian "Karya & Perkembangan" saja. Bagian Tugas memuat SEMUA judul tugas tanpa
        batas (parent perlu tahu status semua tugas), sedangkan Karya (detail lengkap: foto,
        refleksi, skor) sengaja dibatasi 5 terbaru -- keduanya diuji terpisah, jangan dicampur."""
        html = response.content.decode()
        awal = html.index('Karya &amp; Perkembangan')
        akhir = html.index('id="portofolio-anak"')
        return html[awal:akhir]

    def test_batas_karya_dan_tampilkan_semua(self):
        for i in range(1, 8):
            self.buat_karya(judul=f'Proyek nomor {i}', hari=i)
        r = self.dashboard(self.ortu_a)
        bagian = self._bagian_karya(r)
        for i in range(3, 8):
            self.assertIn(f'Proyek nomor {i}', bagian)
        for i in (1, 2):
            self.assertNotIn(f'Proyek nomor {i}', bagian)
        self.assertContains(r, 'Tampilkan semua karya (7)')
        r = self.client.get(reverse('accounts:dashboard_orangtua') + '?semua_karya=1')
        self.assertEqual(r.status_code, 200)                       # middleware tetap mengizinkan (path sama)
        for i in range(1, 8):
            self.assertContains(r, f'Proyek nomor {i}')
        self.assertContains(r, 'Tampilkan karya terbaru saja')
        self.assertNotContains(r, 'Tampilkan semua karya')

    def test_beberapa_ruang_dikelompokkan_terbaru_dulu(self):
        smp = RuangKerja.objects.create(mapel='Prakarya', kelas='VIII B', guru=self.guru)
        self.buat_karya(judul='Karya seni lama', hari=1)
        self.buat_karya(judul='Karya prakarya baru', ruang=smp, emoji='', hari=5)
        html = self.dashboard(self.ortu_a).content.decode()
        # Dibatasi ke bagian "Karya & Perkembangan" saja: bagian Tugas juga memuat judul yang sama,
        # tapi hanya utk ruang yang anak-nya terdaftar sebagai anggota (buat_karya tidak mendaftarkan
        # keanggotaan utk `ruang` kustom), jadi urutannya bisa beda dan bukan itu yang diuji di sini.
        awal = html.index('Karya &amp; Perkembangan')
        bagian_karya = html[awal:]
        # Penanda dipilih dari judul karya, bukan nama mapel: 'Seni' ikut cocok dengan 'Senin' di header tanggal.
        self.assertLess(bagian_karya.index('Karya prakarya baru'), bagian_karya.index('Karya seni lama'))

    def test_catatan_tanpa_karya_tetap_tampil_per_ruang(self):
        lain = RuangKerja.objects.create(mapel='Bahasa', kelas='3', guru=self.guru)
        CatatanRapor.objects.create(ruang_kerja=lain, siswa=self.s_a, catatan_disiplin='Rajin mengumpulkan tugas.')
        r = self.dashboard(self.ortu_a)
        self.assertContains(r, 'Catatan guru · Bahasa')
        self.assertContains(r, 'Disiplin &amp; Kebiasaan Belajar')
        self.assertContains(r, 'Rajin mengumpulkan tugas.')

    def test_tautan_dari_siswa_diberi_catatan_dan_rel_aman(self):
        self.buat_karya(link='https://www.canva.com/design/abc')
        r = self.dashboard(self.ortu_a)
        self.assertContains(r, 'rel="noopener noreferrer nofollow"')
        self.assertContains(r, 'Buka dengan hati-hati')
        LampiranKarya.objects.filter(tipe='link').delete()
        self.assertNotContains(self.dashboard(self.ortu_a), 'Buka dengan hati-hati')

    def test_isi_dari_siswa_tidak_dieksekusi(self):
        smp = RuangKerja.objects.create(mapel='Prakarya', kelas='VIII B', guru=self.guru)
        sub = self.buat_karya(ruang=smp, emoji='', ringkasan='<img src=x onerror=alert(1)>')
        RefleksiKarya.objects.create(submisi=sub, tipe='matriks',
                                     jawaban={'kekuatan': {'skor': 3, 'alasan': '<script>alert(1)</script>'}})
        LampiranKarya.objects.filter(submisi=sub).update(nama_asli='<b>foto</b>.png')
        html = self.dashboard(self.ortu_a).content.decode()
        for mentah in ['<img src=x onerror', '<script>alert(1)</script>']:
            self.assertNotIn(mentah, html)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html)
        self.assertIn('&lt;img src=x onerror=alert(1)&gt;', html)

    def test_berkas_dari_dashboard_hanya_terbuka_untuk_yang_berhak(self):
        self.buat_karya()
        html = self.dashboard(self.ortu_a).content.decode()
        url = re.search(r'src="(/kreasi/media/lampiran/\d+/)"', html).group(1)
        self.assertEqual(self.client.get(url).status_code, 200)          # orang tua anak itu
        self.client.force_login(self.ortu_b)
        self.assertEqual(self.client.get(url).status_code, 403)          # orang tua anak lain
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)          # belum login


class AksesDanTagTest(DasarOrangTua):
    def test_hanya_orang_tua_yang_terhubung_ke_anak(self):
        from django.contrib.auth.models import AnonymousUser
        tanpa_anak = User.objects.create_user('ortu_kosong', password='x', role='orangtua')
        for u in [self.guru, self.u_a, AnonymousUser(), tanpa_anak, None]:
            self.assertIsNone(ringkasan_untuk_orangtua(u), str(u))
        self.assertEqual(ringkasan_untuk_orangtua(self.ortu_a)['siswa'], self.s_a)

    def render_tag(self, user, konteks_tambahan=None):
        req = RequestFactory().get('/akun/dashboard-orangtua/')
        req.user = user
        return Template('{% load kreasi_tags %}{% karya_anak %}').render(Context({'request': req, **(konteks_tambahan or {})}))

    def test_tag_kosong_untuk_selain_orang_tua(self):
        self.buat_karya()
        for u in [self.guru, self.u_a]:
            self.assertEqual(self.render_tag(u).strip(), '')

    def test_tag_mengabaikan_variabel_siswa_di_konteks(self):
        self.buat_karya(judul='Milik Ani saja')
        keluar = self.render_tag(self.ortu_b, {'siswa': self.s_a, 'anak': self.s_a})
        self.assertNotIn('Milik Ani saja', keluar)
        self.assertIn('Perkembangan Budi', keluar)

    def test_jumlah_query_tidak_tumbuh_dengan_jumlah_karya(self):
        def hitung():
            with CaptureQueriesContext(connection) as q:
                ringkasan_untuk_orangtua(self.ortu_a, semua=True)
            return len(q)
        self.buat_karya(skor={KEB: 3, MOT: 4})
        satu = hitung()
        for i in range(6):
            self.buat_karya(skor={KEB: 2, MOT: 3, LIS: 4})
        self.assertEqual(hitung(), satu, 'query tidak boleh bertambah per karya (N+1)')
        self.assertLessEqual(satu, 8)

    def test_batas_karya_default(self):
        for i in range(BATAS_KARYA + 2):
            self.buat_karya(judul=f'Judul {i}')
        b = ringkasan_untuk_orangtua(self.ortu_a)
        self.assertEqual((b['ditampilkan'], b['total_karya'], b['ada_lebih']), (BATAS_KARYA, BATAS_KARYA + 2, True))
        self.assertEqual(ringkasan_untuk_orangtua(self.ortu_a, semua=True)['ditampilkan'], BATAS_KARYA + 2)
