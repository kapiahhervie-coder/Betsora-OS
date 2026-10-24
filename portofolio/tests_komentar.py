"""Tes Fase 2b: komentar guru pada karya."""
from django.urls import reverse

from .models import KaryaSiswa, KomentarKarya
from .tests import DasarPortofolio, TANPA_BATASAN_ORTU, buat_user
from .views import MAKS_KOMENTAR

ISI = "KOMENTAR-GURU-UNIK"


class KomentarTests(DasarPortofolio):
    def kirim(self, user, karya=None, teks=ISI):
        self.client.force_login(user)
        return self.client.post(reverse("portofolio:tambah_komentar", args=[(karya or self.karya_publik).id]), {"teks": teks})

    # --- menulis -------------------------------------------------------------------
    def test_guru_menulis_komentar(self):
        r = self.kirim(self.guru)
        self.assertRedirects(r, reverse("portofolio:detail", args=[self.a.id]), fetch_redirect_response=False)
        k = KomentarKarya.objects.get()
        self.assertEqual((k.teks, k.penulis, k.karya), (ISI, self.guru, self.karya_publik))

    def test_selain_staf_ditolak(self):
        for user in (self.user_a, self.user_b):
            self.assertEqual(self.kirim(user).status_code, 403)
        self.client.logout()
        r = self.client.post(reverse("portofolio:tambah_komentar", args=[self.karya_publik.id]), {"teks": ISI})
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r["Location"])
        self.assertEqual(KomentarKarya.objects.count(), 0)

    @TANPA_BATASAN_ORTU
    def test_orang_tua_tidak_bisa_menulis(self):
        self.assertEqual(self.kirim(self.ortu_a).status_code, 403)
        self.assertEqual(KomentarKarya.objects.count(), 0)

    def test_hanya_post(self):
        self.client.force_login(self.guru)
        self.assertEqual(self.client.get(reverse("portofolio:tambah_komentar", args=[self.karya_publik.id])).status_code, 405)

    def test_kosong_dan_terlalu_panjang_ditolak(self):
        self.kirim(self.guru, teks="   \n  ")
        self.kirim(self.guru, teks="x" * (MAKS_KOMENTAR + 1))
        self.assertEqual(KomentarKarya.objects.count(), 0)
        self.kirim(self.guru, teks="x" * MAKS_KOMENTAR)
        self.assertEqual(KomentarKarya.objects.count(), 1)

    def test_karya_tidak_ada_404(self):
        self.client.force_login(self.guru)
        self.assertEqual(self.client.post(reverse("portofolio:tambah_komentar", args=[999999]), {"teks": ISI}).status_code, 404)

    # --- membaca -------------------------------------------------------------------
    def siapkan(self):
        KomentarKarya.objects.create(karya=self.karya_publik, penulis=self.guru, teks=ISI)

    def test_pemilik_dan_guru_membaca_di_semua_tema(self):
        self.siapkan()
        for user in (self.guru, self.user_a):
            for tema in ("sd", "smp", "sma"):
                self.client.force_login(user)
                resp = self.client.get(reverse("portofolio:detail", args=[self.a.id]) + f"?tema={tema}")
                self.assertContains(resp, ISI, msg_prefix=f"{user}/{tema}")

    @TANPA_BATASAN_ORTU
    def test_orang_tua_anak_itu_membaca_tapi_tanpa_form(self):
        self.siapkan()
        resp = self.buka_detail(self.ortu_a)
        self.assertContains(resp, ISI)
        self.assertNotContains(resp, "Tulis komentar")
        self.assertNotContains(resp, "Hapus komentar")

    @TANPA_BATASAN_ORTU
    def test_orang_tua_anak_lain_ditolak(self):
        self.siapkan()
        self.assertEqual(self.buka_detail(self.ortu_b).status_code, 403)

    def test_siswa_lain_tidak_membaca_walau_karya_dibagikan(self):
        self.siapkan()
        resp = self.buka_detail(self.user_b)
        self.assertContains(resp, "Karya Publik A")
        self.assertNotContains(resp, ISI)
        self.assertNotContains(resp, 'data-pf="komentar"')

    def test_siswa_pemilik_tanpa_form_menulis(self):
        self.siapkan()
        resp = self.buka_detail(self.user_a)
        self.assertNotContains(resp, "Tulis komentar")
        self.assertNotContains(resp, "Hapus komentar")

    def test_guru_melihat_form_menulis_dan_menghapus(self):
        self.siapkan()
        resp = self.buka_detail(self.guru)
        self.assertContains(resp, "Tulis komentar")
        self.assertContains(resp, "Hapus komentar")

    @TANPA_BATASAN_ORTU
    def test_komentar_karya_privat_tidak_terlihat_orang_tua(self):
        KomentarKarya.objects.create(karya=self.karya_privat, penulis=self.guru, teks="KOMENTAR-PRIVAT")
        self.assertNotContains(self.buka_detail(self.ortu_a), "KOMENTAR-PRIVAT")
        self.assertContains(self.buka_detail(self.user_a), "KOMENTAR-PRIVAT")

    def test_html_di_komentar_di_escape(self):
        KomentarKarya.objects.create(karya=self.karya_publik, penulis=self.guru, teks="<script>alert(1)</script>")
        resp = self.buka_detail(self.user_a)
        self.assertNotContains(resp, "<script>alert(1)</script>")
        self.assertContains(resp, "&lt;script&gt;alert(1)&lt;/script&gt;")

    def test_penulis_dihapus_komentar_tetap_ada(self):
        guru2 = buat_user("guru_sementara", "guru")
        KomentarKarya.objects.create(karya=self.karya_publik, penulis=guru2, teks=ISI)
        guru2.delete()
        resp = self.buka_detail(self.user_a)
        self.assertContains(resp, ISI)
        self.assertContains(resp, "Guru · ")

    def test_jumlah_query_tidak_bertambah_per_komentar(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        self.client.force_login(self.guru)
        url = reverse("portofolio:detail", args=[self.a.id])
        self.client.get(url)
        with CaptureQueriesContext(connection) as q1:
            self.client.get(url)
        for i in range(6):
            KomentarKarya.objects.create(karya=self.karya_publik, penulis=buat_user(f"g{i}", "guru"), teks=f"c{i}")
            KomentarKarya.objects.create(karya=self.karya_privat, penulis=self.guru, teks=f"p{i}")
        with CaptureQueriesContext(connection) as q2:
            self.client.get(url)
        self.assertLessEqual(len(q2), len(q1) + 1, [x["sql"][:70] for x in q2.captured_queries])

    # --- menghapus -----------------------------------------------------------------
    def test_staf_menghapus_siswa_tidak_bisa(self):
        k = KomentarKarya.objects.create(karya=self.karya_publik, penulis=self.guru, teks=ISI)
        url = reverse("portofolio:hapus_komentar", args=[k.id])
        self.client.force_login(self.user_a)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.assertEqual(KomentarKarya.objects.count(), 1)
        self.client.force_login(self.guru)
        self.assertEqual(self.client.get(url).status_code, 405)
        r = self.client.post(url)
        self.assertRedirects(r, reverse("portofolio:detail", args=[self.a.id]), fetch_redirect_response=False)
        self.assertEqual(KomentarKarya.objects.count(), 0)

    def test_dihapus_bersama_karya(self):
        self.siapkan()
        self.karya_publik.delete()
        self.assertEqual(KomentarKarya.objects.count(), 0)
