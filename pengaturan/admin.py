from django.contrib import admin
from .models import PengaturanSekolah

@admin.register(PengaturanSekolah)
class PengaturanSekolahAdmin(admin.ModelAdmin):
    list_display = ("nama_institusi", "mode")

    def has_add_permission(self, request):
        return not PengaturanSekolah.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False