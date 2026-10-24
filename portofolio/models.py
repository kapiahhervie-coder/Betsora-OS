import re
from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.db import models
from django.utils import timezone
from accounts.models import Siswa

_ID_YOUTUBE = re.compile(r'^[\w-]{11}$')
_ID_DRIVE = re.compile(r'^[\w-]{10,100}$')
_HOST_YOUTUBE = {'youtube.com', 'www.youtube.com', 'm.youtube.com'}


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
    unggulan = models.BooleanField(default=False, help_text='Karya pilihan yang ditampilkan paling atas (maksimal 3 per siswa)')

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
        """URL embed yang aman, atau '' jika link bukan YouTube/Google Drive yang sah.

        Hanya alamat https/http dari YouTube dan Google Drive dengan ID yang valid yang
        dikembalikan. Link lain (termasuk data lama yang tersimpan sebelum aturan ini)
        dikosongkan, sehingga tidak pernah sampai ke halaman.
        """
        url = (self.video_url or '').strip()
        try:
            p = urlparse(url)
            host = (p.hostname or '').lower()
        except ValueError:
            return ''
        if p.scheme not in ('http', 'https'):
            return ''

        if host == 'youtu.be':
            vid = p.path.lstrip('/').split('/')[0]
        elif host in _HOST_YOUTUBE:
            if p.path == '/watch':
                vid = (parse_qs(p.query).get('v') or [''])[0]
            elif p.path.startswith('/embed/'):
                vid = p.path.split('/')[2] if len(p.path.split('/')) > 2 else ''
            else:
                vid = ''
        else:
            vid = ''
        if vid and _ID_YOUTUBE.match(vid):
            return f'https://www.youtube.com/embed/{vid}'

        if host == 'drive.google.com':
            m = re.match(r'^/file/d/([\w-]+)', p.path)
            if m and _ID_DRIVE.match(m.group(1)):
                return f'https://drive.google.com/file/d/{m.group(1)}/preview'
        return ''

    def has_video(self):
        return bool(self.get_video_embed())


class LencanaDiraih(models.Model):
    """Catatan lencana yang sudah diraih siswa. Sekali diraih, tidak hilang walau data berubah."""
    siswa = models.ForeignKey(Siswa, on_delete=models.CASCADE, related_name='lencana_diraih')
    kode = models.CharField(max_length=30)
    diraih_pada = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('siswa', 'kode')
        ordering = ['diraih_pada']
        verbose_name_plural = 'Lencana Diraih'

    def __str__(self):
        return f"{self.siswa.nama} - {self.kode}"


class KomentarKarya(models.Model):
    """Komentar/apresiasi guru pada sebuah karya. Hanya staf yang menulis; dibaca pemilik, orang tuanya, dan staf."""
    karya = models.ForeignKey(KaryaSiswa, on_delete=models.CASCADE, related_name='komentar')
    penulis = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='komentar_karya')
    teks = models.CharField(max_length=500)
    dibuat_pada = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['dibuat_pada', 'id']
        verbose_name_plural = 'Komentar Karya'

    def __str__(self):
        return f"{self.karya_id}: {self.teks[:40]}"
