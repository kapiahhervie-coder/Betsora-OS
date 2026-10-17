import io
import shutil
import tempfile
from unittest import mock

from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from accounts.models import Siswa, User
from kreasi.fase_config import MAKS_UKURAN_MB
from ruang_kerja.models import AnggotaRuangKerja, Materi, PenilaianTopik, RuangKerja

from .models import CatatanMisi, Misi, PengerjaanMisi, PenugasanMisi

SLUG_ANGKA = "detektif-tanaman"          # kelas 3-7, min 3 catatan, pakai angka
SLUG_RINGAN = "alat-musik-barang-bekas"  # kelas 1-7, min 1 catatan, tanpa angka
SLUG_KELAS_ATAS = "suhu-rumah-seharian"  # kelas 4-7


def png_bytes():
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), "green").save(buffer, "PNG")
    return buffer.getvalue()


class Dasar(TestCase):
    """Satu sekolah kecil: guru, siswa, orang tua, ruang kerja, dan topik."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_misi", verbosity=0)
        buat = User.objects.create_user
        cls.guru = buat("guru1", password="x", role="guru")
        cls.guru2 = buat("guru2", password="x", role="guru")
        cls.kepsek = buat("kepsek1", password="x", role="kepsek")
        cls.user_budi = buat("budi", password="x", role="siswa")
        cls.user_sari = buat("sari", password="x", role="siswa")
        cls.budi = Siswa.objects.create(nama="Budi", nis="001", kelas="III", user=cls.user_budi)
        cls.sari = Siswa.objects.create(nama="Sari", nis="002", kelas="III", user=cls.user_sari)
        cls.ortu_budi = buat("ortu_budi", password="x", role="orangtua", anak=cls.budi)
        cls.ortu_sari = buat("ortu_sari", password="x", role="orangtua", anak=cls.sari)
        cls.rk = RuangKerja.objects.create(mapel="IPA", kelas="III", guru=cls.guru)
        cls.rk2 = RuangKerja.objects.create(mapel="IPA", kelas="IV", guru=cls.guru2)
        AnggotaRuangKerja.objects.create(ruang_kerja=cls.rk, siswa=cls.budi)
        cls.topik = Materi.objects.create(ruang_kerja=cls.rk, judul="Tumbuhan")
        cls.topik2 = Materi.objects.create(ruang_kerja=cls.rk2, judul="Cahaya")

    def masuk(self, user):
        self.client.force_login(user)

    def mulai(self, slug=SLUG_RINGAN, user=None):
        self.masuk(user or self.user_budi)
        self.client.post(reverse("misi:detail", args=[slug]))
        siswa = (user or self.user_budi).profil_siswa
        return PengerjaanMisi.objects.get(siswa=siswa, misi__slug=slug)

    def catat(self, pengerjaan, **data):
        return self.client.post(reverse("misi:tambah_catatan", args=[pengerjaan.pk]), data)

    def sampai_menunggu(self, slug=SLUG_RINGAN, penugasan=None):
        pengerjaan = self.mulai(slug)
        if penugasan:
            pengerjaan.penugasan = penugasan
            pengerjaan.save()
        for i in range(pengerjaan.misi.min_catatan):
            self.catat(pengerjaan, teks=f"temuan {i}", **({"angka": str(10 + i)} if pengerjaan.misi.pakai_angka else {}))
        self.client.post(
            reverse("misi:kirim_refleksi", args=[pengerjaan.pk]), {"refleksi": "Aku belajar banyak hal baru hari ini."}
        )
        pengerjaan.refresh_from_db()
        assert pengerjaan.status == PengerjaanMisi.MENUNGGU
        return pengerjaan


class PeranTests(Dasar):
    def test_home_mengarahkan_sesuai_peran(self):
        tujuan = {
            self.user_budi: "misi:papan",
            self.ortu_budi: "misi:panel_orangtua",
            self.guru: "misi:panel_guru",
            self.kepsek: "misi:panel_guru",
        }
        for user, nama in tujuan.items():
            with self.subTest(user=user.username):
                self.masuk(user)
                self.assertRedirects(self.client.get(reverse("misi:home")), reverse(nama))

    def test_halaman_butuh_login(self):
        for nama in ("misi:home", "misi:papan", "misi:panel_guru", "misi:panel_orangtua"):
            with self.subTest(nama=nama):
                self.assertEqual(self.client.get(reverse(nama)).status_code, 302)

    def test_peran_salah_ditolak(self):
        self.masuk(self.guru)
        self.assertEqual(self.client.get(reverse("misi:papan")).status_code, 403)
        self.masuk(self.user_budi)
        self.assertEqual(self.client.get(reverse("misi:panel_guru")).status_code, 403)
        self.assertEqual(self.client.get(reverse("misi:panel_orangtua")).status_code, 403)
        self.assertEqual(self.client.get(reverse("misi:tugaskan")).status_code, 403)

    def test_akun_siswa_tanpa_profil_ditolak(self):
        yatim = User.objects.create_user("yatim", password="x", role="siswa")
        self.masuk(yatim)
        self.assertEqual(self.client.get(reverse("misi:papan")).status_code, 403)

    def test_orangtua_tanpa_anak_melihat_pesan(self):
        ortu = User.objects.create_user("ortu_kosong", password="x", role="orangtua")
        self.masuk(ortu)
        respons = self.client.get(reverse("misi:panel_orangtua"))
        self.assertContains(respons, "belum dihubungkan")


class PapanTests(Dasar):
    def slugs(self, siswa_user):
        self.masuk(siswa_user)
        respons = self.client.get(reverse("misi:papan"))
        return {k["misi"].slug for k in respons.context["kartu"]}

    def test_filter_berdasarkan_tingkat_kelas(self):
        slugs = self.slugs(self.user_budi)  # kelas III = tingkat 3
        self.assertIn("tiga-daun-berbeda", slugs)
        self.assertIn(SLUG_ANGKA, slugs)
        self.assertNotIn(SLUG_KELAS_ATAS, slugs)

    def test_kelas_smp_tidak_melihat_misi_sd(self):
        self.budi.kelas = "X-1"
        self.budi.save()
        self.assertEqual(self.slugs(self.user_budi), set())

    def test_kelas_tak_terbaca_melihat_semua(self):
        self.budi.kelas = "Pelangi"
        self.budi.save()
        self.assertEqual(len(self.slugs(self.user_budi)), 12)

    def test_filter_kategori(self):
        self.masuk(self.user_budi)
        respons = self.client.get(reverse("misi:papan"), {"kategori": "emosi"})
        self.assertEqual({k["misi"].kategori for k in respons.context["kartu"]}, {"emosi"})

    def test_misi_nonaktif_tidak_tampil(self):
        Misi.objects.filter(slug=SLUG_RINGAN).update(aktif=False)
        self.assertNotIn(SLUG_RINGAN, self.slugs(self.user_budi))
        self.masuk(self.user_budi)
        self.assertEqual(self.client.get(reverse("misi:detail", args=[SLUG_RINGAN])).status_code, 404)


class PengerjaanTests(Dasar):
    def test_mulai_idempoten(self):
        self.mulai()
        self.mulai()
        self.assertEqual(PengerjaanMisi.objects.filter(siswa=self.budi).count(), 1)

    def test_misi_di_luar_tingkat_ditolak_tanpa_penugasan(self):
        self.masuk(self.user_budi)
        self.client.post(reverse("misi:detail", args=[SLUG_KELAS_ATAS]))
        self.assertFalse(PengerjaanMisi.objects.filter(siswa=self.budi).exists())

    def test_misi_di_luar_tingkat_boleh_bila_ditugaskan_guru(self):
        misi = Misi.objects.get(slug=SLUG_KELAS_ATAS)
        tugas = PenugasanMisi.objects.create(misi=misi, ruang_kerja=self.rk, ditugaskan_oleh=self.guru)
        pengerjaan = self.mulai(SLUG_KELAS_ATAS)
        self.assertEqual(pengerjaan.penugasan, tugas)

    def test_catatan_wajib_berisi_dan_angka_tidak_negatif(self):
        pengerjaan = self.mulai(SLUG_ANGKA)
        self.assertEqual(self.catat(pengerjaan, teks="").status_code, 400)
        self.assertEqual(self.catat(pengerjaan, teks="x", angka="-5").status_code, 400)
        self.assertEqual(CatatanMisi.objects.count(), 0)
        self.assertEqual(self.catat(pengerjaan, teks="", angka="12.5").status_code, 302)

    def test_hanya_siswa_pemilik_yang_bisa_mencatat(self):
        pengerjaan = self.mulai()
        self.masuk(self.ortu_budi)
        self.assertEqual(self.catat(pengerjaan, teks="curang").status_code, 403)
        self.masuk(self.user_sari)
        self.assertEqual(self.catat(pengerjaan, teks="curang").status_code, 404)
        self.assertEqual(CatatanMisi.objects.count(), 0)

    def test_refleksi_diblok_sampai_catatan_cukup(self):
        pengerjaan = self.mulai(SLUG_ANGKA)
        self.catat(pengerjaan, teks="a", angka="10")
        self.client.post(reverse("misi:kirim_refleksi", args=[pengerjaan.pk]), {"refleksi": "Refleksi yang cukup panjang."})
        pengerjaan.refresh_from_db()
        self.assertEqual(pengerjaan.status, PengerjaanMisi.BERJALAN)
        self.assertEqual(pengerjaan.refleksi, "")

    def test_refleksi_terlalu_pendek_ditolak(self):
        pengerjaan = self.mulai()
        self.catat(pengerjaan, teks="a")
        respons = self.client.post(reverse("misi:kirim_refleksi", args=[pengerjaan.pk]), {"refleksi": "singkat"})
        self.assertEqual(respons.status_code, 400)

    def test_alur_penuh_dan_grafik(self):
        pengerjaan = self.mulai(SLUG_ANGKA)
        for angka in ("10", "12.5", "15"):
            self.assertEqual(self.catat(pengerjaan, teks="diukur", angka=angka).status_code, 302)
        halaman = self.client.get(reverse("misi:kerjakan", args=[pengerjaan.pk]))
        self.assertEqual([g["persen"] for g in halaman.context["grafik"]], [67, 83, 100])
        self.client.post(reverse("misi:kirim_refleksi", args=[pengerjaan.pk]), {"refleksi": "Tebakanku benar sekali."})
        pengerjaan.refresh_from_db()
        self.assertEqual(pengerjaan.status, PengerjaanMisi.MENUNGGU)

    def test_catatan_terkunci_setelah_dikirim(self):
        pengerjaan = self.sampai_menunggu()
        self.catat(pengerjaan, teks="tambahan")
        self.assertEqual(pengerjaan.catatan.count(), 1)

    def test_siswa_lain_tidak_bisa_membuka_pengerjaan(self):
        pengerjaan = self.mulai()
        self.masuk(self.user_sari)
        self.assertEqual(self.client.get(reverse("misi:kerjakan", args=[pengerjaan.pk])).status_code, 404)
        self.masuk(self.ortu_sari)
        self.assertEqual(self.client.get(reverse("misi:kerjakan", args=[pengerjaan.pk])).status_code, 404)


class KonfirmasiTests(Dasar):
    def konfirmasi(self, pengerjaan, **data):
        return self.client.post(reverse("misi:konfirmasi", args=[pengerjaan.pk]), data)

    def tugas_dengan_topik(self):
        misi = Misi.objects.get(slug=SLUG_RINGAN)
        return PenugasanMisi.objects.create(misi=misi, ruang_kerja=self.rk, materi=self.topik, ditugaskan_oleh=self.guru)

    def test_orangtua_mengonfirmasi_anaknya(self):
        pengerjaan = self.sampai_menunggu()
        self.masuk(self.ortu_budi)
        self.konfirmasi(pengerjaan)
        pengerjaan.refresh_from_db()
        self.assertEqual(pengerjaan.status, PengerjaanMisi.SELESAI)
        self.assertEqual(pengerjaan.dikonfirmasi_oleh, self.ortu_budi)
        self.assertIsNotNone(pengerjaan.dikonfirmasi_pada)

    def test_orangtua_tidak_bisa_mengisi_nilai(self):
        pengerjaan = self.sampai_menunggu(penugasan=self.tugas_dengan_topik())
        self.masuk(self.ortu_budi)
        self.konfirmasi(pengerjaan, nilai="100")
        pengerjaan.refresh_from_db()
        self.assertIsNone(pengerjaan.nilai)
        self.assertEqual(PenilaianTopik.objects.count(), 0)

    def test_orangtua_lain_tidak_bisa_mengonfirmasi(self):
        pengerjaan = self.sampai_menunggu()
        self.masuk(self.ortu_sari)
        self.assertEqual(self.konfirmasi(pengerjaan).status_code, 404)
        pengerjaan.refresh_from_db()
        self.assertEqual(pengerjaan.status, PengerjaanMisi.MENUNGGU)

    def test_siswa_tidak_bisa_mengonfirmasi_dirinya_sendiri(self):
        pengerjaan = self.sampai_menunggu()
        self.assertEqual(self.konfirmasi(pengerjaan).status_code, 403)
        pengerjaan.refresh_from_db()
        self.assertEqual(pengerjaan.status, PengerjaanMisi.MENUNGGU)

    def test_guru_ruang_kerja_mengonfirmasi_dan_nilai_masuk_formatif(self):
        pengerjaan = self.sampai_menunggu(penugasan=self.tugas_dengan_topik())
        self.masuk(self.guru)
        self.konfirmasi(pengerjaan, nilai="85")
        pengerjaan.refresh_from_db()
        self.assertEqual(pengerjaan.status, PengerjaanMisi.SELESAI)
        nilai = PenilaianTopik.objects.get()
        self.assertEqual((nilai.materi, nilai.siswa, nilai.jenis, float(nilai.nilai)), (self.topik, self.budi, "formatif", 85.0))
        self.assertEqual(nilai.dinilai_oleh, self.guru)

    def test_formatif_tidak_mengubah_mastery_topik(self):
        pengerjaan = self.sampai_menunggu(penugasan=self.tugas_dengan_topik())
        self.masuk(self.guru)
        self.konfirmasi(pengerjaan, nilai="100")
        self.assertIsNone(self.topik.hitung_mastery(self.budi))

    def test_tanpa_topik_nilai_tidak_masuk_penilaian(self):
        pengerjaan = self.sampai_menunggu()
        self.masuk(self.guru)
        self.konfirmasi(pengerjaan, nilai="90")
        self.assertEqual(PenilaianTopik.objects.count(), 0)

    def test_guru_lain_tidak_bisa_mengonfirmasi(self):
        pengerjaan = self.sampai_menunggu()
        self.masuk(self.guru2)
        self.assertEqual(self.konfirmasi(pengerjaan).status_code, 404)

    def test_kepsek_bisa_mengonfirmasi(self):
        pengerjaan = self.sampai_menunggu()
        self.masuk(self.kepsek)
        self.konfirmasi(pengerjaan)
        pengerjaan.refresh_from_db()
        self.assertEqual(pengerjaan.status, PengerjaanMisi.SELESAI)

    def test_nilai_di_luar_rentang_ditolak(self):
        pengerjaan = self.sampai_menunggu(penugasan=self.tugas_dengan_topik())
        self.masuk(self.guru)
        self.konfirmasi(pengerjaan, nilai="150")
        pengerjaan.refresh_from_db()
        self.assertEqual(pengerjaan.status, PengerjaanMisi.MENUNGGU)

    def test_tidak_bisa_konfirmasi_dua_kali(self):
        pengerjaan = self.sampai_menunggu(penugasan=self.tugas_dengan_topik())
        self.masuk(self.guru)
        self.konfirmasi(pengerjaan, nilai="80")
        self.konfirmasi(pengerjaan, nilai="60")
        self.assertEqual(PenilaianTopik.objects.count(), 1)

    def test_konfirmasi_harus_post(self):
        pengerjaan = self.sampai_menunggu()
        self.masuk(self.ortu_budi)
        self.assertEqual(self.client.get(reverse("misi:konfirmasi", args=[pengerjaan.pk])).status_code, 405)


class FotoTests(Dasar):
    def setUp(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        self.folder = folder
        patcher = mock.patch.object(CatatanMisi._meta.get_field("foto"), "storage", FileSystemStorage(location=folder))
        patcher.start()
        self.addCleanup(patcher.stop)

    def unggah(self, pengerjaan, berkas=None):
        berkas = berkas or SimpleUploadedFile("daun.png", png_bytes(), content_type="image/png")
        return self.catat(pengerjaan, teks="", foto=berkas)

    def test_unggah_tersimpan_di_penyimpanan_privat(self):
        pengerjaan = self.mulai()
        self.assertEqual(self.unggah(pengerjaan).status_code, 302)
        catatan = CatatanMisi.objects.get()
        self.assertTrue(catatan.foto.name.startswith(f"misi/{self.budi.pk}/"))
        self.assertTrue(catatan.foto.name.endswith(".png"))
        self.assertTrue(FileSystemStorage(location=self.folder).exists(catatan.foto.name))

    def test_yang_berhak_bisa_melihat_foto(self):
        pengerjaan = self.mulai()
        self.unggah(pengerjaan)
        url = reverse("misi:foto", args=[CatatanMisi.objects.get().pk])
        for user in (self.user_budi, self.ortu_budi, self.guru, self.kepsek):
            with self.subTest(user=user.username):
                self.masuk(user)
                respons = self.client.get(url)
                self.assertEqual(respons.status_code, 200)
                self.assertEqual(respons["Content-Type"], "image/png")
                self.assertEqual(respons["X-Content-Type-Options"], "nosniff")
                b"".join(respons.streaming_content)

    def test_yang_tidak_berhak_mendapat_404(self):
        pengerjaan = self.mulai()
        self.unggah(pengerjaan)
        url = reverse("misi:foto", args=[CatatanMisi.objects.get().pk])
        for user in (self.user_sari, self.ortu_sari, self.guru2):
            with self.subTest(user=user.username):
                self.masuk(user)
                self.assertEqual(self.client.get(url).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_berkas_bukan_gambar_ditolak(self):
        pengerjaan = self.mulai()
        palsu = SimpleUploadedFile("x.png", b"bukan gambar", content_type="image/png")
        self.assertEqual(self.unggah(pengerjaan, palsu).status_code, 400)
        self.assertEqual(CatatanMisi.objects.count(), 0)

    def test_foto_terlalu_besar_ditolak(self):
        pengerjaan = self.mulai()
        with mock.patch.dict(MAKS_UKURAN_MB, {"foto": 0}):
            respons = self.unggah(pengerjaan)
        self.assertEqual(respons.status_code, 400)
        self.assertContains(respons, "terlalu besar", status_code=400)

    def test_ekstensi_aneh_dinormalkan(self):
        pengerjaan = self.mulai()
        berkas = SimpleUploadedFile("x.php.png", png_bytes(), content_type="image/png")
        self.unggah(pengerjaan, berkas)
        self.assertTrue(CatatanMisi.objects.get().foto.name.endswith(".png"))


class PenugasanTests(Dasar):
    def data(self, **ubah):
        isi = {"misi": Misi.objects.get(slug=SLUG_RINGAN).pk, "ruang_kerja": self.rk.pk, "materi": self.topik.pk, "tenggat": "2026-11-01T10:00"}
        isi.update(ubah)
        return isi

    def test_guru_menugaskan_ke_ruang_kerjanya(self):
        self.masuk(self.guru)
        respons = self.client.post(reverse("misi:tugaskan"), self.data())
        self.assertRedirects(respons, reverse("misi:panel_guru"))
        tugas = PenugasanMisi.objects.get()
        self.assertEqual((tugas.ruang_kerja, tugas.materi, tugas.ditugaskan_oleh), (self.rk, self.topik, self.guru))
        self.assertIsNotNone(tugas.tenggat)

    def test_guru_tidak_bisa_memakai_ruang_kerja_guru_lain(self):
        self.masuk(self.guru)
        respons = self.client.post(reverse("misi:tugaskan"), self.data(ruang_kerja=self.rk2.pk, materi=self.topik2.pk))
        self.assertEqual(respons.status_code, 400)
        self.assertFalse(PenugasanMisi.objects.exists())

    def test_topik_harus_dari_ruang_kerja_yang_sama(self):
        self.masuk(self.kepsek)
        respons = self.client.post(reverse("misi:tugaskan"), self.data(materi=self.topik2.pk))
        self.assertEqual(respons.status_code, 400)
        self.assertContains(respons, "ruang kerja yang dipilih", status_code=400)

    def test_topik_dan_tenggat_opsional(self):
        self.masuk(self.guru)
        self.client.post(reverse("misi:tugaskan"), self.data(materi="", tenggat=""))
        tugas = PenugasanMisi.objects.get()
        self.assertIsNone(tugas.materi)
        self.assertIsNone(tugas.tenggat)

    def test_penugasan_ganda_ditolak(self):
        self.masuk(self.guru)
        self.client.post(reverse("misi:tugaskan"), self.data())
        respons = self.client.post(reverse("misi:tugaskan"), self.data())
        self.assertEqual(respons.status_code, 400)
        self.assertEqual(PenugasanMisi.objects.count(), 1)

    def test_siswa_melihat_tugas_dari_guru_di_papan(self):
        misi = Misi.objects.get(slug=SLUG_KELAS_ATAS)
        PenugasanMisi.objects.create(misi=misi, ruang_kerja=self.rk, ditugaskan_oleh=self.guru)
        self.masuk(self.user_budi)
        respons = self.client.get(reverse("misi:papan"))
        self.assertEqual([t["penugasan"].misi.slug for t in respons.context["tugas"]], [SLUG_KELAS_ATAS])
        self.masuk(self.user_sari)  # Sari bukan anggota ruang kerja
        self.assertEqual(self.client.get(reverse("misi:papan")).context["tugas"], [])

    def test_panel_guru_hanya_menampilkan_siswa_miliknya(self):
        punya_budi = self.sampai_menunggu()
        sari = self.mulai(SLUG_RINGAN, user=self.user_sari)
        self.catat(sari, teks="a")
        self.client.post(reverse("misi:kirim_refleksi", args=[sari.pk]), {"refleksi": "Refleksi Sari yang cukup panjang."})
        self.masuk(self.guru)
        daftar = self.client.get(reverse("misi:panel_guru")).context["menunggu"]
        self.assertEqual(daftar, [punya_budi])
        self.masuk(self.kepsek)
        self.assertEqual(len(self.client.get(reverse("misi:panel_guru")).context["menunggu"]), 2)


class KoleksiTests(Dasar):
    def test_kartu_muncul_setelah_dikonfirmasi(self):
        pengerjaan = self.sampai_menunggu()
        self.masuk(self.user_budi)
        self.assertEqual(self.client.get(reverse("misi:koleksi")).context["selesai"].count(), 0)
        self.masuk(self.ortu_budi)
        self.client.post(reverse("misi:konfirmasi", args=[pengerjaan.pk]))
        self.masuk(self.user_budi)
        respons = self.client.get(reverse("misi:koleksi"))
        self.assertEqual(respons.context["selesai"].count(), 1)
        self.assertEqual(respons.context["level"], "Pengamat Cilik")
        self.assertContains(respons, "Musisi Kreatif")

    def test_koleksi_dilihat_orangtua_dan_guru_tapi_tidak_orang_lain(self):
        url = reverse("misi:koleksi_siswa", args=[self.budi.pk])
        for user, harapan in ((self.ortu_budi, 200), (self.guru, 200), (self.kepsek, 200), (self.user_budi, 200),
                              (self.user_sari, 404), (self.ortu_sari, 404), (self.guru2, 404)):
            with self.subTest(user=user.username):
                self.masuk(user)
                self.assertEqual(self.client.get(url).status_code, harapan)


class HalamanTests(Dasar):
    def test_semua_halaman_tampil_untuk_peran_yang_berhak(self):
        tugas = PenugasanMisi.objects.create(
            misi=Misi.objects.get(slug=SLUG_ANGKA), ruang_kerja=self.rk, materi=self.topik, ditugaskan_oleh=self.guru
        )
        pengerjaan = self.sampai_menunggu(SLUG_ANGKA, penugasan=tugas)
        kasus = {
            self.user_budi: ["misi:papan", ("misi:detail", [SLUG_ANGKA]), ("misi:kerjakan", [pengerjaan.pk]), "misi:koleksi"],
            self.ortu_budi: ["misi:panel_orangtua", ("misi:kerjakan", [pengerjaan.pk]), ("misi:koleksi_siswa", [self.budi.pk])],
            self.guru: ["misi:panel_guru", "misi:tugaskan", ("misi:kerjakan", [pengerjaan.pk])],
            self.kepsek: ["misi:panel_guru", "misi:tugaskan"],
        }
        for user, halaman in kasus.items():
            self.masuk(user)
            for item in halaman:
                nama, args = (item, []) if isinstance(item, str) else item
                with self.subTest(user=user.username, halaman=nama):
                    self.assertEqual(self.client.get(reverse(nama, args=args)).status_code, 200)

    def test_form_konfirmasi_guru_menampilkan_nilai_hanya_bila_ada_topik(self):
        tugas = PenugasanMisi.objects.create(
            misi=Misi.objects.get(slug=SLUG_RINGAN), ruang_kerja=self.rk, materi=self.topik, ditugaskan_oleh=self.guru
        )
        pengerjaan = self.sampai_menunggu(penugasan=tugas)
        self.masuk(self.guru)
        self.assertContains(self.client.get(reverse("misi:kerjakan", args=[pengerjaan.pk])), "Nilai formatif")
        self.masuk(self.ortu_budi)
        self.assertNotContains(self.client.get(reverse("misi:kerjakan", args=[pengerjaan.pk])), "Nilai formatif")


class ModelTests(Dasar):
    def test_seed_idempoten_dan_data_valid(self):
        call_command("seed_misi", verbosity=0)
        self.assertEqual(Misi.objects.count(), 12)
        for misi in Misi.objects.all():
            with self.subTest(misi=misi.slug):
                self.assertLessEqual(misi.tingkat_min, misi.tingkat_max)
                self.assertGreaterEqual(len(misi.daftar_langkah), 3)
                self.assertTrue(misi.pertanyaan_refleksi)

    def test_cocok_untuk(self):
        misi = Misi.objects.get(slug=SLUG_KELAS_ATAS)  # 4-7
        self.assertTrue(misi.cocok_untuk(None))
        self.assertTrue(misi.cocok_untuk(4))
        self.assertFalse(misi.cocok_untuk(3))
        self.assertFalse(misi.cocok_untuk(8))

    def test_tingkat_terbalik_tidak_valid(self):
        misi = Misi.objects.get(slug=SLUG_RINGAN)
        misi.tingkat_min, misi.tingkat_max = 6, 2
        with self.assertRaises(ValidationError):
            misi.clean()

    def test_penugasan_menolak_topik_dari_ruang_kerja_lain(self):
        tugas = PenugasanMisi(misi=Misi.objects.first(), ruang_kerja=self.rk, materi=self.topik2)
        with self.assertRaises(ValidationError):
            tugas.clean()
