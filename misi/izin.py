"""Aturan akses per peran (guru, kepsek, admin, siswa, orangtua) untuk app misi."""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from ruang_kerja.models import AnggotaRuangKerja

PERAN_STAF = ("guru", "kepsek", "admin")
PERAN_PENUH = ("kepsek", "admin")


def peran_wajib(*peran):
    """Wajib login dan memiliki salah satu peran; selain itu 403."""

    def dekorator(view):
        @wraps(view)
        @login_required
        def dibungkus(request, *args, **kwargs):
            if request.user.role not in peran:
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return dibungkus

    return dekorator


def siswa_dari_user(user):
    """Profil Siswa untuk akun ber-role siswa, atau None."""
    if user.role != "siswa":
        return None
    return getattr(user, "profil_siswa", None)


def anak_dari_user(user):
    """Siswa yang terhubung ke akun ber-role orangtua, atau None."""
    if user.role != "orangtua":
        return None
    return user.anak


def staf_boleh_kelola(user, siswa):
    """Kepsek/admin: semua siswa. Guru: siswa yang menjadi anggota ruang kerjanya."""
    if user.role in PERAN_PENUH:
        return True
    if user.role == "guru":
        return AnggotaRuangKerja.objects.filter(siswa=siswa, ruang_kerja__guru=user).exists()
    return False


def boleh_lihat(user, siswa):
    """Siapa yang boleh melihat catatan/foto seorang siswa."""
    if siswa_dari_user(user) == siswa or anak_dari_user(user) == siswa:
        return True
    return staf_boleh_kelola(user, siswa)


def boleh_konfirmasi(user, siswa):
    """Orang tua siswa tersebut, atau guru/kepsek/admin yang mengelolanya. Siswa tidak boleh."""
    if anak_dari_user(user) == siswa:
        return True
    return staf_boleh_kelola(user, siswa)
