import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import AlbumAudio, Audio, SumberDigital, Zona

# Semua file yang diunggah selama tes ditulis ke folder sementara, bukan ke MEDIA_ROOT asli.
MEDIA_SEMENTARA = tempfile.mkdtemp(prefix='tes_perpustakaan_')

PERAN_STAF = ['guru', 'kepsek', 'admin']
PERAN_BUKAN_STAF = ['siswa', 'orangtua']


def buat_user(role):
    # ASUMSI: model User punya field `role` dan create_user menerimanya sebagai kwarg.
    User = get_user_model()
    return User.objects.create_user(username=f'user_{role}', password='rahasia123', role=role)


@override_settings(MEDIA_ROOT=MEDIA_SEMENTARA)
class IzinAlbumTest(TestCase):

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_SEMENTARA, ignore_errors=True)

    def masuk_sebagai(self, role):
        user = buat_user(role)
        self.client.force_login(user)
        return user

    def file_audio(self):
        return SimpleUploadedFile('lagu.mp3', b'ID3-palsu', content_type='audio/mpeg')

    # --- buat album ---

    def test_staf_boleh_membuat_album(self):
        for role in PERAN_STAF:
            with self.subTest(role=role):
                AlbumAudio.objects.all().delete()
                self.client.logout()
                User = get_user_model()
                User.objects.filter(username=f'user_{role}').delete()
                self.masuk_sebagai(role)
                self.client.post(reverse('perpustakaan:buat'), {'judul': 'Album A'})
                self.assertEqual(AlbumAudio.objects.count(), 1)

    def test_non_staf_tidak_boleh_membuat_album(self):
        for role in PERAN_BUKAN_STAF:
            with self.subTest(role=role):
                self.client.logout()
                get_user_model().objects.filter(username=f'user_{role}').delete()
                self.masuk_sebagai(role)
                self.client.post(reverse('perpustakaan:buat'), {'judul': 'Album X'})
                self.assertEqual(AlbumAudio.objects.count(), 0)

    def test_judul_kosong_tidak_menyebabkan_error_500(self):
        self.masuk_sebagai('guru')
        resp = self.client.post(reverse('perpustakaan:buat'), {'judul': '   '})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(AlbumAudio.objects.count(), 0)

    # --- tambah audio ---

    def test_guru_boleh_menambah_audio(self):
        guru = self.masuk_sebagai('guru')
        album = AlbumAudio.objects.create(judul='A', dibuat_oleh=guru)
        self.client.post(
            reverse('perpustakaan:detail', args=[album.id]),
            {'judul': 'Lagu 1', 'file': self.file_audio()},
        )
        self.assertEqual(Audio.objects.filter(album=album).count(), 1)

    def test_siswa_tidak_boleh_menambah_audio(self):
        album = AlbumAudio.objects.create(judul='A')
        self.masuk_sebagai('siswa')
        self.client.post(
            reverse('perpustakaan:detail', args=[album.id]),
            {'judul': 'Lagu 1', 'file': self.file_audio()},
        )
        self.assertEqual(Audio.objects.count(), 0)

    def test_orangtua_tidak_boleh_menambah_audio(self):
        album = AlbumAudio.objects.create(judul='A')
        self.masuk_sebagai('orangtua')
        self.client.post(
            reverse('perpustakaan:detail', args=[album.id]),
            {'judul': 'Lagu 1', 'file': self.file_audio()},
        )
        self.assertEqual(Audio.objects.count(), 0)

    def test_tambah_audio_tanpa_file_tidak_error_500(self):
        guru = self.masuk_sebagai('guru')
        album = AlbumAudio.objects.create(judul='A', dibuat_oleh=guru)
        resp = self.client.post(reverse('perpustakaan:detail', args=[album.id]), {'judul': 'Tanpa file'})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Audio.objects.count(), 0)

    # --- hapus album / audio ---

    def test_guru_boleh_menghapus_album(self):
        album = AlbumAudio.objects.create(judul='A')
        self.masuk_sebagai('guru')
        self.client.post(reverse('perpustakaan:hapus_album', args=[album.id]))
        self.assertFalse(AlbumAudio.objects.filter(id=album.id).exists())

    def test_siswa_tidak_boleh_menghapus_album(self):
        album = AlbumAudio.objects.create(judul='A')
        self.masuk_sebagai('siswa')
        self.client.post(reverse('perpustakaan:hapus_album', args=[album.id]))
        self.assertTrue(AlbumAudio.objects.filter(id=album.id).exists())

    def test_orangtua_tidak_boleh_menghapus_album(self):
        album = AlbumAudio.objects.create(judul='A')
        self.masuk_sebagai('orangtua')
        self.client.post(reverse('perpustakaan:hapus_album', args=[album.id]))
        self.assertTrue(AlbumAudio.objects.filter(id=album.id).exists())

    def test_guru_boleh_menghapus_audio(self):
        album = AlbumAudio.objects.create(judul='A')
        audio = Audio.objects.create(album=album, judul='L', file=self.file_audio())
        self.masuk_sebagai('guru')
        self.client.post(reverse('perpustakaan:hapus_audio', args=[audio.id]))
        self.assertFalse(Audio.objects.filter(id=audio.id).exists())

    def test_siswa_tidak_boleh_menghapus_audio(self):
        album = AlbumAudio.objects.create(judul='A')
        audio = Audio.objects.create(album=album, judul='L', file=self.file_audio())
        self.masuk_sebagai('siswa')
        self.client.post(reverse('perpustakaan:hapus_audio', args=[audio.id]))
        self.assertTrue(Audio.objects.filter(id=audio.id).exists())

    def test_hapus_lewat_get_tidak_menghapus(self):
        album = AlbumAudio.objects.create(judul='A')
        self.masuk_sebagai('guru')
        self.client.get(reverse('perpustakaan:hapus_album', args=[album.id]))
        self.assertTrue(AlbumAudio.objects.filter(id=album.id).exists())

    # --- belum login ---

    def test_anonim_diarahkan_ke_login(self):
        album = AlbumAudio.objects.create(judul='A')
        resp = self.client.post(reverse('perpustakaan:hapus_album', args=[album.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp.url)
        self.assertTrue(AlbumAudio.objects.filter(id=album.id).exists())


@override_settings(MEDIA_ROOT=MEDIA_SEMENTARA)
class IzinZonaSumberTest(TestCase):
    """Konsistensi izin di zona/sumber: hanya staf yang boleh mengubah data."""

    def masuk_sebagai(self, role):
        self.client.force_login(buat_user(role))

    def test_orangtua_tidak_boleh_menghapus_zona(self):
        zona = Zona.objects.create(nama='Z')
        self.masuk_sebagai('orangtua')
        self.client.post(reverse('perpustakaan:hapus_zona', args=[zona.id]))
        self.assertTrue(Zona.objects.filter(id=zona.id).exists())

    def test_siswa_tidak_boleh_menambah_zona(self):
        self.masuk_sebagai('siswa')
        self.client.post(reverse('perpustakaan:tambah_zona'), {'nama': 'Z'})
        self.assertEqual(Zona.objects.count(), 0)

    def test_guru_boleh_menambah_dan_menghapus_zona(self):
        self.masuk_sebagai('guru')
        self.client.post(reverse('perpustakaan:tambah_zona'), {'nama': 'Z'})
        zona = Zona.objects.get()
        self.client.post(reverse('perpustakaan:hapus_zona', args=[zona.id]))
        self.assertEqual(Zona.objects.count(), 0)

    def test_siswa_tidak_boleh_menghapus_sumber(self):
        zona = Zona.objects.create(nama='Z')
        sumber = SumberDigital.objects.create(zona=zona, judul='S')
        self.masuk_sebagai('siswa')
        self.client.post(reverse('perpustakaan:hapus_sumber', args=[sumber.id]))
        self.assertTrue(SumberDigital.objects.filter(id=sumber.id).exists())

    def test_siswa_tidak_boleh_mengedit_sumber(self):
        zona = Zona.objects.create(nama='Z')
        sumber = SumberDigital.objects.create(zona=zona, judul='Asli')
        self.masuk_sebagai('siswa')
        self.client.post(reverse('perpustakaan:edit_sumber', args=[sumber.id]), {'judul': 'Diubah'})
        sumber.refresh_from_db()
        self.assertEqual(sumber.judul, 'Asli')