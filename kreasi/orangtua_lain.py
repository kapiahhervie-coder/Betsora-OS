"""
Absensi, Tugas (ringkas), dan Portofolio untuk dashboard ORANG TUA.

Terpisah dari orangtua.py (karya Tugas Kreasi) supaya berkas yang sudah teruji di
tahap sebelumnya tidak ikut tersentuh. Aturan akses sama persis dengan orangtua.py:
hanya akun 'orangtua' yang terhubung ke seorang anak, dan yang ditampilkan selalu
anak dari akun yang login (fungsi ini TIDAK menerima parameter siswa/anak).

Lingkup TUGAS sengaja hanya status kumpul (sudah / belum / lewat batas waktu),
TANPA nilai dan TANPA feedback guru -- fungsi orang tua di sini adalah kontrol
perkembangan, bukan duplikat rapor.

Portofolio (portofolio.KaryaSiswa) ditampilkan APA ADANYA termasuk yang belum
`dibagikan`, karena flag itu mengatur visibilitas ke SESAMA SISWA, bukan ke orang
tua siswa itu sendiri.

CATATAN KEAMANAN (bukan bagian tahap ini, hanya diberi tahu):
KaryaSiswa.file disimpan di folder media PUBLIK (upload_to='karya_siswa/'), bukan
penyimpanan privat seperti LampiranKarya milik Tugas Kreasi. URL-nya bisa dibuka
siapa pun yang tahu alamatnya, tanpa login. Ini bukan diperkenalkan oleh modul ini;
app `portofolio` sudah begitu sejak awal.
"""
from django.utils import timezone

from ruang_kerja.models import AnggotaRuangKerja, SubmisiTugas, Tugas

STATUS_LABEL = {'hadir': 'Hadir', 'izin': 'Izin', 'sakit': 'Sakit', 'alpha': 'Alpha'}
BATAS_TUGAS = 10
BATAS_PORTOFOLIO = 12


def _anak_orangtua(user):
    if not (getattr(user, 'is_authenticated', False) and getattr(user, 'role', None) == 'orangtua' and user.anak_id):
        return None
    return user.anak


# ---------------------------------------------------------------- absensi

def ringkasan_absensi_untuk_orangtua(user, batas=15):
    siswa = _anak_orangtua(user)
    if siswa is None:
        return None
    from kelas.models import Absensi

    semua = list(Absensi.objects.filter(siswa=siswa).order_by('-tanggal'))
    hitung = {'hadir': 0, 'izin': 0, 'sakit': 0, 'alpha': 0, 'kosong': 0}
    for a in semua:
        kunci = a.status if a.status in hitung else 'kosong'
        hitung[kunci] += 1
    total = len(semua)
    persen_hadir = round(hitung['hadir'] / total * 100) if total else None

    daftar = [{
        'tanggal': a.tanggal, 'status': a.status, 'label': STATUS_LABEL.get(a.status, 'Belum diisi'),
        'kosong': not a.status, 'catatan': a.catatan,
    } for a in semua[:batas]]

    return {
        'total': total, 'hitung': hitung, 'persen_hadir': persen_hadir,
        'daftar': daftar, 'ada_lebih': total > len(daftar),
    }


# ---------------------------------------------------------------- tugas (status saja, tanpa nilai)

def ringkasan_tugas_untuk_orangtua(user):
    siswa = _anak_orangtua(user)
    if siswa is None:
        return None

    ruang_ids = list(AnggotaRuangKerja.objects.filter(siswa=siswa).values_list('ruang_kerja_id', flat=True))
    if not ruang_ids:
        return {'ruang_list': [], 'total_tugas': 0}

    daftar_tugas = list(
        Tugas.objects.filter(ruang_kerja_id__in=ruang_ids)
        .select_related('ruang_kerja').order_by('ruang_kerja__mapel', '-dibuat_pada')
    )
    sudah_kumpul = set(
        SubmisiTugas.objects.filter(siswa=siswa, tugas_id__in=[t.id for t in daftar_tugas])
        .values_list('tugas_id', flat=True)
    )
    sekarang = timezone.now()

    ruang_map = {}
    for t in daftar_tugas:
        if t.deadline and t.deadline < sekarang and t.id not in sudah_kumpul:
            status, kunci = 'Lewat batas waktu', 'lewat'
        elif t.id in sudah_kumpul:
            status, kunci = 'Sudah dikumpulkan', 'sudah'
        else:
            status, kunci = 'Belum dikumpulkan', 'belum'
        ruang_map.setdefault(t.ruang_kerja_id, {'ruang': t.ruang_kerja, 'tugas': []})['tugas'].append({
            'tugas': t, 'jenis_label': t.get_jenis_display(), 'status': status, 'status_kunci': kunci,
        })

    return {'ruang_list': list(ruang_map.values()), 'total_tugas': len(daftar_tugas)}


# ---------------------------------------------------------------- portofolio / galeri

def ringkasan_portofolio_untuk_orangtua(user, semua=False):
    siswa = _anak_orangtua(user)
    if siswa is None:
        return None
    from portofolio.models import KaryaSiswa

    qs = KaryaSiswa.objects.filter(siswa=siswa).order_by('-diunggah_pada')
    total = qs.count()
    daftar = list(qs if semua else qs[:BATAS_PORTOFOLIO])
    hasil = []
    for k in daftar:
        embed = k.get_video_embed() if k.video_url else ''
        hasil.append({
            'karya': k, 'is_image': k.is_image(),
            'embed_aman': embed if embed and embed != k.video_url else '',   # hanya iframe utk youtube/gdrive yg cocok
            'video_url_mentah': k.video_url if embed == k.video_url else '',  # selain itu, tautan biasa saja
        })
    return {'daftar': hasil, 'total': total, 'ada_lebih': total > len(daftar), 'semua': semua}
