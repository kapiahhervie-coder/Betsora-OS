from django.db import models
from accounts.models import User, Siswa


class RuangKerja(models.Model):
    mapel = models.CharField(max_length=50)
    kelas = models.CharField(max_length=10)
    deskripsi = models.TextField(blank=True)
    guru = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='ruang_kerja_dikelola')
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['kelas', 'mapel']
        unique_together = ['mapel', 'kelas']

    def __str__(self):
        return f"{self.mapel} - Kelas {self.kelas}"


class Materi(models.Model):
    ruang_kerja = models.ForeignKey(RuangKerja, on_delete=models.CASCADE, related_name='materi')
    judul = models.CharField(max_length=150)
    deskripsi = models.TextField(blank=True)
    file = models.FileField(upload_to='materi/', blank=True, null=True)
    diunggah_oleh = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-dibuat_pada']

    def __str__(self):
        return self.judul


class Pengumuman(models.Model):
    ruang_kerja = models.ForeignKey(RuangKerja, on_delete=models.CASCADE, related_name='pengumuman')
    isi = models.TextField()
    diposting_oleh = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-dibuat_pada']

    def __str__(self):
        return f"{self.ruang_kerja} - {self.isi[:30]}"


class Tugas(models.Model):
    ruang_kerja = models.ForeignKey(RuangKerja, on_delete=models.CASCADE, related_name='tugas')
    judul = models.CharField(max_length=150)
    instruksi = models.TextField()
    deadline = models.DateTimeField(null=True, blank=True)
    nilai_maksimal = models.PositiveIntegerField(default=100)
    dibuat_oleh = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-dibuat_pada']

    def __str__(self):
        return self.judul

    def sudah_submit(self, siswa):
        return self.submisi.filter(siswa=siswa).exists()

    def get_submisi(self, siswa):
        return self.submisi.filter(siswa=siswa).first()


class SubmisiTugas(models.Model):
    tugas = models.ForeignKey(Tugas, on_delete=models.CASCADE, related_name='submisi')
    siswa = models.ForeignKey(Siswa, on_delete=models.CASCADE, related_name='submisi_tugas')
    teks_jawaban = models.TextField(blank=True)
    file_jawaban = models.FileField(upload_to='submisi/', blank=True, null=True)
    dikirim_pada = models.DateTimeField(auto_now_add=True)
    nilai = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    feedback = models.TextField(blank=True)
    dinilai_pada = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['tugas', 'siswa']
        ordering = ['-dikirim_pada']

    def __str__(self):
        return f"{self.siswa.nama} - {self.tugas.judul}"


class Diskusi(models.Model):
    ruang_kerja = models.ForeignKey(RuangKerja, on_delete=models.CASCADE, related_name='diskusi')
    judul = models.CharField(max_length=200)
    isi = models.TextField()
    diposting_oleh = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)
    ditutup = models.BooleanField(default=False)

    class Meta:
        ordering = ['-dibuat_pada']

    def __str__(self):
        return self.judul


class KomentarDiskusi(models.Model):
    diskusi = models.ForeignKey(Diskusi, on_delete=models.CASCADE, related_name='komentar')
    isi = models.TextField()
    diposting_oleh = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['dibuat_pada']

    def __str__(self):
        return f"{self.diposting_oleh} - {self.diskusi.judul}"