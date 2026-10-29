"""
Tes integrasi misi ke rapor (ruang_kerja) dan dashboard orang tua.

Tes yang memakai ruang_kerja.views mengandaikan patch ruang_kerja_views.patch sudah diterapkan,
dan kreasi.narasi.susun_narasi_kreasi dipalsukan agar tes tidak bergantung pada data Tugas Kreasi.
"""
from datetime import timedelta
from unittest import mock

from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.template import Context, Template
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from ruang_kerja import views as rk_views
from ruang_kerja.models import PenilaianTopik

from .models import Misi, PengerjaanMisi, PenugasanMisi
from .ringkasan import narasi_misi, nama_level, ringkasan_rapor, ringkasan_untuk_orangtua
from .tests import SLUG_ANGKA, SLUG_RINGAN, Dasar

REFLEKSI = "Aku belajar banyak hal baru hari ini."


class Bantu(Dasar):
    def misi(self, slug):
        return Misi.objects.get(slug=slug)

    def tugaskan(self, slug, ruang=None, materi=None):
        return PenugasanMisi.objects.create(
            misi=self.misi(slug), ruang_kerja=ruang or self.rk, materi=materi, ditugaskan_oleh=self.guru
        )

    def konfirmasi_guru(self, pengerjaan, nilai=None):
        self.masuk(self.guru)
        self.client.post(reverse("misi:konfirmasi", args=[pengerjaan.pk]), {"nilai": nilai} if nilai else {})
        pengerjaan.refresh_from_db()
        self.assertEqual(pengerjaan.status, PengerjaanMisi.SELESAI)
        return pengerjaan

    def selesai_langsung(self, siswa, slug, penugasan=None, nilai=None, menit=0):
        """Jalan pintas lewat ORM untuk menyiapkan data banyak; alur sebenarnya diuji terpisah."""
        return PengerjaanMisi.objects.create(
            siswa=siswa, misi=self.misi(slug), penugasan=penugasan, status=PengerjaanMisi.SELESAI,
            refleksi=REFLEKSI, nilai=nilai, dikonfirmasi_pada=timezone.now() + timedelta(minutes=menit),
        )

    def request_sebagai(self, user, path="/"):
        request = RequestFactory().get(path)
        request.user = user
        return request


class RingkasanRaporTests(Bantu):
    def test_hanya_misi_selesai_yang_ditugaskan_ke_ruang_kerja_itu(self):
        t1 = self.tugaskan(SLUG_RINGAN, materi=self.topik)
        selesai = self.konfirmasi_guru(self.sampai_menunggu(SLUG_RINGAN, penugasan=t1), nilai="80")

        t2 = self.tugaskan(SLUG_ANGKA)
        self.sampai_menunggu(SLUG_ANGKA, penugasan=t2)  # masih menunggu: tidak dihitung

        mandiri = self.sampai_menunggu("tiga-daun-berbeda")  # tanpa penugasan: tidak dihitung
        self.masuk(self.ortu_budi)
        self.client.post(reverse("misi:konfirmasi", args=[mandiri.pk]))
        mandiri.refresh_from_db()
        self.assertEqual(mandiri.status, PengerjaanMisi.SELESAI)

        hasil = ringkasan_rapor(self.budi, self.rk)
        self.assertEqual(hasil["jumlah"], 1)
        self.assertEqual(hasil["daftar"], [selesai])
        self.assertEqual(hasil["rata2_nilai"], 80.0)

    def test_ruang_kerja_lain_dan_siswa_lain_kosong(self):
        self.selesai_langsung(self.budi, SLUG_RINGAN, penugasan=self.tugaskan(SLUG_RINGAN))
        self.assertEqual(ringkasan_rapor(self.budi, self.rk2)["jumlah"], 0)
        self.assertEqual(ringkasan_rapor(self.sari, self.rk)["jumlah"], 0)

    def test_rata2_mengabaikan_misi_tanpa_nilai(self):
        self.selesai_langsung(self.budi, SLUG_RINGAN, penugasan=self.tugaskan(SLUG_RINGAN), nilai=70)
        self.selesai_langsung(self.budi, SLUG_ANGKA, penugasan=self.tugaskan(SLUG_ANGKA), nilai=None, menit=1)
        hasil = ringkasan_rapor(self.budi, self.rk)
        self.assertEqual((hasil["jumlah"], hasil["rata2_nilai"]), (2, 70.0))

    def test_tanpa_nilai_sama_sekali_rata2_none(self):
        self.selesai_langsung(self.budi, SLUG_RINGAN, penugasan=self.tugaskan(SLUG_RINGAN))
        self.assertIsNone(ringkasan_rapor(self.budi, self.rk)["rata2_nilai"])

    def test_nama_level_sama_dengan_papan_dan_koleksi(self):
        self.assertEqual([nama_level(n) for n in (0, 1, 3, 6, 10, 25)],
                         ["Penjelajah Baru", "Pengamat Cilik", "Detektif Alam", "Penjelajah Hebat", "Ilmuwan Cilik", "Ilmuwan Cilik"])


class NarasiMisiTests(Bantu):
    def test_kosong_bila_tidak_ada_misi_selesai(self):
        self.assertEqual(narasi_misi(self.budi, self.rk), "")

    def test_satu_misi(self):
        self.selesai_langsung(self.budi, SLUG_RINGAN, penugasan=self.tugaskan(SLUG_RINGAN))
        teks = narasi_misi(self.budi, self.rk)
        self.assertIn("Budi", teks)
        self.assertIn('"Alat Musik dari Barang Bekas"', teks)
        self.assertIn("dikonfirmasi", teks)
        self.assertNotIn("Rata-rata", teks)

    def test_dua_misi_memakai_kata_dan(self):
        self.selesai_langsung(self.budi, SLUG_RINGAN, penugasan=self.tugaskan(SLUG_RINGAN))
        self.selesai_langsung(self.budi, SLUG_ANGKA, penugasan=self.tugaskan(SLUG_ANGKA), menit=1)
        teks = narasi_misi(self.budi, self.rk)
        self.assertIn("2 misi", teks)
        self.assertIn("yaitu", teks)
        self.assertIn('" dan "', teks)

    def test_banyak_misi_hanya_tiga_judul_pertama(self):
        slugs = [SLUG_RINGAN, SLUG_ANGKA, "tiga-daun-berbeda", "kabar-senang-keluarga"]
        for i, slug in enumerate(slugs):
            self.selesai_langsung(self.budi, slug, penugasan=self.tugaskan(slug), menit=i)
        teks = narasi_misi(self.budi, self.rk)
        self.assertIn("4 misi", teks)
        self.assertIn("antara lain", teks)
        self.assertIn(self.misi(slugs[2]).judul, teks)
        self.assertNotIn(self.misi(slugs[3]).judul, teks)

    def test_kalimat_rata2_nilai_hanya_bila_ada_nilai(self):
        self.selesai_langsung(self.budi, SLUG_RINGAN, penugasan=self.tugaskan(SLUG_RINGAN), nilai=85)
        self.assertIn("Rata-rata nilai formatif dari misi tersebut adalah 85.0.", narasi_misi(self.budi, self.rk))

    def test_nama_siswa_kosong_tidak_error(self):
        self.budi.nama = "  "
        self.selesai_langsung(self.budi, SLUG_RINGAN, penugasan=self.tugaskan(SLUG_RINGAN))
        self.assertIn("Siswa", narasi_misi(self.budi, self.rk))


class DraftKomentarTests(Bantu):
    """generate_draft_komentar milik ruang_kerja, setelah dipatch."""

    def draft(self, kreasi=""):
        with mock.patch("kreasi.narasi.susun_narasi_kreasi", return_value=kreasi):
            return rk_views.generate_draft_komentar(self.rk, self.budi, None)

    def nilai_topik(self):
        PenilaianTopik.objects.create(materi=self.topik, siswa=self.budi, jenis="sumatif", nilai=90)

    def misi_selesai(self):
        self.selesai_langsung(self.budi, SLUG_RINGAN, penugasan=self.tugaskan(SLUG_RINGAN))
        return narasi_misi(self.budi, self.rk)

    def test_tanpa_misi_perilaku_lama_tidak_berubah(self):
        akademik = rk_views._draft_akademik(self.rk, self.budi, None)
        self.assertEqual(self.draft(), akademik)
        self.assertEqual(self.draft(kreasi="KREASI"), "KREASI")  # tanpa topik: hanya kreasi
        self.nilai_topik()
        akademik = rk_views._draft_akademik(self.rk, self.budi, None)
        self.assertEqual(self.draft(kreasi="KREASI"), akademik + "\n\nKREASI")

    def test_misi_tanpa_nilai_topik_tidak_memuat_kalimat_belum_tersedia(self):
        misi = self.misi_selesai()
        self.assertEqual(self.draft(), misi)
        self.assertNotIn("belum tersedia", self.draft())

    def test_misi_ditambahkan_setelah_akademik(self):
        self.nilai_topik()
        misi = self.misi_selesai()
        akademik = rk_views._draft_akademik(self.rk, self.budi, None)
        self.assertEqual(self.draft(), akademik + "\n\n" + misi)

    def test_urutan_akademik_kreasi_misi(self):
        self.nilai_topik()
        misi = self.misi_selesai()
        akademik = rk_views._draft_akademik(self.rk, self.budi, None)
        self.assertEqual(self.draft(kreasi="KREASI"), f"{akademik}\n\nKREASI\n\n{misi}")

    def test_kreasi_dan_misi_tanpa_topik(self):
        misi = self.misi_selesai()
        self.assertEqual(self.draft(kreasi="KREASI"), f"KREASI\n\n{misi}")


class RaporSiswaViewTests(Bantu):
    def konteks(self, user, siswa):
        with mock.patch.object(rk_views, "render", return_value=HttpResponse("ok")) as render:
            rk_views.rapor_siswa(self.request_sebagai(user), self.rk.id, siswa.id)
        return render.call_args.args[2]

    def test_konteks_memuat_misi_rapor_untuk_siswa_sendiri(self):
        self.selesai_langsung(self.budi, SLUG_RINGAN, penugasan=self.tugaskan(SLUG_RINGAN), nilai=88)
        konteks = self.konteks(self.user_budi, self.budi)
        self.assertEqual(konteks["misi_rapor"]["jumlah"], 1)
        self.assertEqual(konteks["misi_rapor"]["rata2_nilai"], 88.0)

    def test_guru_melihat_misi_rapor_siswa(self):
        self.selesai_langsung(self.budi, SLUG_RINGAN, penugasan=self.tugaskan(SLUG_RINGAN))
        self.assertEqual(self.konteks(self.guru, self.budi)["misi_rapor"]["jumlah"], 1)

    def test_konteks_lama_tetap_ada(self):
        konteks = self.konteks(self.user_budi, self.budi)
        for kunci in ("ruang", "siswa", "tugas_nilai", "rata2", "penilaian_topik_list", "total_topik_dinilai"):
            self.assertIn(kunci, konteks)
        self.assertEqual(konteks["misi_rapor"]["jumlah"], 0)

    def test_nilai_formatif_dari_misi_muncul_di_penilaian_topik_seperti_biasa(self):
        """Tidak ada kode baru di jalur ini: konfirmasi guru sudah menulis PenilaianTopik formatif."""
        t = self.tugaskan(SLUG_RINGAN, materi=self.topik)
        self.konfirmasi_guru(self.sampai_menunggu(SLUG_RINGAN, penugasan=t), nilai="85")
        item = self.konteks(self.user_budi, self.budi)["penilaian_topik_list"][0]
        self.assertEqual([f.nilai for f in item["formatif_list"]], [85])
        self.assertIsNone(item["mastery"])  # formatif tidak ikut mastery


class PartialRaporTests(Bantu):
    def render(self, siswa=None):
        return render_to_string("misi/_rapor_misi.html", {"misi_rapor": ringkasan_rapor(siswa or self.budi, self.rk)})

    def test_kosong_tidak_menampilkan_apa_pun(self):
        self.assertEqual(self.render().strip(), "")

    def test_menampilkan_judul_kategori_topik_dan_nilai(self):
        self.selesai_langsung(self.budi, SLUG_RINGAN, penugasan=self.tugaskan(SLUG_RINGAN, materi=self.topik), nilai=85)
        html = self.render()
        self.assertIn("Misi Dunia Nyata", html)
        self.assertIn("Alat Musik dari Barang Bekas", html)
        self.assertIn("Kreativitas", html)
        self.assertIn("topik Tumbuhan", html)
        self.assertIn("nilai 85", html)

    def test_tidak_membocorkan_refleksi_catatan_atau_foto(self):
        t = self.tugaskan(SLUG_RINGAN)
        pengerjaan = self.konfirmasi_guru(self.sampai_menunggu(SLUG_RINGAN, penugasan=t))
        self.assertTrue(pengerjaan.refleksi and pengerjaan.catatan.exists())
        html = self.render()
        self.assertIn("Alat Musik dari Barang Bekas", html)
        self.assertNotIn(pengerjaan.refleksi, html)
        self.assertNotIn(pengerjaan.catatan.first().teks, html)
        self.assertNotIn("/foto/", html)

    def test_teks_di_escape(self):
        Misi.objects.filter(slug=SLUG_RINGAN).update(judul="<script>alert(1)</script>")
        self.selesai_langsung(self.budi, SLUG_RINGAN, penugasan=self.tugaskan(SLUG_RINGAN))
        html = self.render()
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)


class DashboardOrangtuaTests(Bantu):
    def tag(self, user):
        return Template("{% load misi_tags %}{% misi_anak %}").render(Context({"request": self.request_sebagai(user)}))

    def test_orangtua_melihat_ringkasan_anaknya(self):
        self.selesai_langsung(self.budi, SLUG_RINGAN)
        self.sampai_menunggu(SLUG_ANGKA)
        html = self.tag(self.ortu_budi)
        self.assertIn("Misi Dunia Nyata Budi", html)
        self.assertIn("Musisi Kreatif", html)
        self.assertIn("1 misi menunggu konfirmasi Anda", html)
        self.assertIn("Pengamat Cilik", html)
        self.assertIn(reverse("misi:panel_orangtua"), html)

    def test_tidak_ada_data_anak_lain(self):
        self.selesai_langsung(self.budi, SLUG_RINGAN)                     # kartu "Musisi Kreatif"
        self.selesai_langsung(self.sari, "kabar-senang-keluarga")        # kartu "Pendengar Baik"
        punya_budi, punya_sari = self.tag(self.ortu_budi), self.tag(self.ortu_sari)
        self.assertIn("Musisi Kreatif", punya_budi)
        self.assertNotIn("Pendengar Baik", punya_budi)
        self.assertIn("Pendengar Baik", punya_sari)
        self.assertNotIn("Musisi Kreatif", punya_sari)
        self.assertNotIn("Sari", punya_budi)

    def test_tidak_menampilkan_refleksi(self):
        self.selesai_langsung(self.budi, SLUG_RINGAN)
        self.assertNotIn(REFLEKSI, self.tag(self.ortu_budi))

    def test_selain_orangtua_hasilnya_kosong(self):
        self.selesai_langsung(self.budi, SLUG_RINGAN)
        for user in (self.user_budi, self.guru, self.kepsek, AnonymousUser()):
            with self.subTest(user=str(user)):
                self.assertEqual(self.tag(user).strip(), "")

    def test_orangtua_tanpa_anak_kosong(self):
        ortu = User.objects.create_user("ortu_kosong", password="x", role="orangtua")
        self.assertEqual(self.tag(ortu).strip(), "")
        self.assertIsNone(ringkasan_untuk_orangtua(ortu))

    def test_tanpa_misi_menampilkan_pesan_belum_ada(self):
        self.assertIn("Belum ada misi selesai", self.tag(self.ortu_budi))

    def test_tag_tidak_menerima_argumen(self):
        """Pola kreasi_tags: anak selalu dari akun yang login, tidak bisa dipilih lewat template."""
        from django.template import TemplateSyntaxError
        with self.assertRaises(TemplateSyntaxError):
            Template("{% load misi_tags %}{% misi_anak 1 %}")
