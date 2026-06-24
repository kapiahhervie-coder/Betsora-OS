from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg, Sum
from accounts.models import Siswa
from .models import Absensi, Keaktifan
from penilaian.models import Nilai
import datetime


@login_required
def dashboard(request):
    hari_ini = datetime.date.today()
    total_siswa = Siswa.objects.filter(aktif=True).count()
    hadir_hari_ini = Absensi.objects.filter(tanggal=hari_ini, status='hadir').count()
    rata_nilai = Nilai.objects.aggregate(avg=Avg('skor'))['avg']
    kelas_list = Siswa.objects.values_list('kelas', flat=True).distinct().order_by('kelas')
    top_aktif = Keaktifan.objects.values('siswa__nama').annotate(total=Sum('poin')).order_by('-total')[:5]

    persen_hadir = round(hadir_hari_ini / total_siswa * 100) if total_siswa else 0

    perlu_perhatian = []
    for siswa in Siswa.objects.filter(aktif=True):
        total_hari = Absensi.objects.filter(siswa=siswa).count()
        hadir = Absensi.objects.filter(siswa=siswa, status='hadir').count()
        persen = round(hadir / total_hari * 100) if total_hari else 100
        avg = Nilai.objects.filter(siswa=siswa).aggregate(avg=Avg('skor'))['avg']
        alasan = []
        if total_hari > 0 and persen < 80:
            alasan.append(f'kehadiran {persen}%')
        if avg is not None and avg < 75:
            alasan.append(f'rata nilai {round(avg, 1)}')
        if alasan:
            perlu_perhatian.append({'siswa': siswa, 'alasan': ', '.join(alasan)})

    return render(request, 'kelas/dashboard.html', {
        'total_siswa': total_siswa,
        'hadir_hari_ini': hadir_hari_ini,
        'persen_hadir': persen_hadir,
        'rata_nilai': round(rata_nilai, 1) if rata_nilai else '—',
        'kelas_list': kelas_list,
        'top_aktif': top_aktif,
        'hari_ini': hari_ini,
        'perlu_perhatian': perlu_perhatian[:5],
        'jumlah_perlu_perhatian': len(perlu_perhatian),
    })


@login_required
def absensi(request):
    kelas = request.GET.get('kelas', '')
    tanggal_str = request.GET.get('tanggal', '')
    tanggal = datetime.date.fromisoformat(tanggal_str) if tanggal_str else datetime.date.today()
    siswa_list = Siswa.objects.filter(aktif=True, kelas=kelas) if kelas else Siswa.objects.filter(aktif=True)
    absensi_existing = {a.siswa_id: a.status for a in Absensi.objects.filter(tanggal=tanggal, siswa__in=siswa_list)}
    kelas_list = Siswa.objects.values_list('kelas', flat=True).distinct().order_by('kelas')
    if request.method == 'POST':
        for siswa in siswa_list:
            status = request.POST.get(f'status_{siswa.id}', 'alpha')
            Absensi.objects.update_or_create(siswa=siswa, tanggal=tanggal, defaults={'status': status, 'guru': request.user})
        messages.success(request, f'Absensi {tanggal} berhasil disimpan!')
        return redirect('kelas:absensi')
    return render(request, 'kelas/absensi.html', {
        'siswa_list': siswa_list, 'absensi_existing': absensi_existing,
        'kelas_list': kelas_list, 'kelas': kelas, 'tanggal': tanggal,
    })


@login_required
def keaktifan(request):
    kelas = request.GET.get('kelas', '')
    tanggal = datetime.date.today()
    siswa_list = Siswa.objects.filter(aktif=True, kelas=kelas) if kelas else Siswa.objects.filter(aktif=True)
    keaktifan_existing = {k.siswa_id: k.poin for k in Keaktifan.objects.filter(tanggal=tanggal, siswa__in=siswa_list)}
    kelas_list = Siswa.objects.values_list('kelas', flat=True).distinct().order_by('kelas')
    if request.method == 'POST':
        mapel = request.POST.get('mapel', '')
        for siswa in siswa_list:
            poin = int(request.POST.get(f'poin_{siswa.id}', 0) or 0)
            if poin > 0:
                Keaktifan.objects.update_or_create(siswa=siswa, tanggal=tanggal, defaults={'poin': poin, 'deskripsi': request.POST.get(f'desk_{siswa.id}', ''), 'guru': request.user, 'mapel': mapel})
        messages.success(request, 'Keaktifan berhasil disimpan!')
        return redirect('kelas:keaktifan')
    return render(request, 'kelas/keaktifan.html', {
        'siswa_list': siswa_list, 'keaktifan_existing': keaktifan_existing,
        'kelas_list': kelas_list, 'kelas': kelas, 'tanggal': tanggal,
    })