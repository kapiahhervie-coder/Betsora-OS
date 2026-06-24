from django.urls import path
from . import views

app_name = 'kelas'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('absensi/', views.absensi, name='absensi'),
    path('keaktifan/', views.keaktifan, name='keaktifan'),
]