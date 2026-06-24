from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Sum
from accounts.models import Siswa
from kelas.models import Absensi, Keaktifan
from penilaian.models import Nilai


@login_required
def daftar_portofolio(request):
    kelas_filter = request.GET.get('kelas', '')
    siswa_list = Siswa.objects.filter(aktif=True, kelas=kelas_filter) if kelas_filter else Siswa.objects.filter(aktif=True)
    kelas_list = Siswa.objects.values_list('kelas', flat=True).distinct().order_by('kelas')
    data = []
    for siswa in siswa_list:
        total_hari = Absensi.objects.filter(siswa=siswa).count()
        hadir = Absensi.objects.filter(siswa=siswa, status='hadir').count()
        avg_nilai = Nilai.objects.filter(siswa=siswa).aggregate(avg=Avg('skor'))['avg']
        total_poin = Keaktifan.objects.filter(siswa=siswa).aggregate(t=Sum('poin'))['t'] or 0
        data.append({
            'siswa': siswa,
            'kehadiran': round(hadir / total_hari * 100) if total_hari else 0,
            'avg_nilai': round(avg_nilai, 1) if avg_nilai else None,
            'total_poin': total_poin,
            'jumlah_nilai': Nilai.objects.filter(siswa=siswa).count()
        })
    return render(request, 'portofolio/daftar.html', {'data': data, 'kelas_list': kelas_list, 'kelas_filter': kelas_filter})


@login_required
def detail_portofolio(request, siswa_id):
    siswa = get_object_or_404(Siswa, id=siswa_id)
    absensi_list = Absensi.objects.filter(siswa=siswa).order_by('-tanggal')
    total_hari = absensi_list.count()
    hadir = absensi_list.filter(status='hadir').count()
    nilai_list = Nilai.objects.filter(siswa=siswa).select_related('sesi').order_by('-sesi__tanggal')
    avg_nilai = nilai_list.aggregate(avg=Avg('skor'))['avg']
    total_poin = Keaktifan.objects.filter(siswa=siswa).aggregate(t=Sum('poin'))['t'] or 0
    return render(request, 'portofolio/detail.html', {
        'siswa': siswa, 'kehadiran': round(hadir / total_hari * 100) if total_hari else 0,
        'avg_nilai': round(avg_nilai, 1) if avg_nilai else None, 'nilai_list': nilai_list,
        'total_poin': total_poin, 'absensi_list': absensi_list[:10],
        'formatif': nilai_list.filter(sesi__jenis='formatif'), 'sumatif': nilai_list.filter(sesi__jenis='sumatif'),
    })