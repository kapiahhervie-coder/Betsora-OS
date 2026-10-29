from django.db import models
from accounts.tenancy import SekolahManager
from accounts.models import User, Siswa
from kreasi.fase_config import JENJANG_CHOICES, deteksi_jenjang

class Kelas(models.Model):
    objects = SekolahManager()

    sekolah = models.ForeignKey('accounts.Sekolah', on_delete=models.PROTECT, null=True, blank=True)
    nama = models.CharField(max_length=100, help_text="Contoh: III, X-1, Kelas 5")
    jenjang = models.CharField(max_length=10, choices=JENJANG_CHOICES, blank=True, help_text='Kosongkan agar dideteksi otomatis dari nama kelas')
    wali_kelas = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='kelas_diwalikan')
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nama']
        constraints = [
            models.UniqueConstraint(fields=['sekolah', 'nama'], name='kelas_nama_unik_per_sekolah'),
            models.UniqueConstraint(fields=['nama'], condition=models.Q(sekolah__isnull=True), name='kelas_nama_unik_tanpa_sekolah'),
        ]

    def __str__(self):
        return self.label_kelas

    def get_jenjang(self):
        return self.jenjang or deteksi_jenjang(self.nama)

    @property
    def label_kelas(self):
        n = (self.nama or '').strip()
        if n.lower().startswith('kelas'):
            return n
        return 'Kelas ' + n


class RuangKerja(models.Model):
    objects = SekolahManager(guru=('ruang', ''))

    sekolah = models.ForeignKey('accounts.Sekolah', on_delete=models.PROTECT, null=True, blank=True)
    mapel = models.CharField(max_length=50)
    kelas = models.CharField(max_length=100)
    kelas_baru = models.ForeignKey('Kelas', on_delete=models.SET_NULL, null=True, blank=True, related_name='ruang_kerja')
    deskripsi = models.TextField(blank=True)
    guru = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='ruang_kerja_dikelola')
    dibuat_pada = models.DateTimeField(auto_now_add=True)
    jenjang = models.CharField(max_length=10, choices=JENJANG_CHOICES, blank=True, help_text='Kosongkan agar dideteksi otomatis dari nama kelas')

    class Meta:
        ordering = ['kelas', 'mapel']
        constraints = [
            models.UniqueConstraint(fields=['sekolah', 'mapel', 'kelas'], name='ruangkerja_mapel_kelas_unik_per_sekolah'),
            models.UniqueConstraint(fields=['mapel', 'kelas'], condition=models.Q(sekolah__isnull=True), name='ruangkerja_mapel_kelas_unik_tanpa_sekolah'),
        ]

    def __str__(self):
        return f"{self.mapel} - Kelas {self.kelas}"

    def get_jenjang(self):
        """Jenjang pilihan guru, atau tebakan dari nama kelas ('3', 'Kelas III', 'X-1')."""
        return self.jenjang or deteksi_jenjang(self.kelas)

    @property
    def label_kelas(self):
        k = (self.kelas or '').strip()
        if k.lower().startswith('kelas'):
            return k
        return 'Kelas ' + k


class Materi(models.Model):
    objects = SekolahManager('ruang_kerja__sekolah', guru=('ruang', 'ruang_kerja'))

    ruang_kerja = models.ForeignKey(RuangKerja, on_delete=models.CASCADE, related_name='materi')
    judul = models.CharField(max_length=150)
    deskripsi = models.TextField(blank=True)
    file = models.FileField(upload_to='materi/', blank=True, null=True)
    link_url = models.URLField(blank=True, null=True, help_text='Link website/artikel')
    video_url = models.CharField(max_length=300, blank=True, null=True, help_text='Link YouTube/Google Drive')
    urutan = models.PositiveIntegerField(default=0)
    diunggah_oleh = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['urutan', '-dibuat_pada']

    def __str__(self):
        return self.judul

    def get_tipe_media(self):
        # Kumpulan tipe media di topik ini (dari Materi sendiri + semua SubMateri).
        # Dipakai untuk badge indikator multimodal di daftar topik.
        tipe = set()
        items = list(self.sub_materi.all()) + [self]
        for item in items:
            if getattr(item, "is_video_file", None) and item.is_video_file():
                tipe.add("video")
            elif getattr(item, "is_audio_file", None) and item.is_audio_file():
                tipe.add("audio")
            elif item.file:
                tipe.add("dokumen")
            if item.video_url:
                tipe.add("video")
            if item.link_url:
                tipe.add("link")
        return tipe


    def hitung_mastery(self, siswa):
        """
        Hitung persentase mastery siswa untuk topik (Materi) ini.
        Remedial menggantikan Sumatif jika ada. Skala nilai: 0-100.
        Return None jika siswa belum punya nilai sumatif/remedial sama sekali.
        """
        penilaian_qs = self.penilaian.filter(siswa=siswa)
        remedial = penilaian_qs.filter(jenis='remedial').order_by('-diperbarui_pada').first()
        sumatif = penilaian_qs.filter(jenis='sumatif').order_by('-diperbarui_pada').first()

        nilai_akhir = None
        if remedial and remedial.nilai is not None:
            nilai_akhir = remedial.nilai
        elif sumatif and sumatif.nilai is not None:
            nilai_akhir = sumatif.nilai

        if nilai_akhir is None:
            return None
        return round(float(nilai_akhir), 1)

    def is_mastered(self, siswa, threshold=75):
        """True jika mastery siswa terhadap topik ini >= threshold (default 100%)."""
        mastery = self.hitung_mastery(siswa)
        return mastery is not None and mastery >= threshold

    def is_locked_for(self, siswa):
        """
        True jika ada prasyarat yang belum tuntas mastery-nya untuk siswa ini.
        Materi tanpa prasyarat sama sekali selalu unlocked.
        """
        for pra in self.prasyarat.select_related('prasyarat').all():
            mastery_siswa = pra.prasyarat.hitung_mastery(siswa)
            if mastery_siswa is None or mastery_siswa < pra.mastery_required:
                return True
        return False

    def status_selesai(self, siswa):
        """
        Status penyelesaian topik untuk seorang siswa: semua item materi sudah
        dilihat DAN semua tugas yang dihubungkan ke topik ini sudah dikumpulkan.
        Topik tanpa item dan tanpa tugas dianggap selesai (tidak ada yang perlu dikerjakan).
        """
        items = list(self.sub_materi.all())
        total_item = len(items)
        item_dilihat = 0
        if items:
            item_dilihat = ProgresItem.objects.filter(siswa=siswa, sub_materi__in=items).count()
        tugas_ids = list(self.tugas_terkait.values_list('id', flat=True))
        total_tugas = len(tugas_ids)
        tugas_terkirim = 0
        if tugas_ids:
            tugas_terkirim = SubmisiTugas.objects.filter(
                siswa=siswa, tugas_id__in=tugas_ids
            ).values('tugas_id').distinct().count()
        return {
            'selesai': item_dilihat >= total_item and tugas_terkirim >= total_tugas,
            'item_dilihat': item_dilihat,
            'item_total': total_item,
            'tugas_terkirim': tugas_terkirim,
            'tugas_total': total_tugas,
        }


class SubMateri(models.Model):
    objects = SekolahManager('materi__ruang_kerja__sekolah', guru=('ruang', 'materi__ruang_kerja'))

    materi = models.ForeignKey(Materi, on_delete=models.CASCADE, related_name='sub_materi')
    judul = models.CharField(max_length=150)
    deskripsi = models.TextField(blank=True)
    file = models.FileField(upload_to='sub_materi/', blank=True, null=True)
    link_url = models.URLField(blank=True, null=True)
    video_url = models.CharField(max_length=300, blank=True, null=True)
    urutan = models.PositiveIntegerField(default=0)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['urutan', 'dibuat_pada']

    def __str__(self):
        return self.judul

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

    def is_video_file(self):
        if not self.file:
            return False
        ext = self.file.name.lower().split('.')[-1]
        return ext in ['mp4', 'webm', 'ogg', 'mov', 'mkv', 'avi']

    def is_audio_file(self):
        if not self.file:
            return False
        ext = self.file.name.lower().split('.')[-1]
        return ext in ['mp3', 'wav', 'ogg', 'm4a', 'aac']


class Pengumuman(models.Model):
    objects = SekolahManager('ruang_kerja__sekolah', guru=('ruang', 'ruang_kerja'))

    ruang_kerja = models.ForeignKey(RuangKerja, on_delete=models.CASCADE, related_name='pengumuman')
    isi = models.TextField()
    diposting_oleh = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-dibuat_pada']

    def __str__(self):
        return f"{self.ruang_kerja} - {self.isi[:30]}"


class Tugas(models.Model):
    objects = SekolahManager('ruang_kerja__sekolah', guru=('ruang', 'ruang_kerja'))

    JENIS_CHOICES = [
        ('esai', 'Esai / Upload File'),
        ('pilihan_ganda', 'Pilihan Ganda'),
        ('kreasi', 'Tugas Kreasi (Portofolio)'),
    ]
    ruang_kerja = models.ForeignKey(RuangKerja, on_delete=models.CASCADE, related_name='tugas')
    materi = models.ForeignKey('Materi', on_delete=models.SET_NULL, null=True, blank=True, related_name='tugas_terkait', help_text='Opsional: hubungkan ke topik agar jadi syarat membuka topik berikutnya')
    jenis = models.CharField(max_length=20, choices=JENIS_CHOICES, default='esai')
    judul = models.CharField(max_length=150)
    instruksi = models.TextField()
    deadline = models.DateTimeField(null=True, blank=True)
    nilai_maksimal = models.PositiveIntegerField(default=100)
    lampiran = models.FileField(upload_to='tugas_lampiran/', blank=True, null=True)
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
    objects = SekolahManager('tugas__ruang_kerja__sekolah', guru=('ruang', 'tugas__ruang_kerja'))

    tugas = models.ForeignKey(Tugas, on_delete=models.CASCADE, related_name='submisi')
    siswa = models.ForeignKey(Siswa, on_delete=models.CASCADE, related_name='submisi_tugas')
    teks_jawaban = models.TextField(blank=True)
    file_jawaban = models.FileField(upload_to='submisi/', blank=True, null=True)
    dikirim_pada = models.DateTimeField(auto_now_add=True)
    nilai = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    feedback = models.TextField(blank=True)
    dinilai_pada = models.DateTimeField(null=True, blank=True)
    boleh_ulang = models.BooleanField(default=False, help_text='Jika dicentang guru, siswa boleh mengerjakan ulang tugas ini sekali lagi.')

    class Meta:
        unique_together = ['tugas', 'siswa']
        ordering = ['-dikirim_pada']

    def __str__(self):
        return f"{self.siswa.nama} - {self.tugas.judul}"


class Diskusi(models.Model):
    objects = SekolahManager('ruang_kerja__sekolah', guru=('ruang', 'ruang_kerja'))

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
    objects = SekolahManager('diskusi__ruang_kerja__sekolah', guru=('ruang', 'diskusi__ruang_kerja'))

    diskusi = models.ForeignKey(Diskusi, on_delete=models.CASCADE, related_name='komentar')
    isi = models.TextField()
    diposting_oleh = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['dibuat_pada']

    def __str__(self):
        return f"{self.diposting_oleh} - {self.diskusi.judul}"


class PesanChat(models.Model):
    objects = SekolahManager('ruang_kerja__sekolah', guru=('ruang', 'ruang_kerja'))

    ruang_kerja = models.ForeignKey(RuangKerja, on_delete=models.CASCADE, related_name='pesan_chat')
    isi = models.TextField()
    dikirim_oleh = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    dikirim_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['dikirim_pada']

    def __str__(self):
        return f"{self.dikirim_oleh} - {self.isi[:30]}"


class StatusBaca(models.Model):
    objects = SekolahManager('ruang_kerja__sekolah', guru=('ruang', 'ruang_kerja'))

    ruang_kerja = models.ForeignKey(RuangKerja, on_delete=models.CASCADE, related_name='status_baca')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='status_baca_ruang_kerja')
    terakhir_dibaca = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('ruang_kerja', 'user')

    def __str__(self):
        return f"{self.user} - {self.ruang_kerja}"


class AnggotaRuangKerja(models.Model):
    objects = SekolahManager('ruang_kerja__sekolah', guru=('ruang', 'ruang_kerja'))

    ruang_kerja = models.ForeignKey(RuangKerja, on_delete=models.CASCADE, related_name='anggota')
    siswa = models.ForeignKey(Siswa, on_delete=models.CASCADE, related_name='ruang_kerja_diikuti')
    ditambahkan_pada = models.DateTimeField(auto_now_add=True)
    ditambahkan_oleh = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='anggota_ditambahkan')

    class Meta:
        unique_together = ('ruang_kerja', 'siswa')
        ordering = ['siswa__nama']

    def __str__(self):
        return f"{self.siswa.nama} - {self.ruang_kerja}"


class MataPelajaran(models.Model):
    objects = SekolahManager()

    sekolah = models.ForeignKey('accounts.Sekolah', on_delete=models.PROTECT, null=True, blank=True)
    nama = models.CharField(max_length=50)
    dibuat_oleh = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nama']
        constraints = [
            models.UniqueConstraint(fields=['sekolah', 'nama'], name='mapel_nama_unik_per_sekolah'),
            models.UniqueConstraint(fields=['nama'], condition=models.Q(sekolah__isnull=True), name='mapel_nama_unik_tanpa_sekolah'),
        ]

    def __str__(self):
        return self.nama


class RefleksiTopik(models.Model):
    """Refleksi siswa untuk satu topik (Materi), diisi setelah mempelajari topik tersebut."""
    objects = SekolahManager('materi__ruang_kerja__sekolah', guru=('ruang', 'materi__ruang_kerja'))

    materi = models.ForeignKey(Materi, on_delete=models.CASCADE, related_name='refleksi')
    siswa = models.ForeignKey(Siswa, on_delete=models.CASCADE, related_name='refleksi_topik')
    isi = models.TextField(blank=True)
    diperbarui_pada = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('materi', 'siswa')

    def __str__(self):
        return f"Refleksi {self.siswa.nama} - {self.materi.judul}"


class PenilaianTopik(models.Model):
    """Penilaian formatif/sumatif/remedial per siswa untuk satu topik, terpisah dari Tugas.
    Formatif boleh berkali-kali (banyak baris), Sumatif & Remedial biasanya satu baris per siswa
    (diatur di level aplikasi/view, bukan database)."""
    objects = SekolahManager('materi__ruang_kerja__sekolah', guru=('ruang', 'materi__ruang_kerja'))

    JENIS_CHOICES = [
        ('formatif', 'Formatif'),
        ('sumatif', 'Sumatif'),
        ('remedial', 'Remedial'),
    ]
    materi = models.ForeignKey(Materi, on_delete=models.CASCADE, related_name='penilaian')
    siswa = models.ForeignKey(Siswa, on_delete=models.CASCADE, related_name='penilaian_topik')
    jenis = models.CharField(max_length=10, choices=JENIS_CHOICES)
    nilai = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    catatan = models.TextField(blank=True)
    dinilai_oleh = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)
    diperbarui_pada = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['jenis', 'dibuat_pada']

    def __str__(self):
        return f"{self.get_jenis_display()} - {self.siswa.nama} - {self.materi.judul}"


class CatatanRapor(models.Model):
    objects = SekolahManager('ruang_kerja__sekolah', guru=('ruang', 'ruang_kerja'))

    ruang_kerja = models.ForeignKey(RuangKerja, on_delete=models.CASCADE, related_name='catatan_rapor')
    siswa = models.ForeignKey(Siswa, on_delete=models.CASCADE, related_name='catatan_rapor')
    catatan = models.TextField(blank=True)
    catatan_disiplin = models.TextField(blank=True, help_text='Perkembangan disiplin & kebiasaan belajar siswa')
    catatan_fisik_motorik = models.TextField(blank=True, help_text='Perkembangan fisik & motorik siswa')
    diperbarui_oleh = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    diperbarui_pada = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('ruang_kerja', 'siswa')

    def __str__(self):
        return f"Catatan {self.siswa.nama} - {self.ruang_kerja}"


class SoalPG(models.Model):
    objects = SekolahManager('tugas__ruang_kerja__sekolah', guru=('ruang', 'tugas__ruang_kerja'))

    tugas = models.ForeignKey(Tugas, on_delete=models.CASCADE, related_name='soal_pg')
    pertanyaan = models.TextField()
    urutan = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['urutan']

    def __str__(self):
        return self.pertanyaan[:50]


class OpsiPG(models.Model):
    objects = SekolahManager('soal__tugas__ruang_kerja__sekolah', guru=('ruang', 'soal__tugas__ruang_kerja'))

    soal = models.ForeignKey(SoalPG, on_delete=models.CASCADE, related_name='opsi')
    teks = models.CharField(max_length=255)
    is_benar = models.BooleanField(default=False)

    def __str__(self):
        return self.teks


class JawabanPG(models.Model):
    objects = SekolahManager('soal__tugas__ruang_kerja__sekolah', guru=('ruang', 'soal__tugas__ruang_kerja'))

    soal = models.ForeignKey(SoalPG, on_delete=models.CASCADE, related_name='jawaban')
    siswa = models.ForeignKey(Siswa, on_delete=models.CASCADE, related_name='jawaban_pg')
    opsi_dipilih = models.ForeignKey(OpsiPG, on_delete=models.CASCADE)
    dijawab_pada = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('soal', 'siswa')

    def __str__(self):
        return f'{self.siswa.nama} - {self.soal.pertanyaan[:30]}'


class MateriPrasyarat(models.Model):
    """
    Relasi prasyarat antar topik (Materi). Guru menentukan manual topik mana
    harus tuntas dulu sebelum topik lain bisa diakses siswa.
    """
    objects = SekolahManager('materi__ruang_kerja__sekolah', guru=('ruang', 'materi__ruang_kerja'))

    materi = models.ForeignKey(Materi, on_delete=models.CASCADE, related_name='prasyarat')
    prasyarat = models.ForeignKey(Materi, on_delete=models.CASCADE, related_name='membuka')
    mastery_required = models.PositiveSmallIntegerField(default=75, help_text='Persentase mastery minimal (0-100) dari topik prasyarat')
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('materi', 'prasyarat')
        ordering = ['materi', 'prasyarat']

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.materi_id == self.prasyarat_id:
            raise ValidationError('Topik tidak bisa menjadi prasyarat untuk dirinya sendiri.')
        if self.materi.ruang_kerja_id != self.prasyarat.ruang_kerja_id:
            raise ValidationError('Prasyarat harus berasal dari ruang kerja yang sama.')

    def __str__(self):
        return f"{self.prasyarat.judul} -> membuka -> {self.materi.judul}"


class ProgresItem(models.Model):
    """Mencatat item materi yang sudah dibuka/dilihat siswa (syarat membuka topik berikutnya)."""
    objects = SekolahManager('sub_materi__materi__ruang_kerja__sekolah', guru=('ruang', 'sub_materi__materi__ruang_kerja'))

    siswa = models.ForeignKey(Siswa, on_delete=models.CASCADE, related_name='progres_item')
    sub_materi = models.ForeignKey(SubMateri, on_delete=models.CASCADE, related_name='progres')
    dilihat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('siswa', 'sub_materi')

    def __str__(self):
        return f"{self.siswa} - {self.sub_materi}"
