from accounts.permissions import hanya_staf
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import datetime
import mimetypes
import os

from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.db import transaction
from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone
from django.views.decorators.http import require_POST, require_safe
from accounts.models import Siswa
from kelas.models import Absensi, Keaktifan
from penilaian.models import Nilai
from . import jenjang
from .lencana_simpan import gabung_lencana
from .misi_ringkas import ringkasan_misi
from .models import KaryaSiswa, KomentarKarya, ProfilSiswa, Sertifikat
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
        # Siswa lain hanya boleh membuka portofolio yang punya karya dibagikan; jika tidak ada, ditolak.
        if KaryaSiswa.objects.filter(siswa=siswa, dibagikan=True).exists():
            return AKSES_KARYA
        return None
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


def pilih_tema(request, siswa):
    """Tema mengikuti jenjang siswa. Staf boleh melihat pratinjau lewat ?tema=sd|smp|sma."""
    asli = jenjang.jenjang_dari_kelas(siswa.kelas)
    pilihan = request.GET.get('tema', '')
    if request.user.is_staff_role() and pilihan in jenjang.JENJANG:
        return pilihan, asli
    return asli, asli


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
        karya_qs = KaryaSiswa.objects.filter(siswa=siswa).order_by('-unggulan', '-diunggah_pada')
    else:
        karya_qs = KaryaSiswa.objects.filter(siswa=siswa, dibagikan=True).order_by('-unggulan', '-diunggah_pada')
    karya_list = list(karya_qs)
    # Komentar guru hanya dibaca pemilik, orang tuanya, dan staf: sama dengan akses penuh.
    if akses == AKSES_PENUH and karya_list:
        per_karya = {}
        for k in KomentarKarya.objects.filter(karya__in=karya_list).select_related('penulis'):
            per_karya.setdefault(k.karya_id, []).append(k)
        for karya in karya_list:
            karya.komentar_list = per_karya.get(karya.id, [])

    # Tag dikumpulkan dari karya yang boleh dilihat pengguna ini saja, supaya karya privat tidak bocor lewat tag.
    daftar_mapel_karya = sorted({k.mapel for k in karya_list if k.mapel}, key=str.lower)
    mapel_dipilih = request.GET.get('mapel', '')
    karya_tampil = [k for k in karya_list if k.mapel == mapel_dipilih] if mapel_dipilih else karya_list

    tema, tema_asli = pilih_tema(request, siswa)
    context = {
        'siswa': siswa,
        'akses_penuh': akses == AKSES_PENUH,
        'karya_list': karya_tampil,
        'daftar_mapel_karya': daftar_mapel_karya,
        'mapel_dipilih': mapel_dipilih,
        'jumlah_karya': len(karya_list),
        'is_pemilik': is_pemilik,
        'bisa_hapus': is_pemilik or is_staff_role,
        'bisa_komentar': is_staff_role,
        'ukuran_maks_mb': UKURAN_MAKS_BYTE // (1024 * 1024),
        'file_accept': accept_html(),
        'tema': tema,
        'tema_asli': tema_asli,
        'bisa_pratinjau': is_staff_role,
        'target_poin': jenjang.TARGET_POIN,
        'daftar_tema': [('sd', 'SD'), ('smp', 'SMP'), ('sma', 'SMA')],
    }

    if akses == AKSES_PENUH:
        absensi_list = Absensi.objects.filter(siswa=siswa).order_by('-tanggal')
        per_status = {r['status']: r['n'] for r in absensi_list.order_by().values('status').annotate(n=Count('id'))}
        total_hari = sum(per_status.values())
        hadir = per_status.get('hadir', 0)
        nilai_list = list(Nilai.objects.filter(siswa=siswa).select_related('sesi').order_by('-sesi__tanggal'))
        avg_nilai = round(sum(float(n.skor) for n in nilai_list) / len(nilai_list), 1) if nilai_list else None
        total_poin = Keaktifan.objects.filter(siswa=siswa).aggregate(t=Sum('poin'))['t'] or 0
        kehadiran = round(hadir / total_hari * 100) if total_hari else 0
        misi = ringkasan_misi(siswa)
        lencana = jenjang.hitung_lencana(
            kehadiran, total_hari, avg_nilai, total_poin,
            len(karya_list), any(k.refleksi.strip() for k in karya_list),
            misi['total_selesai'] if misi else None,
        )
        lencana = gabung_lencana(siswa, lencana)
        profil = ProfilSiswa.objects.filter(siswa=siswa).first()
        context.update({
            'kehadiran': kehadiran,
            'avg_nilai': avg_nilai if avg_nilai else None,
            'nilai_list': nilai_list,
            'nilai_per_mapel': jenjang.ringkas_nilai(nilai_list),
            'tren_nilai': jenjang.tren_nilai(nilai_list),
            'total_poin': total_poin,
            'persen_poin': jenjang.persen_poin(total_poin),
            'absensi_list': absensi_list[:10],
            'per_status': per_status,
            'status_bars': [
                {'kode': k, 'nama': nama, 'n': per_status.get(k, 0),
                 'lebar': int(per_status.get(k, 0) * 100 // total_hari) if total_hari else 0}
                for k, nama in Absensi.STATUS
            ],
            'total_hari': total_hari,
            'keaktifan_list': Keaktifan.objects.filter(siswa=siswa).order_by('-tanggal', '-id')[:8],
            'misi': misi,
            'bio': profil.bio if profil else '',
            'bisa_ubah_bio': is_pemilik or is_staff_role,
            'maks_bio': MAKS_BIO,
            'sertifikat_list': list(Sertifikat.objects.filter(siswa=siswa)),
            'bisa_terbitkan': is_staff_role,
            'hari_ini': timezone.localdate().isoformat(),
            'saran_mapel': sorted({n.sesi.mapel for n in nilai_list} | set(daftar_mapel_karya), key=str.lower),
            'lencana': lencana,
            'jumlah_lencana': sum(1 for l in lencana if l['diraih']),
        })

    return render(request, f'portofolio/detail_{tema}.html', context)


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
        mapel = ' '.join(request.POST.get('mapel', '').split())
        galat = galat_unggahan(judul, video_url, file)
        if galat:
            messages.error(request, galat)
        elif len(mapel) > MAKS_MAPEL:
            messages.error(request, f'Tag mata pelajaran maksimal {MAKS_MAPEL} karakter.')
        else:
            KaryaSiswa.objects.create(
                siswa=siswa_obj,
                judul=judul,
                deskripsi=request.POST.get('deskripsi', ''),
                file=file,
                video_url=video_url,
                dibagikan=request.POST.get('dibagikan') == 'on',
                refleksi=request.POST.get('refleksi', ''),
                mapel=mapel,
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


MAKS_JUDUL_SERTIFIKAT = Sertifikat._meta.get_field('judul').max_length
MAKS_KET_SERTIFIKAT = Sertifikat._meta.get_field('keterangan').max_length
MAKS_MAPEL = KaryaSiswa._meta.get_field('mapel').max_length
MAKS_BIO = ProfilSiswa._meta.get_field('bio').max_length
MAKS_KOMENTAR = KomentarKarya._meta.get_field('teks').max_length
MAKS_UNGGULAN = 3


@login_required
@require_POST
def unggulkan_karya(request, karya_id):
    """Pasang atau lepas tanda 'unggulan' (pemilik atau staf). Maksimal MAKS_UNGGULAN per siswa."""
    karya = get_object_or_404(KaryaSiswa, id=karya_id)
    if not (adalah_pemilik(request.user, karya.siswa_id) or request.user.is_staff_role()):
        messages.error(request, 'Anda tidak memiliki akses untuk mengatur karya ini.')
        return alihkan_ke_halaman_aman(request.user)
    if karya.unggulan:
        karya.unggulan = False
        karya.save(update_fields=['unggulan'])
        messages.success(request, 'Karya dilepas dari unggulan.')
    elif KaryaSiswa.objects.filter(siswa_id=karya.siswa_id, unggulan=True).count() >= MAKS_UNGGULAN:
        messages.error(request, f'Karya unggulan maksimal {MAKS_UNGGULAN}. Lepas salah satu dulu.')
    else:
        karya.unggulan = True
        karya.save(update_fields=['unggulan'])
        messages.success(request, 'Karya dijadikan unggulan.')
    return redirect('portofolio:detail', siswa_id=karya.siswa_id)


@login_required
@require_POST
def tambah_komentar(request, karya_id):
    """Hanya staf yang boleh menulis komentar pada karya."""
    if not request.user.is_staff_role():
        raise PermissionDenied
    karya = get_object_or_404(KaryaSiswa, id=karya_id)
    teks = ' '.join(request.POST.get('teks', '').split())
    if not teks:
        messages.error(request, 'Komentar tidak boleh kosong.')
    elif len(teks) > MAKS_KOMENTAR:
        messages.error(request, f'Komentar maksimal {MAKS_KOMENTAR} karakter.')
    else:
        KomentarKarya.objects.create(karya=karya, penulis=request.user, teks=teks)
        messages.success(request, 'Komentar terkirim.')
    return redirect('portofolio:detail', siswa_id=karya.siswa_id)


@login_required
@require_POST
def hapus_komentar(request, komentar_id):
    if not request.user.is_staff_role():
        raise PermissionDenied
    komentar = get_object_or_404(KomentarKarya.objects.select_related('karya'), id=komentar_id)
    siswa_id = komentar.karya.siswa_id
    komentar.delete()
    messages.success(request, 'Komentar dihapus.')
    return redirect('portofolio:detail', siswa_id=siswa_id)


@login_required
@require_POST
def atur_mapel(request, karya_id):
    """Pasang, ganti, atau kosongkan tag mata pelajaran sebuah karya (pemilik atau staf)."""
    karya = get_object_or_404(KaryaSiswa, id=karya_id)
    if not (adalah_pemilik(request.user, karya.siswa_id) or request.user.is_staff_role()):
        raise PermissionDenied
    mapel = ' '.join(request.POST.get('mapel', '').split())
    if len(mapel) > MAKS_MAPEL:
        messages.error(request, f'Tag mata pelajaran maksimal {MAKS_MAPEL} karakter.')
    else:
        karya.mapel = mapel
        karya.save(update_fields=['mapel'])
        messages.success(request, 'Tag diperbarui.')
    return redirect('portofolio:detail', siswa_id=karya.siswa_id)


@login_required
@require_POST
def ubah_bio(request, siswa_id):
    """Bio singkat. Pemilik atau staf. Mengirim bio kosong menghapus bio."""
    siswa = get_object_or_404(Siswa, id=siswa_id)
    if not (adalah_pemilik(request.user, siswa.id) or request.user.is_staff_role()):
        raise PermissionDenied
    bio = ' '.join(request.POST.get('bio', '').split())
    if len(bio) > MAKS_BIO:
        messages.error(request, f'Bio maksimal {MAKS_BIO} karakter.')
    elif not bio:
        ProfilSiswa.objects.filter(siswa=siswa).delete()
        messages.success(request, 'Bio dihapus.')
    else:
        ProfilSiswa.objects.update_or_create(siswa=siswa, defaults={'bio': bio})
        messages.success(request, 'Bio disimpan.')
    return redirect('portofolio:detail', siswa_id=siswa.id)


@login_required
@require_POST
def terbitkan_sertifikat(request, siswa_id):
    """Hanya staf yang menerbitkan sertifikat. Nomor dibuat otomatis dan unik."""
    if not request.user.is_staff_role():
        raise PermissionDenied
    siswa = get_object_or_404(Siswa, id=siswa_id)
    judul = ' '.join(request.POST.get('judul', '').split())
    keterangan = ' '.join(request.POST.get('keterangan', '').split())
    teks_tanggal = request.POST.get('tanggal', '').strip()
    hari_ini = timezone.localdate()
    try:
        tanggal = datetime.date.fromisoformat(teks_tanggal) if teks_tanggal else hari_ini
    except ValueError:
        tanggal = None
    if not judul:
        messages.error(request, 'Judul sertifikat wajib diisi.')
    elif len(judul) > MAKS_JUDUL_SERTIFIKAT:
        messages.error(request, f'Judul maksimal {MAKS_JUDUL_SERTIFIKAT} karakter.')
    elif len(keterangan) > MAKS_KET_SERTIFIKAT:
        messages.error(request, f'Keterangan maksimal {MAKS_KET_SERTIFIKAT} karakter.')
    elif tanggal is None or tanggal > hari_ini:
        messages.error(request, 'Tanggal tidak valid (tidak boleh di masa depan).')
    else:
        with transaction.atomic():
            sertifikat = Sertifikat.objects.create(
                siswa=siswa, judul=judul, keterangan=keterangan, tanggal=tanggal,
                diterbitkan_oleh=request.user,
            )
            sertifikat.nomor = f'SRT/{tanggal.year}/{sertifikat.pk:05d}'
            sertifikat.save(update_fields=['nomor'])
        messages.success(request, 'Sertifikat diterbitkan.')
    return redirect('portofolio:detail', siswa_id=siswa.id)


@login_required
@require_safe
def lihat_sertifikat(request, sertifikat_id):
    """Halaman sertifikat siap cetak. Aturan akses sama dengan data lengkap portofolio siswa itu."""
    sertifikat = get_object_or_404(Sertifikat.objects.select_related('siswa', 'diterbitkan_oleh'), id=sertifikat_id)
    if tingkat_akses(request.user, sertifikat.siswa) != AKSES_PENUH:
        raise PermissionDenied
    return render(request, 'portofolio/sertifikat.html', {'s': sertifikat, 'siswa': sertifikat.siswa})


@login_required
@require_POST
def hapus_sertifikat(request, sertifikat_id):
    if not request.user.is_staff_role():
        raise PermissionDenied
    sertifikat = get_object_or_404(Sertifikat, id=sertifikat_id)
    siswa_id = sertifikat.siswa_id
    sertifikat.delete()
    messages.success(request, 'Sertifikat dihapus.')
    return redirect('portofolio:detail', siswa_id=siswa_id)


# Jenis berkas yang aman dibuka langsung di browser. Selain ini (SVG, HTML, dokumen Office,
# berkas lama yang tidak dikenal) selalu diunduh, tidak pernah dijalankan di alamat situs ini.
TIPE_AMAN_INLINE = {
    'image/jpeg', 'image/png', 'image/gif', 'image/webp',
    'application/pdf', 'audio/mpeg', 'video/mp4', 'video/webm',
}


def boleh_lihat_berkas(user, karya):
    """Aturan sama dengan halaman portofolio: pemilik dan staf semuanya; orang tua dan siswa lain
    hanya karya yang dibagikan."""
    if user.is_staff_role() or adalah_pemilik(user, karya.siswa_id):
        return True
    if adalah_orang_tua_dari(user, karya.siswa_id):
        return karya.dibagikan or ORANG_TUA_LIHAT_KARYA_PRIVAT
    if user.role == 'siswa':
        return karya.dibagikan
    return False


def sajikan_berkas(karya):
    """Mengirim berkas karya. Pemanggil sudah memeriksa izin."""
    if not karya.file:
        raise Http404
    try:
        handle = karya.file.open('rb')
    except (FileNotFoundError, ValueError):
        raise Http404
    tipe = mimetypes.guess_type(karya.file.name)[0] or 'application/octet-stream'
    respons = FileResponse(
        handle, content_type=tipe,
        as_attachment=tipe not in TIPE_AMAN_INLINE,
        filename=os.path.basename(karya.file.name),
    )
    respons['X-Content-Type-Options'] = 'nosniff'
    respons['Cache-Control'] = 'private, max-age=300'
    return respons


@login_required
@require_safe
def berkas_karya(request, karya_id):
    """Berkas karya lewat alamat bernomor (dipakai halaman portofolio)."""
    karya = get_object_or_404(KaryaSiswa.objects.select_related('siswa'), id=karya_id)
    if not karya.file:
        raise Http404
    if not boleh_lihat_berkas(request.user, karya):
        raise PermissionDenied
    return sajikan_berkas(karya)


@login_required
@require_safe
def berkas_langsung(request, nama):
    """Menangkap alamat lama /media/karya_siswa/<nama> supaya tidak lagi terbuka untuk umum.

    Dipasang di urls.py proyek sebelum static(MEDIA_URL). Tidak ada jalur file yang dibentuk dari
    masukan pengguna: nama hanya dicocokkan dengan catatan di database.
    """
    daftar = list(KaryaSiswa.objects.select_related('siswa').filter(file=f'karya_siswa/{nama}'))
    if not daftar:
        raise Http404
    for karya in daftar:
        if boleh_lihat_berkas(request.user, karya):
            return sajikan_berkas(karya)
    raise PermissionDenied

