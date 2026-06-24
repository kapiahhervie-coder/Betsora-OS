from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('kelas.urls', namespace='kelas')),
    path('akun/', include('accounts.urls', namespace='accounts')),
    path('penilaian/', include('penilaian.urls', namespace='penilaian')),
    path('portofolio/', include('portofolio.urls', namespace='portofolio')),
    path('ruang-kerja/', include('ruang_kerja.urls', namespace='ruang_kerja')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)