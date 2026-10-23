"""Tes Fase 1: pemilihan tema per jenjang, isi tema, dan perhitungan lencana."""
from types import SimpleNamespace

from django.test import SimpleTestCase
from django.urls import reverse

from kelas.models import Absensi, Keaktifan
from accounts.models import Siswa

from . import jenjang
from .models import KaryaSiswa
from .tests import DasarPortofolio, PAYLOAD_XSS, TANPA_BATASAN_ORTU

TEMA_PER_KELAS = {"3": "sd", "8": "smp", "11": "sma"}


class JenjangTests(SimpleTestCase):
    def test_angka_kelas(self):
        kasus = {
            "3": 3, "3A": 3, "10 IPA": 10, "12": 12, "Kelas 5": 5,
            "VII B": 7, "VIIA": 7, "VI": 6, "IV": 4, "IX": 9, "X": 10, "XI": 11, "XII": 12,
            "": None, "abc": None, None: None,
        }
        for teks, harapan in kasus.items():
            self.assertEqual(jenjang.angka_kelas(teks), harapan, msg=repr(teks))

    def test_batas_jenjang(self):
        kasus = {"1": "sd", "6": "sd", "7": "smp", "9": "smp", "10": "sma", "12": "sma", "": "sd", "abc": "sd"}
        for teks, harapan in kasus.items():
            self.assertEqual(jenjang.jenjang_dari_kelas(teks), harapan, msg=repr(teks))

    def test_ringkas_nilai_dan_tren(self):
        def n(mapel, skor, topik="T"):
            return SimpleNamespace(skor=skor, sesi=SimpleNamespace(mapel=mapel, topik=topik))
        daftar = [n("IPA", 90), n("Matematika", 70), n("IPA", 80), n("IPA", 100)]  # terbaru dulu
        hasil = {m["mapel"]: m for m in jenjang.ringkas_nilai(daftar)}
        self.assertEqual(hasil["IPA"]["rata"], 90.0)
        self.assertEqual(hasil["IPA"]["jumlah"], 3)
        self.assertEqual(hasil["Matematika"]["lebar"], 70)
        tren = jenjang.tren_nilai(daftar)
        self.assertEqual([t["skor"] for t in tren], [100.0, 80.0, 70.0, 90.0])  # lama -> baru
        self.assertTrue(all(4 <= t["tinggi"] <= 100 for t in tren))

    def test_persen_poin_dibatasi(self):
        self.assertEqual(jenjang.persen_poin(0), 0)
        self.assertEqual(jenjang.persen_poin(jenjang.TARGET_POIN // 2), 50)
        self.assertEqual(jenjang.persen_poin(jenjang.TARGET_POIN * 5), 100)

    def test_lencana(self):
        kosong = {l["kode"]: l["diraih"] for l in jenjang.hitung_lencana(0, 0, None, 0, 0, False)}
        self.assertFalse(any(kosong.values()))
        penuh = {l["kode"]: l["diraih"] for l in jenjang.hitung_lencana(
            100, 10, 95.0, jenjang.TARGET_POIN, jenjang.AMBANG_KARYA, True)}
        self.assertTrue(all(penuh.values()))
        # Belum ada absensi sama sekali tidak boleh dianggap "rajin hadir".
        self.assertFalse({l["kode"]: l["diraih"] for l in jenjang.hitung_lencana(0, 0, None, 0, 0, False)}["hadir"])


class TemaTests(DasarPortofolio):
    def atur_kelas(self, kelas):
        Siswa.objects.filter(id=self.a.id).update(kelas=kelas)

    def test_tema_mengikuti_kelas(self):
        for kelas, tema in TEMA_PER_KELAS.items():
            self.atur_kelas(kelas)
            resp = self.buka_detail(self.user_a)
            self.assertEqual(resp.status_code, 200)
            self.assertTemplateUsed(resp, f"portofolio/detail_{tema}.html")

    def test_isi_penuh_di_semua_tema_untuk_guru_dan_pemilik(self):
        for kelas in TEMA_PER_KELAS:
            self.atur_kelas(kelas)
            for user in (self.guru, self.user_a):
                resp = self.buka_detail(user)
                self.assertContains(resp, "TOPIK-RAHASIA-A", msg_prefix=f"{kelas}/{user.username}")
                self.assertContains(resp, "Karya Publik A")
                self.assertContains(resp, "Karya Privat A")

    def test_siswa_lain_hanya_karya_dibagikan_di_semua_tema(self):
        for kelas in TEMA_PER_KELAS:
            self.atur_kelas(kelas)
            resp = self.buka_detail(self.user_b)
            self.assertEqual(resp.status_code, 200)
            self.assertNotContains(resp, "TOPIK-RAHASIA-A", msg_prefix=kelas)
            self.assertNotContains(resp, "Karya Privat A", msg_prefix=kelas)
            self.assertContains(resp, "Karya Publik A", msg_prefix=kelas)
            self.assertNotContains(resp, "NIS", msg_prefix=kelas)

    @TANPA_BATASAN_ORTU
    def test_orang_tua_tetap_ditolak_untuk_anak_lain_di_semua_tema(self):
        for kelas in TEMA_PER_KELAS:
            self.atur_kelas(kelas)
            self.assertEqual(self.buka_detail(self.ortu_b).status_code, 403)

    def test_guru_bisa_pratinjau_tema_lain(self):
        self.client.force_login(self.guru)
        for tema in ("sd", "smp", "sma"):
            resp = self.client.get(reverse("portofolio:detail", args=[self.a.id]) + f"?tema={tema}")
            self.assertTemplateUsed(resp, f"portofolio/detail_{tema}.html")
            self.assertContains(resp, "Pratinjau tema")

    def test_siswa_tidak_bisa_memaksa_tema_dan_tidak_melihat_pemilih(self):
        self.client.force_login(self.user_a)
        resp = self.client.get(reverse("portofolio:detail", args=[self.a.id]) + "?tema=sma")
        self.assertTemplateUsed(resp, "portofolio/detail_sd.html")
        self.assertNotContains(resp, "Pratinjau tema")

    def test_tema_tidak_dikenal_diabaikan(self):
        self.client.force_login(self.guru)
        resp = self.client.get(reverse("portofolio:detail", args=[self.a.id]) + "?tema=<script>")
        self.assertTemplateUsed(resp, "portofolio/detail_sd.html")
        self.assertNotContains(resp, "<script>alert")

    def test_siswa_tanpa_data_tidak_error_di_semua_tema(self):
        kosong = Siswa.objects.create(nama="Kosong", nis="777", kelas="3")
        self.client.force_login(self.guru)
        for tema in ("sd", "smp", "sma"):
            resp = self.client.get(reverse("portofolio:detail", args=[kosong.id]) + f"?tema={tema}")
            self.assertEqual(resp.status_code, 200, msg=tema)
            self.assertContains(resp, "Belum ada karya diunggah.")
            # Tanpa data absensi, kehadiran bukan "0%" (menyesatkan) melainkan "belum ada data".
            self.assertNotContains(resp, ">0%<", msg_prefix=tema)

    def test_kehadiran_tampil_jika_ada_data(self):
        resp = self.buka_detail(self.guru)
        self.assertContains(resp, ">100%<")  # 1 hari hadir dari 1 hari

    def test_video_berbahaya_tidak_sampai_ke_halaman_di_semua_tema(self):
        KaryaSiswa.objects.create(siswa=self.a, judul="Jahat", video_url=PAYLOAD_XSS, dibagikan=True)
        for kelas in TEMA_PER_KELAS:
            self.atur_kelas(kelas)
            resp = self.buka_detail(self.guru)
            self.assertNotContains(resp, "__pwned", msg_prefix=kelas)

    def test_lencana_dan_poin_tampil_di_konteks(self):
        resp = self.buka_detail(self.guru)
        self.assertEqual(resp.context["total_poin"], 7)
        self.assertEqual(resp.context["persen_poin"], jenjang.persen_poin(7))
        kode = {l["kode"]: l["diraih"] for l in resp.context["lencana"]}
        self.assertTrue(kode["hadir"])   # 1 hari hadir = 100%
        self.assertTrue(kode["nilai"])   # rata-rata 88
        self.assertTrue(kode["karya3"] is False)
        self.assertEqual(resp.context["nilai_per_mapel"][0]["mapel"], "Matematika")

    def test_jumlah_query_detail_tetap_kecil(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        self.client.force_login(self.guru)
        url = reverse("portofolio:detail", args=[self.a.id])
        self.client.get(url)  # pemanasan
        with CaptureQueriesContext(connection) as q:
            self.client.get(url)
        self.assertLessEqual(len(q), 14, [x["sql"][:80] for x in q.captured_queries])
