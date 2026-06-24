from django.contrib import admin
from .models import RuangKerja, Materi, Pengumuman, Tugas, SubmisiTugas


@admin.register(RuangKerja)
class RuangKerjaAdmin(admin.ModelAdmin):
    list_display = ['mapel', 'kelas', 'guru']
    list_filter = ['kelas', 'mapel']


@admin.register(Materi)
class MateriAdmin(admin.ModelAdmin):
    list_display = ['judul', 'ruang_kerja', 'dibuat_pada']


@admin.register(Pengumuman)
class PengumumanAdmin(admin.ModelAdmin):
    list_display = ['ruang_kerja', 'dibuat_pada']


@admin.register(Tugas)
class TugasAdmin(admin.ModelAdmin):
    list_display = ['judul', 'ruang_kerja', 'nilai_maksimal', 'dibuat_pada']
    list_filter = ['ruang_kerja']


@admin.register(SubmisiTugas)
class SubmisiTugasAdmin(admin.ModelAdmin):
    list_display = ['siswa', 'tugas', 'dikirim_pada', 'nilai']
    list_filter = ['tugas__ruang_kerja']