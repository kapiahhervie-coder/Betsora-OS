"""Tes penyekatan antar sekolah (Tahap 2).

Dua sekolah uji (A dan B) berisi data yang sama bentuknya. Aturan yang diuji: akun sekolah A tidak
dapat melihat, mengubah, menghapus, atau merujuk data sekolah B, lewat ORM maupun lewat alamat web.
Objek sekolah lain tampil sebagai "tidak ada" (404 / daftar kosong), bukan sebagai "dilarang".
"""
from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import models
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.test import RequestFactory, TestCase

from accounts.models import Sekolah, Siswa
from accounts.tenancy import (
    BEBAS, TOLAK, LintasSekolah, SekolahManagerMixin, dalam_sekolah, sekolah_aktif, username_unik,
)
from kelas.models import Absensi
from penilaian.models import Nilai, SesiPenilaian
from pesan.models import Percakapan
from ruang_kerja.models import AnggotaRuangKerja, Kelas, PesanChat, RuangKerja, Tugas

User = get_user_model()

APP_PROYEK = {
    'accounts', 'kelas', 'kreasi', 'kuis', 'misi', 'pengaturan', 'penilaian',
    'perpustakaan', 'pesan', 'portofolio', 'ruang_kerja',
}
# Sengaja global. Menambah model baru? Beri `objects = SekolahManager(...)` atau tambahkan ke sini
# DENGAN alasan tertulis.
KECUALI = {
    'accounts.Sekolah': 'daftar sekolah itu sendiri',
    'pengaturan.PengaturanSekolah': 'diatur per sekolah pada Tahap 4',
    'misi.Misi': 'katalog misi bersama',
    'kreasi.DimensiPenilaian': 'rubrik bersama',
    'kreasi.DeskriptorLevel': 'rubrik bersama',
}


def _buat_sekolah(nama, kode):
    s = Sekolah.objects.create(nama=nama, kode=kode)
    guru = User.objects.create_user(f'guru-{kode}', password='x', role='guru', first_name=f'Guru {nama}', sekolah=s)
    siswa = Siswa.objects.create(nama=f'Siswa {nama}', nis='001', kelas='4', sekolah=s)
    akun = User.objects.create_user(f'siswa-{kode}', password='x', role='siswa', sekolah=s)
    siswa.user = akun
    siswa.save()
    kelas = Kelas.objects.create(nama='4', sekolah=s)
    ruang = RuangKerja.objects.create(mapel=f'Mapel {nama}', kelas='4', guru=guru, sekolah=s, kelas_baru=kelas)
    tugas = Tugas.objects.create(ruang_kerja=ruang, judul=f'Tugas {nama}', instruksi='x')
    anggota = AnggotaRuangKerja.objects.create(ruang_kerja=ruang, siswa=siswa)
    absen = Absensi.objects.create(siswa=siswa, status='hadir')
    sesi = SesiPenilaian.objects.create(mapel='IPA', jenis='formatif', topik=f'Topik {nama}', kelas='4', guru=guru, sekolah=s)
    nilai = Nilai.objects.create(sesi=sesi, siswa=siswa, skor=80)
    return {'sekolah': s, 'guru': guru, 'siswa': siswa, 'akun': akun, 'kelas': kelas, 'ruang': ruang,
            'tugas': tugas, 'anggota': anggota, 'absen': absen, 'sesi': sesi, 'nilai': nilai}


class DuaSekolah(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a = _buat_sekolah('Alfa', 'alfa')
        cls.b = _buat_sekolah('Beta', 'beta')


# ---------------------------------------------------------------------------------------------
# Struktur: tidak boleh ada model yang terlewat
# ---------------------------------------------------------------------------------------------

class StrukturTest(TestCase):
    def _model_proyek(self):
        return [m for m in apps.get_models() if m._meta.app_label in APP_PROYEK]

    def test_setiap_model_dijaga_atau_dikecualikan_dengan_sengaja(self):
        belum = []
        for m in self._model_proyek():
            nama = f'{m._meta.app_label}.{m.__name__}'
            dijaga = isinstance(m._default_manager, SekolahManagerMixin)
            if not dijaga and nama not in KECUALI:
                belum.append(nama)
            if dijaga and nama in KECUALI:
                belum.append(f'{nama} (dijaga tetapi tercantum di KECUALI)')
        self.assertEqual(belum, [], 'Model tanpa penyaring sekolah: %s' % belum)

    def test_semua_jalur_berujung_ke_kolom_sekolah(self):
        for m in self._model_proyek():
            mgr = m._default_manager
            if not isinstance(mgr, SekolahManagerMixin):
                continue
            for jalur in mgr.jalur:
                model, f = m, None
                for bagian in jalur.split('__'):
                    f = model._meta.get_field(bagian)
                    if bagian != 'sekolah':
                        self.assertTrue(f.is_relation and not f.many_to_many, f'{m.__name__}: {jalur}')
                        model = f.related_model
                self.assertEqual(f.name, 'sekolah', f'{m.__name__}: {jalur}')
                self.assertIs(f.related_model, Sekolah, f'{m.__name__}: {jalur}')
            with dalam_sekolah(1):  # query benar-benar dijalankan
                list(m.objects.all()[:1])

    def test_manajer_tidak_memicu_migrasi_baru(self):
        """SekolahUserManager mendaftar ke migrasi sebagai UserManager biasa, jadi tidak ada migrasi baru."""
        from django.core.management import call_command
        try:
            call_command('makemigrations', 'accounts', 'ruang_kerja', check=True, dry_run=True, verbosity=0)
        except SystemExit:
            self.fail('Ada migrasi tertunda untuk accounts/ruang_kerja: jalankan makemigrations dan periksa isinya.')

    def test_model_tanpa_kolom_sekolah_tidak_ditandai_langsung(self):
        # Model dengan jalur 'sekolah' harus benar-benar punya kolom itu.
        for m in self._model_proyek():
            mgr = m._default_manager
            if isinstance(mgr, SekolahManagerMixin) and mgr.jalur == ('sekolah',):
                self.assertTrue(any(f.name == 'sekolah' for f in m._meta.fields), m.__name__)


# ---------------------------------------------------------------------------------------------
# Lapisan ORM
# ---------------------------------------------------------------------------------------------

class ManajerTest(DuaSekolah):
    def test_bebas_melihat_semuanya(self):
        self.assertIs(sekolah_aktif(), BEBAS)
        self.assertEqual(Siswa.objects.count(), 2)

    def test_hanya_data_sekolah_sendiri(self):
        with dalam_sekolah(self.a['sekolah']):
            self.assertEqual(list(Siswa.objects.all()), [self.a['siswa']])
            self.assertEqual(list(Kelas.objects.all()), [self.a['kelas']])
            self.assertEqual(list(RuangKerja.objects.all()), [self.a['ruang']])
            self.assertEqual(list(Tugas.objects.all()), [self.a['tugas']])
            self.assertEqual(list(AnggotaRuangKerja.objects.all()), [self.a['anggota']])
            self.assertEqual(list(Absensi.objects.all()), [self.a['absen']])
            self.assertEqual(list(SesiPenilaian.objects.all()), [self.a['sesi']])
            self.assertEqual(list(Nilai.objects.all()), [self.a['nilai']])
            self.assertEqual(set(User.objects.all()), {self.a['guru'], self.a['akun']})

    def test_hanya_data_sekolah_sendiri_untuk_sekolah_lain(self):
        with dalam_sekolah(self.b['sekolah']):
            self.assertEqual(list(Siswa.objects.all()), [self.b['siswa']])
            self.assertEqual(list(Tugas.objects.all()), [self.b['tugas']])

    def test_objek_sekolah_lain_tidak_ditemukan_lewat_id(self):
        with dalam_sekolah(self.a['sekolah']):
            for model, objek in [(RuangKerja, self.b['ruang']), (Tugas, self.b['tugas']), (Siswa, self.b['siswa']),
                                 (AnggotaRuangKerja, self.b['anggota']), (Nilai, self.b['nilai']),
                                 (User, self.b['guru']), (Absensi, self.b['absen'])]:
                with self.assertRaises(Http404, msg=model.__name__):
                    get_object_or_404(model, id=objek.id)

    def test_manajer_relasi_ikut_tersaring(self):
        with dalam_sekolah(self.a['sekolah']):
            # ruang milik B dimuat lewat manajer dasar (jalur ForeignKey tidak disaring), isinya tetap disaring
            ruang_b = RuangKerja._base_manager.get(pk=self.b['ruang'].pk)
            self.assertEqual(list(ruang_b.tugas.all()), [])
            self.assertEqual(ruang_b.anggota.count(), 0)
            self.assertEqual(list(self.a['ruang'].tugas.all()), [self.a['tugas']])
            self.assertEqual(self.a['siswa'].nilai.count(), 1)

    def test_update_dan_delete_massal_tidak_menyentuh_sekolah_lain(self):
        with dalam_sekolah(self.a['sekolah']):
            Tugas.objects.filter(id=self.b['tugas'].id).delete()
            Siswa.objects.filter(id=self.b['siswa'].id).update(nama='DIRETAS')
            Tugas.objects.all().delete()
        self.assertTrue(Tugas.objects.filter(id=self.b['tugas'].id).exists())
        self.assertFalse(Tugas.objects.filter(id=self.a['tugas'].id).exists())
        self.assertEqual(Siswa.objects.get(id=self.b['siswa'].id).nama, 'Siswa Beta')

    def test_akun_tanpa_sekolah_tidak_melihat_data_bersekolah(self):
        with dalam_sekolah(None):
            self.assertEqual(Siswa.objects.count(), 0)
            self.assertEqual(Tugas.objects.count(), 0)
            self.assertEqual(Absensi.objects.count(), 0)
            self.assertEqual(User.objects.count(), 0)

    def test_sekolah_nonaktif_tidak_melihat_apa_pun(self):
        with dalam_sekolah(TOLAK):
            self.assertEqual(Siswa.objects.count(), 0)
            self.assertEqual(Tugas.objects.count(), 0)

    def test_percakapan_hanya_dalam_satu_sekolah(self):
        with dalam_sekolah(self.a['sekolah']):
            User.objects.create_user('guru-alfa-2', password='x', role='guru')
            p = Percakapan.get_or_create_antara(self.a['guru'], self.a['akun'])
            self.assertEqual(list(Percakapan.objects.all()), [p])
        with dalam_sekolah(self.b['sekolah']):
            self.assertEqual(Percakapan.objects.count(), 0)

    def test_nonaktif_atau_bebas_tidak_bocor_antar_blok(self):
        with dalam_sekolah(self.a['sekolah']):
            with dalam_sekolah(self.b['sekolah']):
                self.assertEqual(Siswa.objects.get().nama, 'Siswa Beta')
            self.assertEqual(Siswa.objects.get().nama, 'Siswa Alfa')
        self.assertIs(sekolah_aktif(), BEBAS)


class PenulisanTest(DuaSekolah):
    def test_baris_baru_otomatis_diberi_sekolah_aktif(self):
        with dalam_sekolah(self.a['sekolah']):
            s = Siswa.objects.create(nama='Baru', nis='777', kelas='5')
            k = Kelas.objects.create(nama='5')
            u = User.objects.create_user('baru-a', password='x', role='guru')
        self.assertEqual(s.sekolah_id, self.a['sekolah'].id)
        self.assertEqual(k.sekolah_id, self.a['sekolah'].id)
        self.assertEqual(u.sekolah_id, self.a['sekolah'].id)

    def test_nis_sama_boleh_di_dua_sekolah_tetapi_tidak_dalam_satu_sekolah(self):
        # fixture: kedua sekolah sudah memakai NIS '001'
        from django.db import IntegrityError, transaction
        with dalam_sekolah(self.a['sekolah']):
            with self.assertRaises(IntegrityError), transaction.atomic():
                Siswa.objects.create(nama='Ganda', nis='001', kelas='4')

    def test_tidak_boleh_menyimpan_data_untuk_sekolah_lain(self):
        with dalam_sekolah(self.a['sekolah']):
            with self.assertRaises(LintasSekolah):
                Siswa.objects.create(nama='Selundup', nis='999', kelas='4', sekolah=self.b['sekolah'])

    def test_tidak_boleh_merujuk_objek_sekolah_lain(self):
        with dalam_sekolah(self.a['sekolah']):
            # siswa B ke ruang A (celah id mentah dari formulir)
            with self.assertRaises(LintasSekolah):
                AnggotaRuangKerja.objects.create(ruang_kerja=self.a['ruang'], siswa_id=self.b['siswa'].id)
            # tugas di ruang B
            with self.assertRaises(LintasSekolah):
                Tugas.objects.create(ruang_kerja_id=self.b['ruang'].id, judul='x', instruksi='x')
            # absensi untuk siswa B
            with self.assertRaises(LintasSekolah):
                Absensi.objects.create(siswa_id=self.b['siswa'].id)
            # percakapan dengan akun sekolah B
            with self.assertRaises(LintasSekolah):
                Percakapan.get_or_create_antara(self.a['guru'], self.b['guru'])
            # nilai milik siswa B
            with self.assertRaises(LintasSekolah):
                Nilai.objects.create(sesi=self.a['sesi'], siswa_id=self.b['siswa'].id, skor=1)
        self.assertEqual(AnggotaRuangKerja.objects.filter(ruang_kerja=self.a['ruang']).count(), 1)

    def test_merujuk_objek_sendiri_tetap_berfungsi(self):
        with dalam_sekolah(self.a['sekolah']):
            s2 = Siswa.objects.create(nama='Dua', nis='002', kelas='4')
            AnggotaRuangKerja.objects.create(ruang_kerja=self.a['ruang'], siswa=s2)
            Tugas.objects.create(ruang_kerja=self.a['ruang'], judul='ok', instruksi='x')
            PesanChat.objects.create(ruang_kerja=self.a['ruang'], isi='halo', dikirim_oleh=self.a['guru'])
            self.assertEqual(self.a['ruang'].anggota.count(), 2)

    def test_pembaruan_tidak_diblokir_penjaga_rujukan(self):
        with dalam_sekolah(self.a['sekolah']):
            s = Siswa.objects.get(pk=self.a['siswa'].pk)
            s.nama = 'Diubah'
            s.save()
        self.assertEqual(Siswa.objects.get(pk=self.a['siswa'].pk).nama, 'Diubah')

    def test_bebas_tidak_dibatasi_penjaga(self):
        # perintah manajemen / migrasi / admin platform
        Siswa.objects.create(nama='Platform', nis='500', kelas='1', sekolah=self.b['sekolah'])
        AnggotaRuangKerja.objects.create(ruang_kerja=self.a['ruang'], siswa=Siswa.objects.get(nis='500'))


class UsernameTest(DuaSekolah):
    def test_username_bebas_dipakai_apa_adanya(self):
        self.assertEqual(username_unik('555', self.a['sekolah']), '555')

    def test_bentrok_lintas_sekolah_memakai_awalan_kode_sekolah(self):
        with dalam_sekolah(self.a['sekolah']):
            User.objects.create_user('777', password='x', role='siswa')
        # sekolah B tidak "melihat" akun A, tetapi username unik global tetap harus dihormati
        with dalam_sekolah(self.b['sekolah']):
            self.assertFalse(User.objects.filter(username='777').exists())
            self.assertEqual(username_unik('777', self.b['sekolah']), 'beta-777')
            User.objects.create_user('beta-777', password='x', role='siswa')
            self.assertEqual(username_unik('777', self.b['sekolah']), 'beta-777-2')

    def test_tidak_peka_huruf_besar(self):
        with dalam_sekolah(self.a['sekolah']):
            User.objects.create_user('Budi', password='x')
        self.assertEqual(username_unik('budi', self.b['sekolah']), 'beta-budi')


# ---------------------------------------------------------------------------------------------
# Lapisan web
# ---------------------------------------------------------------------------------------------

def _isi(resp):
    """Isi halaman + isi context (agar tes tetap bermakna walau templat sederhana)."""
    bagian = [resp.content.decode('utf-8', 'ignore')]
    ctx = resp.context
    if ctx is not None:
        variabel = ctx.flatten() if hasattr(ctx, 'flatten') else {k: ctx[k] for k in ctx.keys()}
        for nilai in variabel.values():
            try:
                if isinstance(nilai, models.Model):
                    bagian.append(str(nilai))
                elif isinstance(nilai, (list, tuple, set, models.QuerySet)):
                    bagian.append(' '.join(str(x) for x in nilai))
            except Exception:
                pass
    return '\n'.join(bagian)


class WebTest(DuaSekolah):
    def masuk(self, akun):
        self.client.force_login(akun)

    def test_guru_a_tidak_membuka_ruang_dan_tugas_b(self):
        self.masuk(self.a['guru'])
        for nama, kw in [('ruang_kerja:detail', {'ruang_id': self.b['ruang'].id}),
                         ('ruang_kerja:detail_tugas', {'tugas_id': self.b['tugas'].id}),
                         ('ruang_kerja:kelola_anggota', {'ruang_id': self.b['ruang'].id}),
                         ('ruang_kerja:rapor_ruang_kerja', {'ruang_id': self.b['ruang'].id}),
                         ('ruang_kerja:detail_kelas', {'kelas_id': self.b['kelas'].id}),
                         ('penilaian:detail_sesi', {'sesi_id': self.b['sesi'].id})]:
            from django.urls import reverse
            r = self.client.get(reverse(nama, kwargs=kw))
            self.assertEqual(r.status_code, 404, nama)

    def test_guru_a_tidak_dapat_menghapus_data_b(self):
        from django.urls import reverse
        self.masuk(self.a['guru'])
        for nama, kw in [('ruang_kerja:hapus_tugas', {'tugas_id': self.b['tugas'].id}),
                         ('ruang_kerja:hapus_ruang_kerja', {'ruang_id': self.b['ruang'].id}),
                         ('ruang_kerja:hapus_anggota', {'anggota_id': self.b['anggota'].id}),
                         ('ruang_kerja:hapus_kelas', {'kelas_id': self.b['kelas'].id})]:
            r = self.client.post(reverse(nama, kwargs=kw))
            self.assertEqual(r.status_code, 404, nama)
        self.assertTrue(Tugas.objects.filter(id=self.b['tugas'].id).exists())
        self.assertTrue(RuangKerja.objects.filter(id=self.b['ruang'].id).exists())
        self.assertTrue(AnggotaRuangKerja.objects.filter(id=self.b['anggota'].id).exists())
        self.assertTrue(Kelas.objects.filter(id=self.b['kelas'].id).exists())

    def test_tambah_anggota_menolak_id_siswa_sekolah_lain(self):
        from django.urls import reverse
        self.masuk(self.a['guru'])
        r = self.client.post(reverse('ruang_kerja:tambah_anggota', kwargs={'ruang_id': self.a['ruang'].id}),
                             {'siswa_ids': [self.b['siswa'].id]})
        self.assertIn(r.status_code, (200, 302))
        self.assertEqual(AnggotaRuangKerja.objects.filter(siswa=self.b['siswa']).count(), 1)  # hanya di ruang B
        self.assertFalse(AnggotaRuangKerja.objects.filter(ruang_kerja=self.a['ruang'], siswa=self.b['siswa']).exists())

    def test_tambah_tugas_ke_ruang_b_ditolak(self):
        from django.urls import reverse
        self.masuk(self.a['guru'])
        r = self.client.post(reverse('ruang_kerja:tambah_tugas', kwargs={'ruang_id': self.b['ruang'].id}),
                             {'judul': 'Selundup', 'instruksi': 'x', 'jenis': 'esai'})
        self.assertEqual(r.status_code, 404)
        self.assertFalse(Tugas.objects.filter(judul='Selundup').exists())

    def test_daftar_siswa_dan_dashboard_hanya_sekolah_sendiri(self):
        from django.urls import reverse
        self.masuk(self.a['guru'])
        for nama in ('accounts:daftar_siswa', 'kelas:dashboard', 'ruang_kerja:kelola_kelas',
                     'ruang_kerja:kelola_mapel', 'penilaian:home', 'pesan:pilih_kontak'):
            r = self.client.get(reverse(nama))
            self.assertEqual(r.status_code, 200, nama)
            isi = _isi(r)
            self.assertNotIn('Siswa Beta', isi, nama)
            self.assertNotIn('Mapel Beta', isi, nama)
            self.assertNotIn('Topik Beta', isi, nama)
            self.assertNotIn('Guru Beta', isi, nama)

    def test_daftar_siswa_menampilkan_siswa_sendiri(self):
        from django.urls import reverse
        self.masuk(self.a['guru'])
        r = self.client.get(reverse('accounts:daftar_siswa'))
        self.assertIn('Siswa Alfa', _isi(r))

    def test_buat_akun_siswa_b_oleh_guru_a_ditolak(self):
        from django.urls import reverse
        self.masuk(self.a['guru'])
        self.b['siswa'].user = None
        self.b['siswa'].save()
        banyak = User.objects.count()
        r = self.client.post(reverse('accounts:buat_akun_siswa', kwargs={'siswa_id': self.b['siswa'].id}))
        self.assertEqual(r.status_code, 404)
        r = self.client.post(reverse('accounts:buat_akun_orangtua', kwargs={'siswa_id': self.b['siswa'].id}))
        self.assertEqual(r.status_code, 404)
        self.assertEqual(User.objects.count(), banyak)

    def test_tambah_siswa_menerima_nis_yang_sama_dengan_sekolah_lain(self):
        from django.urls import reverse
        self.masuk(self.a['guru'])
        r = self.client.post(reverse('accounts:tambah_siswa'), {'nama': 'Citra', 'nis': '002', 'kelas': '4'})
        self.assertEqual(r.status_code, 302)
        baru = Siswa.objects.get(nama='Citra')
        self.assertEqual(baru.sekolah_id, self.a['sekolah'].id)
        # NIS yang sama di sekolah B tidak dianggap bentrok, tetapi di sekolah sendiri bentrok
        r = self.client.post(reverse('accounts:tambah_siswa'), {'nama': 'Dewi', 'nis': '002', 'kelas': '4'})
        self.assertEqual(Siswa.objects.filter(nama='Dewi').count(), 0)

    def test_nis_sama_membuat_username_berbeda(self):
        from django.urls import reverse
        # akun siswa A sudah memakai username 'siswa-alfa'; kedua sekolah punya NIS '001'
        self.masuk(self.a['guru'])
        self.a['siswa'].user = None
        self.a['siswa'].save()
        self.client.post(reverse('accounts:buat_akun_siswa', kwargs={'siswa_id': self.a['siswa'].id}))
        self.client.logout()
        self.masuk(self.b['guru'])
        self.b['siswa'].user = None
        self.b['siswa'].save()
        r = self.client.post(reverse('accounts:buat_akun_siswa', kwargs={'siswa_id': self.b['siswa'].id}))
        self.assertEqual(r.status_code, 302)
        self.b['siswa'].refresh_from_db()
        self.assertIsNotNone(self.b['siswa'].user)
        self.assertEqual(self.b['siswa'].user.username, 'beta-001')
        self.assertEqual(self.b['siswa'].user.sekolah_id, self.b['sekolah'].id)

    def test_chat_dengan_akun_sekolah_lain_ditolak(self):
        from django.urls import reverse
        self.masuk(self.a['guru'])
        r = self.client.get(reverse('pesan:chat', kwargs={'user_id': self.b['guru'].id}))
        self.assertEqual(r.status_code, 404)
        self.assertEqual(Percakapan.objects.count(), 0)

    def test_pesan_pribadi_dalam_satu_sekolah_berfungsi(self):
        from django.urls import reverse
        self.masuk(self.a['guru'])
        guru2 = User.objects.create_user('guru-alfa-2', password='x', role='guru', first_name='Guru Dua', sekolah=self.a['sekolah'])
        r = self.client.post(reverse('pesan:chat', kwargs={'user_id': guru2.id}), {'isi': 'halo sesama guru'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Percakapan.objects.count(), 1)
        self.assertEqual(self.client.get(reverse('pesan:daftar')).status_code, 200)
        self.assertEqual(self.client.get(reverse('pesan:chat', kwargs={'user_id': guru2.id})).status_code, 200)
        # guru B tidak melihat percakapan itu
        self.client.logout()
        self.masuk(self.b['guru'])
        r = self.client.get(reverse('pesan:daftar'))
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('Guru Dua', _isi(r))

    def test_daftar_kontak_hanya_akun_sekolah_sendiri(self):
        from django.urls import reverse
        self.masuk(self.a['akun'])  # siswa A hanya dapat menghubungi guru: hanya guru A
        r = self.client.get(reverse('pesan:pilih_kontak'))
        isi = _isi(r)
        self.assertIn('Guru Alfa', isi)
        self.assertNotIn('Guru Beta', isi)

    def test_siswa_a_tidak_melihat_ruang_b(self):
        from django.urls import reverse
        self.masuk(self.a['akun'])
        r = self.client.get(reverse('ruang_kerja:detail', kwargs={'ruang_id': self.b['ruang'].id}))
        self.assertEqual(r.status_code, 404)
        r = self.client.get(reverse('ruang_kerja:detail_tugas', kwargs={'tugas_id': self.b['tugas'].id}))
        self.assertEqual(r.status_code, 404)

    def test_superuser_platform_melihat_semua_sekolah(self):
        from django.urls import reverse
        su = User.objects.create_superuser('platform', password='x')
        self.client.force_login(su)
        r = self.client.get(reverse('ruang_kerja:detail', kwargs={'ruang_id': self.b['ruang'].id}))
        self.assertEqual(r.status_code, 200)

    def test_akun_tanpa_sekolah_tidak_melihat_data_sekolah(self):
        from django.urls import reverse
        yatim = User.objects.create_user('yatim', password='x', role='guru')
        self.client.force_login(yatim)
        for rk in (self.a['ruang'], self.b['ruang']):
            r = self.client.get(reverse('ruang_kerja:detail', kwargs={'ruang_id': rk.id}))
            self.assertEqual(r.status_code, 404)

    def test_sekolah_nonaktif_diblokir(self):
        from django.urls import reverse
        s = self.a['sekolah']
        s.aktif = False
        s.save()
        self.masuk(self.a['guru'])
        r = self.client.get(reverse('ruang_kerja:detail', kwargs={'ruang_id': self.a['ruang'].id}))
        self.assertEqual(r.status_code, 404)

    def test_lingkup_dibersihkan_setelah_permintaan(self):
        from django.urls import reverse
        self.masuk(self.a['guru'])
        self.client.get(reverse('kelas:dashboard'))
        self.assertIs(sekolah_aktif(), BEBAS)

    def test_request_sekolah_terisi(self):
        from accounts.tenancy import SekolahMiddleware
        rf = RequestFactory()
        req = rf.get('/')
        req.user = self.a['guru']
        diamati = {}

        def view(request):
            diamati['sekolah'] = request.sekolah
            diamati['aktif'] = sekolah_aktif()
            from django.http import HttpResponse
            return HttpResponse('ok')
        SekolahMiddleware(view)(req)
        self.assertEqual(diamati['sekolah'], self.a['sekolah'])
        self.assertEqual(diamati['aktif'], self.a['sekolah'].pk)


class ProsesLatarTest(DuaSekolah):
    """Pengolah konteks templat dipakai di setiap halaman, jadi ikut dijaga."""

    def test_notifikasi_tidak_menghitung_ruang_sekolah_lain(self):
        from pengaturan.context_processors import notifikasi_belum_dibaca
        PesanChat.objects.create(ruang_kerja=self.b['ruang'], isi='rahasia B', dikirim_oleh=self.b['guru'])
        PesanChat.objects.create(ruang_kerja=self.a['ruang'], isi='milik A', dikirim_oleh=self.a['guru'])
        req = RequestFactory().get('/')
        req.user = self.a['guru']
        with dalam_sekolah(self.a['sekolah']):
            self.assertEqual(notifikasi_belum_dibaca(req)['total_belum_dibaca'], 1)
        with dalam_sekolah(self.b['sekolah']):
            req.user = self.b['guru']
            self.assertEqual(notifikasi_belum_dibaca(req)['total_belum_dibaca'], 1)

    def test_sidebar_kelas_hanya_sekolah_sendiri(self):
        from ruang_kerja.context_processors import sidebar_kelas
        req = RequestFactory().get('/')
        req.user = self.a['guru']
        with dalam_sekolah(self.a['sekolah']):
            self.assertEqual(list(sidebar_kelas(req)['sidebar_kelas_list']), [self.a['kelas']])
