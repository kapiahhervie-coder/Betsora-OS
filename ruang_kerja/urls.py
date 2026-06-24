from django.urls import path
from . import views

app_name = 'ruang_kerja'

urlpatterns = [
    path('', views.daftar_ruang_kerja, name='daftar'),
    path('buat/', views.buat_ruang_kerja, name='buat'),
    path('<int:ruang_id>/', views.detail_ruang_kerja, name='detail'),
    path('<int:ruang_id>/materi/tambah/', views.tambah_materi, name='tambah_materi'),
    path('<int:ruang_id>/pengumuman/tambah/', views.tambah_pengumuman, name='tambah_pengumuman'),
    path('<int:ruang_id>/tugas/tambah/', views.tambah_tugas, name='tambah_tugas'),
    path('tugas/<int:tugas_id>/', views.detail_tugas, name='detail_tugas'),
    path('submisi/<int:submisi_id>/nilai/', views.nilai_submisi, name='nilai_submisi'),
    path('<int:ruang_id>/diskusi/', views.daftar_diskusi, name='daftar_diskusi'),
    path('diskusi/<int:diskusi_id>/', views.detail_diskusi, name='detail_diskusi'),
]