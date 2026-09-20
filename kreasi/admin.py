from django.contrib import admin

from .models import DeskriptorLevel, DimensiPenilaian, LampiranKarya, RefleksiKarya, SkorDimensi


class DeskriptorInline(admin.TabularInline):
    model = DeskriptorLevel
    extra = 0
    max_num = 4


@admin.register(DimensiPenilaian)
class DimensiPenilaianAdmin(admin.ModelAdmin):
    list_display = ('nama', 'jenjang', 'urutan', 'aktif')
    list_filter = ('jenjang', 'aktif')
    inlines = [DeskriptorInline]


# Berkas privat: tidak ditampilkan di admin agar tidak ada tautan ke /media/.
@admin.register(LampiranKarya)
class LampiranKaryaAdmin(admin.ModelAdmin):
    list_display = ('submisi', 'tipe', 'nama_asli', 'dibuat_pada')
    list_filter = ('tipe',)
    exclude = ('file',)
    readonly_fields = ('nama_asli',)


@admin.register(RefleksiKarya)
class RefleksiKaryaAdmin(admin.ModelAdmin):
    list_display = ('submisi', 'tipe', 'dibuat_pada')
    exclude = ('audio',)


@admin.register(SkorDimensi)
class SkorDimensiAdmin(admin.ModelAdmin):
    list_display = ('submisi', 'dimensi', 'level', 'dinilai_oleh', 'diperbarui_pada')
    list_filter = ('dimensi__jenjang',)
