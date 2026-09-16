from django.urls import path
from . import views

app_name = 'pesan'

urlpatterns = [
    path('', views.daftar_percakapan, name='daftar'),
    path('kontak/', views.pilih_kontak, name='pilih_kontak'),
    path('chat/<int:user_id>/', views.buka_chat, name='chat'),
]
