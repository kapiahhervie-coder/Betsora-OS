import shutil
import tempfile
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.conf import settings
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from accounts.models import Siswa
from kelas.models import Absensi, Keaktifan
from penilaian.models import Nilai, SesiPenilaian

from .models import KaryaSiswa

User = get_user_model()

# Middleware project ini mengalihkan akun orang tua dari semua halaman di luar dashboard dan misi.
# Tes logika view orang tua dijalankan dengan middleware itu dimatikan, supaya yang diuji
# adalah view-nya sendiri (lapisan pertahanan kedua).
MIDDLEWARE_ORTU = "accounts.middleware.BatasiAksesOrangTuaMiddleware"
TANPA_BATASAN_ORTU = override_settings(
    MIDDLEWARE=[m for m in settings.MIDDLEWARE if m != MIDDLEWARE_ORTU]
)

PAYLOAD_XSS = "x');window.__pwned=1;//"
PNG_KECIL = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def buat_user(username, role, **kw):
    return User.objects.create_user(username, password="x", role=role, **kw)


class DasarPortofolio(TestCase):
    @classmethod
    def setUpClass(cls):
        # Unggahan saat tes tidak boleh menulis ke folder media yang asli.
        folder = tempfile.mkdtemp()
        cls.addClassCleanup(shutil.rmtree, folder, True)
        ganti = override_settings(MEDIA_ROOT=folder)
        ganti.enable()
        cls.addClassCleanup(ganti.disable)
        super().setUpClass()

    @classmethod
    def setUpTestData(cls):
        cls.guru = buat_user("guru1", "guru")
        cls.user_a = buat_user("siswa_a", "siswa")
        cls.a = Siswa.objects.create(user=cls.user_a, nama="Anak A", nis="1", kelas="3A")
        cls.user_b = buat_user("siswa_b", "siswa")
        cls.b = Siswa.objects.create(user=cls.user_b, nama="Anak B", nis="2", kelas="3A")
        cls.ortu_a = buat_user("ortu_a", "orangtua", anak=cls.a)
        cls.ortu_b = buat_user("ortu_b", "orangtua", anak=cls.b)

        sesi = SesiPenilaian.objects.create(
            mapel="Matematika", jenis="formatif", topik="TOPIK-RAHASIA-A", kelas="3A", guru=cls.guru
        )
        Nilai.objects.create(sesi=sesi, siswa=cls.a, skor=88)
        Absensi.objects.create(siswa=cls.a, status="hadir")
        Keaktifan.objects.create(siswa=cls.a, poin=7)

        cls.karya_publik = KaryaSiswa.objects.create(siswa=cls.a, judul="Karya Publik A", dibagikan=True)
        cls.karya_privat = KaryaSiswa.objects.create(siswa=cls.a, judul="Karya Privat A", dibagikan=False)

    def buka_detail(self, user, siswa=None):
        self.client.force_login(user)
        return self.client.get(reverse("portofolio:detail", args=[(siswa or self.a).id]))


class AksesDetailTests(DasarPortofolio):
    def test_anonim_dialihkan_ke_login(self):
        resp = self.client.get(reverse("portofolio:detail", args=[self.a.id]))
        self.assertEqual(resp.status_code, 302)

    def test_guru_melihat_semuanya(self):
        resp = self.buka_detail(self.guru)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "TOPIK-RAHASIA-A")
        self.assertContains(resp, "Karya Publik A")
        self.assertContains(resp, "Karya Privat A")

    def test_pemilik_melihat_semuanya_termasuk_karya_privat(self):
        resp = self.buka_detail(self.user_a)
        self.assertContains(resp, "TOPIK-RAHASIA-A")
        self.assertContains(resp, "Karya Privat A")

    def test_siswa_lain_hanya_melihat_karya_yang_dibagikan(self):
        resp = self.buka_detail(self.user_b)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Karya Publik A")
        self.assertNotContains(resp, "Karya Privat A")

    def test_siswa_lain_tidak_melihat_nilai_dan_absensi(self):
        resp = self.buka_detail(self.user_b)
        self.assertNotContains(resp, "TOPIK-RAHASIA-A")

    def test_orang_tua_tidak_menerima_portofolio_anak_lain(self):
        """Dengan pengaturan asli project (middleware aktif): dialihkan (302) atau ditolak (403)."""
        resp = self.buka_detail(self.ortu_b)
        self.assertIn(resp.status_code, (302, 403))
        self.assertNotContains(resp, "TOPIK-RAHASIA-A", status_code=resp.status_code)

    @TANPA_BATASAN_ORTU
    def test_view_menolak_orang_tua_anak_lain(self):
        resp = self.buka_detail(self.ortu_b)
        self.assertEqual(resp.status_code, 403)

    @TANPA_BATASAN_ORTU
    def test_view_orang_tua_anak_sendiri_melihat_nilai(self):
        resp = self.buka_detail(self.ortu_a)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "TOPIK-RAHASIA-A")

    @TANPA_BATASAN_ORTU
    def test_view_orang_tua_hanya_melihat_karya_dibagikan_sesuai_perilaku_lama(self):
        resp = self.buka_detail(self.ortu_a)
        self.assertContains(resp, "Karya Publik A")
        self.assertNotContains(resp, "Karya Privat A")


class HapusKaryaTests(DasarPortofolio):
    def url_hapus(self, karya):
        return reverse("portofolio:hapus_karya", args=[karya.id])

    def test_get_tidak_menghapus(self):
        self.client.force_login(self.user_a)
        resp = self.client.get(self.url_hapus(self.karya_privat))
        self.assertEqual(resp.status_code, 405)
        self.assertTrue(KaryaSiswa.objects.filter(id=self.karya_privat.id).exists())

    def test_pemilik_bisa_menghapus(self):
        self.client.force_login(self.user_a)
        self.client.post(self.url_hapus(self.karya_privat))
        self.assertFalse(KaryaSiswa.objects.filter(id=self.karya_privat.id).exists())

    def test_guru_bisa_menghapus(self):
        self.client.force_login(self.guru)
        self.client.post(self.url_hapus(self.karya_publik))
        self.assertFalse(KaryaSiswa.objects.filter(id=self.karya_publik.id).exists())

    def test_siswa_lain_tidak_bisa_menghapus(self):
        self.client.force_login(self.user_b)
        self.client.post(self.url_hapus(self.karya_publik))
        self.assertTrue(KaryaSiswa.objects.filter(id=self.karya_publik.id).exists())

    def test_orang_tua_tidak_bisa_menghapus(self):
        self.client.force_login(self.ortu_a)
        self.client.post(self.url_hapus(self.karya_publik))
        self.assertTrue(KaryaSiswa.objects.filter(id=self.karya_publik.id).exists())

    @TANPA_BATASAN_ORTU
    def test_tombol_hapus_tidak_tampil_untuk_orang_tua_dan_siswa_lain(self):
        for user in (self.ortu_a, self.user_b):
            resp = self.buka_detail(user)
            self.assertNotContains(resp, self.url_hapus(self.karya_publik), msg_prefix=user.username)

    def test_tombol_hapus_tampil_untuk_pemilik_dan_guru(self):
        for user in (self.user_a, self.guru):
            resp = self.buka_detail(user)
            self.assertContains(resp, self.url_hapus(self.karya_publik), msg_prefix=user.username)


class VideoAmanTests(DasarPortofolio):
    def embed(self, url):
        return KaryaSiswa(video_url=url).get_video_embed()

    def test_youtube_dan_drive_yang_sah(self):
        self.assertEqual(self.embed("https://youtu.be/dQw4w9WgXcQ"), "https://www.youtube.com/embed/dQw4w9WgXcQ")
        self.assertEqual(
            self.embed("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=3"),
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
        )
        self.assertEqual(
            self.embed("https://www.youtube.com/embed/dQw4w9WgXcQ"),
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
        )
        self.assertEqual(
            self.embed("https://drive.google.com/file/d/1AbC_dEf-123456789/view?usp=sharing"),
            "https://drive.google.com/file/d/1AbC_dEf-123456789/preview",
        )

    def test_url_berbahaya_atau_asing_dikosongkan(self):
        for url in (PAYLOAD_XSS, "javascript:alert(1)", "data:text/html,<script>1</script>",
                    "https://evil.example/video", "https://youtube.com.evil.example/watch?v=dQw4w9WgXcQ",
                    "ftp://youtu.be/dQw4w9WgXcQ", ""):
            self.assertEqual(self.embed(url), "", msg=url)

    def test_data_lama_berbahaya_tidak_mencapai_halaman(self):
        KaryaSiswa.objects.create(siswa=self.a, judul="Lama", video_url=PAYLOAD_XSS)
        KaryaSiswa.objects.create(siswa=self.a, judul="Lama2", video_url="javascript:alert(1)")
        resp = self.buka_detail(self.guru)
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "__pwned")
        self.assertNotContains(resp, "javascript:alert")

    def test_halaman_tidak_memakai_onclick_berisi_url_video(self):
        KaryaSiswa.objects.create(siswa=self.a, judul="Sah", video_url="https://youtu.be/dQw4w9WgXcQ")
        resp = self.buka_detail(self.guru)
        self.assertContains(resp, "https://www.youtube.com/embed/dQw4w9WgXcQ")
        self.assertNotContains(resp, 'onclick="bukaVideoModal')


class TambahKaryaTests(DasarPortofolio):
    def kirim(self, **data):
        self.client.force_login(self.user_a)
        awal = KaryaSiswa.objects.count()
        self.client.post(reverse("portofolio:tambah_karya"), data)
        return KaryaSiswa.objects.count() - awal

    def test_video_youtube_sah_diterima(self):
        self.assertEqual(self.kirim(judul="V", video_url="https://youtu.be/dQw4w9WgXcQ"), 1)

    def test_video_berbahaya_ditolak(self):
        self.assertEqual(self.kirim(judul="V", video_url=PAYLOAD_XSS), 0)
        self.assertEqual(self.kirim(judul="V", video_url="javascript:alert(1)"), 0)
        self.assertEqual(self.kirim(judul="V", video_url="https://evil.example/x"), 0)

    def test_judul_kosong_ditolak(self):
        self.assertEqual(self.kirim(judul="  ", video_url="https://youtu.be/dQw4w9WgXcQ"), 0)

    def test_judul_terlalu_panjang_ditolak(self):
        self.assertEqual(self.kirim(judul="x" * 151, video_url="https://youtu.be/dQw4w9WgXcQ"), 0)

    def test_gambar_sah_diterima(self):
        berkas = SimpleUploadedFile("foto.png", PNG_KECIL, content_type="image/png")
        self.assertEqual(self.kirim(judul="Foto", file=berkas), 1)

    def test_jenis_file_berbahaya_ditolak(self):
        for nama in ("a.html", "a.svg", "a.exe", "a.php", "a.js"):
            berkas = SimpleUploadedFile(nama, b"<script>1</script>")
            self.assertEqual(self.kirim(judul="X", file=berkas), 0, msg=nama)

    def test_file_terlalu_besar_ditolak(self):
        berkas = SimpleUploadedFile("foto.png", PNG_KECIL, content_type="image/png")
        with mock.patch("portofolio.validasi.UKURAN_MAKS_BYTE", 10):
            self.assertEqual(self.kirim(judul="Besar", file=berkas), 0)

    def test_hanya_siswa_yang_bisa_mengunggah(self):
        self.client.force_login(self.guru)
        self.client.post(reverse("portofolio:tambah_karya"), {"judul": "Guru", "video_url": "https://youtu.be/dQw4w9WgXcQ"})
        self.assertFalse(KaryaSiswa.objects.filter(judul="Guru").exists())


class DaftarTests(DasarPortofolio):
    def hitung_query(self):
        self.client.force_login(self.guru)
        with CaptureQueriesContext(connection) as q:
            resp = self.client.get(reverse("portofolio:daftar"))
        self.assertEqual(resp.status_code, 200)
        return len(q)

    def test_jumlah_query_tidak_bertambah_seiring_jumlah_siswa(self):
        self.hitung_query()  # pemanasan: request pertama mengisi cache (sesi, content type, dll.)
        sedikit = self.hitung_query()
        for i in range(10):
            s = Siswa.objects.create(nama=f"Tambahan {i}", nis=f"9{i}", kelas="3A")
            Absensi.objects.create(siswa=s, status="hadir")
            Keaktifan.objects.create(siswa=s, poin=1)
        banyak = self.hitung_query()
        self.assertEqual(sedikit, banyak)

    def test_angka_ringkasan_tetap_benar(self):
        self.client.force_login(self.guru)
        resp = self.client.get(reverse("portofolio:daftar"))
        baris = {d["siswa"].id: d for d in resp.context["data"]}
        a = baris[self.a.id]
        self.assertEqual(a["kehadiran"], 100)
        self.assertEqual(float(a["avg_nilai"]), 88.0)
        self.assertEqual(a["total_poin"], 7)
        self.assertEqual(a["jumlah_nilai"], 1)
        b = baris[self.b.id]
        self.assertEqual(b["kehadiran"], 0)
        self.assertIsNone(b["avg_nilai"])
        self.assertEqual(b["total_poin"], 0)

    def test_filter_kelas(self):
        Siswa.objects.create(nama="Kelas Lain", nis="77", kelas="5B")
        self.client.force_login(self.guru)
        resp = self.client.get(reverse("portofolio:daftar"), {"kelas": "5B"})
        self.assertEqual([d["siswa"].nama for d in resp.context["data"]], ["Kelas Lain"])
