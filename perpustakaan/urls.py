from django.urls import path
from . import views

app_name = 'perpustakaan'

urlpatterns = [
    path('', views.daftar_album, name='daftar'),
    path('buat/', views.buat_album, name='buat'),
    path('album/<int:album_id>/', views.detail_album, name='detail'),
    path('album/<int:album_id>/hapus/', views.hapus_album, name='hapus_album'),
    path('audio/<int:audio_id>/hapus/', views.hapus_audio, name='hapus_audio'),
]
