"""Penyaji /media/ yang memeriksa IZIN, bukan hanya login (Tahap 4).

Sebelumnya semua akun yang login dapat mengunduh berkas apa pun di /media/ bila tahu (atau menebak)
namanya, termasuk berkas sekolah lain. Sekarang sebuah berkas hanya disajikan bila ada baris database
yang memilikinya DAN baris itu terlihat oleh akun yang meminta. "Terlihat" memakai penyaring yang sama
dengan seluruh aplikasi: sekolah, dan untuk guru juga ruang kerja/siswa miliknya (lihat accounts.tenancy).

Tambahan untuk siswa dan orang tua: berkas jawaban tugas dan berkas refleksi hanya untuk siswa pemiliknya.
Berkas privat (kreasi, foto catatan misi) tidak lewat sini; mereka punya penyaji berizin sendiri.
Berkas karya portofolio (/media/karya_siswa/) memakai penyaji portofolio dan tidak pernah sampai ke sini.
Berkas tanpa pemilik (sisa lama) hanya dapat dibuka superuser.
"""
import posixpath
from functools import lru_cache

from django.apps import apps
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.db import models
from django.http import Http404
from django.views.static import serve

BERBAHAYA = {'.html', '.htm', '.xhtml', '.svg', '.xml', '.js', '.mjs', '.swf'}
DILAYANI_PENYAJI_LAIN = {'portofolio.KaryaSiswa'}
# (model, bidang) -> nama kolom siswa; hanya siswa itu sendiri (atau orang tuanya) yang boleh membuka
MILIK_SISWA = {
    ('ruang_kerja.SubmisiTugas', 'file_jawaban'): 'siswa',
    ('perpustakaan.RefleksiSiswa', 'file'): 'siswa',
}


@lru_cache(maxsize=1)
def _bidang_berkas():
    """[(model, nama_bidang, awalan_upload_to or None)] untuk semua FileField di penyimpanan publik."""
    hasil = []
    for model in apps.get_models():
        label = f'{model._meta.app_label}.{model.__name__}'
        if label in DILAYANI_PENYAJI_LAIN:
            continue
        for f in model._meta.concrete_fields:
            if not isinstance(f, models.FileField) or f.storage is not default_storage:
                continue  # penyimpanan privat dilayani penyaji lain
            awalan = f.upload_to if isinstance(f.upload_to, str) else None
            if awalan is not None:
                awalan = awalan.split('%')[0]
            hasil.append((model, f.name, awalan or None))
    return tuple(hasil)


def _id_siswa(user):
    if getattr(user, 'role', None) == 'orangtua':
        return user.anak_id
    from accounts.models import Siswa
    return Siswa._base_manager.filter(user=user).values_list('pk', flat=True).first()


def boleh_membuka(user, path):
    """True bila ada baris berkas bernama `path` yang terlihat oleh `user` (dalam lingkup permintaan)."""
    role = getattr(user, 'role', None)
    id_siswa = None
    for model, bidang, awalan in _bidang_berkas():
        if awalan and not path.startswith(awalan):
            continue
        qs = model._default_manager.filter(**{bidang: path})
        kolom_siswa = MILIK_SISWA.get((f'{model._meta.app_label}.{model.__name__}', bidang))
        if kolom_siswa and role in ('siswa', 'orangtua'):
            if id_siswa is None:
                id_siswa = _id_siswa(user) or 0
            qs = qs.filter(**{kolom_siswa + '_id': id_siswa})
        if qs.exists():
            return True
    return False


@login_required
def sajikan_media(request, path):
    bersih = posixpath.normpath(path.replace('\\', '/'))
    if bersih in ('.', '') or bersih.startswith('/') or '..' in bersih.split('/'):
        raise Http404
    if not request.user.is_superuser and not boleh_membuka(request.user, bersih):
        raise Http404
    respons = serve(request, bersih, document_root=settings.MEDIA_ROOT)
    respons['X-Content-Type-Options'] = 'nosniff'
    respons['Cache-Control'] = 'private, max-age=300'
    ext = posixpath.splitext(bersih)[1].lower()
    if ext in BERBAHAYA:
        respons['Content-Disposition'] = 'attachment'
    return respons
