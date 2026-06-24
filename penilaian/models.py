from django.db import models
from accounts.models import Siswa, User
import datetime


class SesiPenilaian(models.Model):
    JENIS = [('formatif', 'Formatif'), ('sumatif', 'Sumatif')]
    mapel = models.CharField(max_length=50)
    jenis = models.CharField(max_length=10, choices=JENIS)
    topik = models.CharField(max_length=100)
    tanggal = models.DateField(default=datetime.date.today)
    kelas = models.CharField(max_length=10)
    guru = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['-tanggal']

    def __str__(self):
        return f"{self.mapel} - {self.topik} ({self.jenis})"

    def rata_rata(self):
        hasil = self.nilai_set.aggregate(avg=models.Avg('skor'))
        return round(hasil['avg'], 1) if hasil['avg'] else 0


class Nilai(models.Model):
    sesi = models.ForeignKey(SesiPenilaian, on_delete=models.CASCADE)
    siswa = models.ForeignKey(Siswa, on_delete=models.CASCADE, related_name='nilai')
    skor = models.DecimalField(max_digits=5, decimal_places=1)
    catatan = models.TextField(blank=True)

    class Meta:
        unique_together = ['sesi', 'siswa']

    def __str__(self):
        return f"{self.siswa.nama} - {self.sesi.topik} - {self.skor}"