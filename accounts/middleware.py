import re

from django.shortcuts import redirect
from django.urls import reverse


class BatasiAksesOrangTuaMiddleware:
    """
    Akun dengan role 'orangtua' hanya boleh mengakses dashboard mereka sendiri,
    halaman logout/ganti password, dan halaman Misi Anak (app misi) yang memang
    untuk orang tua. Menggunakan request.path (bukan resolver_match, yang
    belum terisi pada tahap ini) untuk pencocokan URL.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def _portofolio_anak(path, user):
        """Portofolio, sertifikat, dan berkas karya anak sendiri. Izin rinci tetap dicek di view portofolio."""
        anak_id = getattr(user, 'anak_id', None)
        if anak_id is None:
            return False
        dasar = reverse('portofolio:daftar')  # '/portofolio/'
        if path == reverse('portofolio:detail', args=[anak_id]):
            return True
        return bool(
            re.fullmatch(re.escape(dasar) + r'sertifikat/\d+/', path)
            or re.fullmatch(re.escape(dasar) + r'karya/\d+/berkas/', path)
        )

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user and user.is_authenticated and getattr(user, 'role', None) == 'orangtua':
            misi = reverse('misi:home')  # '/misi/'
            allowed_paths = {
                reverse('accounts:dashboard_orangtua'),
                reverse('accounts:logout'),
                reverse('accounts:ganti_password'),
                misi,  # pintu masuk menu; langsung dialihkan ke panel orang tua
            }
            is_media_or_static = (
                request.path.startswith('/media/') or request.path.startswith('/static/')
                or request.path.startswith('/kreasi/media/')  # berkas privat; izin per-anak dicek di view
            )
            # Hanya empat bagian app misi yang dibuka untuk orang tua. Halaman guru
            # (/misi/guru/...), papan siswa (/misi/papan/...), dan lainnya tetap dialihkan.
            # Izin per-anak (hanya anaknya sendiri) tetap dicek di view misi.
            is_misi_orangtua = request.path.startswith((
                misi + 'orangtua/',   # panel Misi Anak
                misi + 'kerjakan/',   # melihat hasil kerja + konfirmasi
                misi + 'koleksi/',    # buku koleksi anak
                misi + 'foto/',       # foto catatan (izin per-anak dicek di view)
            ))
            is_portofolio_anak = request.method in ('GET', 'HEAD') and self._portofolio_anak(request.path, user)
            if (request.path not in allowed_paths and not is_media_or_static
                    and not is_misi_orangtua and not is_portofolio_anak):
                return redirect('accounts:dashboard_orangtua')
        return self.get_response(request)