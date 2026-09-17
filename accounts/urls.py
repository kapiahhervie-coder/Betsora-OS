from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('siswa/', views.daftar_siswa, name='daftar_siswa'),
    path('siswa/tambah/', views.tambah_siswa, name='tambah_siswa'),
    path('siswa/<int:siswa_id>/buat-akun/', views.buat_akun_siswa, name='buat_akun_siswa'),
    path('siswa/<int:siswa_id>/buat-akun-orangtua/', views.buat_akun_orangtua, name='buat_akun_orangtua'),
    path('dashboard-siswa/', views.dashboard_siswa, name='dashboard_siswa'),
    path('dashboard-orangtua/', views.dashboard_orangtua, name='dashboard_orangtua'),
]
