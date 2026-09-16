from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import User
from .models import Percakapan, PesanPribadi


@login_required
def daftar_percakapan(request):
    user = request.user
    percakapan_list = Percakapan.objects.filter(peserta_1=user) | Percakapan.objects.filter(peserta_2=user)
    percakapan_list = list(percakapan_list.distinct().order_by('-diperbarui_pada'))
    for p in percakapan_list:
        p.lawan = p.lawan_bicara(user)
    return render(request, 'pesan/daftar.html', {
        'percakapan_list': percakapan_list,
    })


@login_required
def pilih_kontak(request):
    user = request.user
    if user.role == 'siswa':
        kontak_list = User.objects.filter(role='guru')
    else:
        kontak_list = User.objects.exclude(id=user.id)
    return render(request, 'pesan/pilih_kontak.html', {
        'kontak_list': kontak_list,
    })


@login_required
def buka_chat(request, user_id):
    lawan = get_object_or_404(User, id=user_id)
    user = request.user

    if user.role == 'siswa' and lawan.role != 'guru':
        messages.error(request, 'Siswa hanya dapat mengirim pesan ke guru.')
        return redirect('pesan:daftar')

    percakapan = Percakapan.get_or_create_antara(user, lawan)

    if request.method == 'POST':
        isi = request.POST.get('isi', '').strip()
        if isi:
            PesanPribadi.objects.create(percakapan=percakapan, pengirim=user, isi=isi)
            percakapan.save()
        return redirect('pesan:chat', user_id=lawan.id)

    pesan_list = percakapan.pesan.all()
    pesan_list.filter(sudah_dibaca=False).exclude(pengirim=user).update(sudah_dibaca=True)

    return render(request, 'pesan/chat.html', {
        'lawan': lawan,
        'percakapan': percakapan,
        'pesan_list': pesan_list,
    })
