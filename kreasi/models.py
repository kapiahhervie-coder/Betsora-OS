import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse

from .fase_config import JENJANG_CHOICES, LEVEL_LABEL
from .storage import private_storage

EKSTENSI_TIPE = {
    'foto': {'jpg', 'jpeg', 'png', 'gif', 'webp', 'heic'},
    'audio': {'mp3', 'wav', 'ogg', 'm4a', 'aac', 'webm'},
    'video': {'mp4', 'mov', 'mkv', 'avi', 'webm'},
    'dokumen': {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt'},
}


def _path_lampiran(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f'lampiran/{instance.submisi.siswa_id}/{uuid.uuid4().hex}{ext}'


def _path_refleksi(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f'refleksi/{instance.submisi.siswa_id}/{uuid.uuid4().hex}{ext}'


class LampiranKarya(models.Model):
    """Satu bagian dari karya siswa. Satu submisi boleh punya banyak lampiran."""
    TIPE_CHOICES = [
        ('foto', 'Foto'),
        ('audio', 'Rekaman Suara'),
        ('video', 'Video'),
        ('dokumen', 'Dokumen'),
        ('link', 'Tautan'),
    ]
    submisi = models.ForeignKey('ruang_kerja.SubmisiTugas', on_delete=models.CASCADE, related_name='lampiran_karya')
    tipe = models.CharField(max_length=10, choices=TIPE_CHOICES)
    file = models.FileField(upload_to=_path_lampiran, storage=private_storage, blank=True, null=True)
    nama_asli = models.CharField(max_length=255, blank=True)
    url = models.URLField(max_length=500, blank=True)
    keterangan = models.CharField(max_length=200, blank=True)
    urutan = models.PositiveSmallIntegerField(default=0)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['urutan', 'id']
        verbose_name = 'Lampiran karya'
        verbose_name_plural = 'Lampiran karya'

    def __str__(self):
        return f'{self.get_tipe_display()} - {self.nama_asli or self.url or self.pk}'

    def clean(self):
        if not self.file and not self.url:
            raise ValidationError('Lampiran harus berisi berkas atau tautan.')

    @staticmethod
    def deteksi_tipe(nama_file, petunjuk=None):
        """
        Tebak tipe dari ekstensi. `.webm` ambigu (rekaman suara browser juga .webm),
        jadi bila `petunjuk` valid (mis. dari tombol yang ditekan siswa), petunjuk dipakai.
        """
        ext = os.path.splitext(nama_file or '')[1].lower().lstrip('.')
        if petunjuk in EKSTENSI_TIPE and ext in EKSTENSI_TIPE[petunjuk]:
            return petunjuk
        for tipe in ('foto', 'dokumen', 'video', 'audio'):
            if ext in EKSTENSI_TIPE[tipe]:
                return tipe
        return None

    @property
    def url_akses(self):
        if not self.file:
            return self.url
        return reverse('kreasi:media', args=['lampiran', self.pk])


class RefleksiKarya(models.Model):
    """Refleksi siswa atas karyanya. Bentuk isinya mengikuti jenjang (lihat fase_config)."""
    TIPE_CHOICES = [
        ('emoji_suara', 'Emoji + Rekaman Suara'),
        ('teks_terbimbing', 'Teks Terbimbing'),
        ('matriks', 'Matriks Evaluasi Diri'),
        ('metakognitif', 'Refleksi Metakognitif'),
    ]
    submisi = models.OneToOneField('ruang_kerja.SubmisiTugas', on_delete=models.CASCADE, related_name='refleksi_karya')
    tipe = models.CharField(max_length=20, choices=TIPE_CHOICES)
    emoji = models.CharField(max_length=20, blank=True, help_text='Kunci pilihan emoji, mis. "bangga"')
    jawaban = models.JSONField(default=dict, blank=True, help_text='Jawaban terbimbing / matriks, kunci = kode pertanyaan')
    audio = models.FileField(upload_to=_path_refleksi, storage=private_storage, blank=True, null=True)
    transkrip = models.TextField(blank=True, help_text='Diisi otomatis oleh speech-to-text pada tahap lanjutan')
    dibuat_pada = models.DateTimeField(auto_now_add=True)
    diperbarui_pada = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Refleksi karya'
        verbose_name_plural = 'Refleksi karya'

    def __str__(self):
        return f'Refleksi {self.submisi}'

    @property
    def url_audio(self):
        if not self.audio:
            return ''
        return reverse('kreasi:media', args=['refleksi', self.pk])


class DimensiPenilaian(models.Model):
    """
    Dimensi rapor sebagai DATA, bukan kolom tetap. Sekolah bisa menambah dimensi baru
    (mis. Profil Pelajar Pancasila) atau menonaktifkan yang lama tanpa migrasi.
    """
    jenjang = models.CharField(max_length=10, choices=JENJANG_CHOICES)
    kode = models.SlugField(max_length=40)
    nama = models.CharField(max_length=100)
    urutan = models.PositiveSmallIntegerField(default=0)
    aktif = models.BooleanField(default=True, help_text='Nonaktifkan, jangan hapus, agar skor lama tetap tersimpan')

    class Meta:
        ordering = ['jenjang', 'urutan', 'id']
        unique_together = ('jenjang', 'kode')
        verbose_name = 'Dimensi penilaian'
        verbose_name_plural = 'Dimensi penilaian'

    def __str__(self):
        return f'{self.get_jenjang_display()} - {self.nama}'


class DeskriptorLevel(models.Model):
    """Satu kalimat per dimensi per level (1-4). Pakai {nama} untuk nama depan siswa."""
    LEVEL_CHOICES = [(k, f'{k} - {v}') for k, v in LEVEL_LABEL.items()]
    dimensi = models.ForeignKey(DimensiPenilaian, on_delete=models.CASCADE, related_name='deskriptor')
    level = models.PositiveSmallIntegerField(choices=LEVEL_CHOICES)
    kalimat = models.TextField()

    class Meta:
        ordering = ['dimensi', 'level']
        unique_together = ('dimensi', 'level')
        verbose_name = 'Deskriptor level'
        verbose_name_plural = 'Deskriptor level'

    def __str__(self):
        return f'{self.dimensi.nama} - level {self.level}'

    def untuk(self, nama_depan):
        return self.kalimat.replace('{nama}', nama_depan)


class SkorDimensi(models.Model):
    """Skor guru (1-4) untuk satu dimensi pada satu submisi karya."""
    submisi = models.ForeignKey('ruang_kerja.SubmisiTugas', on_delete=models.CASCADE, related_name='skor_dimensi')
    dimensi = models.ForeignKey(DimensiPenilaian, on_delete=models.PROTECT, related_name='skor')
    level = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(4)])
    catatan = models.TextField(blank=True)
    dinilai_oleh = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    diperbarui_pada = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('submisi', 'dimensi')
        ordering = ['submisi', 'dimensi__urutan']
        verbose_name = 'Skor dimensi'
        verbose_name_plural = 'Skor dimensi'

    def __str__(self):
        return f'{self.dimensi.nama}: {self.level}'

    @property
    def label_level(self):
        return LEVEL_LABEL.get(self.level, '')
