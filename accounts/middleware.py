from django.shortcuts import redirect
from django.urls import reverse


class BatasiAksesOrangTuaMiddleware:
    """
    Akun dengan role 'orangtua' hanya boleh mengakses dashboard mereka sendiri
    dan halaman logout. Menggunakan request.path (bukan resolver_match, yang
    belum terisi pada tahap ini) untuk pencocokan URL.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user and user.is_authenticated and getattr(user, 'role', None) == 'orangtua':
            allowed_paths = {
                reverse('accounts:dashboard_orangtua'),
                reverse('accounts:logout'),
                reverse('accounts:ganti_password'),
            }
            is_media_or_static = (
                request.path.startswith('/media/') or request.path.startswith('/static/')
                or request.path.startswith('/kreasi/media/')  # berkas privat; izin per-anak dicek di view
            )
            if request.path not in allowed_paths and not is_media_or_static:
                return redirect('accounts:dashboard_orangtua')
        return self.get_response(request)
