from django.db import models
from accounts.models import User, Siswa


class RuangKerja(models.Model):
    mapel = models.CharField(max_length=50)
    kelas = models.CharField(max_length=100)
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
    link_url = models.URLField(blank=True, null=True, help_text='Link website/artikel')
    video_url = models.CharField(max_length=300, blank=True, null=True, help_text='Link YouTube/Google Drive')
    urutan = models.PositiveIntegerField(default=0)
    diunggah_oleh = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['urutan', '-dibuat_pada']

    def __str__(self):
        return self.judul


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

class SubMateri(models.Model):
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
    ruang_kerja = models.ForeignKey(RuangKerja, on_delete=models.CASCADE, related_name='pengumuman')
    isi = models.TextField()
    diposting_oleh = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-dibuat_pada']

    def __str__(self):
        return f"{self.ruang_kerja} - {self.isi[:30]}"


class Tugas(models.Model):
    JENIS_CHOICES = [
        ('esai', 'Esai / Upload File'),
        ('pilihan_ganda', 'Pilihan Ganda'),
    ]
    ruang_kerja = models.ForeignKey(RuangKerja, on_delete=models.CASCADE, related_name='tugas')
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


class PesanChat(models.Model):
    ruang_kerja = models.ForeignKey(RuangKerja, on_delete=models.CASCADE, related_name='pesan_chat')
    isi = models.TextField()
    dikirim_oleh = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    dikirim_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['dikirim_pada']

    def __str__(self):
        return f"{self.dikirim_oleh} - {self.isi[:30]}"


class StatusBaca(models.Model):
    ruang_kerja = models.ForeignKey(RuangKerja, on_delete=models.CASCADE, related_name='status_baca')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='status_baca_ruang_kerja')
    terakhir_dibaca = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('ruang_kerja', 'user')

    def __str__(self):
        return f"{self.user} - {self.ruang_kerja}"


class AnggotaRuangKerja(models.Model):
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
    nama = models.CharField(max_length=50, unique=True)
    dibuat_oleh = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nama']

    def __str__(self):
        return self.nama


class RefleksiTopik(models.Model):
    """Refleksi siswa untuk satu topik (Materi), diisi setelah mempelajari topik tersebut."""
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
    ruang_kerja = models.ForeignKey(RuangKerja, on_delete=models.CASCADE, related_name='catatan_rapor')
    siswa = models.ForeignKey(Siswa, on_delete=models.CASCADE, related_name='catatan_rapor')
    catatan = models.TextField(blank=True)
    diperbarui_oleh = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    diperbarui_pada = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('ruang_kerja', 'siswa')

    def __str__(self):
        return f"Catatan {self.siswa.nama} - {self.ruang_kerja}"


class SoalPG(models.Model):
    tugas = models.ForeignKey(Tugas, on_delete=models.CASCADE, related_name='soal_pg')
    pertanyaan = models.TextField()
    urutan = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['urutan']

    def __str__(self):
        return self.pertanyaan[:50]


class OpsiPG(models.Model):
    soal = models.ForeignKey(SoalPG, on_delete=models.CASCADE, related_name='opsi')
    teks = models.CharField(max_length=255)
    is_benar = models.BooleanField(default=False)

    def __str__(self):
        return self.teks


class JawabanPG(models.Model):
    soal = models.ForeignKey(SoalPG, on_delete=models.CASCADE, related_name='jawaban')
    siswa = models.ForeignKey(Siswa, on_delete=models.CASCADE, related_name='jawaban_pg')
    opsi_dipilih = models.ForeignKey(OpsiPG, on_delete=models.CASCADE)
    dijawab_pada = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('soal', 'siswa')

    def __str__(self):
        return f'{self.siswa.nama} - {self.soal.pertanyaan[:30]}'
