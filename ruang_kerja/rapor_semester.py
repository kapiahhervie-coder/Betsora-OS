"""
Rapor semester: nilai akhir dan deskripsi per mata pelajaran, serta data semester yang diisi wali kelas.

Bagian ini berisi:
  * aturan predikat dari nilai akhir (90+ / 80-89 / 70-79 / di bawah 70),
  * pembuat draf deskripsi mapel (Inggris atau Indonesia) dari ketuntasan topik,
  * halaman guru mapel untuk mengisi nilai akhir + deskripsi (draf bisa diikuti lalu diedit),
  * penyimpanan data semester (spiritual, ekstrakurikuler, prestasi, pertumbuhan, komentar guru).
"""
import datetime
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import Siswa
from .models import AnggotaRuangKerja, NilaiRaporMapel, RaporSemester, RuangKerja
from .views import _bukan_staf, hitung_rata_rata_nilai

PREDIKAT = {
    'en': ((90, 'Really Good'), (80, 'Good'), (70, 'Adequate'), (0, 'Need Improvement')),
    'id': ((90, 'Sangat Baik'), (80, 'Baik'), (70, 'Cukup'), (0, 'Perlu Peningkatan')),
}
LABEL = {
    'en': {'nilai': 'Final Score', 'predikat': 'Predicate'},
    'id': {'nilai': 'Nilai Akhir', 'predikat': 'Predikat'},
}
GAYA = (
    ('otomatis', 'Otomatis (ikut nilai akhir)'),
    ('atas', 'Di atas ekspektasi tingkat kelas'),
    ('sesuai', 'Sesuai ekspektasi tingkat kelas'),
    ('mulai', 'Mulai berkembang'),
)


# ------------------------------------------------------------------ semester dan tahun ajaran
def tahun_ajaran_sekarang(hari=None):
    hari = hari or datetime.date.today()
    if hari.month >= 7:
        return '%d/%d' % (hari.year, hari.year + 1), 1
    return '%d/%d' % (hari.year - 1, hari.year), 2


def tahun_ajaran_valid(teks):
    m = re.fullmatch(r'(\d{4})/(\d{4})', (teks or '').strip())
    return bool(m) and int(m.group(2)) == int(m.group(1)) + 1


def baca_periode(data):
    """(tahun_ajaran, semester) dari GET/POST; yang tidak sah diganti dengan periode sekarang."""
    ta_default, sem_default = tahun_ajaran_sekarang()
    ta = (data.get('ta') or '').strip()
    if not tahun_ajaran_valid(ta):
        ta = ta_default
    try:
        sem = int(data.get('sem'))
    except (TypeError, ValueError):
        sem = sem_default
    return ta, (sem if sem in (1, 2) else sem_default)


def rentang_semester(tahun_ajaran, semester):
    awal = int(tahun_ajaran[:4])
    if semester == 1:
        return datetime.date(awal, 7, 1), datetime.date(awal, 12, 31)
    return datetime.date(awal + 1, 1, 1), datetime.date(awal + 1, 6, 30)


# ------------------------------------------------------------------ predikat
def predikat(nilai, bahasa='en'):
    if nilai is None:
        return ''
    for batas, nama in PREDIKAT.get(bahasa, PREDIKAT['en']):
        if nilai >= batas:
            return nama
    return ''


# ------------------------------------------------------------------ data topik dan saran nilai
def info_topik(ruang, siswa):
    """Topik yang sudah dinilai: [{'id', 'judul', 'mastery'}]."""
    hasil = []
    for t in ruang.materi.all():
        m = t.hitung_mastery(siswa)
        if m is not None:
            hasil.append({'id': t.id, 'judul': t.judul.strip(), 'mastery': float(m)})
    return hasil


def saran_nilai(ruang, siswa, topik=None):
    """Saran nilai akhir: rata-rata dari rata-rata nilai tugas dan rata-rata ketuntasan topik."""
    topik = info_topik(ruang, siswa) if topik is None else topik
    bagian = []
    rata_tugas = hitung_rata_rata_nilai(ruang, siswa)
    if rata_tugas is not None:
        bagian.append(float(rata_tugas))
    if topik:
        bagian.append(sum(t['mastery'] for t in topik) / len(topik))
    return int(round(sum(bagian) / len(bagian))) if bagian else None


# ------------------------------------------------------------------ pembuat draf deskripsi
def _tingkat_topik(mastery):
    if mastery >= 90:
        return 'atas'
    return 'sesuai' if mastery >= 75 else 'mulai'


def _tingkat_umum(nilai, gaya):
    if gaya in ('atas', 'sesuai', 'mulai'):
        return gaya
    if nilai is None:
        return 'sesuai'
    return 'atas' if nilai >= 90 else 'sesuai' if nilai >= 80 else 'mulai'


_EN = {
    'umum': {
        'atas': 'Overall, {n} is able to demonstrate the cognitive abilities and/or skills beyond the grade level expectations.',
        'sesuai': 'Overall, {n} is able to demonstrate the cognitive abilities and/or skills in accordance with the grade level expectations.',
        'mulai': 'Overall, {n} is starting to develop the cognitive abilities and/or skills in accordance with the grade level expectations.',
    },
    'topik': {
        'atas': '{n} is able to demonstrate the cognitive abilities and/or skills exceeding the grade level expectation in {t}.',
        'sesuai': '{n} is able to demonstrate the cognitive abilities and/or skills in accordance with the grade level expectation in {t}.',
        'mulai': '{n} is starting to develop the cognitive abilities and/or skills in accordance with the grade level expectation in {t}.',
    },
    'khusus': 'Specifically, ', 'tambahan': 'In addition, ',
    'bantu': 'Assistance is needed to overcome the difficulties in the related topics.',
    'usaha_penuh': 'Maximum effort is needed to master the related topic.',
    'usaha_konsisten': 'More consistent effort is needed to achieve better results.',
}
_ID = {
    'umum': {
        'atas': 'Secara menyeluruh, {n} dapat menunjukkan kemampuan kognitif dan/atau keterampilan melebihi ekspektasi tingkat kelas.',
        'sesuai': 'Secara menyeluruh, {n} dapat menunjukkan kemampuan kognitif dan/atau keterampilan sesuai dengan ekspektasi tingkat kelas.',
        'mulai': 'Secara menyeluruh, {n} mulai mengembangkan kemampuan kognitif dan/atau keterampilan sesuai dengan ekspektasi tingkat kelas.',
    },
    'topik': {
        'atas': '{n} dapat menunjukkan kemampuan kognitif dan/atau keterampilan melebihi ekspektasi tingkat kelas pada materi {t}.',
        'sesuai': '{n} dapat menunjukkan kemampuan kognitif dan/atau keterampilan sesuai dengan ekspektasi tingkat kelas pada materi {t}.',
        'mulai': '{n} mulai mengembangkan kemampuan kognitif dan/atau keterampilan sesuai dengan ekspektasi tingkat kelas pada materi {t}.',
    },
    'khusus': 'Secara khusus, ', 'tambahan': 'Selain itu, ',
    'bantu': 'Pendampingan diperlukan untuk mengatasi kesulitan pada topik terkait.',
    'usaha_penuh': 'Usaha yang maksimal diperlukan untuk menguasai topik terkait.',
    'usaha_konsisten': 'Usaha yang lebih konsisten diperlukan untuk mencapai hasil yang lebih baik.',
}


def nama_panggilan(siswa):
    kata = (siswa.nama or '').split()
    return kata[0].capitalize() if kata else ''


def buat_draf(nama, nilai, topik_utama, topik_tambahan, bahasa='en', gaya='otomatis'):
    """Susun deskripsi mapel. topik_* = {'judul', 'mastery'} atau None."""
    T = _ID if bahasa == 'id' else _EN
    umum = _tingkat_umum(nilai, gaya)
    kalimat = [T['umum'][umum].format(n=nama)]
    ada_kesulitan = umum == 'mulai'
    if topik_utama:
        tk = _tingkat_topik(topik_utama['mastery'])
        kalimat.append(T['khusus'] + T['topik'][tk].format(n=nama, t=topik_utama['judul']))
        if tk == 'mulai':
            ada_kesulitan = True
            kalimat.append(T['bantu'])
    if topik_tambahan:
        tk = _tingkat_topik(topik_tambahan['mastery'])
        kalimat.append(T['tambahan'] + T['topik'][tk].format(n=nama, t=topik_tambahan['judul']))
        ada_kesulitan = ada_kesulitan or tk == 'mulai'
    kalimat.append(T['usaha_penuh'] if ada_kesulitan else T['usaha_konsisten'])
    return ' '.join(kalimat)


def _pilih_topik(topik, utama_id, tambahan_id):
    """Topik utama bawaan = ketuntasan terendah; tambahan = tertinggi (seperti contoh rapor)."""
    peta = {t['id']: t for t in topik}

    def ambil(kode):
        try:
            return peta.get(int(kode))
        except (TypeError, ValueError):
            return None

    utama, tambahan = ambil(utama_id), ambil(tambahan_id)
    if utama is None and utama_id in (None, '') and topik:
        utama = min(topik, key=lambda t: t['mastery'])
    if tambahan is None and tambahan_id in (None, '') and len(topik) > 1:
        tambahan = max((t for t in topik if utama is None or t['id'] != utama['id']), key=lambda t: t['mastery'])
    return utama, tambahan


# ------------------------------------------------------------------ halaman guru mapel
@login_required
def nilai_mapel_rapor(request, ruang_id, siswa_id):
    if _bukan_staf(request.user):
        messages.error(request, 'Hanya guru yang dapat mengisi nilai rapor.')
        return redirect('ruang_kerja:daftar')
    ruang = get_object_or_404(RuangKerja, id=ruang_id)
    siswa = get_object_or_404(Siswa, id=siswa_id)
    if not AnggotaRuangKerja.objects.filter(ruang_kerja=ruang, siswa=siswa).exists():
        messages.error(request, 'Siswa ini tidak terdaftar di mata pelajaran tersebut.')
        return redirect('ruang_kerja:rapor_ruang_kerja', ruang_id=ruang.id)
    sumber = request.POST if request.method == 'POST' else request.GET
    ta, sem = baca_periode(sumber)
    topik = info_topik(ruang, siswa)
    nama = nama_panggilan(siswa)

    if request.method == 'GET' and request.GET.get('draf') == '1':
        bahasa = 'id' if request.GET.get('bahasa') == 'id' else 'en'
        try:
            nilai = int(request.GET.get('nilai'))
        except (TypeError, ValueError):
            nilai = saran_nilai(ruang, siswa, topik)
        utama, tambahan = _pilih_topik(topik, request.GET.get('utama'), request.GET.get('tambahan'))
        gaya = request.GET.get('gaya') if request.GET.get('gaya') in dict(GAYA) else 'otomatis'
        return JsonResponse({'draf': buat_draf(nama, nilai, utama, tambahan, bahasa, gaya)})

    if request.method == 'POST':
        try:
            nilai = int(request.POST.get('nilai_akhir'))
            if not 0 <= nilai <= 100:
                raise ValueError
        except (TypeError, ValueError):
            nilai = None
        bahasa = 'id' if request.POST.get('bahasa') == 'id' else 'en'
        NilaiRaporMapel.objects.update_or_create(
            ruang_kerja=ruang, siswa=siswa, tahun_ajaran=ta, semester=sem,
            defaults={'nilai_akhir': nilai, 'bahasa': bahasa,
                      'nama_tampil': request.POST.get('nama_tampil', '').strip()[:120],
                      'deskripsi': request.POST.get('deskripsi', '').strip(),
                      'diperbarui_oleh': request.user})
        messages.success(request, 'Nilai rapor %s untuk %s disimpan.' % (ruang.mapel, siswa.nama))
        return redirect('%s?ta=%s&sem=%d' % (request.path, ta, sem))

    tersimpan = NilaiRaporMapel.objects.filter(ruang_kerja=ruang, siswa=siswa, tahun_ajaran=ta, semester=sem).first()
    saran = saran_nilai(ruang, siswa, topik)
    utama, tambahan = _pilih_topik(topik, None, None)
    bahasa = tersimpan.bahasa if tersimpan else 'en'
    return render(request, 'ruang_kerja/rapor_nilai_mapel.html', {
        'ruang': ruang, 'siswa': siswa, 'ta': ta, 'sem': sem,
        'tersimpan': tersimpan, 'topik': topik, 'saran': saran,
        'utama': utama, 'tambahan': tambahan,
        'bahasa': bahasa, 'gaya_list': GAYA,
        'nilai_awal': tersimpan.nilai_akhir if tersimpan and tersimpan.nilai_akhir is not None else saran,
        'deskripsi_awal': tersimpan.deskripsi if tersimpan else buat_draf(nama, saran, utama, tambahan, bahasa),
        'predikat_aturan': PREDIKAT,
    })


# ------------------------------------------------------------------ data semester (wali kelas)
def _daftar(post, *kolom):
    """Baris-baris isian berulang -> [{kolom: nilai}], baris yang seluruhnya kosong dibuang."""
    cols = [post.getlist(k) for k in kolom]
    baris = []
    for nilai in zip(*cols) if cols else []:
        nilai = [v.strip() for v in nilai]
        if any(nilai):
            baris.append(dict(zip([k.split('_', 1)[1] for k in kolom], nilai)))
    return baris


def _hari(teks):
    try:
        n = int((teks or '').strip())
        return n if 0 <= n <= 366 else None
    except ValueError:
        return None


def _tanggal(teks):
    try:
        return datetime.date.fromisoformat((teks or '').strip())
    except ValueError:
        return None


def simpan_data_semester(request, siswa, ta, sem):
    """Simpan formulir data semester dari POST. Mengembalikan objek RaporSemester."""
    p = request.POST
    data = {
        'nisn': p.get('nisn', '').strip()[:30],
        'alamat_sekolah': p.get('alamat_sekolah', '').strip()[:250],
        'tempat': p.get('tempat', '').strip()[:100],
        'tanggal_rapor': _tanggal(p.get('tanggal_rapor')),
        'nama_kepala_sekolah': p.get('nama_kepala_sekolah', '').strip()[:150],
        'spiritual': _daftar(p, 'sp_aspek', 'sp_predikat'),
        'ekskul': _daftar(p, 'ek_kegiatan', 'ek_predikat', 'ek_deskripsi'),
        'prestasi': _daftar(p, 'pr_kegiatan', 'pr_catatan'),
        'berat_badan': p.get('berat_badan', '').strip()[:30],
        'tinggi_badan': p.get('tinggi_badan', '').strip()[:30],
        'lingkar_kepala': p.get('lingkar_kepala', '').strip()[:30],
        'pendengaran': p.get('pendengaran', '').strip()[:60],
        'penglihatan': p.get('penglihatan', '').strip()[:60],
        'gigi': p.get('gigi', '').strip()[:60],
        'sakit_hari': _hari(p.get('sakit_hari')),
        'izin_hari': _hari(p.get('izin_hari')),
        'alpha_hari': _hari(p.get('alpha_hari')),
        'komentar_guru': p.get('komentar_guru', '').strip(),
        'diperbarui_oleh': request.user,
    }
    obj, _ = RaporSemester.objects.update_or_create(siswa=siswa, tahun_ajaran=ta, semester=sem, defaults=data)
    return obj
