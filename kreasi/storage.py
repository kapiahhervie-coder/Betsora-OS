import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateMediaStorage(FileSystemStorage):
    """
    Penyimpanan di luar MEDIA_ROOT. Berkas di sini TIDAK punya URL publik dan
    hanya bisa dibuka lewat view `kreasi:media`, yang mengecek hak akses.

    Lokasi dibaca dari settings.PRIVATE_MEDIA_ROOT setiap dipakai (bukan disimpan
    saat impor), sehingga bisa diganti lewat environment dan override_settings di tes.
    """

    @property
    def base_location(self):
        return str(settings.PRIVATE_MEDIA_ROOT)

    @property
    def location(self):
        return os.path.abspath(self.base_location)

    def url(self, name):
        # Sengaja kosong: jangan sampai berkas privat bocor lewat /media/.
        # Pakai properti `url_akses` pada model.
        return ''


def private_storage():
    """Dipanggil Django saat inisialisasi field, sehingga path tidak ikut tertulis di file migrasi."""
    return PrivateMediaStorage()
