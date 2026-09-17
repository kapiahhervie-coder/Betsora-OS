from django.db import models
from accounts.models import Siswa


class KaryaSiswa(models.Model):
    """
    Karya/proyek yang diunggah siswa sendiri ke portofolio mereka.
    Field 'dibagikan' mengatur visibilitas: False = hanya siswa itu sendiri
    dan guru yang bisa lihat; True = sesama siswa juga bisa lihat.
    """
    siswa = models.ForeignKey(Siswa, on_delete=models.CASCADE, related_name='karya')
    judul = models.CharField(max_length=150)
    deskripsi = models.TextField(blank=True)
    file = models.FileField(upload_to='karya_siswa/')
    dibagikan = models.BooleanField(default=False, help_text='Jika dicentang, siswa lain juga bisa melihat karya ini')
    diunggah_pada = models.DateTimeField(auto_now_add=True)
    refleksi = models.TextField(blank=True, help_text='Refleksi siswa: tantangan terbesar & perasaan setelah menyelesaikan karya ini')

    class Meta:
        ordering = ['-diunggah_pada']
        verbose_name_plural = 'Karya Siswa'

    def __str__(self):
        return f"{self.siswa.nama} - {self.judul}"
