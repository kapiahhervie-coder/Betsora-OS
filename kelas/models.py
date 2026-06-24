from django.db import models
from accounts.models import Siswa, User
import datetime


class Absensi(models.Model):
    STATUS = [('hadir', 'Hadir'), ('izin', 'Izin'), ('sakit', 'Sakit'), ('alpha', 'Alpha')]
    siswa = models.ForeignKey(Siswa, on_delete=models.CASCADE, related_name='absensi')
    tanggal = models.DateField(default=datetime.date.today)
    status = models.CharField(max_length=6, choices=STATUS, default='hadir')
    catatan = models.TextField(blank=True)
    guru = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ['siswa', 'tanggal']
        ordering = ['-tanggal']

    def __str__(self):
        return f"{self.siswa.nama} - {self.tanggal} - {self.status}"


class Keaktifan(models.Model):
    siswa = models.ForeignKey(Siswa, on_delete=models.CASCADE, related_name='keaktifan')
    tanggal = models.DateField(default=datetime.date.today)
    poin = models.PositiveIntegerField(default=0)
    deskripsi = models.TextField(blank=True)
    mapel = models.CharField(max_length=50, blank=True)
    guru = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-tanggal']

    def __str__(self):
        return f"{self.siswa.nama} - {self.tanggal} - {self.poin} poin"