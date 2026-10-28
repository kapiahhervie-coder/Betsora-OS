import importlib
import inspect

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from accounts.models import User, Siswa
from ruang_kerja.models import (RuangKerja, Materi, SubMateri, Tugas, SubmisiTugas, AnggotaRuangKerja,
                                MataPelajaran, Kelas, SoalPG, PenilaianTopik, Pengumuman)


_AKUN = ('tambah_siswa', 'buat_akun_siswa', 'buat_akun_orangtua')


def url(fn, pk=None):
    """URL view berdasarkan nama fungsi (nama URL di proyek ini sama dengan nama fungsinya)."""
    app = 'accounts' if fn in _AKUN else 'ruang_kerja'
    if pk is None:
        return reverse(f'{app}:{fn}')
    param = list(inspect.signature(getattr(importlib.import_module(f'{app}.views'), fn)).parameters)[1]
    return reverse(f'{app}:{fn}', kwargs={param: pk})


def U(nama, role, **kw):
    return User.objects.create_user(username=nama, password='x', role=role, **kw)


class Dasar(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.guru = U('guru', 'guru')
        cls.kepsek = U('kepsek', 'kepsek')
        cls.su = User.objects.create_superuser('su', 'a@b.c', 'x')
        cls.s1 = Siswa.objects.create(nama='Ani', nis='1', kelas='X-1')
        cls.s2 = Siswa.objects.create(nama='Budi', nis='2', kelas='X-1')
        cls.siswa = U('siswa', 'siswa'); cls.s1.user = cls.siswa; cls.s1.save()
        cls.ortu = U('ortu', 'orangtua', anak=cls.s1)
        cls.kelas = Kelas.objects.create(nama='X-1')
        cls.ruang = RuangKerja.objects.create(mapel='MTK', kelas='X-1', kelas_baru=cls.kelas, guru=cls.guru)

    def buat(self):
        """Isi baru untuk tiap putaran; data putaran sebelumnya dibersihkan dulu."""
        for m in (Materi, Tugas, AnggotaRuangKerja, MataPelajaran):
            m.objects.all().delete()
        self.materi = Materi.objects.create(ruang_kerja=self.ruang, judul='M1', diunggah_oleh=self.guru)
        self.item = SubMateri.objects.create(materi=self.materi, judul='I1')
        self.tugas = Tugas.objects.create(ruang_kerja=self.ruang, judul='T1', instruksi='i', dibuat_oleh=self.guru)
        self.sub = SubmisiTugas.objects.create(tugas=self.tugas, siswa=self.s1, nilai=50)
        self.angg = AnggotaRuangKerja.objects.create(ruang_kerja=self.ruang, siswa=self.s1)
        self.mapel = MataPelajaran.objects.create(nama='Seni')
        self.soal = SoalPG.objects.create(tugas=self.tugas, pertanyaan='q')
        self.formatif = PenilaianTopik.objects.create(materi=self.materi, siswa=self.s1, jenis='formatif', nilai=10)

    def masuk(self, user):
        self.client.force_login(user)

    def hapus_semua(self):
        return [
            (url('hapus_tugas', self.tugas.id), Tugas, self.tugas.id),
            (url('hapus_topik', self.materi.id), Materi, self.materi.id),
            (url('hapus_formatif', self.formatif.id), PenilaianTopik, self.formatif.id),
            (url('hapus_item', self.item.id), SubMateri, self.item.id),
            (url('hapus_anggota', self.angg.id), AnggotaRuangKerja, self.angg.id),
            (url('hapus_mapel', self.mapel.id), MataPelajaran, self.mapel.id),
            (url('hapus_soal', self.soal.id), SoalPG, self.soal.id),
        ]


class HapusTerbalik(Dasar):
    def test_siswa_dan_ortu_tidak_bisa_menghapus(self):
        for pelaku in (self.siswa, self.ortu):
            self.buat(); self.masuk(pelaku)
            for u_, model, pk in self.hapus_semua():
                self.client.post(u_)
                self.assertTrue(model.objects.filter(pk=pk).exists(), f'{pelaku.role} berhasil menghapus lewat {u_}')

    def test_staf_bisa_menghapus(self):
        for pelaku in (self.guru, self.kepsek, self.su):
            self.buat(); self.masuk(pelaku)
            for u_, model, pk in self.hapus_semua():
                self.client.post(u_)
                self.assertFalse(model.objects.filter(pk=pk).exists(), f'{pelaku.role} gagal menghapus lewat {u_}')

    def test_get_tidak_menghapus(self):
        self.buat(); self.masuk(self.guru)
        for u_, model, pk in self.hapus_semua():
            self.client.get(u_)
            self.assertTrue(model.objects.filter(pk=pk).exists(), u_)


# Middleware pembatas orang tua dimatikan: yang diuji di sini adalah pemeriksaan di dalam view itu sendiri.
@override_settings(MIDDLEWARE=[m for m in settings.MIDDLEWARE if 'BatasiAksesOrangTua' not in m])
class OrangTuaBukanGuru(Dasar):
    def setUp(self):
        self.buat()

    def test_ortu_tidak_bisa_mengubah(self):
        self.masuk(self.ortu)
        c = self.client
        c.post(url('tambah_materi', self.ruang.id), {'judul': 'bocor'})
        self.assertFalse(Materi.objects.filter(judul='bocor').exists())
        c.post(url('tambah_pengumuman', self.ruang.id), {'isi': 'bocor'})
        self.assertEqual(Pengumuman.objects.count(), 0)
        c.post(url('tambah_tugas', self.ruang.id), {'judul': 'bocor', 'instruksi': 'x'})
        self.assertFalse(Tugas.objects.filter(judul='bocor').exists())
        c.post(url('nilai_submisi', self.sub.id), {'nilai': '100', 'feedback': 'x'})
        self.sub.refresh_from_db(); self.assertEqual(float(self.sub.nilai), 50.0)
        c.post(url('izinkan_ulang', self.sub.id))
        self.sub.refresh_from_db(); self.assertFalse(self.sub.boleh_ulang)
        c.post(url('tambah_anggota', self.ruang.id), {'siswa_ids': [self.s2.id]})
        self.assertFalse(AnggotaRuangKerja.objects.filter(siswa=self.s2).exists())
        c.post(url('hapus_kelas', self.kelas.id))
        self.assertTrue(Kelas.objects.filter(pk=self.kelas.pk).exists())
        c.post(url('hapus_ruang_kerja', self.ruang.id))
        self.assertTrue(RuangKerja.objects.filter(pk=self.ruang.pk).exists())
        c.post(url('tambah_soal', self.tugas.id), {'pertanyaan': 'bocor', 'opsi_teks': ['a', 'b']})
        self.assertFalse(SoalPG.objects.filter(pertanyaan='bocor').exists())
        c.post(url('duplikat_materi', self.materi.id))
        self.assertEqual(Materi.objects.count(), 1)
        c.post(url('tambah_mapel'), {'nama': 'bocor'})
        self.assertFalse(MataPelajaran.objects.filter(nama='bocor').exists())
        c.post(url('tambah_kelas'), {'nama': 'bocor'})
        self.assertFalse(Kelas.objects.filter(nama='bocor').exists())

    def test_ortu_ditolak_di_halaman_kelola(self):
        self.masuk(self.ortu)
        for u in (url('kelola_anggota', self.ruang.id), url('kelola_soal', self.tugas.id),
                  url('kelola_mapel'), url('kelola_kelas'), url('rapor_ruang_kerja', self.ruang.id)):
            r = self.client.get(u)
            self.assertEqual(r.status_code, 302, u)

    def test_siswa_tetap_ditolak(self):
        self.masuk(self.siswa)
        self.client.post(url('tambah_materi', self.ruang.id), {'judul': 'bocor'})
        self.assertFalse(Materi.objects.filter(judul='bocor').exists())
        self.client.post(url('nilai_submisi', self.sub.id), {'nilai': '100'})
        self.sub.refresh_from_db(); self.assertEqual(float(self.sub.nilai), 50.0)


class GuruTidakTerganggu(Dasar):
    def setUp(self):
        self.buat()

    def test_guru_masih_bisa_bekerja(self):
        for pelaku in (self.guru, self.kepsek, self.su):
            self.masuk(pelaku)
            self.client.post(url('tambah_materi', self.ruang.id), {'judul': 'baru-' + pelaku.username})
            self.assertTrue(Materi.objects.filter(judul='baru-' + pelaku.username).exists(), pelaku.role)
            self.client.post(url('nilai_submisi', self.sub.id), {'nilai': '77', 'feedback': 'ok'})
            self.sub.refresh_from_db(); self.assertEqual(float(self.sub.nilai), 77.0)
            self.client.post(url('izinkan_ulang', self.sub.id))
            self.sub.refresh_from_db(); self.assertTrue(self.sub.boleh_ulang)
            self.sub.boleh_ulang = False; self.sub.save()


class AkunSiswa(Dasar):
    def test_tambah_siswa_valid_dan_tidak_valid(self):
        self.masuk(self.guru)
        n = Siswa.objects.count()
        r = self.client.post(url('tambah_siswa'), {'nama': 'Cici', 'nis': '3', 'kelas': 'X-2'})
        self.assertEqual(Siswa.objects.count(), n + 1)
        self.assertEqual(r.status_code, 302)
        for data in ({'nama': 'Dodo', 'nis': '3', 'kelas': 'X-2'},          # NIS ganda
                     {'nama': 'Dodo', 'nis': '', 'kelas': 'X-2'},           # kosong
                     {'nama': 'Dodo'},                                        # field hilang
                     {'nama': 'D', 'nis': 'x' * 21, 'kelas': 'X'},           # terlalu panjang
                     {'nama': 'D', 'nis': '9', 'kelas': 'k' * 11}):
            r = self.client.post(url('tambah_siswa'), data)
            self.assertEqual(r.status_code, 200, data)
            self.assertEqual(Siswa.objects.count(), n + 1, data)

    def test_spasi_dipangkas(self):
        self.masuk(self.guru)
        self.client.post(url('tambah_siswa'), {'nama': ' Eka ', 'nis': ' 5 ', 'kelas': ' X '})
        s = Siswa.objects.get(nis='5'); self.assertEqual((s.nama, s.kelas), ('Eka', 'X'))

    def test_username_bentrok_tidak_error_500(self):
        self.masuk(self.guru)
        U('2', 'guru')                       # username sama dengan NIS siswa s2
        r = self.client.post(url('buat_akun_siswa', self.s2.id))
        self.assertEqual(r.status_code, 302)
        self.s2.refresh_from_db(); self.assertIsNone(self.s2.user)
        U('ortu2', 'guru')
        r = self.client.post(url('buat_akun_orangtua', self.s2.id))
        self.assertEqual(r.status_code, 302)
        self.assertFalse(User.objects.filter(role='orangtua', anak=self.s2).exists())

    def test_buat_akun_normal_masih_jalan(self):
        self.masuk(self.guru)
        self.client.post(url('buat_akun_siswa', self.s2.id))
        self.s2.refresh_from_db(); self.assertIsNotNone(self.s2.user)
        self.client.post(url('buat_akun_orangtua', self.s2.id))
        self.assertTrue(User.objects.filter(role='orangtua', anak=self.s2).exists())
