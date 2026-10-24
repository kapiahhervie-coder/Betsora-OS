"""Tes Fase 2c: tag mata pelajaran pada karya dan bio siswa."""
from django.urls import reverse

from .models import KaryaSiswa, ProfilSiswa
from .tests import DasarPortofolio, TANPA_BATASAN_ORTU
from .views import MAKS_BIO, MAKS_MAPEL

YT = "https://youtu.be/dQw4w9WgXcQ"


class TagMapelTests(DasarPortofolio):
    def detail(self, user, **q):
        self.client.force_login(user)
        return self.client.get(reverse("portofolio:detail", args=[self.a.id]), q)

    def atur(self, user, karya, mapel):
        self.client.force_login(user)
        return self.client.post(reverse("portofolio:atur_mapel", args=[karya.id]), {"mapel": mapel})

    def test_unggah_dengan_tag(self):
        self.client.force_login(self.user_a)
        self.client.post(reverse("portofolio:tambah_karya"), {"judul": "Baru", "video_url": YT, "mapel": "  IPA   Alam  "})
        self.assertEqual(KaryaSiswa.objects.get(judul="Baru").mapel, "IPA Alam")  # spasi dirapikan

    def test_unggah_tag_terlalu_panjang_ditolak(self):
        self.client.force_login(self.user_a)
        self.client.post(reverse("portofolio:tambah_karya"), {"judul": "Baru", "video_url": YT, "mapel": "x" * (MAKS_MAPEL + 1)})
        self.assertFalse(KaryaSiswa.objects.filter(judul="Baru").exists())

    def test_unggah_tanpa_tag_tetap_boleh(self):
        self.client.force_login(self.user_a)
        self.client.post(reverse("portofolio:tambah_karya"), {"judul": "Baru", "video_url": YT})
        self.assertEqual(KaryaSiswa.objects.get(judul="Baru").mapel, "")

    def test_pemilik_dan_guru_mengatur_tag(self):
        self.atur(self.user_a, self.karya_publik, "Matematika")
        self.karya_publik.refresh_from_db()
        self.assertEqual(self.karya_publik.mapel, "Matematika")
        self.atur(self.guru, self.karya_publik, "IPA")
        self.karya_publik.refresh_from_db()
        self.assertEqual(self.karya_publik.mapel, "IPA")
        self.atur(self.guru, self.karya_publik, "")
        self.karya_publik.refresh_from_db()
        self.assertEqual(self.karya_publik.mapel, "")

    def test_orang_lain_tidak_boleh_mengatur_tag(self):
        self.assertEqual(self.atur(self.user_b, self.karya_publik, "X").status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.post(reverse("portofolio:atur_mapel", args=[self.karya_publik.id]), {"mapel": "X"}).status_code, 302)
        self.karya_publik.refresh_from_db()
        self.assertEqual(self.karya_publik.mapel, "")

    @TANPA_BATASAN_ORTU
    def test_orang_tua_tidak_boleh_mengatur_tag(self):
        self.assertEqual(self.atur(self.ortu_a, self.karya_publik, "X").status_code, 403)

    def test_tag_terlalu_panjang_tidak_disimpan_dan_hanya_post(self):
        self.atur(self.guru, self.karya_publik, "x" * (MAKS_MAPEL + 1))
        self.karya_publik.refresh_from_db()
        self.assertEqual(self.karya_publik.mapel, "")
        self.client.force_login(self.guru)
        self.assertEqual(self.client.get(reverse("portofolio:atur_mapel", args=[self.karya_publik.id])).status_code, 405)

    def siapkan(self):
        KaryaSiswa.objects.filter(pk=self.karya_publik.pk).update(mapel="Matematika")
        self.ipa = KaryaSiswa.objects.create(siswa=self.a, judul="Proyek IPA", mapel="IPA", dibagikan=True)

    def test_filter_menyaring_di_semua_tema(self):
        self.siapkan()
        for tema in ("sd", "smp", "sma"):
            resp = self.detail(self.guru, tema=tema, mapel="IPA")
            judul = [k.judul for k in resp.context["karya_list"]]
            self.assertEqual(judul, ["Proyek IPA"], msg=tema)
            self.assertEqual(resp.context["jumlah_karya"], 3)  # hitungan lencana tidak ikut tersaring
            self.assertContains(resp, 'data-pf="filter-mapel"', msg_prefix=tema)

    def test_tanpa_filter_semua_tampil_dan_filter_asing_kosong(self):
        self.siapkan()
        self.assertEqual(len(self.detail(self.guru).context["karya_list"]), 3)
        resp = self.detail(self.guru, mapel="TIDAK-ADA")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["karya_list"], [])

    def test_tag_karya_privat_tidak_bocor_ke_siswa_lain(self):
        KaryaSiswa.objects.filter(pk=self.karya_privat.pk).update(mapel="RAHASIA-MAPEL")
        self.client.force_login(self.user_b)
        resp = self.client.get(reverse("portofolio:detail", args=[self.a.id]))
        self.assertNotContains(resp, "RAHASIA-MAPEL")
        self.assertNotIn("RAHASIA-MAPEL", resp.context["daftar_mapel_karya"])
        resp = self.client.get(reverse("portofolio:detail", args=[self.a.id]), {"mapel": "RAHASIA-MAPEL"})
        self.assertEqual(resp.context["karya_list"], [])
        self.assertNotContains(resp, "Karya Privat A")

    def test_tag_di_escape(self):
        KaryaSiswa.objects.filter(pk=self.karya_publik.pk).update(mapel="<b>x</b>")
        resp = self.detail(self.guru)
        self.assertNotContains(resp, "<b>x</b>")
        self.assertContains(resp, "&lt;b&gt;x&lt;/b&gt;")

    def test_saran_mapel_dari_nilai_dan_karya(self):
        self.siapkan()
        saran = self.detail(self.user_a).context["saran_mapel"]
        self.assertIn("Matematika", saran)  # dari nilai dasar tes
        self.assertIn("IPA", saran)         # dari tag karya


class BioTests(DasarPortofolio):
    def simpan(self, user, bio, siswa=None):
        self.client.force_login(user)
        return self.client.post(reverse("portofolio:ubah_bio", args=[(siswa or self.a).id]), {"bio": bio})

    def test_pemilik_dan_guru_menyimpan(self):
        r = self.simpan(self.user_a, "Aku suka   menggambar")
        self.assertRedirects(r, reverse("portofolio:detail", args=[self.a.id]), fetch_redirect_response=False)
        self.assertEqual(ProfilSiswa.objects.get(siswa=self.a).bio, "Aku suka menggambar")
        self.simpan(self.guru, "Diubah guru")
        self.assertEqual(ProfilSiswa.objects.filter(siswa=self.a).count(), 1)
        self.assertEqual(ProfilSiswa.objects.get(siswa=self.a).bio, "Diubah guru")

    def test_bio_kosong_menghapus(self):
        self.simpan(self.user_a, "Ada")
        self.simpan(self.user_a, "   ")
        self.assertFalse(ProfilSiswa.objects.filter(siswa=self.a).exists())

    def test_terlalu_panjang_ditolak(self):
        self.simpan(self.user_a, "x" * (MAKS_BIO + 1))
        self.assertFalse(ProfilSiswa.objects.exists())
        self.simpan(self.user_a, "x" * MAKS_BIO)
        self.assertEqual(ProfilSiswa.objects.count(), 1)

    def test_orang_lain_ditolak(self):
        self.assertEqual(self.simpan(self.user_b, "Dibajak").status_code, 403)
        self.assertEqual(self.simpan(self.user_a, "Bio B", siswa=self.b).status_code, 403)
        self.client.logout()
        r = self.client.post(reverse("portofolio:ubah_bio", args=[self.a.id]), {"bio": "x"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(ProfilSiswa.objects.count(), 0)

    @TANPA_BATASAN_ORTU
    def test_orang_tua_tidak_boleh_mengubah_tapi_boleh_membaca(self):
        self.assertEqual(self.simpan(self.ortu_a, "x").status_code, 403)
        ProfilSiswa.objects.create(siswa=self.a, bio="BIO-UNIK")
        self.client.force_login(self.ortu_a)
        resp = self.client.get(reverse("portofolio:detail", args=[self.a.id]))
        self.assertContains(resp, "BIO-UNIK")
        self.assertNotContains(resp, "Ubah bio")

    def test_hanya_post(self):
        self.client.force_login(self.user_a)
        self.assertEqual(self.client.get(reverse("portofolio:ubah_bio", args=[self.a.id])).status_code, 405)

    def test_tampil_di_semua_tema_untuk_akses_penuh(self):
        ProfilSiswa.objects.create(siswa=self.a, bio="BIO-UNIK")
        for tema in ("sd", "smp", "sma"):
            self.client.force_login(self.guru)
            resp = self.client.get(reverse("portofolio:detail", args=[self.a.id]) + f"?tema={tema}")
            self.assertContains(resp, "BIO-UNIK", msg_prefix=tema)
            self.assertContains(resp, "Ubah bio", msg_prefix=tema)

    def test_siswa_lain_tidak_melihat_bio(self):
        ProfilSiswa.objects.create(siswa=self.a, bio="BIO-UNIK")
        self.client.force_login(self.user_b)
        resp = self.client.get(reverse("portofolio:detail", args=[self.a.id]))
        self.assertNotContains(resp, "BIO-UNIK")
        self.assertNotContains(resp, 'data-pf="bio"')

    def test_bio_di_escape_dan_pesan_kosong(self):
        resp = self.buka_detail(self.user_a)
        self.assertContains(resp, "Belum ada bio.")
        ProfilSiswa.objects.create(siswa=self.a, bio="<script>alert(1)</script>")
        resp = self.buka_detail(self.user_a)
        self.assertNotContains(resp, "<script>alert(1)</script>")
        self.assertContains(resp, "&lt;script&gt;alert(1)&lt;/script&gt;")

    def test_dihapus_bersama_siswa(self):
        ProfilSiswa.objects.create(siswa=self.a, bio="x")
        self.a.delete()
        self.assertEqual(ProfilSiswa.objects.count(), 0)
