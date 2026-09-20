import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Siswa, User
from ruang_kerja.models import RuangKerja, SubmisiTugas, Tugas

from .fase_config import deteksi_jenjang, deteksi_tingkat
from .models import DeskriptorLevel, DimensiPenilaian, LampiranKarya, RefleksiKarya

TMP = tempfile.mkdtemp()


class DeteksiJenjangTest(TestCase):
    def test_format_yang_dipakai_sekolah(self):
        kasus = {
            '1': (1, 'sd_awal'), '3': (3, 'sd_awal'), '4': (4, 'sd_akhir'),
            'Kelas III': (3, 'sd_awal'), 'kelas vi': (6, 'sd_akhir'),
            '7A': (7, 'smp'), 'VIII B': (8, 'smp'), 'Kelas 9': (9, 'smp'),
            'X-1': (10, 'sma'), 'XI IPA 2': (11, 'sma'), 'XII IPS 3': (12, 'sma'),
            '10 IPA 1': (10, 'sma'),
        }
        for teks, (tingkat, jenjang) in kasus.items():
            self.assertEqual(deteksi_tingkat(teks), tingkat, teks)
            self.assertEqual(deteksi_jenjang(teks), jenjang, teks)

    def test_tidak_bisa_ditebak(self):
        for teks in ['', None, 'Kelas Bahasa Inggris', 'Kursus Coding', '13', '0']:
            self.assertIsNone(deteksi_jenjang(teks), teks)

    def test_ruang_kerja_pilihan_guru_menang(self):
        r = RuangKerja(mapel='IPA', kelas='Kelas III')
        self.assertEqual(r.get_jenjang(), 'sd_awal')
        r.jenjang = 'smp'
        self.assertEqual(r.get_jenjang(), 'smp')


class SeedTest(TestCase):
    def test_seed_idempoten_dan_tidak_menimpa_edit(self):
        call_command('seed_kreasi')
        self.assertEqual(DimensiPenilaian.objects.count(), 12)
        self.assertEqual(DeskriptorLevel.objects.count(), 48)
        d = DeskriptorLevel.objects.first()
        d.kalimat = 'EDIT GURU {nama}'
        d.save()
        call_command('seed_kreasi')
        self.assertEqual(DeskriptorLevel.objects.count(), 48)
        d.refresh_from_db()
        self.assertEqual(d.kalimat, 'EDIT GURU {nama}')
        self.assertEqual(d.untuk('Rani'), 'EDIT GURU Rani')


@override_settings(PRIVATE_MEDIA_ROOT=TMP)
class MediaPrivatTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.guru = User.objects.create_user('guru1', password='x', role='guru')
        cls.guru_lain = User.objects.create_user('guru2', password='x', role='guru')
        cls.kepsek = User.objects.create_user('kepsek', password='x', role='kepsek')
        cls.u_a = User.objects.create_user('siswa_a', password='x', role='siswa')
        cls.u_b = User.objects.create_user('siswa_b', password='x', role='siswa')
        cls.s_a = Siswa.objects.create(user=cls.u_a, nama='Ani', nis='1', kelas='3')
        cls.s_b = Siswa.objects.create(user=cls.u_b, nama='Budi', nis='2', kelas='3')
        cls.ortu_a = User.objects.create_user('ortu_a', password='x', role='orangtua', anak=cls.s_a)
        cls.ortu_b = User.objects.create_user('ortu_b', password='x', role='orangtua', anak=cls.s_b)
        ruang = RuangKerja.objects.create(mapel='Seni', kelas='Kelas III', guru=cls.guru)
        tugas = Tugas.objects.create(ruang_kerja=ruang, jenis='kreasi', judul='Maket', instruksi='x')
        cls.sub = SubmisiTugas.objects.create(tugas=tugas, siswa=cls.s_a)
        cls.isi = bytes(range(256)) * 40  # 10240 byte
        cls.foto = LampiranKarya.objects.create(
            submisi=cls.sub, tipe='foto', nama_asli='maket.png',
            file=SimpleUploadedFile('maket.png', cls.isi))
        cls.html = LampiranKarya.objects.create(
            submisi=cls.sub, tipe='dokumen', nama_asli='jahat.html',
            file=SimpleUploadedFile('jahat.html', b'<script>alert(1)</script>'))
        cls.rekam = RefleksiKarya.objects.create(
            submisi=cls.sub, tipe='emoji_suara', emoji='bangga',
            audio=SimpleUploadedFile('rekaman.webm', cls.isi))

    def url(self, jenis, obj):
        return reverse('kreasi:media', args=[jenis, obj.pk])

    def buka(self, user, jenis, obj, **kw):
        self.client.logout()
        if user:
            self.client.force_login(user)
        return self.client.get(self.url(jenis, obj), **kw)

    def test_hak_akses(self):
        boleh = [self.u_a, self.ortu_a, self.guru, self.kepsek]
        ditolak = [self.u_b, self.ortu_b, self.guru_lain]
        for u in boleh:
            self.assertEqual(self.buka(u, 'lampiran', self.foto).status_code, 200, u.username)
        for u in ditolak:
            self.assertEqual(self.buka(u, 'lampiran', self.foto).status_code, 403, u.username)

    def test_belum_login_diarahkan_ke_login(self):
        r = self.buka(None, 'lampiran', self.foto)
        self.assertEqual(r.status_code, 302)

    def test_tidak_ada_url_publik(self):
        self.assertEqual(self.foto.file.url, '')
        self.assertTrue(self.foto.url_akses.startswith('/kreasi/media/lampiran/'))
        # berkas fisik tidak berada di MEDIA_ROOT
        self.assertTrue(self.foto.file.path.startswith(TMP))

    def test_foto_tampil_inline_html_dipaksa_unduh(self):
        r = self.buka(self.guru, 'lampiran', self.foto)
        self.assertEqual(r['Content-Type'], 'image/png')
        self.assertTrue(r['Content-Disposition'].startswith('inline'))
        r = self.buka(self.guru, 'lampiran', self.html)
        self.assertTrue(r['Content-Disposition'].startswith('attachment'))

    def test_range_untuk_audio(self):
        r = self.buka(self.u_a, 'refleksi', self.rekam, headers={'Range': 'bytes=100-199'})
        self.assertEqual(r.status_code, 206)
        self.assertEqual(r['Content-Range'], 'bytes 100-199/10240')
        self.assertEqual(b''.join(r.streaming_content), self.isi[100:200])
        self.assertEqual(r['Content-Type'], 'audio/webm')
        r = self.buka(self.u_a, 'refleksi', self.rekam, headers={'Range': 'bytes=10000-'})
        self.assertEqual(b''.join(r.streaming_content), self.isi[10000:])
        r = self.buka(self.u_a, 'refleksi', self.rekam, headers={'Range': 'bytes=-50'})
        self.assertEqual(b''.join(r.streaming_content), self.isi[-50:])
        r = self.buka(self.u_a, 'refleksi', self.rekam, headers={'Range': 'bytes=99999-'})
        self.assertEqual(r.status_code, 416)

    def test_jenis_ngawur_dan_id_tidak_ada(self):
        self.client.force_login(self.guru)
        self.assertEqual(self.client.get('/kreasi/media/apa/1/').status_code, 404)
        self.assertEqual(self.client.get('/kreasi/media/lampiran/99999/').status_code, 404)

    def test_deteksi_tipe_lampiran(self):
        d = LampiranKarya.deteksi_tipe
        self.assertEqual(d('a.JPG'), 'foto')
        self.assertEqual(d('a.pdf'), 'dokumen')
        self.assertEqual(d('a.webm'), 'video')
        self.assertEqual(d('a.webm', petunjuk='audio'), 'audio')
        self.assertEqual(d('a.mp3', petunjuk='foto'), 'audio')  # petunjuk salah diabaikan
        self.assertIsNone(d('a.exe'))


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)
