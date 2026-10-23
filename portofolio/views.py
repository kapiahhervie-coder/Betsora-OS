from accounts.permissions import hanya_staf
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Avg, Count, Q, Sum
from django.views.decorators.http import require_POST
from accounts.models import Siswa
from kelas.models import Absensi, Keaktifan
from penilaian.models import Nilai
from .models import KaryaSiswa
from .validasi import accept_html, cek_file_karya, UKURAN_MAKS_BYTE

# Perilaku lama dipertahankan: orang tua hanya melihat karya yang sudah "dibagikan".
# Ubah ke True jika orang tua boleh melihat juga karya privat anaknya.
ORANG_TUA_LIHAT_KARYA_PRIVAT = False

AKSES_PENUH = 'penuh'   # nilai, absensi, keaktifan, karya
AKSES_KARYA = 'karya'   # hanya karya yang dibagikan (siswa lain)


def get_siswa_obj(user):
    return getattr(user, 'profil_siswa', None)


def adalah_pemilik(user, siswa_id):
    siswa_obj = get_siswa_obj(user)
    return siswa_obj is not None and siswa_obj.id == siswa_id


def adalah_orang_tua_dari(user, siswa_id):
    return user.role == 'orangtua' and user.anak_id == siswa_id


def tingkat_akses(user, siswa):
    """Siapa boleh melihat apa di portofolio seorang siswa.

    - Staf (guru, kepsek, admin), siswa itu sendiri, dan orang tuanya: akses penuh.
    - Siswa lain: hanya karya yang dibagikan.
    - Orang tua anak lain, dan peran lain: ditolak.
    """
    if user.is_staff_role() or adalah_pemilik(user, siswa.id) or adalah_orang_tua_dari(user, siswa.id):
        return AKSES_PENUH
    if user.role == 'siswa':
        return AKSES_KARYA
    return None


def alihkan_ke_halaman_aman(user):
    """Halaman tujuan yang pasti boleh dibuka pengguna ini (daftar hanya untuk staf)."""
    if user.is_staff_role():
        return redirect('portofolio:daftar')
    siswa_obj = get_siswa_obj(user)
    if siswa_obj:
        return redirect('portofolio:detail', siswa_id=siswa_obj.id)
    return redirect('kelas:dashboard')


def ringkasan_per_siswa(siswa_list):
    """Kehadiran, rata-rata, poin, dan jumlah nilai untuk banyak siswa sekaligus.

    Tiga query tetap, berapa pun jumlah siswanya (sebelumnya lima query per siswa).
    """
    ids = [s.id for s in siswa_list]
    absensi = {
        r['siswa_id']: r
        for r in Absensi.objects.filter(siswa_id__in=ids).order_by().values('siswa_id')
        .annotate(total=Count('id'), hadir=Count('id', filter=Q(status='hadir')))
    }
    nilai = {
        r['siswa_id']: r
        for r in Nilai.objects.filter(siswa_id__in=ids).order_by().values('siswa_id')
        .annotate(avg=Avg('skor'), jumlah=Count('id'))
    }
    poin = {
        r['siswa_id']: r['t']
        for r in Keaktifan.objects.filter(siswa_id__in=ids).order_by().values('siswa_id').annotate(t=Sum('poin'))
    }
    data = []
    for siswa in siswa_list:
        a = absensi.get(siswa.id)
        n = nilai.get(siswa.id)
        total_hari = a['total'] if a else 0
        hadir = a['hadir'] if a else 0
        avg_nilai = n['avg'] if n else None
        data.append({
            'siswa': siswa,
            'kehadiran': round(hadir / total_hari * 100) if total_hari else 0,
            'avg_nilai': round(avg_nilai, 1) if avg_nilai else None,
            'total_poin': poin.get(siswa.id) or 0,
            'jumlah_nilai': n['jumlah'] if n else 0,
        })
    return data


@login_required
@hanya_staf
def daftar_portofolio(request):
    kelas_filter = request.GET.get('kelas', '')
    siswa_list = Siswa.objects.filter(aktif=True, kelas=kelas_filter) if kelas_filter else Siswa.objects.filter(aktif=True)
    kelas_list = Siswa.objects.values_list('kelas', flat=True).distinct().order_by('kelas')
    data = ringkasan_per_siswa(list(siswa_list))
    return render(request, 'portofolio/daftar.html', {'data': data, 'kelas_list': kelas_list, 'kelas_filter': kelas_filter})


@login_required
def detail_portofolio(request, siswa_id):
    siswa = get_object_or_404(Siswa, id=siswa_id)
    akses = tingkat_akses(request.user, siswa)
    if akses is None:
        raise PermissionDenied

    is_pemilik = adalah_pemilik(request.user, siswa.id)
    is_staff_role = request.user.is_staff_role()
    lihat_privat = is_pemilik or is_staff_role or (
        ORANG_TUA_LIHAT_KARYA_PRIVAT and adalah_orang_tua_dari(request.user, siswa.id)
    )
    if lihat_privat:
        karya_list = KaryaSiswa.objects.filter(siswa=siswa)
    else:
        karya_list = KaryaSiswa.objects.filter(siswa=siswa, dibagikan=True)

    context = {
        'siswa': siswa,
        'akses_penuh': akses == AKSES_PENUH,
        'karya_list': karya_list,
        'is_pemilik': is_pemilik,
        'bisa_hapus': is_pemilik or is_staff_role,
        'ukuran_maks_mb': UKURAN_MAKS_BYTE // (1024 * 1024),
        'file_accept': accept_html(),
    }

    if akses == AKSES_PENUH:
        absensi_list = Absensi.objects.filter(siswa=siswa).order_by('-tanggal')
        total_hari = absensi_list.count()
        hadir = absensi_list.filter(status='hadir').count()
        nilai_list = Nilai.objects.filter(siswa=siswa).select_related('sesi').order_by('-sesi__tanggal')
        avg_nilai = nilai_list.aggregate(avg=Avg('skor'))['avg']
        total_poin = Keaktifan.objects.filter(siswa=siswa).aggregate(t=Sum('poin'))['t'] or 0
        context.update({
            'kehadiran': round(hadir / total_hari * 100) if total_hari else 0,
            'avg_nilai': round(avg_nilai, 1) if avg_nilai else None,
            'nilai_list': nilai_list,
            'total_poin': total_poin,
            'absensi_list': absensi_list[:10],
            'formatif': nilai_list.filter(sesi__jenis='formatif'),
            'sumatif': nilai_list.filter(sesi__jenis='sumatif'),
        })

    return render(request, 'portofolio/detail.html', context)


def galat_unggahan(judul, video_url, file):
    """Pesan galat untuk unggahan karya, atau None jika semuanya sah."""
    maks_judul = KaryaSiswa._meta.get_field('judul').max_length
    maks_url = KaryaSiswa._meta.get_field('video_url').max_length
    if not judul or not (file or video_url):
        return 'Judul wajib diisi, dan minimal file atau link video harus dilampirkan.'
    if len(judul) > maks_judul:
        return f'Judul maksimal {maks_judul} karakter.'
    if file:
        galat = cek_file_karya(file)
        if galat:
            return galat
    if video_url:
        if len(video_url) > maks_url or not KaryaSiswa(video_url=video_url).get_video_embed():
            return 'Link video harus berupa link YouTube atau Google Drive yang valid.'
    return None


@login_required
def tambah_karya(request):
    siswa_obj = get_siswa_obj(request.user)
    if not siswa_obj:
        messages.error(request, 'Hanya siswa yang dapat mengunggah karya.')
        return alihkan_ke_halaman_aman(request.user)
    if request.method == 'POST':
        judul = request.POST.get('judul', '').strip()
        file = request.FILES.get('file')
        video_url = request.POST.get('video_url', '').strip()
        galat = galat_unggahan(judul, video_url, file)
        if galat:
            messages.error(request, galat)
        else:
            KaryaSiswa.objects.create(
                siswa=siswa_obj,
                judul=judul,
                deskripsi=request.POST.get('deskripsi', ''),
                file=file,
                video_url=video_url,
                dibagikan=request.POST.get('dibagikan') == 'on',
                refleksi=request.POST.get('refleksi', ''),
            )
            messages.success(request, 'Karya berhasil diunggah.')
    return redirect('portofolio:detail', siswa_id=siswa_obj.id)


@login_required
@require_POST
def hapus_karya(request, karya_id):
    karya = get_object_or_404(KaryaSiswa, id=karya_id)
    if adalah_pemilik(request.user, karya.siswa_id) or request.user.is_staff_role():
        siswa_id = karya.siswa_id
        karya.delete()
        messages.success(request, 'Karya berhasil dihapus.')
        return redirect('portofolio:detail', siswa_id=siswa_id)
    messages.error(request, 'Anda tidak memiliki akses untuk menghapus karya ini.')
    return alihkan_ke_halaman_aman(request.user)
