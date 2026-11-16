from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Sekolah, Siswa, User
from kelas.models import Absensi
from ruang_kerja.models import (AnggotaRuangKerja, CatatanRapor, Kelas, Materi, NilaiRaporMapel,
                                PenilaianTopik, RaporSemester, RuangKerja, SubmisiTugas, Tugas)
from ruang_kerja.rapor_semester import buat_draf, predikat, rentang_semester, tahun_ajaran_sekarang

TA = '2026/2027'


def akun(nama, role, sekolah, **kw):
    return User.objects.create_user(username=nama, password='x', role=role, sekolah=sekolah, **kw)


# Halaman memakai base.html (file statis). Di uji, manifest statis produksi tidak ada, jadi pakai penyimpanan biasa.
@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class RaporKeseluruhan(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sk = Sekolah.objects.create(nama='SD Contoh', kode='sdc')
        cls.lain = Sekolah.objects.create(nama='SD Lain', kode='sdl')
        cls.wali = akun('wali', 'guru', cls.sk)
        cls.guru_mtk = akun('mtk', 'guru', cls.sk)
        cls.guru_ipa = akun('ipa', 'guru', cls.sk)
        cls.guru_luar = akun('luar', 'guru', cls.sk)
        cls.kepsek = akun('kepsek', 'kepsek', cls.sk)
        cls.guru_lain = akun('guru_lain', 'guru', cls.lain)
        cls.siswa = Siswa.objects.create(nama='Ani Putri', nis='1', kelas='4', sekolah=cls.sk)
        cls.user_siswa = akun('siswa', 'siswa', cls.sk)
        cls.siswa.user = cls.user_siswa
        cls.siswa.save()
        cls.ortu = akun('ortu', 'orangtua', cls.sk, anak=cls.siswa)
        kelas = Kelas.objects.create(nama='IV', sekolah=cls.sk, wali_kelas=cls.wali)
        cls.mtk = RuangKerja.objects.create(mapel='Matematika', kelas='4', kelas_baru=kelas, guru=cls.guru_mtk, sekolah=cls.sk)
        cls.ipa = RuangKerja.objects.create(mapel='IPA', kelas='4', kelas_baru=kelas, guru=cls.guru_ipa, sekolah=cls.sk)
        for r in (cls.mtk, cls.ipa):
            AnggotaRuangKerja.objects.create(ruang_kerja=r, siswa=cls.siswa)
        tugas = Tugas.objects.create(ruang_kerja=cls.mtk, judul='T1', instruksi='i', dibuat_oleh=cls.guru_mtk)
        SubmisiTugas.objects.create(tugas=tugas, siswa=cls.siswa, nilai=80)
        tugas2 = Tugas.objects.create(ruang_kerja=cls.ipa, judul='T2', instruksi='i', dibuat_oleh=cls.guru_ipa)
        SubmisiTugas.objects.create(tugas=tugas2, siswa=cls.siswa, nilai=90)
        materi = Materi.objects.create(ruang_kerja=cls.mtk, judul='Pecahan', diunggah_oleh=cls.guru_mtk)
        PenilaianTopik.objects.create(materi=materi, siswa=cls.siswa, jenis='sumatif', nilai=85)
        CatatanRapor.objects.create(ruang_kerja=cls.ipa, siswa=cls.siswa, catatan='Aktif bereksperimen.')
        for status in ('hadir', 'hadir', 'hadir', 'sakit'):
            Absensi.objects.create(siswa=cls.siswa, status=status, tanggal='2026-10-%02d' % (Absensi.objects.count() + 1))
        cls.url = reverse('ruang_kerja:rapor_keseluruhan', args=[cls.siswa.id])
        cls.url_semester = reverse('ruang_kerja:simpan_rapor_semester', args=[cls.siswa.id])

    def buka(self, user):
        self.client.force_login(user)
        return self.client.get(self.url)

    def test_wali_kelas_melihat_semua_mapel_dan_nilai_semester(self):
        NilaiRaporMapel.objects.create(ruang_kerja=self.mtk, siswa=self.siswa, tahun_ajaran=TA, semester=2,
                                       nilai_akhir=92, deskripsi='Sangat paham pecahan.')
        self.client.force_login(self.wali)
        r = self.client.get(self.url, {'ta': TA, 'sem': 2})
        self.assertEqual(r.status_code, 200)
        self.assertEqual([b['ruang'].mapel for b in r.context['baris']], ['Matematika', 'IPA'])
        mtk = r.context['baris'][0]
        self.assertEqual((mtk['nilai'], mtk['predikat']), (92, 'Really Good'))
        self.assertContains(r, 'Sangat paham pecahan.')
        self.assertContains(r, 'Final Score')
        self.assertContains(r, 'of 4')
        self.assertTrue(r.context['semua_mapel'])

    def test_kehadiran_otomatis_dari_absensi_dan_bisa_ditimpa(self):
        r = self.buka(self.wali)
        self.assertEqual(r.context['hari'], {'sakit': 1, 'izin': 0, 'alpha': 0})
        self.client.post(self.url_semester, {'ta': TA, 'sem': 2, 'sakit_hari': '3', 'izin_hari': '', 'alpha_hari': '1'})
        r = self.client.get(self.url, {'ta': TA, 'sem': 2})
        self.assertEqual(r.context['hari'], {'sakit': 3, 'izin': 0, 'alpha': 1})

    def test_wali_menyimpan_data_semester(self):
        self.client.force_login(self.wali)
        self.client.post(self.url_semester, {
            'ta': TA, 'sem': 2, 'nisn': '99', 'tempat': 'Manado', 'tanggal_rapor': '2026-06-20',
            'sp_aspek': ['Berdoa', ''], 'sp_predikat': ['Good', ''],
            'ek_kegiatan': ['Pramuka'], 'ek_predikat': ['Good'], 'ek_deskripsi': ['Aktif'],
            'pr_kegiatan': ['Lomba'], 'pr_catatan': ['Juara 1'],
            'berat_badan': '30 kg', 'komentar_guru': 'Pertahankan.'})
        d = RaporSemester.objects.get(siswa=self.siswa, tahun_ajaran=TA, semester=2)
        self.assertEqual(d.spiritual, [{'aspek': 'Berdoa', 'predikat': 'Good'}])
        self.assertEqual(d.prestasi, [{'kegiatan': 'Lomba', 'catatan': 'Juara 1'}])
        r = self.client.get(self.url, {'ta': TA, 'sem': 2})
        for teks in ('Berdoa', 'Pramuka', 'Juara 1', '30 kg', 'Pertahankan.', 'Manado'):
            self.assertContains(r, teks)

    def test_guru_mapel_tidak_boleh_menyimpan_data_semester(self):
        self.client.force_login(self.guru_mtk)
        self.client.post(self.url_semester, {'ta': TA, 'sem': 2, 'komentar_guru': 'x'})
        self.assertFalse(RaporSemester.objects.exists())

    def test_kepsek_melihat_semua_mapel(self):
        r = self.buka(self.kepsek)
        self.assertEqual(len(r.context['baris']), 2)

    def test_guru_mapel_hanya_melihat_mapelnya_sendiri(self):
        r = self.buka(self.guru_mtk)
        self.assertEqual([b['ruang'].mapel for b in r.context['baris']], ['Matematika'])
        self.assertFalse(r.context['semua_mapel'])

    def test_siswa_dan_ortu_ditolak(self):
        for u in (self.user_siswa, self.ortu):
            self.assertEqual(self.buka(u).status_code, 302)

    def test_guru_sekolah_lain_tidak_menemukan_siswa(self):
        self.assertEqual(self.buka(self.guru_lain).status_code, 404)

    def test_guru_tanpa_hubungan_dengan_siswa_tidak_menemukan(self):
        self.assertEqual(self.buka(self.guru_luar).status_code, 404)

    def test_siswa_tidak_boleh_menyimpan_data_semester(self):
        self.client.force_login(self.user_siswa)
        self.client.post(self.url_semester, {'ta': TA, 'sem': 2, 'komentar_guru': 'x'})
        self.assertFalse(RaporSemester.objects.exists())

    def test_periode_tidak_sah_diganti_periode_sekarang(self):
        self.client.force_login(self.wali)
        r = self.client.get(self.url, {'ta': 'ngawur', 'sem': '9'})
        self.assertEqual(r.status_code, 200)
        self.assertIn(r.context['sem'], (1, 2))


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class NilaiMapel(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sk = Sekolah.objects.create(nama='SD Contoh', kode='sdc')
        cls.guru = akun('mtk', 'guru', cls.sk)
        cls.guru2 = akun('ipa', 'guru', cls.sk)
        cls.siswa = Siswa.objects.create(nama='Ani Putri', nis='1', kelas='4', sekolah=cls.sk)
        cls.ruang = RuangKerja.objects.create(mapel='Matematika', kelas='4', guru=cls.guru, sekolah=cls.sk)
        AnggotaRuangKerja.objects.create(ruang_kerja=cls.ruang, siswa=cls.siswa)
        cls.url = reverse('ruang_kerja:nilai_mapel_rapor', args=[cls.ruang.id, cls.siswa.id])

    def test_predikat(self):
        for nilai, en, idn in ((95, 'Really Good', 'Sangat Baik'), (90, 'Really Good', 'Sangat Baik'),
                               (89, 'Good', 'Baik'), (80, 'Good', 'Baik'), (79, 'Adequate', 'Cukup'),
                               (70, 'Adequate', 'Cukup'), (69, 'Need Improvement', 'Perlu Peningkatan')):
            self.assertEqual(predikat(nilai, 'en'), en)
            self.assertEqual(predikat(nilai, 'id'), idn)
        self.assertEqual(predikat(None), '')

    def test_semester_dan_rentang(self):
        import datetime
        self.assertEqual(tahun_ajaran_sekarang(datetime.date(2026, 10, 1)), ('2026/2027', 1))
        self.assertEqual(tahun_ajaran_sekarang(datetime.date(2027, 3, 1)), ('2026/2027', 2))
        self.assertEqual(rentang_semester('2026/2027', 2), (datetime.date(2027, 1, 1), datetime.date(2027, 6, 30)))

    def test_draf_inggris_dan_indonesia(self):
        topik = {'judul': 'Fractions', 'mastery': 60.0}
        en = buat_draf('Ani', 85, topik, None, 'en')
        self.assertIn('Ani', en)
        self.assertIn('Fractions', en)
        self.assertIn('Assistance is needed', en)
        idn = buat_draf('Ani', 95, {'judul': 'Pecahan', 'mastery': 95.0}, None, 'id')
        self.assertIn('melebihi ekspektasi', idn)
        self.assertIn('Pecahan', idn)

    def test_guru_menyimpan_nilai_dan_deskripsi_sendiri(self):
        self.client.force_login(self.guru)
        r = self.client.post(self.url, {'ta': TA, 'sem': 2, 'nilai_akhir': '85', 'bahasa': 'id',
                                        'deskripsi': 'Tulisan guru sendiri.'})
        self.assertEqual(r.status_code, 302)
        n = NilaiRaporMapel.objects.get(ruang_kerja=self.ruang, siswa=self.siswa)
        self.assertEqual((n.nilai_akhir, n.bahasa, n.deskripsi), (85, 'id', 'Tulisan guru sendiri.'))
        self.client.post(self.url, {'ta': TA, 'sem': 2, 'nilai_akhir': '120', 'bahasa': 'en', 'deskripsi': 'x'})
        self.assertIsNone(NilaiRaporMapel.objects.get(ruang_kerja=self.ruang, siswa=self.siswa).nilai_akhir)
        self.assertEqual(NilaiRaporMapel.objects.count(), 1)

    def test_draf_lewat_json(self):
        self.client.force_login(self.guru)
        r = self.client.get(self.url, {'draf': '1', 'nilai': '95', 'bahasa': 'en'})
        self.assertIn('Ani', r.json()['draf'])

    def test_guru_lain_tidak_boleh_dan_siswa_ditolak(self):
        self.client.force_login(self.guru2)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        siswa_user = akun('siswa', 'siswa', self.sk)
        self.client.force_login(siswa_user)
        self.assertEqual(self.client.get(self.url).status_code, 302)


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class DaftarRapor(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sk = Sekolah.objects.create(nama='SD Contoh', kode='sdc')
        cls.lain = Sekolah.objects.create(nama='SD Lain', kode='sdl')
        cls.kepsek = akun('kepsek', 'kepsek', cls.sk)
        cls.user_siswa = akun('siswa', 'siswa', cls.sk)
        Siswa.objects.create(nama='Ani Putri', nis='1', kelas='4', sekolah=cls.sk, user=cls.user_siswa)
        Siswa.objects.create(nama='Budi Santoso', nis='2', kelas='5', sekolah=cls.sk)
        Siswa.objects.create(nama='Siswa Sekolah Lain', nis='3', kelas='4', sekolah=cls.lain)
        cls.url = reverse('ruang_kerja:rapor_daftar')

    def test_kepsek_melihat_siswa_sekolahnya_saja_dan_menu_rapor_tampil(self):
        self.client.force_login(self.kepsek)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual({s.nama for s in r.context['siswa']}, {'Ani Putri', 'Budi Santoso'})
        self.assertContains(r, reverse('ruang_kerja:rapor_daftar'))   # menu "Rapor" di sidebar

    def test_filter_kelas_dan_pencarian(self):
        self.client.force_login(self.kepsek)
        self.assertEqual([s.nama for s in self.client.get(self.url, {'kelas': '5'}).context['siswa']], ['Budi Santoso'])
        self.assertEqual([s.nama for s in self.client.get(self.url, {'q': 'ani'}).context['siswa']], ['Ani Putri'])

    def test_siswa_ditolak_dan_tidak_melihat_menu(self):
        self.client.force_login(self.user_siswa)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 302)
        r = self.client.get(reverse('kelas:dashboard'), follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, self.url)
