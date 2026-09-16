from django.db import models


class PengaturanSekolah(models.Model):
    MODE_CHOICES = [
        ("formal", "Sekolah Formal"),
        ("homeschool", "Homeschooling"),
        ("kursus_online", "Kursus Online"),
    ]

    nama_institusi = models.CharField(max_length=200, default="Sekolah Digital")
    sub_judul = models.CharField(max_length=200, blank=True, default="")
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default="formal")

    LABEL_RUANG_KERJA = {
        "formal": "My Class",
        "homeschool": "My Class",
        "kursus_online": "My Class",
    }

    @property
    def label_ruang_kerja(self):
        return self.LABEL_RUANG_KERJA.get(self.mode, "Ruang Kerja")

    class Meta:
        verbose_name = "Pengaturan Sekolah"
        verbose_name_plural = "Pengaturan Sekolah"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return self.nama_institusi

