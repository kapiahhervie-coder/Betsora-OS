from django.db import models
from accounts.models import User, Siswa


class AlbumAudio(models.Model):
    judul = models.CharField(max_length=150)
    deskripsi = models.TextField(blank=True)
    dibuat_oleh = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-dibuat_pada']

    def __str__(self):
        return self.judul


class Audio(models.Model):
    album = models.ForeignKey(AlbumAudio, on_delete=models.CASCADE, related_name='audio_list')
    judul = models.CharField(max_length=150)
    file = models.FileField(upload_to='perpustakaan_audio/')
    urutan = models.PositiveIntegerField(default=0)
    diunggah_oleh = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['urutan', 'dibuat_pada']

    def __str__(self):
        return self.judul


class Zona(models.Model):
    nama = models.CharField(max_length=100)
    ikon = models.CharField(max_length=10, blank=True, help_text='Emoji, contoh: (tempel manual di sini)')
    warna = models.CharField(max_length=20, default='#0B3D26')
    deskripsi = models.TextField(blank=True)
    urutan = models.PositiveIntegerField(default=0)
    dibuat_oleh = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['urutan', 'nama']

    def __str__(self):
        return self.nama


class Lencana(models.Model):
    nama = models.CharField(max_length=100)
    ikon = models.CharField(max_length=10, blank=True)
    deskripsi = models.TextField(blank=True)

    class Meta:
        ordering = ['nama']

    def __str__(self):
        return self.nama


class SumberDigital(models.Model):
    JENIS_CHOICES = [
        ('TEKS', 'E-Book / Teks'),
        ('AUDIO', 'Audiobook'),
        ('VIDEO', 'Video'),
    ]
    zona = models.ForeignKey(Zona, on_delete=models.CASCADE, related_name='sumber_list')
    judul = models.CharField(max_length=200)
    deskripsi = models.TextField(blank=True)
    jenis = models.CharField(max_length=10, choices=JENIS_CHOICES, default='TEKS')
    cover = models.ImageField(upload_to='perpustakaan_cover/', blank=True, null=True)
    file = models.FileField(upload_to='perpustakaan_sumber/', blank=True, null=True)
    link_url = models.URLField(blank=True, null=True, help_text='Link video YouTube atau audio eksternal')
    teks_baca = models.TextField(blank=True, default='', help_text='Teks yang dibacakan otomatis (audiobook)')
    lencana_hadiah = models.ForeignKey(Lencana, on_delete=models.SET_NULL, null=True, blank=True)
    diunggah_oleh = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-dibuat_pada']

    def __str__(self):
        return self.judul

    def get_video_embed(self):
        import re
        url = self.link_url or ''
        yt_match = re.search(r'(?:youtu\.be/|youtube\.com/(?:watch\?v=|embed/|shorts/))([\w-]{11})', url)
        if yt_match:
            return 'https://www.youtube.com/embed/' + yt_match.group(1)
        return url


class RefleksiSiswa(models.Model):
    JENIS_CHOICES = [
        ('TEKS', 'Teks'),
        ('AUDIO', 'Rekaman Suara'),
        ('FOTO', 'Foto Karya'),
    ]
    siswa = models.ForeignKey('accounts.Siswa', on_delete=models.CASCADE, related_name='refleksi_perpustakaan')
    sumber = models.ForeignKey(SumberDigital, on_delete=models.CASCADE, related_name='refleksi_list')
    jenis = models.CharField(max_length=10, choices=JENIS_CHOICES, default='TEKS')
    teks = models.TextField(blank=True)
    file = models.FileField(upload_to='perpustakaan_refleksi/', blank=True, null=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-dibuat_pada']

    def __str__(self):
        return self.siswa.nama + ' - ' + self.sumber.judul


class LencanaDiperoleh(models.Model):
    siswa = models.ForeignKey('accounts.Siswa', on_delete=models.CASCADE, related_name='lencana_list')
    lencana = models.ForeignKey(Lencana, on_delete=models.CASCADE)
    sumber = models.ForeignKey(SumberDigital, on_delete=models.SET_NULL, null=True, blank=True)
    diperoleh_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('siswa', 'lencana', 'sumber')
        ordering = ['-diperoleh_pada']

    def __str__(self):
        return self.siswa.nama + ' - ' + self.lencana.nama


class HalamanSumber(models.Model):
    sumber = models.ForeignKey(SumberDigital, on_delete=models.CASCADE, related_name='halaman_list')
    nomor = models.PositiveIntegerField()
    gambar = models.ImageField(upload_to='perpustakaan_halaman/')
    teks = models.TextField(blank=True)

    class Meta:
        ordering = ['nomor']
        unique_together = ('sumber', 'nomor')

    def __str__(self):
        return self.sumber.judul + ' - hal ' + str(self.nomor)


class RiwayatBaca(models.Model):
    siswa = models.ForeignKey('accounts.Siswa', on_delete=models.CASCADE, related_name='riwayat_baca')
    sumber = models.ForeignKey(SumberDigital, on_delete=models.CASCADE, related_name='riwayat_baca')
    selesai_pada = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('siswa', 'sumber')
        ordering = ['-selesai_pada']

    def __str__(self):
        return self.siswa.nama + ' selesai baca ' + self.sumber.judul
