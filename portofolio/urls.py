from django.urls import path
from . import views

app_name = 'portofolio'

urlpatterns = [
    path('', views.daftar_portofolio, name='daftar'),
    path('<int:siswa_id>/', views.detail_portofolio, name='detail'),
    path('karya/tambah/', views.tambah_karya, name='tambah_karya'),
    path('karya/<int:karya_id>/hapus/', views.hapus_karya, name='hapus_karya'),
]
