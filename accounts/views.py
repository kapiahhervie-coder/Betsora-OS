from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.crypto import get_random_string
from .models import Siswa, User


def login_view(request):
    if request.user.is_authenticated:
        if request.user.role == 'siswa':
            return redirect('accounts:dashboard_siswa')
        elif request.user.role == 'orangtua':
            return redirect('accounts:dashboard_orangtua')
        return redirect('kelas:dashboard')
    if request.method == 'POST':
        user = authenticate(request, username=request.POST.get('username'), password=request.POST.get('password'))
        if user:
            login(request, user)
            if user.role == 'siswa':
                return redirect('accounts:dashboard_siswa')
            elif user.role == 'orangtua':
                return redirect('accounts:dashboard_orangtua')
            return redirect('kelas:dashboard')
        messages.error(request, 'Username atau password salah.')
    return render(request, 'accounts/login.html')


def logout_view(request):
    logout(request)
    return redirect('accounts:login')


@login_required
def daftar_siswa(request):
    if request.user.role in ('siswa', 'orangtua'):
        messages.error(request, 'Anda tidak punya akses ke halaman ini.')
        return redirect('kelas:dashboard')
    kelas_filter = request.GET.get('kelas', '')
    siswa = Siswa.objects.filter(aktif=True)
    if kelas_filter:
        siswa = siswa.filter(kelas=kelas_filter)
    kelas_list = Siswa.objects.values_list('kelas', flat=True).distinct().order_by('kelas')
    return render(request, 'accounts/daftar_siswa.html', {'siswa': siswa, 'kelas_list': kelas_list, 'kelas_filter': kelas_filter})


@login_required
def tambah_siswa(request):
    if request.user.role in ('siswa', 'orangtua'):
        messages.error(request, 'Anda tidak punya akses ke halaman ini.')
        return redirect('kelas:dashboard')
    if request.method == 'POST':
        Siswa.objects.create(
            nama=request.POST['nama'], nis=request.POST['nis'], kelas=request.POST['kelas'],
            no_ortu=request.POST.get('no_ortu', ''), alamat=request.POST.get('alamat', '')
        )
        messages.success(request, 'Siswa berhasil ditambahkan.')
        return redirect('accounts:daftar_siswa')
    return render(request, 'accounts/tambah_siswa.html')


@login_required
def buat_akun_siswa(request, siswa_id):
    if request.user.role in ('siswa', 'orangtua'):
        messages.error(request, 'Anda tidak punya akses ke halaman ini.')
        return redirect('kelas:dashboard')
    siswa = get_object_or_404(Siswa, id=siswa_id)
    if siswa.user:
        messages.error(request, f'{siswa.nama} sudah punya akun login.')
        return redirect('accounts:daftar_siswa')

    username = siswa.nis
    password = get_random_string(8, allowed_chars='abcdefghjkmnpqrstuvwxyz23456789')

    user = User.objects.create_user(username=username, password=password, role='siswa', first_name=siswa.nama)
    siswa.user = user
    siswa.save()

    messages.success(request, f'Akun untuk {siswa.nama} dibuat. Username: {username} - Password: {password} (catat sekarang, password tidak akan ditampilkan lagi)')
    return redirect('accounts:daftar_siswa')


@login_required
def dashboard_siswa(request):
    if not hasattr(request.user, 'profil_siswa'):
        messages.error(request, 'Akun ini tidak terhubung ke data siswa manapun.')
        return redirect('accounts:logout')
    siswa = request.user.profil_siswa
    from perpustakaan.models import LencanaDiperoleh, ProgresBaca
    from ruang_kerja.models import Tugas

    ruang_ids = siswa.ruang_kerja_diikuti.values_list('ruang_kerja_id', flat=True)
    tugas_menunggu = [
        t for t in Tugas.objects.filter(ruang_kerja_id__in=ruang_ids).select_related('ruang_kerja')
        if not t.sudah_submit(siswa)
    ]
    lencana_list = LencanaDiperoleh.objects.filter(siswa=siswa).select_related('lencana', 'sumber')
    return render(request, 'accounts/dashboard_siswa.html', {'siswa': siswa, 'lencana_list': lencana_list,
        'progres_list': ProgresBaca.objects.filter(siswa=siswa).select_related('sumber')[:8],
        'tugas_menunggu': tugas_menunggu})

@login_required
def buat_akun_orangtua(request, siswa_id):
    if request.user.role in ('siswa', 'orangtua'):
        messages.error(request, 'Anda tidak punya akses ke halaman ini.')
        return redirect('kelas:dashboard')
    siswa = get_object_or_404(Siswa, id=siswa_id)
    if User.objects.filter(anak=siswa, role='orangtua').exists():
        messages.error(request, f'{siswa.nama} sudah punya akun orang tua yang terhubung.')
        return redirect('accounts:daftar_siswa')

    username = f'ortu{siswa.nis}'
    password = get_random_string(8, allowed_chars='abcdefghjkmnpqrstuvwxyz23456789')

    User.objects.create_user(username=username, password=password, role='orangtua', anak=siswa, first_name=f'Orang Tua {siswa.nama}')

    messages.success(request, f'Akun orang tua untuk {siswa.nama} dibuat. Username: {username} - Password: {password} (catat sekarang, password tidak akan ditampilkan lagi)')
    return redirect('accounts:daftar_siswa')


@login_required
def dashboard_orangtua(request):
    if request.user.role != 'orangtua' or not request.user.anak:
        messages.error(request, 'Akun ini tidak terhubung ke data siswa manapun.')
        return redirect('accounts:logout')

    from django.db.models import Avg, Sum
    from kelas.models import Absensi, Keaktifan
    from penilaian.models import Nilai

    siswa = request.user.anak
    absensi_list = Absensi.objects.filter(siswa=siswa).order_by('-tanggal')
    total_hari = absensi_list.count()
    hadir = absensi_list.filter(status='hadir').count()
    avg_nilai = Nilai.objects.filter(siswa=siswa).aggregate(avg=Avg('skor'))['avg']
    total_poin = Keaktifan.objects.filter(siswa=siswa).aggregate(t=Sum('poin'))['t'] or 0

    from perpustakaan.models import LencanaDiperoleh, ProgresBaca
    lencana_list = LencanaDiperoleh.objects.filter(siswa=siswa).select_related('lencana', 'sumber')

    return render(request, 'accounts/dashboard_orangtua.html', {
        'siswa': siswa,
        'kehadiran': round(hadir / total_hari * 100) if total_hari else 0,
        'avg_nilai': round(avg_nilai, 1) if avg_nilai else None,
        'total_poin': total_poin,
        'absensi_list': absensi_list[:10],
        'lencana_list': lencana_list,
        'progres_list': ProgresBaca.objects.filter(siswa=siswa).select_related('sumber')[:8],
    })


def _redirect_ke_dashboard(user):
    """Sama seperti logika di login_view: arahkan sesuai role."""
    if user.role == 'siswa':
        return redirect('accounts:dashboard_siswa')
    elif user.role == 'orangtua':
        return redirect('accounts:dashboard_orangtua')
    return redirect('kelas:dashboard')


@login_required
def ganti_password(request):
    """
    Ganti password untuk akun yang sedang login (siapa pun: siswa, orang tua, guru, dst).
    Memakai update_session_auth_hash supaya sesi TIDAK terputus setelah password diganti --
    tanpa itu, Django akan memaksa logout begitu password berubah.
    """
    if request.method == 'POST':
        password_lama = request.POST.get('password_lama', '')
        password_baru = request.POST.get('password_baru', '')
        konfirmasi = request.POST.get('konfirmasi_password', '')

        if not request.user.check_password(password_lama):
            messages.error(request, 'Password lama tidak sesuai.')
        elif not password_baru or password_baru != konfirmasi:
            messages.error(request, 'Konfirmasi password baru tidak cocok.')
        else:
            try:
                validate_password(password_baru, user=request.user)
            except ValidationError as e:
                for pesan in e.messages:
                    messages.error(request, pesan)
            else:
                request.user.set_password(password_baru)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, 'Password berhasil diganti.')
                return _redirect_ke_dashboard(request.user)

    return render(request, 'accounts/ganti_password.html')
