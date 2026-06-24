from django.contrib import admin
from .models import Absensi, Keaktifan


@admin.register(Absensi)
class AbsensiAdmin(admin.ModelAdmin):
    list_display = ['siswa', 'tanggal', 'status']
    list_filter = ['status', 'tanggal']


@admin.register(Keaktifan)
class KeaktifanAdmin(admin.ModelAdmin):
    list_display = ['siswa', 'tanggal', 'poin', 'mapel']