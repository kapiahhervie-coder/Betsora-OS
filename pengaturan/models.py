from django.db import models


class PengaturanSekolah(models.Model):
    sekolah = models.OneToOneField('accounts.Sekolah', on_delete=models.CASCADE, null=True, blank=True, related_name='pengaturan')
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
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def get_settings(cls):
        """Pengaturan milik SEKOLAH AKTIF (dibuat otomatis untuk sekolah baru).

        Tanpa sekolah aktif (halaman login, perintah manajemen): bila hanya ada satu pengaturan, itu yang
        dipakai; bila ada banyak, tampil netral (tidak disimpan) supaya nama satu sekolah tidak bocor ke
        sekolah lain."""
        from accounts.tenancy import TOLAK, sekolah_aktif

        sid = sekolah_aktif()
        if isinstance(sid, int) and sid > 0:
            obj = cls._base_manager.filter(sekolah_id=sid).first()
            if obj is None:
                from accounts.models import Sekolah

                sekolah = Sekolah._base_manager.filter(pk=sid).first()
                nama = sekolah.nama if sekolah else cls._meta.get_field('nama_institusi').default
                obj = cls._base_manager.create(sekolah=sekolah, nama_institusi=nama)
            return obj
        if sid != TOLAK:
            semua = list(cls._base_manager.all()[:2])
            if len(semua) == 1:
                return semua[0]
        return cls()

    def __str__(self):
        return self.nama_institusi

