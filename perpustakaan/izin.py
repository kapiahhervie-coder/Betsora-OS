"""Satu-satunya tempat yang menentukan siapa yang dianggap staf di app perpustakaan.

Sebelumnya ada tiga mekanisme berbeda (@hanya_staf, STAF_ROLES, is_staff_role()) yang
dipakai bergantian dan di beberapa view saling bertentangan. Sekarang semua view
memakai `adalah_staf` / `staf_required` dari sini.
"""
from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

# Kalau ada peran staf baru (misalnya 'operator'), cukup tambahkan di sini.
STAF_ROLES = ('guru', 'kepsek', 'admin')


def adalah_staf(user):
    """True untuk guru/kepsek/admin (dan superuser). Anonim selalu False."""
    if not user.is_authenticated:
        return False
    return user.is_superuser or getattr(user, 'role', None) in STAF_ROLES


def staf_required(pesan='Hanya guru yang dapat melakukan ini.', ke='perpustakaan:daftar'):
    """Dekorator untuk view yang URL tujuan penolakannya tidak butuh argumen.

    Pasang SETELAH @login_required:

        @login_required
        @staf_required('Hanya guru yang dapat membuat album.')
        def buat_album(request): ...

    Untuk view yang harus kembali ke halaman dengan argumen (mis. detail_zona),
    pakai `adalah_staf(request.user)` langsung di dalam view.
    """
    def dekorator(view):
        @wraps(view)
        def pembungkus(request, *args, **kwargs):
            if not adalah_staf(request.user):
                messages.error(request, pesan)
                return redirect(ke)
            return view(request, *args, **kwargs)
        return pembungkus
    return dekorator