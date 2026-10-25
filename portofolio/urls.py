from django.urls import path
from . import views

app_name = 'portofolio'

urlpatterns = [
    path('', views.daftar_portofolio, name='daftar'),
    path('<int:siswa_id>/', views.detail_portofolio, name='detail'),
    path('karya/tambah/', views.tambah_karya, name='tambah_karya'),
    path('karya/<int:karya_id>/hapus/', views.hapus_karya, name='hapus_karya'),
    path('karya/<int:karya_id>/unggulan/', views.unggulkan_karya, name='unggulkan_karya'),
    path('karya/<int:karya_id>/komentar/', views.tambah_komentar, name='tambah_komentar'),
    path('komentar/<int:komentar_id>/hapus/', views.hapus_komentar, name='hapus_komentar'),
    path('karya/<int:karya_id>/mapel/', views.atur_mapel, name='atur_mapel'),
    path('<int:siswa_id>/bio/', views.ubah_bio, name='ubah_bio'),
    path('<int:siswa_id>/sertifikat/', views.terbitkan_sertifikat, name='terbitkan_sertifikat'),
    path('sertifikat/<int:sertifikat_id>/', views.lihat_sertifikat, name='sertifikat'),
    path('sertifikat/<int:sertifikat_id>/hapus/', views.hapus_sertifikat, name='hapus_sertifikat'),
    path('karya/<int:karya_id>/berkas/', views.berkas_karya, name='berkas'),
]
