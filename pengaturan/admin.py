from django.contrib import admin
from .models import PengaturanSekolah

@admin.register(PengaturanSekolah)
class PengaturanSekolahAdmin(admin.ModelAdmin):
    list_display = ("nama_institusi", "sekolah", "mode")

    def has_add_permission(self, request):
        return True  # satu per sekolah dijamin OneToOne

    def has_delete_permission(self, request, obj=None):
        return False