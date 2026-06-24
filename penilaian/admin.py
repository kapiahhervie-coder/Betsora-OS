from django.contrib import admin
from .models import SesiPenilaian, Nilai


@admin.register(SesiPenilaian)
class SesiAdmin(admin.ModelAdmin):
    list_display = ['mapel', 'topik', 'jenis', 'kelas', 'tanggal']
    list_filter = ['jenis', 'mapel', 'kelas']


@admin.register(Nilai)
class NilaiAdmin(admin.ModelAdmin):
    list_display = ['siswa', 'sesi', 'skor']