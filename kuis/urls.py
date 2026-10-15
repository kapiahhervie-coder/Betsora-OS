from django.urls import path

from . import views

app_name = "kuis"

urlpatterns = [
    path("", views.kuis_home, name="home"),
    path("api/daftar/", views.api_daftar, name="api_daftar"),
    path("api/simpan/", views.api_simpan, name="api_simpan"),
    path("api/<int:pk>/", views.api_detail, name="api_detail"),
    path("api/<int:pk>/hapus/", views.api_hapus, name="api_hapus"),
]