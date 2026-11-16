"""
Rapor Keseluruhan: satu halaman rapor yang merangkum SEMUA mata pelajaran seorang siswa.

Rapor semester 4 halaman: spiritual, nilai akhir + deskripsi tiap mapel, ekstrakurikuler, prestasi,
pertumbuhan, kehadiran, komentar guru, masukan orang tua. Hanya dibaca oleh guru, kepala sekolah, dan admin.

Hak akses mengikuti aturan multi-sekolah (accounts/tenancy.py):
  * kepala sekolah, admin, dan superuser melihat semua mapel siswa itu;
  * wali kelas dari kelas siswa melihat semua mapel siswa itu;
  * guru mapel biasa hanya melihat mapel miliknya (tertulis jelas di halaman).
Catatan wali kelas hanya bisa ditulis oleh wali kelas siswa itu, kepala sekolah, atau admin.
"""
from contextlib import nullcontext

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.models import Siswa
from accounts.tenancy import _norm_kelas, dalam_sekolah
from .models import AnggotaRuangKerja, CatatanWaliKelas, Kelas, NilaiRaporMapel, RaporSemester
from .rapor_semester import (LABEL, PREDIKAT, baca_periode, predikat, rentang_semester,
                             simpan_data_semester, tahun_ajaran_sekarang)
from .views import _bukan_staf


def _adalah_wali(user, siswa):
    """True bila `user` adalah wali kelas dari kelas tempat `siswa` berada."""
    if user.role != 'guru':
        return False
    kelas_siswa = _norm_kelas(siswa.kelas)
    if not kelas_siswa:
        return False
    for nama in Kelas.objects.filter(wali_kelas=user).values_list('nama', flat=True):
        if _norm_kelas(nama) == kelas_siswa:
            return True
    return False


def _punya_semua_mapel(user, siswa):
    return user.is_superuser or user.role in ('kepsek', 'admin') or _adalah_wali(user, siswa)


def _boleh_menulis_catatan(user, siswa):
    return user.is_superuser or user.role in ('kepsek', 'admin') or _adalah_wali(user, siswa)


def _lingkup(request, siswa):
    """Wali kelas harus melihat semua mapel siswanya, bukan hanya mapel yang ia ajar."""
    user = request.user
    if user.role == 'guru' and not user.is_superuser and user.sekolah_id and _adalah_wali(user, siswa):
        return dalam_sekolah(user.sekolah_id)   # tetap dibatasi sekolah, tanpa pembatasan peran guru
    return nullcontext()


def _nama_wali(siswa):
    for k in Kelas.objects.filter(wali_kelas__isnull=False).select_related('wali_kelas'):
        if _norm_kelas(k.nama) == _norm_kelas(siswa.kelas):
            return k.wali_kelas.get_full_name() or k.wali_kelas.username
    return ''


def _kehadiran(siswa, dari, sampai):
    from kelas.models import Absensi
    qs = Absensi.objects.filter(siswa=siswa, tanggal__gte=dari, tanggal__lte=sampai)
    hitung = {}
    for status in qs.values_list('status', flat=True):
        hitung[status] = hitung.get(status, 0) + 1
    return {'sakit': hitung.get('sakit', 0), 'izin': hitung.get('izin', 0), 'alpha': hitung.get('alpha', 0)}


def _baris_nilai(siswa, ta, sem):
    """Satu baris per mapel: nilai akhir, predikat, deskripsi (dari NilaiRaporMapel)."""
    anggota = (AnggotaRuangKerja.objects.filter(siswa=siswa)
               .select_related('ruang_kerja').order_by('ruang_kerja_id'))
    tersimpan = {n.ruang_kerja_id: n for n in NilaiRaporMapel.objects.filter(siswa=siswa, tahun_ajaran=ta, semester=sem)}
    baris = []
    for a in anggota:
        ruang = a.ruang_kerja
        n = tersimpan.get(ruang.id)
        bahasa = n.bahasa if n else 'en'
        baris.append({
            'ruang': ruang,
            'nama': (n.nama_tampil if n and n.nama_tampil else ruang.mapel),
            'nilai': n.nilai_akhir if n else None,
            'predikat': predikat(n.nilai_akhir, bahasa) if n else '',
            'deskripsi': n.deskripsi if n else '',
            'label': LABEL[bahasa],
            'terisi': bool(n and n.nilai_akhir is not None),
        })
    return baris


@login_required
def rapor_keseluruhan(request, siswa_id):
    if _bukan_staf(request.user):
        messages.error(request, 'Hanya guru yang dapat melihat rapor keseluruhan.')
        return redirect('ruang_kerja:daftar')
    siswa = get_object_or_404(Siswa, id=siswa_id)
    ta, sem = baca_periode(request.GET)
    dari, sampai = rentang_semester(ta, sem)

    with _lingkup(request, siswa):
        baris = _baris_nilai(siswa, ta, sem)
        hadir = _kehadiran(siswa, dari, sampai)

    data = RaporSemester.objects.filter(siswa=siswa, tahun_ajaran=ta, semester=sem).first()
    hari = {
        'sakit': data.sakit_hari if data and data.sakit_hari is not None else hadir['sakit'],
        'izin': data.izin_hari if data and data.izin_hari is not None else hadir['izin'],
        'alpha': data.alpha_hari if data and data.alpha_hari is not None else hadir['alpha'],
    }
    sekolah = getattr(request, 'sekolah', None) or siswa.sekolah
    boleh = _boleh_menulis_catatan(request.user, siswa)
    return render(request, 'ruang_kerja/rapor_keseluruhan.html', {
        'siswa': siswa, 'baris': baris, 'data': data, 'hari': hari,
        'ta': ta, 'sem': sem, 'sekolah': sekolah,
        'nama_wali': _nama_wali(siswa),
        'boleh_menulis': boleh,
        'semua_mapel': _punya_semua_mapel(request.user, siswa),
        'predikat_list': [n for _, n in PREDIKAT['en']],
        'jumlah_halaman': 4,
        'ta_list': [ta_default for ta_default in dict.fromkeys([ta, tahun_ajaran_sekarang()[0]])],
    })


@login_required
def simpan_rapor_semester(request, siswa_id):
    if _bukan_staf(request.user):
        messages.error(request, 'Hanya guru yang dapat mengisi rapor.')
        return redirect('ruang_kerja:daftar')
    siswa = get_object_or_404(Siswa, id=siswa_id)
    ta, sem = baca_periode(request.POST)
    if not _boleh_menulis_catatan(request.user, siswa):
        messages.error(request, 'Data semester hanya dapat diisi oleh wali kelas siswa ini, kepala sekolah, atau admin.')
    elif request.method == 'POST':
        simpan_data_semester(request, siswa, ta, sem)
        messages.success(request, 'Data rapor semester %s disimpan.' % siswa.nama)
    return redirect('%s?ta=%s&sem=%d' % (reverse('ruang_kerja:rapor_keseluruhan', args=[siswa.id]), ta, sem))


@login_required
def simpan_catatan_wali(request, siswa_id):
    if _bukan_staf(request.user):
        messages.error(request, 'Hanya guru yang dapat mengisi catatan wali kelas.')
        return redirect('ruang_kerja:daftar')
    siswa = get_object_or_404(Siswa, id=siswa_id)
    if not _boleh_menulis_catatan(request.user, siswa):
        messages.error(request, 'Catatan wali kelas hanya dapat diisi oleh wali kelas siswa ini, kepala sekolah, atau admin.')
        return redirect('ruang_kerja:rapor_keseluruhan', siswa_id=siswa.id)
    if request.method == 'POST':
        CatatanWaliKelas.objects.update_or_create(
            siswa=siswa,
            defaults={'catatan': request.POST.get('catatan', '').strip(), 'diperbarui_oleh': request.user},
        )
        messages.success(request, 'Catatan wali kelas %s disimpan.' % siswa.nama)
    return redirect('ruang_kerja:rapor_keseluruhan', siswa_id=siswa.id)


@login_required
def daftar_rapor(request):
    """Daftar siswa (per kelas, bisa dicari) untuk membuka Rapor Keseluruhan dari menu samping."""
    if _bukan_staf(request.user):
        messages.error(request, 'Hanya guru yang dapat melihat rapor keseluruhan.')
        return redirect('ruang_kerja:daftar')
    kelas_filter = request.GET.get('kelas', '').strip()
    cari = request.GET.get('q', '').strip()
    semua = Siswa.objects.filter(aktif=True)
    kelas_list = semua.values_list('kelas', flat=True).distinct().order_by('kelas')
    siswa = semua.order_by('kelas', 'nama')
    if kelas_filter:
        siswa = siswa.filter(kelas=kelas_filter)
    if cari:
        siswa = siswa.filter(nama__icontains=cari)
    return render(request, 'ruang_kerja/rapor_daftar.html', {
        'siswa': siswa, 'kelas_list': kelas_list, 'kelas_filter': kelas_filter, 'cari': cari,
    })
