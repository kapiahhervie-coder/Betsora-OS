from django.urls import path
from . import views

app_name = 'portofolio'

urlpatterns = [
    path('', views.daftar_portofolio, name='daftar'),
    path('<int:siswa_id>/', views.detail_portofolio, name='detail'),
]