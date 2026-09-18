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
    file = models.FileField(upload_to='karya_siswa/', blank=True, null=True)
    video_url = models.CharField(max_length=300, blank=True, null=True, help_text='Link YouTube/Google Drive (opsional)')
    dibagikan = models.BooleanField(default=False, help_text='Jika dicentang, siswa lain juga bisa melihat karya ini')
    diunggah_pada = models.DateTimeField(auto_now_add=True)
    refleksi = models.TextField(blank=True, help_text='Refleksi siswa: tantangan terbesar & perasaan setelah menyelesaikan karya ini')

    class Meta:
        ordering = ['-diunggah_pada']
        verbose_name_plural = 'Karya Siswa'

    def __str__(self):
        return f"{self.siswa.nama} - {self.judul}"

    def is_image(self):
        if not self.file:
            return False
        ext = self.file.name.lower().split('.')[-1]
        return ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']

    def get_video_embed(self):
        import re
        url = self.video_url or ''
        yt_match = re.search(r'(?:youtu\.be/|youtube\.com/watch\?v=|youtube\.com/embed/)([\w-]+)', url)
        if yt_match:
            return f'https://www.youtube.com/embed/{yt_match.group(1)}'
        gdrive_match = re.search(r'drive\.google\.com/file/d/([\w-]+)', url)
        if gdrive_match:
            return f'https://drive.google.com/file/d/{gdrive_match.group(1)}/preview'
        return url
