"""Tes Fase 2d: sertifikat."""
import datetime

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from .models import Sertifikat
from .tests import DasarPortofolio, TANPA_BATASAN_ORTU, buat_user
from .views import MAKS_JUDUL_SERTIFIKAT, MAKS_KET_SERTIFIKAT

JUDUL = "JUARA-1-MENGGAMBAR"


class SertifikatTests(DasarPortofolio):
    def terbit(self, user, siswa=None, **data):
        self.client.force_login(user)
        data.setdefault("judul", JUDUL)
        return self.client.post(reverse("portofolio:terbitkan_sertifikat", args=[(siswa or self.a).id]), data)

    def buat(self, **kw):
        kw.setdefault("judul", JUDUL)
        s = Sertifikat.objects.create(siswa=self.a, diterbitkan_oleh=self.guru, **kw)
        s.nomor = f"SRT/{s.tanggal.year}/{s.pk:05d}"
        s.save(update_fields=["nomor"])
        return s

    # --- menerbitkan ---------------------------------------------------------------
    def test_staf_menerbitkan_dengan_nomor_unik(self):
        r = self.terbit(self.guru, keterangan="Lomba tingkat kelas", tanggal="2026-10-01")
        self.assertRedirects(r, reverse("portofolio:detail", args=[self.a.id]), fetch_redirect_response=False)
        s = Sertifikat.objects.get()
        self.assertEqual((s.judul, s.keterangan, s.tanggal, s.diterbitkan_oleh), (JUDUL, "Lomba tingkat kelas", datetime.date(2026, 10, 1), self.guru))
        self.assertEqual(s.nomor, f"SRT/2026/{s.pk:05d}")
        self.terbit(self.guru, judul="Lain")
        self.assertEqual(Sertifikat.objects.values("nomor").distinct().count(), 2)

    def test_tanggal_kosong_memakai_hari_ini(self):
        self.terbit(self.guru)
        self.assertEqual(Sertifikat.objects.get().tanggal, timezone.localdate())

    def test_selain_staf_ditolak(self):
        self.assertEqual(self.terbit(self.user_a).status_code, 403)
        self.assertEqual(self.terbit(self.user_b).status_code, 403)
        self.client.logout()
        r = self.client.post(reverse("portofolio:terbitkan_sertifikat", args=[self.a.id]), {"judul": JUDUL})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Sertifikat.objects.count(), 0)

    @TANPA_BATASAN_ORTU
    def test_orang_tua_ditolak(self):
        self.assertEqual(self.terbit(self.ortu_a).status_code, 403)
        self.assertEqual(Sertifikat.objects.count(), 0)

    def test_hanya_post(self):
        self.client.force_login(self.guru)
        self.assertEqual(self.client.get(reverse("portofolio:terbitkan_sertifikat", args=[self.a.id])).status_code, 405)

    def test_validasi_masukan(self):
        besok = (timezone.localdate() + datetime.timedelta(days=1)).isoformat()
        for data in (
            {"judul": "   "},
            {"judul": "x" * (MAKS_JUDUL_SERTIFIKAT + 1)},
            {"judul": JUDUL, "keterangan": "x" * (MAKS_KET_SERTIFIKAT + 1)},
            {"judul": JUDUL, "tanggal": "bukan-tanggal"},
            {"judul": JUDUL, "tanggal": besok},
        ):
            self.terbit(self.guru, **data)
        self.assertEqual(Sertifikat.objects.count(), 0)

    def test_siswa_tidak_ada_404(self):
        self.client.force_login(self.guru)
        self.assertEqual(self.client.post(reverse("portofolio:terbitkan_sertifikat", args=[999999]), {"judul": JUDUL}).status_code, 404)

    # --- melihat -------------------------------------------------------------------
    def lihat(self, user, s):
        self.client.force_login(user)
        return self.client.get(reverse("portofolio:sertifikat", args=[s.id]))

    def test_pemilik_dan_guru_membuka_halaman_sertifikat(self):
        s = self.buat(keterangan="KET-UNIK")
        for user in (self.guru, self.user_a):
            resp = self.lihat(user, s)
            self.assertEqual(resp.status_code, 200)
            self.assertTemplateUsed(resp, "portofolio/sertifikat.html")
            for teks in (JUDUL, "Anak A", s.nomor, "KET-UNIK", "SERTIFIKAT"):
                self.assertContains(resp, teks)

    @TANPA_BATASAN_ORTU
    def test_orang_tua_anak_itu_boleh_anak_lain_tidak(self):
        s = self.buat()
        self.assertEqual(self.lihat(self.ortu_a, s).status_code, 200)
        self.assertEqual(self.lihat(self.ortu_b, s).status_code, 403)

    def test_siswa_lain_dan_anonim_ditolak(self):
        s = self.buat()
        self.assertEqual(self.lihat(self.user_b, s).status_code, 403)
        self.client.logout()
        r = self.client.get(reverse("portofolio:sertifikat", args=[s.id]))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r["Location"])

    def test_tidak_ada_404(self):
        self.client.force_login(self.guru)
        self.assertEqual(self.client.get(reverse("portofolio:sertifikat", args=[999999])).status_code, 404)

    def test_teks_di_escape(self):
        s = self.buat(judul="<script>alert(1)</script>", keterangan="<b>x</b>")
        resp = self.lihat(self.guru, s)
        self.assertNotContains(resp, "<script>alert(1)</script>")
        self.assertContains(resp, "&lt;script&gt;alert(1)&lt;/script&gt;")
        resp = self.buka_detail(self.guru)
        self.assertNotContains(resp, "<script>alert(1)</script>")

    def test_penerbit_dihapus_halaman_tetap_jalan(self):
        s = self.buat()
        self.guru.delete()
        resp = self.lihat(self.user_a, s)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Kepala Sekolah")

    # --- di halaman portofolio -----------------------------------------------------
    def test_daftar_tampil_di_semua_tema_untuk_akses_penuh(self):
        self.buat()
        for tema in ("sd", "smp", "sma"):
            self.client.force_login(self.guru)
            resp = self.client.get(reverse("portofolio:detail", args=[self.a.id]) + f"?tema={tema}")
            self.assertContains(resp, 'data-pf="sertifikat"', msg_prefix=tema)
            self.assertContains(resp, JUDUL, msg_prefix=tema)
            self.assertContains(resp, "Terbitkan sertifikat", msg_prefix=tema)

    def test_pemilik_melihat_daftar_tanpa_form_terbit(self):
        self.buat()
        resp = self.buka_detail(self.user_a)
        self.assertContains(resp, JUDUL)
        self.assertNotContains(resp, "Terbitkan sertifikat")
        self.assertNotContains(resp, reverse("portofolio:hapus_sertifikat", args=[Sertifikat.objects.get().id]))

    def test_siswa_lain_tidak_melihat_sertifikat(self):
        self.buat()
        resp = self.buka_detail(self.user_b)
        self.assertNotContains(resp, JUDUL)
        self.assertNotContains(resp, 'data-pf="sertifikat"')

    def test_pemilik_tanpa_sertifikat_tidak_melihat_kartu(self):
        self.assertNotContains(self.buka_detail(self.user_a), 'data-pf="sertifikat"')

    # --- menghapus -----------------------------------------------------------------
    def test_staf_menghapus_siswa_tidak(self):
        s = self.buat()
        url = reverse("portofolio:hapus_sertifikat", args=[s.id])
        self.client.force_login(self.user_a)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.client.force_login(self.guru)
        self.assertEqual(self.client.get(url).status_code, 405)
        r = self.client.post(url)
        self.assertRedirects(r, reverse("portofolio:detail", args=[self.a.id]), fetch_redirect_response=False)
        self.assertEqual(Sertifikat.objects.count(), 0)

    def test_dihapus_bersama_siswa(self):
        self.buat()
        self.a.delete()
        self.assertEqual(Sertifikat.objects.count(), 0)

    def test_query_tidak_tumbuh_per_sertifikat(self):
        self.client.force_login(self.guru)
        url = reverse("portofolio:detail", args=[self.a.id])
        self.client.get(url)
        with CaptureQueriesContext(connection) as q1:
            self.client.get(url)
        for i in range(8):
            self.buat(judul=f"S{i}")
        with CaptureQueriesContext(connection) as q2:
            self.client.get(url)
        self.assertLessEqual(len(q2), len(q1) + 1)
