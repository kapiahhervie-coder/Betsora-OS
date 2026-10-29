import glob
import importlib.util
import os
from io import StringIO

from django.apps import apps as registri_apps
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import Siswa, Sekolah, User
from pengaturan.models import PengaturanSekolah
from penilaian.models import SesiPenilaian
from perpustakaan.models import AlbumAudio, Lencana, Zona
from ruang_kerja.models import Kelas, MataPelajaran, RuangKerja


def _kosongkan():
    """Basis data uji kadang berisi data bawaan; tes migrasi data butuh keadaan kosong yang pasti."""
    for m in (SesiPenilaian, RuangKerja, Kelas, MataPelajaran, Zona, AlbumAudio, Lencana, Siswa, PengaturanSekolah):
        m.objects.all().delete()
    User.objects.filter(is_superuser=False).delete()
    Sekolah.objects.all().delete()


def _muat_migrasi_data():
    """Memuat berkas migrasi *_isi_sekolah_awal.py (namanya diawali angka, jadi tidak bisa di-import biasa)."""
    folder = os.path.join(os.path.dirname(__file__), 'migrations')
    ada = glob.glob(os.path.join(folder, '*_isi_sekolah_awal.py'))
    assert len(ada) == 1, 'migrasi isi_sekolah_awal tidak ditemukan / ganda'
    spek = importlib.util.spec_from_file_location('isi_sekolah_awal_uji', ada[0])
    modul = importlib.util.module_from_spec(spek)
    spek.loader.exec_module(modul)
    return modul


class BatasanUnikPerSekolah(TestCase):
    @classmethod
    def setUpTestData(cls):
        _kosongkan()
        cls.a = Sekolah.objects.create(nama='Sekolah A', kode='a')
        cls.b = Sekolah.objects.create(nama='Sekolah B', kode='b')

    def gagal(self, fungsi):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                fungsi()

    def test_nis_sama_boleh_di_sekolah_berbeda(self):
        Siswa.objects.create(nama='Ani', nis='1', kelas='3', sekolah=self.a)
        Siswa.objects.create(nama='Ani B', nis='1', kelas='3', sekolah=self.b)
        self.assertEqual(Siswa.objects.filter(nis='1').count(), 2)

    def test_nis_sama_di_satu_sekolah_ditolak(self):
        Siswa.objects.create(nama='Ani', nis='1', kelas='3', sekolah=self.a)
        self.gagal(lambda: Siswa.objects.create(nama='Dobel', nis='1', kelas='3', sekolah=self.a))

    def test_nis_ganda_tanpa_sekolah_tetap_ditolak(self):
        Siswa.objects.create(nama='Ani', nis='7', kelas='3')
        self.gagal(lambda: Siswa.objects.create(nama='Dobel', nis='7', kelas='3'))

    def test_kelas_per_sekolah(self):
        Kelas.objects.create(nama='X-1', sekolah=self.a)
        Kelas.objects.create(nama='X-1', sekolah=self.b)
        self.gagal(lambda: Kelas.objects.create(nama='X-1', sekolah=self.a))
        Kelas.objects.create(nama='Z')
        self.gagal(lambda: Kelas.objects.create(nama='Z'))

    def test_mapel_per_sekolah(self):
        MataPelajaran.objects.create(nama='Seni', sekolah=self.a)
        MataPelajaran.objects.create(nama='Seni', sekolah=self.b)
        self.gagal(lambda: MataPelajaran.objects.create(nama='Seni', sekolah=self.a))

    def test_ruang_kerja_mapel_kelas_per_sekolah(self):
        RuangKerja.objects.create(mapel='MTK', kelas='3', sekolah=self.a)
        RuangKerja.objects.create(mapel='MTK', kelas='3', sekolah=self.b)
        self.gagal(lambda: RuangKerja.objects.create(mapel='MTK', kelas='3', sekolah=self.a))
        RuangKerja.objects.create(mapel='IPA', kelas='3')
        self.gagal(lambda: RuangKerja.objects.create(mapel='IPA', kelas='3'))

    def test_sekolah_tidak_bisa_dihapus_bila_masih_ada_data(self):
        Siswa.objects.create(nama='Ani', nis='1', kelas='3', sekolah=self.a)
        from django.db.models import ProtectedError
        with self.assertRaises(ProtectedError):
            self.a.delete()

    def test_kode_sekolah_unik(self):
        self.gagal(lambda: Sekolah.objects.create(nama='Lain', kode='a'))


class MigrasiDataSekolahAwal(TestCase):
    def setUp(self):
        _kosongkan()
        self.modul = _muat_migrasi_data()

    def jalankan(self):
        self.modul.isi_sekolah_awal(registri_apps, None)

    def test_database_kosong_tidak_membuat_sekolah(self):
        self.jalankan()
        self.assertEqual(Sekolah.objects.count(), 0)

    def test_hanya_superuser_tidak_membuat_sekolah(self):
        User.objects.create_superuser('root', 'r@x.id', 'x')
        self.jalankan()
        self.assertEqual(Sekolah.objects.count(), 0)

    def test_data_lama_ditandai_satu_sekolah_awal(self):
        su = User.objects.create_superuser('root', 'r@x.id', 'x')
        guru = User.objects.create_user('g', password='x', role='guru')
        siswa = Siswa.objects.create(nama='Ani', nis='1', kelas='3')
        kelas = Kelas.objects.create(nama='3')
        rk = RuangKerja.objects.create(mapel='MTK', kelas='3', guru=guru)
        mp = MataPelajaran.objects.create(nama='Seni')
        sp = SesiPenilaian.objects.create(mapel='MTK', jenis='formatif', topik='t', kelas='3', guru=guru)
        zona = Zona.objects.create(nama='Z'); alb = AlbumAudio.objects.create(judul='A'); len_ = Lencana.objects.create(nama='L')
        peng, _ = PengaturanSekolah.objects.update_or_create(pk=1, defaults={'nama_institusi': 'SD Harapan Bangsa'})

        self.jalankan()

        self.assertEqual(Sekolah.objects.count(), 1)
        s = Sekolah.objects.get()
        self.assertEqual((s.nama, s.kode), ('SD Harapan Bangsa', 'sd-harapan-bangsa'))
        for obj in (guru, siswa, kelas, rk, mp, sp, zona, alb, len_, peng):
            obj.refresh_from_db()
            self.assertEqual(obj.sekolah_id, s.id, repr(obj))
        su.refresh_from_db()
        self.assertIsNone(su.sekolah_id)        # admin platform tidak milik sekolah mana pun

    def test_nama_cadangan_tanpa_pengaturan(self):
        Siswa.objects.create(nama='Ani', nis='1', kelas='3')
        self.jalankan()
        s = Sekolah.objects.get()
        self.assertEqual((s.nama, s.kode), ('Sekolah Awal', 'sekolah-awal'))

    def test_dijalankan_dua_kali_aman(self):
        Siswa.objects.create(nama='Ani', nis='1', kelas='3')
        self.jalankan(); self.jalankan()
        self.assertEqual(Sekolah.objects.count(), 1)

    def test_sudah_ada_beberapa_sekolah_data_yatim_dibiarkan(self):
        a = Sekolah.objects.create(nama='A', kode='a')
        Sekolah.objects.create(nama='B', kode='b')
        milik_a = Siswa.objects.create(nama='Citra', nis='9', kelas='3', sekolah=a)
        yatim = Siswa.objects.create(nama='Yatim', nis='1', kelas='3')
        self.jalankan()
        milik_a.refresh_from_db(); yatim.refresh_from_db()
        self.assertEqual(milik_a.sekolah_id, a.id)
        self.assertIsNone(yatim.sekolah_id)           # tidak ditebak

    def test_tepat_satu_sekolah_ada_dipakai_untuk_data_yatim(self):
        a = Sekolah.objects.create(nama='A', kode='a')
        yatim = Siswa.objects.create(nama='Yatim', nis='1', kelas='3')
        self.jalankan()
        yatim.refresh_from_db()
        self.assertEqual(yatim.sekolah_id, a.id)
        self.assertEqual(Sekolah.objects.count(), 1)


class PerintahPeriksaSekolah(TestCase):
    def setUp(self):
        _kosongkan()

    def keluaran(self, *arg):
        o = StringIO()
        call_command('periksa_sekolah', *arg, stdout=o)
        return o.getvalue()

    def test_laporan_data_yatim_dan_per_sekolah(self):
        s = Sekolah.objects.create(nama='Sekolah A', kode='a')
        Siswa.objects.create(nama='Ani', nis='1', kelas='3', sekolah=s)
        Siswa.objects.create(nama='Yatim', nis='2', kelas='3')
        out = self.keluaran()
        self.assertIn('accounts.Siswa: 1', out)
        self.assertIn('[a] Sekolah A', out)
        self.assertIn('siswa=1', out)

    def test_ketat_gagal_bila_ada_yatim(self):
        Siswa.objects.create(nama='Yatim', nis='2', kelas='3')
        with self.assertRaises(CommandError):
            self.keluaran('--ketat')

    def test_ketat_lulus_bila_bersih(self):
        s = Sekolah.objects.create(nama='Sekolah A', kode='a')
        Siswa.objects.create(nama='Ani', nis='1', kelas='3', sekolah=s)
        User.objects.create_superuser('root', 'r@x.id', 'x')       # superuser tanpa sekolah bukan yatim
        self.assertIn('Selesai.', self.keluaran('--ketat'))
