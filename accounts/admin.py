from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Siswa


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'get_full_name', 'role']
    fieldsets = UserAdmin.fieldsets + (('Role', {'fields': ('role',)}),)


@admin.register(Siswa)
class SiswaAdmin(admin.ModelAdmin):
    list_display = ['nama', 'nis', 'kelas', 'aktif']
    list_filter = ['kelas', 'aktif']
    search_fields = ['nama', 'nis']