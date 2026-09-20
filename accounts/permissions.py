from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect

STAF = ('guru', 'kepsek', 'admin')


def hanya_staf(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        u = request.user
        if u.is_authenticated and (getattr(u, 'role', None) in STAF or u.is_superuser):
            return view(request, *args, **kwargs)
        messages.error(request, 'Anda tidak punya akses ke halaman ini.')
        role = getattr(u, 'role', None)
        if role == 'siswa':
            return redirect('accounts:dashboard_siswa')
        if role == 'orangtua':
            return redirect('accounts:dashboard_orangtua')
        return redirect('accounts:login')
    return wrapper
