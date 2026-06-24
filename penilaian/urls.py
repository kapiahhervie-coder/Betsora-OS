from django.urls import path
from . import views

app_name = 'penilaian'

urlpatterns = [
    path('', views.penilaian_home, name='home'),
    path('input/', views.input_nilai, name='input'),
    path('sesi/<int:sesi_id>/', views.detail_sesi, name='detail_sesi'),
]