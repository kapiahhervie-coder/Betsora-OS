from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Siswa, Sekolah


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'get_full_name', 'role', 'sekolah']
    list_filter = UserAdmin.list_filter + ('role', 'sekolah')
    fieldsets = UserAdmin.fieldsets + (('Role', {'fields': ('role', 'sekolah')}),)
    add_fieldsets = UserAdmin.add_fieldsets + ((None, {'fields': ('role', 'sekolah')}),)


@admin.register(Siswa)
class SiswaAdmin(admin.ModelAdmin):
    list_display = ['nama', 'nis', 'kelas', 'aktif', 'sekolah']
    list_filter = ['sekolah', 'kelas', 'aktif']
    search_fields = ['nama', 'nis']


@admin.register(Sekolah)
class SekolahAdmin(admin.ModelAdmin):
    list_display = ['nama', 'kode', 'aktif', 'dibuat_pada']
    list_filter = ['aktif']
    search_fields = ['nama', 'kode']
    prepopulated_fields = {'kode': ('nama',)}


def _hanya_superuser(request):
    """Django admin adalah alat ADMIN PLATFORM: ia melihat semua sekolah. Kepala sekolah dan admin sekolah
    memakai halaman aplikasi (yang disaring per sekolah), bukan Django admin."""
    return bool(request.user.is_active and request.user.is_superuser)


admin.site.has_permission = _hanya_superuser
