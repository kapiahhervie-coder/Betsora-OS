from django.db import models
from accounts.models import User


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
