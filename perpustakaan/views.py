from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import AlbumAudio, Audio


@login_required
def daftar_album(request):
    album_list = AlbumAudio.objects.all()
    return render(request, 'perpustakaan/daftar_album.html', {
        'album_list': album_list,
    })


@login_required
def buat_album(request):
    if request.user.role == 'siswa':
        messages.error(request, 'Hanya guru yang dapat membuat album.')
        return redirect('perpustakaan:daftar')
    if request.method == 'POST':
        AlbumAudio.objects.create(
            judul=request.POST.get('judul'),
            deskripsi=request.POST.get('deskripsi', ''),
            dibuat_oleh=request.user,
        )
        messages.success(request, 'Album berhasil dibuat.')
        return redirect('perpustakaan:daftar')
    return render(request, 'perpustakaan/buat_album.html')


@login_required
def detail_album(request, album_id):
    album = get_object_or_404(AlbumAudio, id=album_id)
    if request.method == 'POST' and not request.user.is_staff_role():
        urutan = album.audio_list.count()
        Audio.objects.create(
            album=album,
            judul=request.POST.get('judul'),
            file=request.FILES.get('file'),
            urutan=urutan,
            diunggah_oleh=request.user,
        )
        messages.success(request, 'Audio berhasil ditambahkan.')
        return redirect('perpustakaan:detail', album_id=album.id)
    return render(request, 'perpustakaan/detail_album.html', {
        'album': album,
    })


@login_required
def hapus_album(request, album_id):
    album = get_object_or_404(AlbumAudio, id=album_id)
    if not request.user.is_staff_role() and request.method == 'POST':
        album.delete()
        messages.success(request, 'Album berhasil dihapus.')
    return redirect('perpustakaan:daftar')


@login_required
def hapus_audio(request, audio_id):
    audio = get_object_or_404(Audio, id=audio_id)
    album_id = audio.album.id
    if not request.user.is_staff_role() and request.method == 'POST':
        audio.delete()
        messages.success(request, 'Audio berhasil dihapus.')
    return redirect('perpustakaan:detail', album_id=album_id)
