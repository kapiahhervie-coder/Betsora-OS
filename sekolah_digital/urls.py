from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static
from portofolio.views import berkas_langsung


urlpatterns = [
    path('admin/', admin.site.urls),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('', include('kelas.urls', namespace='kelas')),
    path('akun/', include('accounts.urls', namespace='accounts')),
    path('penilaian/', include('penilaian.urls', namespace='penilaian')),
    path('portofolio/', include('portofolio.urls', namespace='portofolio')),
    path('ruang-kerja/', include('ruang_kerja.urls', namespace='ruang_kerja')),
    path('pesan/', include('pesan.urls', namespace='pesan')),
    path('perpustakaan/', include('perpustakaan.urls', namespace='perpustakaan')),
    path('kreasi/', include('kreasi.urls', namespace='kreasi')),
    path("kuis/", include("kuis.urls")),
    path('misi/', include('misi.urls')),
    path(settings.MEDIA_URL.lstrip('/') + 'karya_siswa/<path:nama>', berkas_langsung, name='karya_media_langsung'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Produksi (DEBUG=False): static() di atas tidak aktif, jadi /media/ disajikan di sini dan wajib login.
# Rute berizin khusus (mis. /media/karya_siswa/) berada di atas dan tetap didahulukan.
if not settings.DEBUG:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', login_required(serve), {'document_root': settings.MEDIA_ROOT}),
    ]
