from django.urls import path

from . import views

app_name = "misi"

urlpatterns = [
    path("", views.home, name="home"),
    path("papan/", views.papan, name="papan"),
    path("misi/<slug:slug>/", views.detail_misi, name="detail"),
    path("kerjakan/<int:pk>/", views.kerjakan, name="kerjakan"),
    path("kerjakan/<int:pk>/catatan/", views.tambah_catatan, name="tambah_catatan"),
    path("kerjakan/<int:pk>/refleksi/", views.kirim_refleksi, name="kirim_refleksi"),
    path("kerjakan/<int:pk>/konfirmasi/", views.konfirmasi, name="konfirmasi"),
    path("koleksi/", views.koleksi, name="koleksi"),
    path("koleksi/<int:siswa_id>/", views.koleksi_siswa, name="koleksi_siswa"),
    path("orangtua/", views.panel_orangtua, name="panel_orangtua"),
    path("guru/", views.panel_guru, name="panel_guru"),
    path("guru/tugaskan/", views.tugaskan, name="tugaskan"),
    path("foto/<int:pk>/", views.foto, name="foto"),
]
