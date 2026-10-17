import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils import timezone

from kreasi.storage import private_storage  # penyimpanan privat yang sama dengan app kreasi
from ruang_kerja.models import Materi, PenilaianTopik, RuangKerja


class Misi(models.Model):
    """Perpustakaan misi. Dikelola guru/admin lewat halaman admin."""

    SAINS = "sains"
    MATEMATIKA = "matematika"
    BAHASA = "bahasa"
    BUDAYA = "budaya"
    LINGKUNGAN = "lingkungan"
    KREATIF = "kreatif"
    EMOSI = "emosi"
    KATEGORI_CHOICES = [
        (SAINS, "Sains alam"),
        (MATEMATIKA, "Matematika"),
        (BAHASA, "Bahasa dan sosial"),
        (BUDAYA, "Budaya lokal"),
        (LINGKUNGAN, "Lingkungan"),
        (KREATIF, "Kreativitas"),
        (EMOSI, "Emosi"),
    ]
    IKON = {
        SAINS: "ti-plant-2",
        MATEMATIKA: "ti-ruler-measure",
        BAHASA: "ti-message-2",
        BUDAYA: "ti-soup",
        LINGKUNGAN: "ti-recycle",
        KREATIF: "ti-palette",
        EMOSI: "ti-heart",
    }

    slug = models.SlugField(unique=True)
    judul = models.CharField(max_length=120)
    kategori = models.CharField(max_length=20, choices=KATEGORI_CHOICES)
    ringkasan = models.CharField(max_length=240)
    langkah = models.TextField(help_text="Satu langkah per baris")
    bahan = models.CharField(max_length=200, blank=True)
    catatan_keselamatan = models.CharField(max_length=240, blank=True)
    tingkat_min = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text="Tingkat kelas terendah (1-12)",
    )
    tingkat_max = models.PositiveSmallIntegerField(
        default=6, validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text="Tingkat kelas tertinggi (1-12)",
    )
    durasi_menit = models.PositiveSmallIntegerField(default=20)
    min_catatan = models.PositiveSmallIntegerField(
        default=1, help_text="Jumlah catatan minimal sebelum siswa boleh menulis refleksi"
    )
    label_angka = models.CharField(
        max_length=60, blank=True, help_text="Kosongkan bila misi tidak butuh angka"
    )
    satuan_angka = models.CharField(max_length=20, blank=True)
    pertanyaan_refleksi = models.CharField(max_length=240)
    misi_keluarga = models.BooleanField(default=False)
    judul_kartu = models.CharField(max_length=80)
    emoji_kartu = models.CharField(max_length=8, default="⭐")
    aktif = models.BooleanField(default=True)
    dibuat_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="misi_dibuat"
    )

    class Meta:
        ordering = ["tingkat_min", "judul"]
        verbose_name = "Misi"
        verbose_name_plural = "Misi"

    def __str__(self):
        return self.judul

    def clean(self):
        if self.tingkat_min and self.tingkat_max and self.tingkat_min > self.tingkat_max:
            raise ValidationError("Tingkat minimal tidak boleh lebih besar dari tingkat maksimal.")

    @property
    def ikon(self):
        return self.IKON.get(self.kategori, "ti-compass")

    @property
    def daftar_langkah(self):
        return [baris.strip() for baris in self.langkah.splitlines() if baris.strip()]

    @property
    def pakai_angka(self):
        return bool(self.label_angka)

    def cocok_untuk(self, tingkat):
        """Tingkat None (kelas tidak terbaca) berarti semua misi ditampilkan."""
        return tingkat is None or self.tingkat_min <= tingkat <= self.tingkat_max


class PenugasanMisi(models.Model):
    """Guru menugaskan satu misi ke satu ruang kerja (kelas/mapel), opsional dikaitkan ke topik."""

    misi = models.ForeignKey(Misi, on_delete=models.CASCADE, related_name="penugasan")
    ruang_kerja = models.ForeignKey(RuangKerja, on_delete=models.CASCADE, related_name="penugasan_misi")
    materi = models.ForeignKey(
        Materi, on_delete=models.SET_NULL, null=True, blank=True, related_name="penugasan_misi",
        help_text="Opsional: hasil yang dikonfirmasi guru dicatat sebagai nilai formatif topik ini",
    )
    tenggat = models.DateTimeField(null=True, blank=True)
    ditugaskan_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="penugasan_misi_dibuat"
    )
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("misi", "ruang_kerja")
        ordering = ["-dibuat_pada"]
        verbose_name = "Penugasan misi"
        verbose_name_plural = "Penugasan misi"

    def __str__(self):
        return f"{self.misi} -> {self.ruang_kerja}"

    def clean(self):
        if self.materi_id and self.ruang_kerja_id and self.materi.ruang_kerja_id != self.ruang_kerja_id:
            raise ValidationError("Topik harus berasal dari ruang kerja yang dipilih.")


class PengerjaanMisi(models.Model):
    BERJALAN = "berjalan"
    MENUNGGU = "menunggu"
    SELESAI = "selesai"
    STATUS_CHOICES = [
        (BERJALAN, "Sedang dikerjakan"),
        (MENUNGGU, "Menunggu konfirmasi"),
        (SELESAI, "Selesai"),
    ]
    LEVEL = [
        (10, "Ilmuwan Cilik"),
        (6, "Penjelajah Hebat"),
        (3, "Detektif Alam"),
        (1, "Pengamat Cilik"),
        (0, "Penjelajah Baru"),
    ]

    siswa = models.ForeignKey("accounts.Siswa", on_delete=models.CASCADE, related_name="pengerjaan_misi")
    misi = models.ForeignKey(Misi, on_delete=models.CASCADE, related_name="pengerjaan")
    penugasan = models.ForeignKey(
        PenugasanMisi, on_delete=models.SET_NULL, null=True, blank=True, related_name="pengerjaan"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=BERJALAN)
    refleksi = models.TextField(blank=True)
    mulai_pada = models.DateTimeField(default=timezone.now)
    refleksi_pada = models.DateTimeField(null=True, blank=True)
    dikonfirmasi_pada = models.DateTimeField(null=True, blank=True)
    dikonfirmasi_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="misi_dikonfirmasi"
    )
    nilai = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)

    class Meta:
        unique_together = ("siswa", "misi")
        ordering = ["-mulai_pada"]
        verbose_name = "Pengerjaan misi"
        verbose_name_plural = "Pengerjaan misi"

    def __str__(self):
        return f"{self.siswa.nama} - {self.misi}"

    @property
    def jumlah_catatan(self):
        return self.catatan.count()

    @property
    def kurang_catatan(self):
        return max(self.misi.min_catatan - self.jumlah_catatan, 0)

    @property
    def bisa_refleksi(self):
        return self.status == self.BERJALAN and self.kurang_catatan == 0

    def kirim_refleksi(self, teks):
        self.refleksi = teks
        self.refleksi_pada = timezone.now()
        self.status = self.MENUNGGU
        self.save(update_fields=["refleksi", "refleksi_pada", "status"])

    @transaction.atomic
    def konfirmasi(self, oleh, nilai=None):
        """
        Konfirmasi oleh orang tua atau guru. Bila `nilai` diberikan dan misi ini ditugaskan
        ke sebuah topik, nilai dicatat sebagai penilaian FORMATIF topik tersebut. Formatif tidak
        ikut `hitung_mastery`, jadi tidak mengubah kunci/prasyarat topik.
        """
        self.status = self.SELESAI
        self.dikonfirmasi_pada = timezone.now()
        self.dikonfirmasi_oleh = oleh
        self.nilai = nilai
        self.save(update_fields=["status", "dikonfirmasi_pada", "dikonfirmasi_oleh", "nilai"])
        materi = self.penugasan.materi if self.penugasan_id else None
        if nilai is not None and materi is not None:
            PenilaianTopik.objects.create(
                materi=materi,
                siswa=self.siswa,
                jenis="formatif",
                nilai=nilai,
                catatan=f"Misi Dunia Nyata: {self.misi.judul}",
                dinilai_oleh=oleh,
            )


_EKSTENSI_FOTO = {"jpg", "jpeg", "png", "gif", "webp", "heic"}


def _path_foto(instance, filename):
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    if ext not in _EKSTENSI_FOTO:
        ext = "jpg"
    return f"misi/{instance.pengerjaan.siswa_id}/{uuid.uuid4().hex}.{ext}"


class CatatanMisi(models.Model):
    pengerjaan = models.ForeignKey(PengerjaanMisi, on_delete=models.CASCADE, related_name="catatan")
    teks = models.TextField(blank=True)
    angka = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    foto = models.ImageField(upload_to=_path_foto, storage=private_storage, blank=True, null=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["dibuat_pada", "id"]
        verbose_name = "Catatan misi"
        verbose_name_plural = "Catatan misi"

    def __str__(self):
        return f"Catatan {self.pk} - {self.pengerjaan}"
