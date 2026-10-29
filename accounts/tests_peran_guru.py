"""Tes pembatasan peran guru di dalam satu sekolah (Tahap 3).

Aturan yang diuji:
  - guru melihat ruang kerja miliknya sendiri dan isinya, bukan milik guru lain;
  - guru melihat siswa yang (a) terdaftar di ruang kerjanya, (b) sekelas dengan salah satu ruang kerjanya,
    (c) ada di kelas yang ia walikan; siswa lain di sekolah yang sama tidak terlihat (404 / daftar kosong);
  - data anak siswa (nilai, absensi, ...) mengikuti siswa yang terlihat;
  - kepala sekolah dan admin sekolah melihat seluruh sekolahnya.
"""
from django.contrib.auth import get_user_model
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.test import TestCase
from django.urls import reverse

from accounts.models import Sekolah, Siswa
from accounts.tenancy import LintasSekolah, dalam_sekolah
from accounts.tests_tenancy import _isi
from kelas.models import Absensi
from penilaian.models import Nilai, SesiPenilaian
from ruang_kerja.models import AnggotaRuangKerja, Kelas, RuangKerja, Tugas

User = get_user_model()


class Sekolah1(TestCase):
    @classmethod
    def setUpTestData(cls):
        s = cls.sekolah = Sekolah.objects.create(nama='Alfa', kode='alfa')

        def akun(nama, role='guru'):
            return User.objects.create_user(nama, password='x', role=role, first_name=nama, sekolah=s)

        cls.g1, cls.g2, cls.w = akun('g1'), akun('g2'), akun('wali')
        cls.kepsek, cls.admin = akun('kepsek', 'kepsek'), akun('admin', 'admin')

        def murid(nama, kelas):
            return Siswa.objects.create(nama=nama, nis=nama, kelas=kelas, sekolah=s)

        cls.s4a, cls.s4b = murid('Ani4a', '4'), murid('Budi4b', 'Kelas 4')
        cls.s5, cls.s6, cls.s7 = murid('Cici5', '5'), murid('Dedi6', '6'), murid('Eka7', '7')

        cls.k6 = Kelas.objects.create(nama='VI', wali_kelas=cls.w, sekolah=s)  # romawi = '6'
        cls.r1 = RuangKerja.objects.create(mapel='IPA', kelas='4', guru=cls.g1, sekolah=s)
        cls.r2 = RuangKerja.objects.create(mapel='IPS', kelas='5', guru=cls.g2, sekolah=s)
        AnggotaRuangKerja.objects.create(ruang_kerja=cls.r1, siswa=cls.s4a)
        AnggotaRuangKerja.objects.create(ruang_kerja=cls.r2, siswa=cls.s5)
        AnggotaRuangKerja.objects.create(ruang_kerja=cls.r2, siswa=cls.s7)  # kelas 7, tetapi anggota ruang g2
        cls.t1 = Tugas.objects.create(ruang_kerja=cls.r1, judul='Tugas G1', instruksi='x')
        cls.t2 = Tugas.objects.create(ruang_kerja=cls.r2, judul='Tugas G2', instruksi='x')
        cls.ab4, cls.ab5 = Absensi.objects.create(siswa=cls.s4a), Absensi.objects.create(siswa=cls.s5)
        cls.sesi1 = SesiPenilaian.objects.create(mapel='IPA', jenis='formatif', topik='Sesi G1', kelas='4', guru=cls.g1, sekolah=s)
        cls.sesi2 = SesiPenilaian.objects.create(mapel='IPS', jenis='formatif', topik='Sesi G2', kelas='5', guru=cls.g2, sekolah=s)
        cls.n4 = Nilai.objects.create(sesi=cls.sesi1, siswa=cls.s4a, skor=80)
        cls.n5 = Nilai.objects.create(sesi=cls.sesi2, siswa=cls.s5, skor=70)

    def sbg(self, user):
        return dalam_sekolah(self.sekolah, guru=user if user.role == 'guru' else None)


class SiswaTerlihatTest(Sekolah1):
    def nama(self, user):
        with self.sbg(user):
            return {s.nama for s in Siswa.objects.all()}

    def test_guru_melihat_siswa_ruang_dan_sekelas(self):
        # Ani (anggota R1) dan Budi ('Kelas 4' = kelas '4', bukan anggota)
        self.assertEqual(self.nama(self.g1), {'Ani4a', 'Budi4b'})

    def test_guru_melihat_anggota_ruangnya_walau_beda_kelas(self):
        self.assertEqual(self.nama(self.g2), {'Cici5', 'Eka7'})

    def test_wali_kelas_hanya_siswa_kelasnya_walau_romawi(self):
        self.assertEqual(self.nama(self.w), {'Dedi6'})

    def test_kepsek_dan_admin_melihat_seluruh_sekolah(self):
        for u in (self.kepsek, self.admin):
            self.assertEqual(len(self.nama(u)), 5)

    def test_guru_tanpa_ruang_dan_bukan_wali_tidak_melihat_siapa_pun(self):
        baru = User.objects.create_user('baru', password='x', role='guru', sekolah=self.sekolah)
        self.assertEqual(self.nama(baru), set())

    def test_kelas_baru_pada_ruang_ikut_dihitung(self):
        k = Kelas.objects.create(nama='Kelas 7', sekolah=self.sekolah)
        RuangKerja.objects.create(mapel='Seni', kelas='ruang tujuh', kelas_baru=k, guru=self.g1, sekolah=self.sekolah)
        self.assertEqual(self.nama(self.g1), {'Ani4a', 'Budi4b', 'Eka7'})

    def test_membuat_ruang_baru_langsung_menambah_siswa_terlihat(self):
        with self.sbg(self.g1):
            self.assertEqual(Siswa.objects.filter(nama='Cici5').count(), 0)
            RuangKerja.objects.create(mapel='Seni', kelas='5', guru=self.g1)
            self.assertEqual(Siswa.objects.filter(nama='Cici5').count(), 1)  # cache dibersihkan sinyal
            AnggotaRuangKerja.objects.filter(ruang_kerja__guru=self.g1)  # tidak error

    def test_ruang_dialihkan_ke_guru_lain(self):
        self.r1.guru = self.g2
        self.r1.save()
        self.assertEqual(self.nama(self.g1), set())
        self.assertEqual(self.nama(self.g2), {'Ani4a', 'Budi4b', 'Cici5', 'Eka7'})


class RuangDanIsiTest(Sekolah1):
    def test_guru_hanya_melihat_ruang_sendiri(self):
        with self.sbg(self.g1):
            self.assertEqual(list(RuangKerja.objects.all()), [self.r1])
        with self.sbg(self.g2):
            self.assertEqual(list(RuangKerja.objects.all()), [self.r2])
        with self.sbg(self.w):
            self.assertEqual(list(RuangKerja.objects.all()), [])  # wali kelas melihat siswanya, bukan ruang guru lain

    def test_kepsek_melihat_semua_ruang(self):
        with self.sbg(self.kepsek):
            self.assertEqual(set(RuangKerja.objects.all()), {self.r1, self.r2})

    def test_isi_ruang_guru_lain_tidak_ditemukan(self):
        with self.sbg(self.g1):
            self.assertEqual(get_object_or_404(Tugas, id=self.t1.id), self.t1)
            with self.assertRaises(Http404):
                get_object_or_404(Tugas, id=self.t2.id)
            with self.assertRaises(Http404):
                get_object_or_404(RuangKerja, id=self.r2.id)
            self.assertEqual(AnggotaRuangKerja.objects.filter(ruang_kerja=self.r2).count(), 0)

    def test_manajer_relasi_ikut_dibatasi(self):
        with self.sbg(self.g1):
            r2 = RuangKerja._base_manager.get(pk=self.r2.pk)
            self.assertEqual(r2.tugas.count(), 0)

    def test_data_anak_siswa_mengikuti_siswa_terlihat(self):
        with self.sbg(self.g1):
            self.assertEqual(list(Absensi.objects.all()), [self.ab4])
            self.assertEqual(list(Nilai.objects.all()), [self.n4])
            with self.assertRaises(Http404):
                get_object_or_404(Absensi, id=self.ab5.id)
            with self.assertRaises(Http404):
                get_object_or_404(Nilai, id=self.n5.id)

    def test_sesi_penilaian_hanya_milik_sendiri(self):
        with self.sbg(self.g1):
            self.assertEqual(list(SesiPenilaian.objects.all()), [self.sesi1])
        with self.sbg(self.kepsek):
            self.assertEqual(SesiPenilaian.objects.count(), 2)

    def test_update_dan_hapus_massal_tidak_menyentuh_ruang_guru_lain(self):
        with self.sbg(self.g1):
            Tugas.objects.all().delete()
            Siswa.objects.all().update(nama='X')
        self.assertTrue(Tugas.objects.filter(id=self.t2.id).exists())
        self.assertFalse(Tugas.objects.filter(id=self.t1.id).exists())
        self.assertEqual(Siswa.objects.get(pk=self.s5.pk).nama, 'Cici5')

    def test_guru_tanpa_sekolah_tidak_dibatasi_peran(self):
        # keadaan data lama / tes: tidak ada pembatasan peran bila akun tidak punya sekolah
        with dalam_sekolah(None, guru=self.g1):  # guru tanpa sekolah tidak mendapat peran (id sekolah bukan int)
            self.assertEqual(RuangKerja.objects.count(), 0)  # tetapi tetap hanya melihat data tanpa sekolah


class PenulisanGuruTest(Sekolah1):
    def test_guru_tidak_dapat_menulis_untuk_siswa_atau_ruang_yang_tidak_terlihat(self):
        with self.sbg(self.g1):
            with self.assertRaises(LintasSekolah):
                Nilai.objects.create(sesi=self.sesi1, siswa_id=self.s5.id, skor=1)
            with self.assertRaises(LintasSekolah):
                Absensi.objects.create(siswa_id=self.s5.id)
            with self.assertRaises(LintasSekolah):
                Tugas.objects.create(ruang_kerja_id=self.r2.id, judul='x', instruksi='x')
            with self.assertRaises(LintasSekolah):
                AnggotaRuangKerja.objects.create(ruang_kerja_id=self.r1.id, siswa_id=self.s5.id)
            with self.assertRaises(LintasSekolah):
                Nilai.objects.create(sesi_id=self.sesi2.id, siswa=self.s4a, skor=1)

    def test_guru_dapat_menulis_untuk_miliknya(self):
        with self.sbg(self.g1):
            AnggotaRuangKerja.objects.create(ruang_kerja=self.r1, siswa=self.s4b)
            Tugas.objects.create(ruang_kerja=self.r1, judul='Baru', instruksi='x')
            Absensi.objects.create(siswa=self.s4b)
            Nilai.objects.create(sesi=self.sesi1, siswa=self.s4b, skor=90)

    def test_wali_kelas_dapat_mengabsen_siswa_kelasnya(self):
        with self.sbg(self.w):
            Absensi.objects.create(siswa=self.s6)
            with self.assertRaises(LintasSekolah):
                Absensi.objects.create(siswa=self.s4a)


class WebGuruTest(Sekolah1):
    def masuk(self, u):
        self.client.force_login(u)

    def test_guru_tidak_membuka_ruang_guru_lain_di_sekolah_sama(self):
        self.masuk(self.g1)
        self.assertEqual(self.client.get(reverse('ruang_kerja:detail', kwargs={'ruang_id': self.r1.id})).status_code, 200)
        for nama, kw in [('ruang_kerja:detail', {'ruang_id': self.r2.id}),
                         ('ruang_kerja:detail_tugas', {'tugas_id': self.t2.id}),
                         ('ruang_kerja:kelola_anggota', {'ruang_id': self.r2.id}),
                         ('ruang_kerja:rapor_ruang_kerja', {'ruang_id': self.r2.id}),
                         ('penilaian:detail_sesi', {'sesi_id': self.sesi2.id})]:
            self.assertEqual(self.client.get(reverse(nama, kwargs=kw)).status_code, 404, nama)

    def test_guru_tidak_menghapus_atau_mengubah_ruang_guru_lain(self):
        self.masuk(self.g1)
        for nama, kw in [('ruang_kerja:hapus_tugas', {'tugas_id': self.t2.id}),
                         ('ruang_kerja:hapus_ruang_kerja', {'ruang_id': self.r2.id})]:
            self.assertEqual(self.client.post(reverse(nama, kwargs=kw)).status_code, 404, nama)
        r = self.client.post(reverse('ruang_kerja:tambah_tugas', kwargs={'ruang_id': self.r2.id}),
                             {'judul': 'Selundup', 'instruksi': 'x', 'jenis': 'esai'})
        self.assertEqual(r.status_code, 404)
        self.assertTrue(Tugas.objects.filter(id=self.t2.id).exists())
        self.assertFalse(Tugas.objects.filter(judul='Selundup').exists())

    def test_daftar_siswa_guru(self):
        self.masuk(self.g1)
        r = self.client.get(reverse('accounts:daftar_siswa'))
        isi = _isi(r)
        self.assertIn('Ani4a', isi)
        self.assertNotIn('Cici5', isi)
        self.assertNotIn('Dedi6', isi)

    def test_wali_kelas_hanya_melihat_siswa_kelasnya(self):
        self.masuk(self.w)
        isi = _isi(self.client.get(reverse('accounts:daftar_siswa')))
        self.assertIn('Dedi6', isi)
        self.assertNotIn('Ani4a', isi)
        self.assertNotIn('Cici5', isi)

    def test_kepsek_melihat_semua(self):
        self.masuk(self.kepsek)
        for rk in (self.r1, self.r2):
            self.assertEqual(self.client.get(reverse('ruang_kerja:detail', kwargs={'ruang_id': rk.id})).status_code, 200)
        isi = _isi(self.client.get(reverse('accounts:daftar_siswa')))
        for nama in ('Ani4a', 'Cici5', 'Dedi6', 'Eka7'):
            self.assertIn(nama, isi)

    def test_buat_akun_hanya_untuk_siswa_terlihat(self):
        self.masuk(self.g1)
        banyak = User.objects.count()
        self.assertEqual(self.client.post(reverse('accounts:buat_akun_siswa', kwargs={'siswa_id': self.s5.id})).status_code, 404)
        self.assertEqual(self.client.post(reverse('accounts:buat_akun_orangtua', kwargs={'siswa_id': self.s5.id})).status_code, 404)
        self.assertEqual(User.objects.count(), banyak)
        self.assertEqual(self.client.post(reverse('accounts:buat_akun_siswa', kwargs={'siswa_id': self.s4a.id})).status_code, 302)
        self.assertEqual(User.objects.count(), banyak + 1)

    def test_tambah_anggota_menolak_siswa_yang_tidak_terlihat(self):
        self.masuk(self.g1)
        self.client.post(reverse('ruang_kerja:tambah_anggota', kwargs={'ruang_id': self.r1.id}),
                         {'siswa_ids': [self.s5.id, self.s4b.id]})
        self.assertTrue(AnggotaRuangKerja.objects.filter(ruang_kerja=self.r1, siswa=self.s4b).exists())
        self.assertFalse(AnggotaRuangKerja.objects.filter(ruang_kerja=self.r1, siswa=self.s5).exists())

    def test_dashboard_guru_berfungsi(self):
        for u in (self.g1, self.w, self.kepsek):
            self.masuk(u)
            self.assertEqual(self.client.get(reverse('kelas:dashboard')).status_code, 200)
            self.assertEqual(self.client.get(reverse('pesan:pilih_kontak')).status_code, 200)

    def test_lingkup_peran_dibersihkan_setelah_permintaan(self):
        from accounts import tenancy
        self.masuk(self.g1)
        self.client.get(reverse('kelas:dashboard'))
        self.assertIsNone(tenancy._peran.get())


class LaporanTest(Sekolah1):
    def test_periksa_guru_melaporkan_tanpa_error(self):
        from io import StringIO
        from django.core.management import call_command
        RuangKerja.objects.create(mapel='Yatim', kelas='9', guru=None, sekolah=self.sekolah)
        keluar = StringIO()
        call_command('periksa_guru', '--sekolah', 'alfa', stdout=keluar)
        teks = keluar.getvalue()
        self.assertIn('guru g1: 1 ruang kerja, 2 siswa terlihat', teks)
        self.assertIn('guru g2: 1 ruang kerja, 2 siswa terlihat', teks)
        self.assertIn('guru wali: 0 ruang kerja, 1 siswa terlihat', teks)
        self.assertIn('TANPA guru', teks)
        self.assertIn('total siswa: 5', teks)
