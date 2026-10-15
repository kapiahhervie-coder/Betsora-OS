from django.contrib import admin

from .models import Kuis, Soal


class SoalInline(admin.TabularInline):
    model = Soal
    extra = 0


@admin.register(Kuis)
class KuisAdmin(admin.ModelAdmin):
    list_display = ("judul", "pembuat", "dibagikan", "diperbarui_pada")
    list_filter = ("dibagikan",)
    search_fields = ("judul", "pembuat__username")
    inlines = [SoalInline]