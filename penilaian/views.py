from accounts.permissions import hanya_staf
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import Siswa
from .models import SesiPenilaian, Nilai


@login_required
@hanya_staf
def penilaian_home(request):
    from ruang_kerja.models import Materi, RuangKerja
    kelas_filter = request.GET.get('kelas', '')

    materi_qs = (Materi.objects
                 .filter(penilaian__isnull=False)
                 .select_related('ruang_kerja')
                 .distinct()
                 .order_by('-dibuat_pada'))
    kelas_list = RuangKerja.objects.values_list('kelas', flat=True).distinct().order_by('kelas')
    if kelas_filter:
        materi_qs = materi_qs.filter(ruang_kerja__kelas=kelas_filter)

    topik_list = []
    for materi in materi_qs:
        siswa_ids = materi.penilaian.values_list('siswa_id', flat=True).distinct()
        siswa_dinilai = Siswa.objects.filter(id__in=siswa_ids)
        mastery_list = []
        tuntas = 0
        for s in siswa_dinilai:
            m = materi.hitung_mastery(s)
            if m is not None:
                mastery_list.append(m)
                if materi.is_mastered(s):
                    tuntas += 1
        rata2 = round(sum(mastery_list) / len(mastery_list), 1) if mastery_list else None
        topik_list.append({
            'materi': materi,
            'ruang': materi.ruang_kerja,
            'jumlah_dinilai': siswa_dinilai.count(),
            'tuntas': tuntas,
            'rata2': rata2,
        })

    return render(request, 'penilaian/home.html', {
        'topik_list': topik_list,
        'kelas_list': kelas_list,
        'kelas_filter': kelas_filter,
    })


@login_required
@hanya_staf
def input_nilai(request):
    kelas_list = Siswa.objects.values_list('kelas', flat=True).distinct().order_by('kelas')
    if request.method == 'POST':
        sesi = SesiPenilaian.objects.create(
            mapel=request.POST.get('mapel'), jenis=request.POST.get('jenis'),
            topik=request.POST.get('topik'), kelas=request.POST.get('kelas'), guru=request.user
        )
        count = 0
        for siswa in Siswa.objects.filter(kelas=request.POST.get('kelas'), aktif=True):
            skor_str = request.POST.get(f'skor_{siswa.id}', '').strip()
            if skor_str:
                Nilai.objects.create(sesi=sesi, siswa=siswa, skor=float(skor_str))
                count += 1
        messages.success(request, f'Nilai berhasil disimpan untuk {count} siswa!')
        return redirect('penilaian:home')
    kelas_dipilih = request.GET.get('kelas', '')
    siswa_list = Siswa.objects.filter(kelas=kelas_dipilih, aktif=True) if kelas_dipilih else []
    return render(request, 'penilaian/input_nilai.html', {'kelas_list': kelas_list, 'kelas_dipilih': kelas_dipilih, 'siswa_list': siswa_list})


@login_required
@hanya_staf
def detail_sesi(request, sesi_id):
    sesi = get_object_or_404(SesiPenilaian, id=sesi_id)
    nilai_list = sesi.nilai_set.select_related('siswa').order_by('siswa__nama')
    return render(request, 'penilaian/detail_sesi.html', {'sesi': sesi, 'nilai_list': nilai_list})