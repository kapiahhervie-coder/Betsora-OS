"""Tes Fase 2e: orang tua boleh membuka portofolio ANAKNYA SENDIRI lewat middleware yang sebenarnya.

Berbeda dari tes lain, tes di sini TIDAK mematikan BatasiAksesOrangTuaMiddleware: yang diuji adalah
gabungan middleware + view, sama seperti saat pengguna sungguhan membuka halaman.
"""
from django.conf import settings
from django.core.files.base import ContentFile
from django.test import override_settings
from django.urls import reverse

from accounts.models import Siswa

from .models import KaryaSiswa, KomentarKarya, ProfilSiswa, Sertifikat
from .tests import DasarPortofolio, PNG_KECIL, buat_user

MW = "accounts.middleware.BatasiAksesOrangTuaMiddleware"
DENGAN_BATASAN = override_settings(
    MIDDLEWARE=list(settings.MIDDLEWARE) + ([] if MW in settings.MIDDLEWARE else [MW])
)


@DENGAN_BATASAN
class OrangTuaPortofolioTests(DasarPortofolio):
    def setUp(self):
        self.dashboard = reverse("accounts:dashboard_orangtua")
        self.sert = Sertifikat.objects.create(siswa=self.a, judul="SERT-A", diterbitkan_oleh=self.guru)
        self.sert_b = Sertifikat.objects.create(siswa=self.b, judul="SERT-B", diterbitkan_oleh=self.guru)

    def alihkan(self, resp):
        self.assertRedirects(resp, self.dashboard, fetch_redirect_response=False)

    def get(self, user, url):
        self.client.force_login(user)
        return self.client.get(url)

    def post(self, user, url, data=None):
        self.client.force_login(user)
        return self.client.post(url, data or {})

    # --- yang dibuka ----------------------------------------------------------------
    def test_orang_tua_membuka_portofolio_anak_sendiri(self):
        resp = self.get(self.ortu_a, reverse("portofolio:detail", args=[self.a.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "TOPIK-RAHASIA-A")
        self.assertContains(resp, "Karya Publik A")
        self.assertNotContains(resp, "Karya Privat A")  # aturan lama: karya privat tetap tertutup
        self.assertNotContains(resp, "Jadikan unggulan")
        self.assertNotContains(resp, "Terbitkan sertifikat")
        self.assertContains(resp, "SERT-A")

    def test_orang_tua_membuka_sertifikat_anak_sendiri(self):
        resp = self.get(self.ortu_a, reverse("portofolio:sertifikat", args=[self.sert.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "SERT-A")

    def test_orang_tua_membuka_berkas_karya_yang_dibagikan_saja(self):
        self.karya_publik.file.save("publik.png", ContentFile(PNG_KECIL), save=True)
        self.karya_privat.file.save("privat.png", ContentFile(PNG_KECIL), save=True)
        ok = self.get(self.ortu_a, reverse("portofolio:berkas", args=[self.karya_publik.id]))
        self.assertEqual(ok.status_code, 200)
        b"".join(ok.streaming_content)  # baca habis; jangan close() (menutup koneksi DB di tes)
        # Lolos middleware tetapi ditolak view: karya privat bukan untuk orang tua.
        self.assertEqual(self.get(self.ortu_a, reverse("portofolio:berkas", args=[self.karya_privat.id])).status_code, 403)

    # --- yang tetap tertutup --------------------------------------------------------
    def test_portofolio_anak_lain_dialihkan(self):
        self.alihkan(self.get(self.ortu_a, reverse("portofolio:detail", args=[self.b.id])))
        self.alihkan(self.get(self.ortu_b, reverse("portofolio:detail", args=[self.a.id])))

    def test_daftar_seluruh_siswa_dialihkan(self):
        self.alihkan(self.get(self.ortu_a, reverse("portofolio:daftar")))

    def test_sertifikat_anak_lain_ditolak_view(self):
        # Alamatnya lolos middleware (pola yang sama), tetapi view memeriksa pemilik sertifikat.
        self.assertEqual(self.get(self.ortu_a, reverse("portofolio:sertifikat", args=[self.sert_b.id])).status_code, 403)

    def test_orang_tua_tanpa_anak_terhubung_dialihkan(self):
        sendiri = buat_user("ortu_kosong", "orangtua")
        self.alihkan(self.get(sendiri, reverse("portofolio:detail", args=[self.a.id])))
        self.alihkan(self.get(sendiri, reverse("portofolio:sertifikat", args=[self.sert.id])))

    def test_semua_aksi_tulis_tetap_dialihkan_dan_tidak_mengubah_data(self):
        k = self.karya_publik
        aksi = [
            reverse("portofolio:unggulkan_karya", args=[k.id]),
            reverse("portofolio:atur_mapel", args=[k.id]),
            reverse("portofolio:tambah_komentar", args=[k.id]),
            reverse("portofolio:hapus_karya", args=[k.id]),
            reverse("portofolio:tambah_karya"),
            reverse("portofolio:ubah_bio", args=[self.a.id]),
            reverse("portofolio:terbitkan_sertifikat", args=[self.a.id]),
            reverse("portofolio:hapus_sertifikat", args=[self.sert.id]),
        ]
        for url in aksi:
            self.alihkan(self.post(self.ortu_a, url, {"judul": "x", "teks": "x", "mapel": "x", "bio": "x"}))
        k.refresh_from_db()
        self.assertEqual((k.unggulan, k.mapel), (False, ""))
        self.assertTrue(KaryaSiswa.objects.filter(id=k.id).exists())
        self.assertEqual(KomentarKarya.objects.count(), 0)
        self.assertEqual(ProfilSiswa.objects.count(), 0)
        self.assertEqual(Sertifikat.objects.count(), 2)

    def test_post_ke_alamat_portofolio_anak_sendiri_juga_dialihkan(self):
        self.alihkan(self.post(self.ortu_a, reverse("portofolio:detail", args=[self.a.id])))

    def test_alamat_mirip_tidak_lolos(self):
        for jalur in (f"/portofolio/{self.a.id}/bio/", f"/portofolio/{self.a.id}/sertifikat/",
                      f"/portofolio/sertifikat/{self.sert.id}/hapus/", f"/portofolio/karya/{self.karya_publik.id}/komentar/",
                      f"/portofolio/{self.a.id}//", "/portofolio/karya/1/berkas"):
            self.client.force_login(self.ortu_a)
            self.alihkan(self.client.get(jalur))

    # --- pengguna lain tidak terpengaruh -------------------------------------------
    def test_guru_dan_siswa_tidak_terpengaruh(self):
        self.assertEqual(self.get(self.guru, reverse("portofolio:daftar")).status_code, 200)
        self.assertEqual(self.get(self.user_a, reverse("portofolio:detail", args=[self.a.id])).status_code, 200)
