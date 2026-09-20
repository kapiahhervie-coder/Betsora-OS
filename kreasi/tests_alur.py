"""Uji alur lengkap Tugas Kreasi lewat rute asli aplikasi (detail_tugas), bukan memanggil fungsi kreasi langsung."""
import os
import shutil
import tempfile
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Siswa, User
from ruang_kerja.models import AnggotaRuangKerja, RuangKerja, SubmisiTugas, Tugas

from .models import DimensiPenilaian, LampiranKarya, RefleksiKarya, SkorDimensi

PNG = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
       b'\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa7\x9a\xa0\xa0\x00\x00\x00\x00IEND\xaeB`\x82')
SUARA = b'\x1a\x45\xdf\xa3' + b'\x00' * 500  # kepala EBML/webm palsu, cukup untuk uji unggah


def foto(nama='maket.png', isi=PNG):
    return SimpleUploadedFile(nama, isi, content_type='image/png')


def suara(nama='rekaman.webm'):
    return SimpleUploadedFile(nama, SUARA, content_type='audio/webm')


def berkas_di_disk(root):
    return [os.path.join(r, f) for r, _, fs in os.walk(root) for f in fs]


class DasarKreasi(TestCase):
    kelas_ruang = 'Kelas III'
    tingkat_siswa = '3'

    @classmethod
    def setUpTestData(cls):
        call_command('seed_kreasi', verbosity=0)
        cls.guru = User.objects.create_user('guru1', password='x', role='guru')
        cls.guru_lain = User.objects.create_user('guru2', password='x', role='guru')
        cls.u_a = User.objects.create_user('siswa_a', password='x', role='siswa')
        cls.u_b = User.objects.create_user('siswa_b', password='x', role='siswa')
        cls.s_a = Siswa.objects.create(user=cls.u_a, nama='Ani Lestari', nis='1', kelas=cls.tingkat_siswa)
        cls.s_b = Siswa.objects.create(user=cls.u_b, nama='Budi Santoso', nis='2', kelas=cls.tingkat_siswa)
        cls.ortu_a = User.objects.create_user('ortu_a', password='x', role='orangtua', anak=cls.s_a)
        cls.ortu_b = User.objects.create_user('ortu_b', password='x', role='orangtua', anak=cls.s_b)
        cls.ruang = RuangKerja.objects.create(mapel='Seni', kelas=cls.kelas_ruang, guru=cls.guru)
        AnggotaRuangKerja.objects.create(ruang_kerja=cls.ruang, siswa=cls.s_a)
        AnggotaRuangKerja.objects.create(ruang_kerja=cls.ruang, siswa=cls.s_b)
        cls.tugas = Tugas.objects.create(ruang_kerja=cls.ruang, jenis='kreasi', judul='Maket rumahku', instruksi='Buat maket.')

    def setUp(self):
        # folder penyimpanan privat terpisah untuk setiap tes, agar berkas tidak saling mengotori
        self.tmp = tempfile.mkdtemp()
        pengaturan = override_settings(PRIVATE_MEDIA_ROOT=self.tmp)
        pengaturan.enable()
        self.addCleanup(pengaturan.disable)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def disk(self):
        return berkas_di_disk(self.tmp)

    def url(self):
        return reverse('ruang_kerja:detail_tugas', args=[self.tugas.id])

    def masuk(self, user):
        self.client.logout()
        self.client.force_login(user)


class SiswaSDAwalTest(DasarKreasi):
    def data_valid(self, **tambahan):
        d = {'lampiran_foto': [foto()], 'lampiran_audio': suara(), 'refleksi_emoji': 'bangga',
             'refleksi_audio': suara('refleksi.webm')}
        d.update(tambahan)
        return d

    def test_form_sesuai_jenjang(self):
        self.masuk(self.u_a)
        r = self.client.get(self.url())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Foto karya')
        self.assertContains(r, 'data-rekam')            # perekam suara ada
        self.assertContains(r, 'name="refleksi_emoji"')  # pilihan emoji
        self.assertNotContains(r, 'name="lampiran_link"')  # SD awal tidak pakai tautan
        self.assertNotContains(r, 'name="lampiran_video"')

    def test_kumpul_berhasil_dan_tampil(self):
        self.masuk(self.u_a)
        r = self.client.post(self.url(), self.data_valid())
        self.assertEqual(r.status_code, 302)
        sub = SubmisiTugas.objects.get(tugas=self.tugas, siswa=self.s_a)
        self.assertEqual(sorted(sub.lampiran_karya.values_list('tipe', flat=True)), ['audio', 'foto'])
        self.assertEqual(sub.refleksi_karya.emoji, 'bangga')
        self.assertTrue(sub.refleksi_karya.audio)
        self.assertEqual(len(self.disk()), 3)
        # berkas ada di penyimpanan privat, bukan di MEDIA_ROOT
        for p in self.disk():
            self.assertTrue(p.startswith(self.tmp))
        # halaman hasil
        r = self.client.get(self.url())
        self.assertContains(r, 'Sudah dikumpulkan')
        foto_l = sub.lampiran_karya.get(tipe='foto')
        self.assertContains(r, f'src="{foto_l.url_akses}"')
        self.assertContains(r, 'Merasa bangga')
        # dan siswa bisa membuka fotonya sendiri, siswa lain tidak
        self.assertEqual(self.client.get(foto_l.url_akses).status_code, 200)
        self.masuk(self.u_b)
        self.assertEqual(self.client.get(foto_l.url_akses).status_code, 403)

    def test_foto_wajib(self):
        self.masuk(self.u_a)
        r = self.client.post(self.url(), {'lampiran_audio': suara(), 'refleksi_emoji': 'senang'})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'harus menyertakan foto karya')
        self.assertFalse(SubmisiTugas.objects.exists())
        self.assertEqual(self.disk(), [])

    def test_emoji_wajib_dan_harus_valid(self):
        self.masuk(self.u_a)
        for nilai in [None, 'marah', '<script>']:
            d = {'lampiran_foto': [foto()], 'lampiran_audio': suara()}
            if nilai: d['refleksi_emoji'] = nilai
            r = self.client.post(self.url(), d)
            self.assertContains(r, 'Pilih dulu perasaanmu')
        self.assertFalse(SubmisiTugas.objects.exists())

    def test_audio_refleksi_opsional(self):
        self.masuk(self.u_a)
        r = self.client.post(self.url(), {'lampiran_foto': [foto()], 'lampiran_audio': suara(), 'refleksi_emoji': 'sulit'})
        self.assertEqual(r.status_code, 302)
        self.assertFalse(SubmisiTugas.objects.get().refleksi_karya.audio)

    def test_berkas_berbahaya_ditolak_dan_tidak_meninggalkan_sisa(self):
        self.masuk(self.u_a)
        for nama, tipe in [('jahat.html', 'foto'), ('virus.exe', 'foto'), ('x.svg', 'foto'), ('foto.png', 'audio')]:
            d = self.data_valid()
            if tipe == 'foto':
                d['lampiran_foto'] = [foto(nama, b'<script>alert(1)</script>')]
            else:
                d['lampiran_audio'] = SimpleUploadedFile(nama, PNG)
            r = self.client.post(self.url(), d)
            self.assertEqual(r.status_code, 200, nama)
            self.assertContains(r, 'bukan jenis', msg_prefix=nama)
        self.assertFalse(SubmisiTugas.objects.exists())
        self.assertEqual(self.disk(), [])

    def test_berkas_kosong_dan_terlalu_besar(self):
        self.masuk(self.u_a)
        r = self.client.post(self.url(), self.data_valid(lampiran_foto=[foto('a.png', b'')]))
        self.assertContains(r, 'kosong')
        with mock.patch.dict('kreasi.layanan.MAKS_UKURAN_MB', {'foto': 0}):
            r = self.client.post(self.url(), self.data_valid())
            self.assertContains(r, 'terlalu besar')
        self.assertFalse(SubmisiTugas.objects.exists())

    def test_gagal_di_tengah_menghapus_berkas_dan_rollback(self):
        self.masuk(self.u_a)
        with mock.patch('kreasi.layanan.RefleksiKarya.objects.create', side_effect=RuntimeError('boom')):
            with self.assertRaises(RuntimeError):
                self.client.post(self.url(), self.data_valid())
        self.assertFalse(SubmisiTugas.objects.exists())
        self.assertFalse(LampiranKarya.objects.exists())
        self.assertEqual(self.disk(), [], 'berkas yatim harus dibersihkan')

    def test_kirim_dua_kali_tidak_menggandakan(self):
        self.masuk(self.u_a)
        self.client.post(self.url(), self.data_valid())
        r = self.client.post(self.url(), self.data_valid(lampiran_foto=[foto('lagi.png')]))
        self.assertEqual(SubmisiTugas.objects.filter(siswa=self.s_a).count(), 1)
        self.assertEqual(LampiranKarya.objects.count(), 2)


class SMPTest(DasarKreasi):
    kelas_ruang = 'VIII B'
    tingkat_siswa = '8'

    def dasar(self, **t):
        d = {'lampiran_dokumen': [SimpleUploadedFile('laporan.pdf', b'%PDF-1.4 x')], 'ringkasan': 'Solusi limbah sekolah.'}
        for k in ('kekuatan', 'perbaikan', 'relevansi'):
            d[f'refleksi_{k}_skor'] = '3'
            d[f'refleksi_{k}_alasan'] = f'alasan {k}'
        d.update(t)
        return d

    def test_jenjang_terdeteksi_dari_romawi(self):
        self.assertEqual(self.ruang.get_jenjang(), 'smp')
        self.masuk(self.u_a)
        r = self.client.get(self.url())
        self.assertContains(r, 'name="lampiran_link"')
        self.assertContains(r, 'refleksi_kekuatan_skor')

    def test_kumpul_dengan_tautan_dan_matriks(self):
        self.masuk(self.u_a)
        r = self.client.post(self.url(), self.dasar(lampiran_link=['https://www.canva.com/design/abc', '']))
        self.assertEqual(r.status_code, 302)
        sub = SubmisiTugas.objects.get()
        self.assertEqual(sub.teks_jawaban, 'Solusi limbah sekolah.')
        self.assertEqual(sub.lampiran_karya.get(tipe='link').url, 'https://www.canva.com/design/abc')
        self.assertEqual(sub.refleksi_karya.jawaban['relevansi'], {'skor': 3, 'alasan': 'alasan relevansi'})
        r = self.client.get(self.url())
        self.assertContains(r, 'rel="noopener noreferrer nofollow"')
        self.assertContains(r, 'Relevansi dengan kehidupan nyata')

    def test_tautan_berbahaya_ditolak(self):
        self.masuk(self.u_a)
        for u in ['javascript:alert(1)', 'ftp://x.com/a', 'data:text/html,<b>', 'bukan url']:
            r = self.client.post(self.url(), self.dasar(lampiran_link=[u]))
            self.assertContains(r, 'Tautan tidak valid', msg_prefix=u)
        self.assertFalse(SubmisiTugas.objects.exists())

    def test_ringkasan_wajib_dan_skor_matriks_valid(self):
        self.masuk(self.u_a)
        r = self.client.post(self.url(), self.dasar(ringkasan=''))
        self.assertContains(r, 'Tulis rangkuman')
        r = self.client.post(self.url(), self.dasar(refleksi_kekuatan_skor='9'))
        self.assertContains(r, 'Beri nilai 1-4')
        self.assertFalse(SubmisiTugas.objects.exists())


class SDAkhirTest(DasarKreasi):
    kelas_ruang = '5'
    tingkat_siswa = '5'

    def test_refleksi_teks_terbimbing_wajib(self):
        self.masuk(self.u_a)
        r = self.client.post(self.url(), {'lampiran_foto': [foto()]})
        self.assertContains(r, 'Apa bagian tersulit')
        d = {'lampiran_foto': [foto()]}
        d.update({'refleksi_dibuat': 'Poster', 'refleksi_kesulitan': 'Mewarnai', 'refleksi_perbaikan': 'Lebih rapi'})
        self.assertEqual(self.client.post(self.url(), d).status_code, 302)
        self.assertEqual(SubmisiTugas.objects.get().refleksi_karya.jawaban['kesulitan'], 'Mewarnai')


class GuruTest(DasarKreasi):
    def kumpul(self):
        self.masuk(self.u_a)
        self.client.post(self.url(), {'lampiran_foto': [foto()], 'lampiran_audio': suara(), 'refleksi_emoji': 'bangga'})
        return SubmisiTugas.objects.get(siswa=self.s_a)

    def test_daftar_karya(self):
        sub = self.kumpul()
        self.masuk(self.guru)
        r = self.client.get(self.url())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Ani Lestari')
        self.assertContains(r, 'Belum dinilai')
        self.assertContains(r, 'Budi Santoso')     # daftar belum mengumpulkan
        self.assertContains(r, reverse('kreasi:nilai_karya', args=[sub.id]))

    def test_halaman_nilai_menampilkan_karya_dan_rubrik(self):
        sub = self.kumpul()
        self.masuk(self.guru)
        r = self.client.get(reverse('kreasi:nilai_karya', args=[sub.id]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Keberanian Berekspresi')
        self.assertContains(r, 'Ani masih perlu ditemani')   # deskriptor dengan nama depan
        self.assertContains(r, sub.lampiran_karya.get(tipe='foto').url_akses)
        self.assertEqual(r.content.decode().count('type="radio"'), 3 * 4)

    def test_simpan_penilaian_dan_tampil_ke_siswa(self):
        sub = self.kumpul()
        dims = list(DimensiPenilaian.objects.filter(jenjang='sd_awal', aktif=True))
        self.masuk(self.guru)
        data = {f'level_{d.id}': str(i + 2) for i, d in enumerate(dims)}   # 2,3,4
        data['catatan_%d' % dims[0].id] = 'Sudah berani maju'
        data['feedback'] = 'Hebat, Ani!'
        r = self.client.post(reverse('kreasi:nilai_karya', args=[sub.id]), data)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(SkorDimensi.objects.filter(submisi=sub).count(), 3)
        sub.refresh_from_db()
        self.assertEqual(sub.feedback, 'Hebat, Ani!')
        self.assertIsNotNone(sub.dinilai_pada)
        self.assertIsNone(sub.nilai)               # rubrik tidak mengisi nilai angka
        # daftar guru: sudah dinilai
        self.assertContains(self.client.get(self.url()), 'Sudah dinilai')
        # siswa melihat hasil dengan kalimat deskriptor
        self.masuk(self.u_a)
        r = self.client.get(self.url())
        self.assertContains(r, 'Penilaian gurumu')
        self.assertContains(r, 'Hebat, Ani!')
        self.assertContains(r, 'Cakap (3/4)')
        self.assertContains(r, 'Sudah berani maju')
        # ulang: ubah level, tidak menggandakan
        self.masuk(self.guru)
        data[f'level_{dims[0].id}'] = '4'
        self.client.post(reverse('kreasi:nilai_karya', args=[sub.id]), data)
        self.assertEqual(SkorDimensi.objects.filter(submisi=sub).count(), 3)
        self.assertEqual(SkorDimensi.objects.get(submisi=sub, dimensi=dims[0]).level, 4)

    def test_level_tidak_valid_ditolak(self):
        sub = self.kumpul()
        d = DimensiPenilaian.objects.filter(jenjang='sd_awal').first()
        self.masuk(self.guru)
        r = self.client.post(reverse('kreasi:nilai_karya', args=[sub.id]), {f'level_{d.id}': '7'})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'tidak valid')
        self.assertFalse(SkorDimensi.objects.exists())

    def test_hak_akses_penilaian(self):
        sub = self.kumpul()
        d = DimensiPenilaian.objects.filter(jenjang='sd_awal').first()
        url = reverse('kreasi:nilai_karya', args=[sub.id])
        for user in [self.guru_lain, self.u_a, self.u_b]:
            self.masuk(user)
            self.assertEqual(self.client.get(url).status_code, 302, user.username)
            self.assertEqual(self.client.post(url, {f'level_{d.id}': '4'}).status_code, 302, user.username)
        self.assertFalse(SkorDimensi.objects.exists())
        # guru lain juga tidak boleh melihat daftar karya lewat halaman tugas
        self.masuk(self.guru_lain)
        r = self.client.get(self.url())
        self.assertEqual(r.status_code, 302)

    def test_dimensi_nonaktif_tidak_muncul(self):
        sub = self.kumpul()
        DimensiPenilaian.objects.filter(jenjang='sd_awal', kode='motorik_halus').update(aktif=False)
        self.masuk(self.guru)
        r = self.client.get(reverse('kreasi:nilai_karya', args=[sub.id]))
        self.assertNotContains(r, 'Motorik Halus')
        self.assertEqual(r.content.decode().count('type="radio"'), 2 * 4)


class JenjangBelumDiaturTest(DasarKreasi):
    kelas_ruang = 'Kursus Coding'

    def test_siswa_diberi_penjelasan_guru_bisa_mengatur(self):
        self.assertIsNone(self.ruang.get_jenjang())
        self.masuk(self.u_a)
        self.assertContains(self.client.get(self.url()), 'Guru belum mengatur jenjang')
        self.masuk(self.guru)
        r = self.client.get(self.url())
        self.assertContains(r, 'Jenjang kelas belum diketahui')
        self.assertContains(r, reverse('kreasi:atur_jenjang', args=[self.ruang.id]))
        # guru lain & siswa tidak bisa mengatur
        for u in [self.guru_lain, self.u_a]:
            self.masuk(u)
            self.client.post(reverse('kreasi:atur_jenjang', args=[self.ruang.id]), {'jenjang': 'smp'})
            self.ruang.refresh_from_db()
            self.assertEqual(self.ruang.jenjang, '')
        self.masuk(self.guru)
        self.client.post(reverse('kreasi:atur_jenjang', args=[self.ruang.id]), {'jenjang': 'ngawur'})
        self.ruang.refresh_from_db(); self.assertEqual(self.ruang.jenjang, '')
        r = self.client.post(reverse('kreasi:atur_jenjang', args=[self.ruang.id]), {'jenjang': 'smp', 'tugas_id': self.tugas.id})
        self.assertRedirects(r, self.url(), fetch_redirect_response=False)
        self.ruang.refresh_from_db(); self.assertEqual(self.ruang.jenjang, 'smp')


class OrangTuaDanMiddlewareTest(DasarKreasi):
    def test_orang_tua_hanya_anaknya_lewat_middleware_asli(self):
        self.masuk(self.u_a)
        self.client.post(self.url(), {'lampiran_foto': [foto()], 'lampiran_audio': suara(), 'refleksi_emoji': 'senang'})
        f = LampiranKarya.objects.get(tipe='foto')
        self.masuk(self.ortu_a)
        self.assertEqual(self.client.get(f.url_akses).status_code, 200)   # anaknya sendiri
        self.masuk(self.ortu_b)
        self.assertEqual(self.client.get(f.url_akses).status_code, 403)   # anak orang lain
        # halaman guru/tugas tetap tertutup bagi orang tua (middleware mengalihkan ke dashboard)
        r = self.client.get(self.url())
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r['Location'], reverse('accounts:dashboard_orangtua'))



class EsaiRegresiTest(DasarKreasi):
    """Tugas esai lama (template asli) harus tetap bekerja persis seperti sebelumnya."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.esai = Tugas.objects.create(ruang_kerja=cls.ruang, jenis='esai', judul='Esai lama', instruksi='Tulis esai.')

    def test_siswa_kumpul_dan_guru_melihat(self):
        url = reverse('ruang_kerja:detail_tugas', args=[self.esai.id])
        self.masuk(self.u_a)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Kumpulkan Jawaban')            # form esai asli, bukan form kreasi
        self.assertNotContains(r, 'data-rekam')
        r = self.client.post(url, {'teks_jawaban': 'Jawaban saya'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(SubmisiTugas.objects.get(tugas=self.esai).teks_jawaban, 'Jawaban saya')
        self.masuk(self.guru)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Daftar Submisi Siswa')          # halaman guru asli
        self.assertContains(r, 'Jawaban saya')


class KirimLatarBelakangTest(DasarKreasi):
    """Pengiriman via XHR: galat dikirim sebagai JSON, halaman (dan isian di browser) tidak dimuat ulang."""

    def kirim(self, data):
        return self.client.post(self.url(), data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def test_galat_dijawab_json_dan_tidak_menyimpan(self):
        self.masuk(self.u_a)
        r = self.kirim({'refleksi_emoji': 'senang'})           # foto & suara belum ada
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r['Content-Type'], 'application/json')
        galat = r.json()['galat']
        self.assertFalse(r.json()['ok'])
        self.assertIn('Karya harus menyertakan foto karya.', galat)
        self.assertIn('Karya harus menyertakan rekaman suara.', galat)
        self.assertFalse(SubmisiTugas.objects.exists())
        self.assertEqual(self.disk(), [])

    def test_sukses_dijawab_json(self):
        self.masuk(self.u_a)
        r = self.kirim({'lampiran_foto': [foto()], 'lampiran_audio': suara(), 'refleksi_emoji': 'bangga'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {'ok': True, 'url': self.url()})
        self.assertEqual(SubmisiTugas.objects.count(), 1)

    def test_kirim_ulang_setelah_sukses_diarahkan_ke_hasil(self):
        self.masuk(self.u_a)
        data = lambda: {'lampiran_foto': [foto()], 'lampiran_audio': suara(), 'refleksi_emoji': 'bangga'}
        self.kirim(data())
        r = self.kirim(data())                                   # klik ganda / kirim ulang
        self.assertEqual(r.json(), {'ok': True, 'url': self.url()})
        self.assertEqual(SubmisiTugas.objects.count(), 1)
        self.assertEqual(LampiranKarya.objects.count(), 2)

    def test_form_menandai_kolom_wajib_untuk_pemeriksaan_di_browser(self):
        self.masuk(self.u_a)
        html = self.client.get(self.url()).content.decode()
        self.assertIn('data-wajib="1"', html)
        self.assertIn('data-label="Foto karya"', html)
        self.assertIn('data-label="Rekaman suara"', html)
        self.assertIn('id="kotak-galat"', html)

    def test_pesan_galat_tidak_membuka_celah_html(self):
        # nama berkas yang berisi tag HTML tidak boleh muncul mentah di halaman non-JS
        self.masuk(self.u_a)
        r = self.client.post(self.url(), {'lampiran_foto': [foto('<img src=x onerror=alert(1)>.png', b'')],
                                          'lampiran_audio': suara(), 'refleksi_emoji': 'senang'})
        self.assertNotContains(r, '<img src=x onerror=alert(1)>')
