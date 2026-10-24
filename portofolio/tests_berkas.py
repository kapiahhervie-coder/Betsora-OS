"""Tes penyajian berkas karya lewat view beraturan izin (bukan alamat /media/ yang terbuka)."""
from django.core.files.base import ContentFile
from django.urls import reverse

from .models import KaryaSiswa
from .tests import DasarPortofolio, PNG_KECIL, TANPA_BATASAN_ORTU

ISI_HTML = b"<script>window.__pwned=1</script>"


def baca(resp):
    """Habiskan isi respons streaming. Penutupan ditangani klien uji sendiri; memanggil
    resp.close() lagi akan menutup koneksi database di tengah tes (PostgreSQL)."""
    return b"".join(resp.streaming_content)


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


class BerkasLangsungTests(DasarPortofolio):
    """Alamat lama /media/karya_siswa/<nama> tidak boleh lagi membuka berkas tanpa izin."""

    def setUp(self):
        self.publik = KaryaSiswa(siswa=self.a, judul="Publik", dibagikan=True)
        self.publik.file.save("langsung_publik.png", ContentFile(PNG_KECIL), save=True)
        self.privat = KaryaSiswa(siswa=self.a, judul="Privat", dibagikan=False)
        self.privat.file.save("langsung_privat.png", ContentFile(PNG_KECIL), save=True)

    def buka(self, user, alamat):
        if user is not None:
            self.client.force_login(user)
        return self.client.get(alamat)

    def test_alamat_media_tetap_sama_dengan_yang_dipakai_django(self):
        self.assertTrue(self.privat.file.url.startswith("/media/karya_siswa/"))

    def test_anonim_dialihkan_ke_login(self):
        resp = self.buka(None, self.privat.file.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp["Location"])

    def test_pemilik_dan_guru_boleh_berkas_privat(self):
        for user in (self.user_a, self.guru):
            resp = self.buka(user, self.privat.file.url)
            self.assertEqual(resp.status_code, 200, msg=user.username)
            self.assertEqual(baca(resp), PNG_KECIL)

    def test_siswa_lain_ditolak_untuk_berkas_privat_tetapi_boleh_yang_dibagikan(self):
        self.assertEqual(self.buka(self.user_b, self.privat.file.url).status_code, 403)
        resp = self.buka(self.user_b, self.publik.file.url)
        self.assertEqual(resp.status_code, 200)
        baca(resp)

    @TANPA_BATASAN_ORTU
    def test_orang_tua_anak_lain_ditolak(self):
        self.assertEqual(self.buka(self.ortu_b, self.publik.file.url).status_code, 403)

    def test_berkas_yang_dipakai_dua_karya_boleh_jika_salah_satunya_dibagikan(self):
        KaryaSiswa.objects.create(siswa=self.a, judul="Salinan", dibagikan=True, file=self.privat.file.name)
        resp = self.buka(self.user_b, self.privat.file.url)
        self.assertEqual(resp.status_code, 200)
        baca(resp)

    def test_nama_tidak_dikenal_atau_mencoba_keluar_folder_404(self):
        for alamat in ("/media/karya_siswa/tidak_ada.png", "/media/karya_siswa/../../settings.py",
                       "/media/karya_siswa/%2e%2e/rahasia.txt"):
            self.assertEqual(self.buka(self.guru, alamat).status_code, 404, msg=alamat)

    def test_metode_selain_baca_ditolak(self):
        self.client.force_login(self.guru)
        self.assertEqual(self.client.post(self.privat.file.url).status_code, 405)

    def test_berkas_lama_berbahaya_diunduh_bukan_dijalankan(self):
        lama = KaryaSiswa(siswa=self.a, judul="Lama", dibagikan=True)
        lama.file.save("lama_langsung.html", ContentFile(ISI_HTML), save=True)
        resp = self.buka(self.user_b, lama.file.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp["Content-Disposition"].startswith("attachment"))
        self.assertEqual(resp["X-Content-Type-Options"], "nosniff")
        baca(resp)
