from django.urls import path
from . import views

app_name = "kuis"

urlpatterns = [
    path("", views.kuis_home, name="home"),
]
