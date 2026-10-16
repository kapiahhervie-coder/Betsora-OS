from django.urls import path
from . import views

app_name = 'perpustakaan'

urlpatterns = [
    path('sumber/<int:sumber_id>/baca/', views.baca_sumber, name='baca_sumber'),
    path('sumber/<int:sumber_id>/progres/', views.simpan_progres, name='simpan_progres'),
    path('sumber/<int:sumber_id>/glosarium/', views.glosarium_sumber, name='glosarium'),
    path('glosarium/<int:glos_id>/hapus/', views.hapus_glosarium, name='hapus_glosarium'),
    path('', views.daftar_album, name='daftar'),
    path('buat/', views.buat_album, name='buat'),
    path('album/<int:album_id>/', views.detail_album, name='detail'),
    path('album/<int:album_id>/hapus/', views.hapus_album, name='hapus_album'),
    path('audio/<int:audio_id>/hapus/', views.hapus_audio, name='hapus_audio'),
    path('peta/', views.peta_perpustakaan, name='peta'),
    path('zona/tambah/', views.tambah_zona, name='tambah_zona'),
    path('zona/<int:zona_id>/', views.detail_zona, name='detail_zona'),
    path('zona/<int:zona_id>/hapus/', views.hapus_zona, name='hapus_zona'),
    path('zona/<int:zona_id>/sumber/tambah/', views.tambah_sumber, name='tambah_sumber'),
    path('sumber/<int:sumber_id>/', views.detail_sumber, name='detail_sumber'),
    path('sumber/<int:sumber_id>/hapus/', views.hapus_sumber, name='hapus_sumber'),
    path('zona/<int:zona_id>/edit/', views.edit_zona, name='edit_zona'),
    path('sumber/<int:sumber_id>/edit/', views.edit_sumber, name='edit_sumber'),
    path('sumber/<int:sumber_id>/ekstrak-teks/', views.ekstrak_teks, name='ekstrak_teks'),
    path('sumber/<int:sumber_id>/ekstrak-halaman/', views.ekstrak_halaman, name='ekstrak_halaman'),
    path('sumber/<int:sumber_id>/selesai-baca/', views.catat_selesai_baca, name='catat_selesai_baca'),
    path('refleksi/<int:refleksi_id>/hapus/', views.hapus_refleksi, name='hapus_refleksi'),
    path('sumber/<int:sumber_id>/narasi/', views.kelola_narasi, name='kelola_narasi'),
    path('narasi/<int:halaman_id>/simpan/', views.simpan_narasi, name='simpan_narasi'),
    path('narasi/<int:halaman_id>/hapus/', views.hapus_narasi, name='hapus_narasi'),
    path('galeri-karya/', views.galeri_karya, name='galeri_karya'),
]
