"""Tes penyajian berkas karya lewat view beraturan izin (bukan alamat /media/ yang terbuka)."""
from django.core.files.base import ContentFile
from django.urls import reverse

from .models import KaryaSiswa
from .tests import DasarPortofolio, PNG_KECIL, TANPA_BATASAN_ORTU

ISI_HTML = b"<script>window.__pwned=1</script>"


def baca(resp):
    isi = b"".join(resp.streaming_content)
    return isi


class BerkasKaryaTests(DasarPortofolio):
    def setUp(self):
        self.foto_publik = KaryaSiswa(siswa=self.a, judul="Foto Publik", dibagikan=True)
        self.foto_publik.file.save("publik.png", ContentFile(PNG_KECIL), save=True)
        self.foto_privat = KaryaSiswa(siswa=self.a, judul="Foto Privat", dibagikan=False)
        self.foto_privat.file.save("privat.png", ContentFile(PNG_KECIL), save=True)

    def url(self, karya):
        return reverse("portofolio:berkas", args=[karya.id])

    def ambil(self, user, karya):
        self.client.force_login(user)
        return self.client.get(self.url(karya))

    def test_anonim_dialihkan_ke_login(self):
        resp = self.client.get(self.url(self.foto_publik))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp["Location"])

    def test_pemilik_dan_guru_melihat_berkas_privat(self):
        for user in (self.user_a, self.guru):
            resp = self.ambil(user, self.foto_privat)
            self.assertEqual(resp.status_code, 200, msg=user.username)
            self.assertEqual(baca(resp), PNG_KECIL)

    def test_siswa_lain_tidak_boleh_berkas_privat(self):
        self.assertEqual(self.ambil(self.user_b, self.foto_privat).status_code, 403)

    def test_siswa_lain_boleh_berkas_yang_dibagikan(self):
        resp = self.ambil(self.user_b, self.foto_publik)
        self.assertEqual(resp.status_code, 200)
        baca(resp)

    @TANPA_BATASAN_ORTU
    def test_orang_tua_sesuai_aturan_halaman_portofolio(self):
        # Orang tua anak sendiri: hanya yang dibagikan (perilaku lama dipertahankan).
        resp = self.ambil(self.ortu_a, self.foto_publik)
        self.assertEqual(resp.status_code, 200)
        baca(resp)
        self.assertEqual(self.ambil(self.ortu_a, self.foto_privat).status_code, 403)
        # Orang tua anak lain: tidak boleh sama sekali.
        self.assertEqual(self.ambil(self.ortu_b, self.foto_publik).status_code, 403)

    def test_gambar_dibuka_inline_dengan_perlindungan(self):
        resp = self.ambil(self.user_a, self.foto_publik)
        self.assertEqual(resp["Content-Type"], "image/png")
        self.assertTrue(resp["Content-Disposition"].startswith("inline"))
        self.assertEqual(resp["X-Content-Type-Options"], "nosniff")
        self.assertIn("private", resp["Cache-Control"])
        baca(resp)

    def test_berkas_lama_berbahaya_selalu_diunduh_bukan_dijalankan(self):
        for nama in ("lama.html", "lama.svg", "lama.htm"):
            karya = KaryaSiswa(siswa=self.a, judul=nama, dibagikan=True)
            karya.file.save(nama, ContentFile(ISI_HTML), save=True)
            resp = self.ambil(self.user_a, karya)
            self.assertEqual(resp.status_code, 200, msg=nama)
            self.assertTrue(resp["Content-Disposition"].startswith("attachment"), msg=nama)
            self.assertEqual(resp["X-Content-Type-Options"], "nosniff")
            baca(resp)

    def test_karya_tanpa_file_atau_berkas_hilang_404(self):
        tanpa = KaryaSiswa.objects.create(siswa=self.a, judul="Hanya Video", video_url="https://youtu.be/dQw4w9WgXcQ")
        self.assertEqual(self.ambil(self.user_a, tanpa).status_code, 404)
        self.foto_publik.file.delete(save=False)  # catatan masih ada, file di disk hilang
        KaryaSiswa.objects.filter(id=self.foto_publik.id).update(file="karya_siswa/tidak_ada.png")
        self.assertEqual(self.ambil(self.user_a, self.foto_publik).status_code, 404)

    def test_karya_tidak_ada_404(self):
        self.client.force_login(self.guru)
        self.assertEqual(self.client.get(reverse("portofolio:berkas", args=[999999])).status_code, 404)

    def test_halaman_tidak_lagi_memuat_alamat_media_langsung(self):
        for user in (self.guru, self.user_a, self.user_b):
            resp = self.buka_detail(user)
            self.assertNotContains(resp, "/media/", msg_prefix=user.username)
            self.assertContains(resp, self.url(self.foto_publik), msg_prefix=user.username)
