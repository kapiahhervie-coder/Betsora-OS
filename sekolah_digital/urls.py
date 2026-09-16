from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

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
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
