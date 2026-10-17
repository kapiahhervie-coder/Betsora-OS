from django.contrib import admin

from .models import CatatanMisi, Misi, PengerjaanMisi, PenugasanMisi


@admin.register(Misi)
class MisiAdmin(admin.ModelAdmin):
    list_display = ("judul", "kategori", "tingkat_min", "tingkat_max", "min_catatan", "misi_keluarga", "aktif")
    list_filter = ("kategori", "misi_keluarga", "aktif")
    search_fields = ("judul", "ringkasan")
    prepopulated_fields = {"slug": ("judul",)}

    def save_model(self, request, obj, form, change):
        if not change and not obj.dibuat_oleh_id:
            obj.dibuat_oleh = request.user
        super().save_model(request, obj, form, change)


@admin.register(PenugasanMisi)
class PenugasanMisiAdmin(admin.ModelAdmin):
    list_display = ("misi", "ruang_kerja", "materi", "tenggat", "dibuat_pada")
    list_filter = ("ruang_kerja",)


class CatatanInline(admin.TabularInline):
    model = CatatanMisi
    extra = 0


@admin.register(PengerjaanMisi)
class PengerjaanMisiAdmin(admin.ModelAdmin):
    list_display = ("siswa", "misi", "status", "mulai_pada", "dikonfirmasi_pada", "nilai")
    list_filter = ("status",)
    search_fields = ("siswa__nama", "misi__judul")
    inlines = [CatatanInline]
