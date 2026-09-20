from django.urls import path

from . import views

app_name = 'kreasi'

urlpatterns = [
    path('media/<str:jenis>/<int:pk>/', views.media_privat, name='media'),
    path('karya/<int:submisi_id>/nilai/', views.nilai_karya, name='nilai_karya'),
    path('ruang/<int:ruang_id>/jenjang/', views.atur_jenjang, name='atur_jenjang'),
]
