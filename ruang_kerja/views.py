from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from accounts.models import Siswa
from .models import RuangKerja, Materi, Pengumuman, Tugas, SubmisiTugas


def get_kelas_siswa(user):
    if hasattr(user, 'profil_siswa'):
        return user.profil_siswa.kelas
    return None


@login_required
def daftar_ruang_kerja(request):
    if request.user.role == 'siswa':
        kelas = get_kelas_siswa(request.user)
        ruang_list = RuangKerja.objects.filter(kelas=kelas) if kelas else RuangKerja.objects.none()
    else:
        ruang_list = RuangKerja.objects.all()
    kelas_list = Siswa.objects.values_list('kelas', flat=True).distinct().order_by('kelas')
    return render(request, 'ruang_kerja/daftar.html', {'ruang_list': ruang_list, 'kelas_list': kelas_list})


@login_required
def buat_ruang_kerja(request):
    if request.user.role == 'siswa':
        messages.error(request, 'Hanya guru yang dapat membuat ruang kerja.')
        return redirect('ruang_kerja:daftar')
    kelas_list = Siswa.objects.values_list('kelas', flat=True).distinct().order_by('kelas')
    if request.method == 'POST':
        mapel = request.POST.get('mapel')
        kelas = request.POST.get('kelas')
        if RuangKerja.objects.filter(mapel=mapel, kelas=kelas).exists():
            messages.error(request, f'Ruang kerja {mapel} Kelas {kelas} sudah ada.')
        else:
            RuangKerja.objects.create(
                mapel=mapel, kelas=kelas,
                deskripsi=request.POST.get('deskripsi', ''),
                guru=request.user
            )
            messages.success(request, 'Ruang kerja berhasil dibuat.')
            return redirect('ruang_kerja:daftar')
    return render(request, 'ruang_kerja/buat.html', {'kelas_list': kelas_list})


@login_required
def detail_ruang_kerja(request, ruang_id):
    ruang = get_object_or_404(RuangKerja, id=ruang_id)
    if request.user.role == 'siswa':
        kelas = get_kelas_siswa(request.user)
        if kelas != ruang.kelas:
            messages.error(request, 'Anda tidak memiliki akses ke ruang kerja ini.')
            return redirect('ruang_kerja:daftar')

    siswa_obj = None
    tugas_sudah_submit = set()
    if request.user.role == 'siswa' and hasattr(request.user, 'profil_siswa'):
        siswa_obj = request.user.profil_siswa
        tugas_sudah_submit = set(
            SubmisiTugas.objects.filter(siswa=siswa_obj, tugas__ruang_kerja=ruang)
            .values_list('tugas_id', flat=True)
        )

    materi_list = ruang.materi.all()
    pengumuman_list = ruang.pengumuman.all()
    tugas_list = ruang.tugas.all()

    return render(request, 'ruang_kerja/detail.html', {
        'ruang': ruang,
        'materi_list': materi_list,
        'pengumuman_list': pengumuman_list,
        'tugas_list': tugas_list,
        'siswa_obj': siswa_obj,
        'tugas_sudah_submit': tugas_sudah_submit,
    })


@login_required
def tambah_materi(request, ruang_id):
    ruang = get_object_or_404(RuangKerja, id=ruang_id)
    if request.user.role == 'siswa':
        messages.error(request, 'Hanya guru yang dapat menambah materi.')
        return redirect('ruang_kerja:detail', ruang_id=ruang.id)
    if request.method == 'POST':
        Materi.objects.create(
            ruang_kerja=ruang,
            judul=request.POST.get('judul'),
            deskripsi=request.POST.get('deskripsi', ''),
            file=request.FILES.get('file'),
            diunggah_oleh=request.user,
        )
        messages.success(request, 'Materi berhasil diunggah.')
    return redirect('ruang_kerja:detail', ruang_id=ruang.id)


@login_required
def tambah_pengumuman(request, ruang_id):
    ruang = get_object_or_404(RuangKerja, id=ruang_id)
    if request.user.role == 'siswa':
        messages.error(request, 'Hanya guru yang dapat membuat pengumuman.')
        return redirect('ruang_kerja:detail', ruang_id=ruang.id)
    if request.method == 'POST':
        Pengumuman.objects.create(
            ruang_kerja=ruang,
            isi=request.POST.get('isi'),
            diposting_oleh=request.user
        )
        messages.success(request, 'Pengumuman berhasil diposting.')
    return redirect('ruang_kerja:detail', ruang_id=ruang.id)


@login_required
def tambah_tugas(request, ruang_id):
    ruang = get_object_or_404(RuangKerja, id=ruang_id)
    if request.user.role == 'siswa':
        messages.error(request, 'Hanya guru yang dapat membuat tugas.')
        return redirect('ruang_kerja:detail', ruang_id=ruang.id)
    if request.method == 'POST':
        Tugas.objects.create(
            ruang_kerja=ruang,
            judul=request.POST.get('judul'),
            instruksi=request.POST.get('instruksi'),
            nilai_maksimal=int(request.POST.get('nilai_maksimal', 100)),
            dibuat_oleh=request.user,
        )
        messages.success(request, 'Tugas berhasil dibuat.')
    return redirect('ruang_kerja:detail', ruang_id=ruang.id)


@login_required
def detail_tugas(request, tugas_id):
    tugas = get_object_or_404(Tugas, id=tugas_id)
    ruang = tugas.ruang_kerja

    if request.user.role == 'siswa':
        kelas = get_kelas_siswa(request.user)
        if kelas != ruang.kelas:
            messages.error(request, 'Anda tidak memiliki akses.')
            return redirect('ruang_kerja:daftar')
        siswa_obj = request.user.profil_siswa
        submisi = tugas.get_submisi(siswa_obj)
        if request.method == 'POST' and not submisi:
            SubmisiTugas.objects.create(
                tugas=tugas,
                siswa=siswa_obj,
                teks_jawaban=request.POST.get('teks_jawaban', ''),
                file_jawaban=request.FILES.get('file_jawaban'),
            )
            messages.success(request, 'Tugas berhasil dikumpulkan!')
            return redirect('ruang_kerja:detail_tugas', tugas_id=tugas.id)
        return render(request, 'ruang_kerja/detail_tugas_siswa.html', {
            'tugas': tugas, 'ruang': ruang, 'submisi': submisi,
        })

    # Guru — lihat semua submisi
    submisi_list = tugas.submisi.select_related('siswa').all()
    return render(request, 'ruang_kerja/detail_tugas_guru.html', {
        'tugas': tugas, 'ruang': ruang, 'submisi_list': submisi_list,
    })


@login_required
def nilai_submisi(request, submisi_id):
    submisi = get_object_or_404(SubmisiTugas, id=submisi_id)
    if request.user.role == 'siswa':
        messages.error(request, 'Hanya guru yang dapat memberi nilai.')
        return redirect('ruang_kerja:daftar')
    if request.method == 'POST':
        submisi.nilai = request.POST.get('nilai')
        submisi.feedback = request.POST.get('feedback', '')
        submisi.dinilai_pada = timezone.now()
        submisi.save()
        messages.success(request, f'Nilai untuk {submisi.siswa.nama} berhasil disimpan.')
    return redirect('ruang_kerja:detail_tugas', tugas_id=submisi.tugas.id)

@login_required
def daftar_diskusi(request, ruang_id):
    from .models import Diskusi
    ruang = get_object_or_404(RuangKerja, id=ruang_id)
    if request.user.role == 'siswa':
        kelas = get_kelas_siswa(request.user)
        if kelas != ruang.kelas:
            messages.error(request, 'Anda tidak memiliki akses.')
            return redirect('ruang_kerja:daftar')
    diskusi_list = ruang.diskusi.all()
    if request.method == 'POST':
        from .models import Diskusi
        Diskusi.objects.create(
            ruang_kerja=ruang,
            judul=request.POST.get('judul'),
            isi=request.POST.get('isi'),
            diposting_oleh=request.user,
        )
        messages.success(request, 'Diskusi berhasil dibuat.')
        return redirect('ruang_kerja:daftar_diskusi', ruang_id=ruang.id)
    return render(request, 'ruang_kerja/diskusi.html', {'ruang': ruang, 'diskusi_list': diskusi_list})


@login_required
def detail_diskusi(request, diskusi_id):
    from .models import Diskusi, KomentarDiskusi
    diskusi = get_object_or_404(Diskusi, id=diskusi_id)
    ruang = diskusi.ruang_kerja
    if request.user.role == 'siswa':
        kelas = get_kelas_siswa(request.user)
        if kelas != ruang.kelas:
            messages.error(request, 'Anda tidak memiliki akses.')
            return redirect('ruang_kerja:daftar')
    komentar_list = diskusi.komentar.all()
    if request.method == 'POST' and not diskusi.ditutup:
        KomentarDiskusi.objects.create(
            diskusi=diskusi,
            isi=request.POST.get('isi'),
            diposting_oleh=request.user,
        )
        return redirect('ruang_kerja:detail_diskusi', diskusi_id=diskusi.id)
    return render(request, 'ruang_kerja/detail_diskusi.html', {
        'diskusi': diskusi, 'ruang': ruang, 'komentar_list': komentar_list,
    })