from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [('guru', 'Guru'), ('kepsek', 'Kepala Sekolah'), ('admin', 'Admin'), ('siswa', 'Siswa'), ('orangtua', 'Orang Tua')]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='guru')
    anak = models.ForeignKey('Siswa', on_delete=models.SET_NULL, null=True, blank=True, related_name='orang_tua_list', help_text='Diisi hanya untuk akun dengan role Orang Tua')

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    def is_staff_role(self):
        return self.role in ('guru', 'kepsek', 'admin')


class Siswa(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='profil_siswa')
    nama = models.CharField(max_length=100)
    nis = models.CharField(max_length=20, unique=True)
    kelas = models.CharField(max_length=10)
    foto = models.ImageField(upload_to='foto_siswa/', blank=True, null=True)
    aktif = models.BooleanField(default=True)
    no_ortu = models.CharField(max_length=20, blank=True)
    alamat = models.TextField(blank=True)

    class Meta:
        ordering = ['nama']
        verbose_name_plural = 'Siswa'

    def __str__(self):
        return f"{self.nama} ({self.kelas})"
