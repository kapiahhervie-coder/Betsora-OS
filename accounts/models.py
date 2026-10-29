from django.contrib.auth.models import AbstractUser
from django.db import models
from accounts.tenancy import SekolahManager, SekolahUserManager


class Sekolah(models.Model):
    """Satu sekolah (tenant). Semua data sekolah ditandai dengan kolom `sekolah`."""
    nama = models.CharField(max_length=200)
    kode = models.SlugField(max_length=30, unique=True, help_text='Singkatan unik, dipakai pada nama pengguna akun sekolah baru')
    aktif = models.BooleanField(default=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nama']
        verbose_name_plural = 'Sekolah'

    def __str__(self):
        return self.nama


class User(AbstractUser):
    objects = SekolahUserManager()

    sekolah = models.ForeignKey('accounts.Sekolah', on_delete=models.PROTECT, null=True, blank=True)
    ROLE_CHOICES = [('guru', 'Guru'), ('kepsek', 'Kepala Sekolah'), ('admin', 'Admin'), ('siswa', 'Siswa'), ('orangtua', 'Orang Tua')]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='guru')
    anak = models.ForeignKey('Siswa', on_delete=models.SET_NULL, null=True, blank=True, related_name='orang_tua_list', help_text='Diisi hanya untuk akun dengan role Orang Tua')

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    def is_staff_role(self):
        return self.role in ('guru', 'kepsek', 'admin')


class Siswa(models.Model):
    objects = SekolahManager(guru=('siswa', ''))

    sekolah = models.ForeignKey('accounts.Sekolah', on_delete=models.PROTECT, null=True, blank=True)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='profil_siswa')
    nama = models.CharField(max_length=100)
    nis = models.CharField(max_length=20)
    kelas = models.CharField(max_length=10)
    foto = models.ImageField(upload_to='foto_siswa/', blank=True, null=True)
    aktif = models.BooleanField(default=True)
    no_ortu = models.CharField(max_length=20, blank=True)
    alamat = models.TextField(blank=True)

    class Meta:
        ordering = ['nama']
        verbose_name_plural = 'Siswa'
        constraints = [
            models.UniqueConstraint(fields=['sekolah', 'nis'], name='siswa_nis_unik_per_sekolah'),
            models.UniqueConstraint(fields=['nis'], condition=models.Q(sekolah__isnull=True), name='siswa_nis_unik_tanpa_sekolah'),
        ]

    def __str__(self):
        return f"{self.nama} ({self.kelas})"
