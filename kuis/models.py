from django.conf import settings
from django.db import models


class Kuis(models.Model):
    judul = models.CharField(max_length=200)
    pembuat = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="kuis_dibuat",
    )
    dibagikan = models.BooleanField(
        default=False,
        help_text="Jika dicentang, kuis bisa dimainkan semua pengguna yang punya akses Quiz Battle.",
    )
    dibuat_pada = models.DateTimeField(auto_now_add=True)
    diperbarui_pada = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-diperbarui_pada"]
        verbose_name = "Kuis"
        verbose_name_plural = "Kuis"

    def __str__(self):
        return self.judul


class Soal(models.Model):
    kuis = models.ForeignKey(Kuis, on_delete=models.CASCADE, related_name="soal")
    urutan = models.PositiveSmallIntegerField(default=0)
    teks = models.TextField()
    pilihan = models.JSONField(help_text="Daftar 4 pilihan jawaban (A, B, C, D).")
    jawaban_benar = models.PositiveSmallIntegerField(help_text="Indeks jawaban benar: 0=A, 1=B, 2=C, 3=D.")
    petunjuk = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["urutan", "id"]
        verbose_name = "Soal"
        verbose_name_plural = "Soal"

    def __str__(self):
        return self.teks[:60]