"""Tes Fase 1b: misi dunia nyata tampil di portofolio tanpa membocorkan isi pribadinya."""
from datetime import timedelta
from unittest import skipUnless

from django.apps import apps
from django.urls import reverse
from django.utils import timezone

from . import jenjang
from .misi_ringkas import ringkasan_misi
from .tests import DasarPortofolio, TANPA_BATASAN_ORTU

ADA_MISI = apps.is_installed('misi')
# Teks "Misi Dunia Nyata" juga ada di sidebar base.html, jadi kartunya dikenali lewat atribut ini.
KARTU = 'data-pf="misi"'
RAHASIA = "REFLEKSI-RAHASIA-XYZ"
CATATAN = "CATATAN-RAHASIA-XYZ"


@skipUnless(ADA_MISI, "app misi tidak terpasang")
class MisiPortofolioTests(DasarPortofolio):
    def buat_misi(self, slug, judul, kategori="sains", emoji="🌱"):
        from misi.models import Misi
        return Misi.objects.create(
            slug=slug, judul=judul, kategori=kategori, ringkasan="r", langkah="a\nb",
            pertanyaan_refleksi="?", judul_kartu="Kartu", emoji_kartu=emoji,
        )

    def kerjakan(self, siswa, misi, status, nilai=None, hari_lalu=0):
        from misi.models import PengerjaanMisi, CatatanMisi
        p = PengerjaanMisi.objects.create(
            siswa=siswa, misi=misi, status=status, refleksi=RAHASIA, nilai=nilai,
            dikonfirmasi_pada=timezone.now() - timedelta(days=hari_lalu) if status == "selesai" else None,
        )
        CatatanMisi.objects.create(pengerjaan=p, teks=CATATAN)
        return p

    def siapkan(self):
        m1 = self.buat_misi("tanam", "Menanam Kacang")
        m2 = self.buat_misi("hemat", "Hemat Air", kategori="lingkungan", emoji="💧")
        m3 = self.buat_misi("belum", "Misi Belum Selesai")
        m4 = self.buat_misi("tunggu", "Misi Menunggu")
        self.kerjakan(self.a, m1, "selesai", nilai=80, hari_lalu=5)
        self.kerjakan(self.a, m2, "selesai", nilai=90, hari_lalu=1)
        self.kerjakan(self.a, m3, "berjalan")
        self.kerjakan(self.a, m4, "menunggu")

    # --- ringkasan -----------------------------------------------------------------
    def test_ringkasan_menghitung_dengan_benar(self):
        self.siapkan()
        r = ringkasan_misi(self.a)
        self.assertEqual(r["total_selesai"], 2)
        self.assertEqual(r["menunggu"], 1)
        self.assertEqual(r["berjalan"], 1)
        self.assertEqual(r["rata2_nilai"], 85.0)
        self.assertEqual(r["level"], "Pengamat Cilik")  # 2 selesai: batas 1 <= 2 < 3
        self.assertEqual([m["judul"] for m in r["daftar"]], ["Hemat Air", "Menanam Kacang"])  # terbaru dulu
        self.assertEqual(dict(r["per_kategori"]), {"Sains alam": 1, "Lingkungan": 1})

    def test_ringkasan_tidak_memuat_isi_pribadi(self):
        self.siapkan()
        self.assertNotIn(RAHASIA, repr(ringkasan_misi(self.a)))
        self.assertNotIn(CATATAN, repr(ringkasan_misi(self.a)))

    def test_siswa_tanpa_misi_tidak_error(self):
        r = ringkasan_misi(self.a)
        self.assertEqual(r["total_selesai"], 0)
        self.assertEqual(r["level"], "Penjelajah Baru")
        self.assertIsNone(r["rata2_nilai"])
        self.assertEqual(r["daftar"], [])

    def test_hanya_misi_milik_siswa_itu(self):
        self.siapkan()
        self.assertEqual(ringkasan_misi(self.b)["total_selesai"], 0)

    def test_daftar_dibatasi(self):
        for i in range(8):
            self.kerjakan(self.a, self.buat_misi(f"m{i}", f"Misi {i}"), "selesai", hari_lalu=i)
        r = ringkasan_misi(self.a)
        self.assertEqual(r["total_selesai"], 8)
        self.assertEqual(len(r["daftar"]), 6)

    # --- lencana -------------------------------------------------------------------
    def test_lencana_misi(self):
        ada = {l["kode"]: l["diraih"] for l in jenjang.hitung_lencana(0, 0, None, 0, 0, False, 0)}
        self.assertIn("misi", ada)
        self.assertFalse(ada["misi"])
        self.assertTrue({l["kode"]: l["diraih"] for l in jenjang.hitung_lencana(0, 0, None, 0, 0, False, 1)}["misi"])
        tanpa = {l["kode"] for l in jenjang.hitung_lencana(0, 0, None, 0, 0, False)}
        self.assertNotIn("misi", tanpa)  # app misi tidak dipakai -> lencana tidak ditampilkan

    # --- halaman -------------------------------------------------------------------
    def test_tampil_di_semua_tema_untuk_guru_dan_pemilik(self):
        self.siapkan()
        for user in (self.guru, self.user_a):
            for tema in ("sd", "smp", "sma"):
                self.client.force_login(user)
                resp = self.client.get(reverse("portofolio:detail", args=[self.a.id]) + f"?tema={tema}")
                self.assertEqual(resp.status_code, 200)
                if user == self.user_a:
                    self.assertTemplateUsed(resp, "portofolio/detail_sd.html")
                else:
                    self.assertTemplateUsed(resp, f"portofolio/detail_{tema}.html")
                self.assertContains(resp, "Menanam Kacang")
                self.assertContains(resp, "Hemat Air")
                self.assertContains(resp, KARTU)
                self.assertNotContains(resp, "Misi Belum Selesai")  # yang belum selesai tidak dipajang
                self.assertNotContains(resp, RAHASIA)
                self.assertNotContains(resp, CATATAN)
                self.assertEqual(resp.context["misi"]["total_selesai"], 2)

    def test_lencana_penjelajah_nyata_di_halaman(self):
        resp = self.buka_detail(self.guru)
        self.assertFalse({l["kode"]: l["diraih"] for l in resp.context["lencana"]}["misi"])
        self.siapkan()
        resp = self.buka_detail(self.guru)
        self.assertTrue({l["kode"]: l["diraih"] for l in resp.context["lencana"]}["misi"])

    def test_siswa_lain_tidak_melihat_misi(self):
        self.siapkan()
        resp = self.buka_detail(self.user_b)
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Menanam Kacang")
        self.assertNotContains(resp, KARTU)
        self.assertNotIn("misi", resp.context)

    @TANPA_BATASAN_ORTU
    def test_orang_tua_anak_itu_melihat_misi_tanpa_isi_pribadi(self):
        self.siapkan()
        resp = self.buka_detail(self.ortu_a)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Menanam Kacang")
        self.assertNotContains(resp, RAHASIA)

    @TANPA_BATASAN_ORTU
    def test_orang_tua_anak_lain_tetap_ditolak(self):
        self.siapkan()
        self.assertEqual(self.buka_detail(self.ortu_b).status_code, 403)

    def test_judul_misi_di_escape(self):
        m = self.buat_misi("xss", "<script>alert(1)</script>", emoji="<b>")
        self.kerjakan(self.a, m, "selesai")
        resp = self.buka_detail(self.guru)
        self.assertNotContains(resp, "<script>alert(1)</script>")
        self.assertContains(resp, "&lt;script&gt;alert(1)&lt;/script&gt;")

    def test_halaman_tanpa_misi_menampilkan_pesan_kosong(self):
        resp = self.buka_detail(self.guru)
        self.assertContains(resp, KARTU)
        self.assertContains(resp, "Belum ada misi yang selesai")
