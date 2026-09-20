import mimetypes
import os
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponse, HttpResponseForbidden, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import content_disposition_header

from ruang_kerja.models import AnggotaRuangKerja, SubmisiTugas

from .fase_config import LEVEL_LABEL, get_config
from .izin import boleh_kelola_ruang, boleh_lihat_submisi
from .layanan import KesalahanForm, kolom_unggah, proses_pengumpulan, ringkas_refleksi
from .models import DimensiPenilaian, LampiranKarya, RefleksiKarya, SkorDimensi

_RE_RANGE = re.compile(r'^bytes=(\d*)-(\d*)$')

# Hanya jenis ini yang boleh ditampilkan langsung di browser. Selain itu (html, svg,
# dll.) dipaksa diunduh supaya berkas unggahan siswa tidak bisa menjalankan skrip
# di dalam sesi guru.
_INLINE_AMAN = ('image/jpeg', 'image/png', 'image/gif', 'image/webp', 'application/pdf')
_INLINE_AMAN_PREFIX = ('audio/', 'video/')


def _tipe_konten(nama, audio=False):
    ext = os.path.splitext(nama)[1].lower()
    if audio and ext == '.webm':
        return 'audio/webm'  # rekaman suara browser
    return mimetypes.guess_type(nama)[0] or 'application/octet-stream'


def _iter_berkas(path, awal, panjang, chunk=64 * 1024):
    with open(path, 'rb') as f:
        f.seek(awal)
        sisa = panjang
        while sisa > 0:
            data = f.read(min(chunk, sisa))
            if not data:
                break
            sisa -= len(data)
            yield data


@login_required
def media_privat(request, jenis, pk):
    """Layani berkas privat hanya kepada yang berhak. Mendukung Range (perlu untuk audio/video di Safari)."""
    if jenis == 'lampiran':
        obj = get_obj(LampiranKarya, pk)
        berkas, nama_unduh, audio = obj.file, obj.nama_asli, obj.tipe == 'audio'
    elif jenis == 'refleksi':
        obj = get_obj(RefleksiKarya, pk)
        berkas, nama_unduh, audio = obj.audio, 'refleksi' + os.path.splitext(obj.audio.name or '')[1], True
    else:
        raise Http404

    if not berkas:
        raise Http404
    if not boleh_lihat_submisi(request.user, obj.submisi):
        return HttpResponseForbidden('Anda tidak memiliki akses ke berkas ini.')

    try:
        path = berkas.path
    except (ValueError, NotImplementedError):
        raise Http404
    if not os.path.isfile(path):
        raise Http404

    tipe = _tipe_konten(berkas.name, audio=audio)
    inline = tipe in _INLINE_AMAN or tipe.startswith(_INLINE_AMAN_PREFIX)
    nama_unduh = nama_unduh or os.path.basename(berkas.name)
    ukuran = os.path.getsize(path)

    rentang = request.headers.get('Range', '').strip()
    m = _RE_RANGE.match(rentang) if rentang else None
    if m and (m.group(1) or m.group(2)):
        if m.group(1) == '':  # "bytes=-500": 500 byte terakhir
            awal = max(ukuran - int(m.group(2)), 0)
            akhir = ukuran - 1
        else:
            awal = int(m.group(1))
            akhir = min(int(m.group(2)), ukuran - 1) if m.group(2) else ukuran - 1
        if awal >= ukuran or awal > akhir:
            resp = HttpResponse(status=416)
            resp['Content-Range'] = f'bytes */{ukuran}'
            return resp
        panjang = akhir - awal + 1
        resp = StreamingHttpResponse(_iter_berkas(path, awal, panjang), status=206, content_type=tipe)
        resp['Content-Range'] = f'bytes {awal}-{akhir}/{ukuran}'
        resp['Content-Length'] = str(panjang)
    else:
        resp = FileResponse(open(path, 'rb'), content_type=tipe)
        resp['Content-Length'] = str(ukuran)

    resp['Accept-Ranges'] = 'bytes'
    resp['Content-Disposition'] = content_disposition_header(not inline, nama_unduh)
    resp['Cache-Control'] = 'private, no-cache'
    resp['X-Content-Type-Options'] = 'nosniff'
    return resp


def get_obj(model, pk):
    try:
        return model.objects.select_related(
            'submisi__siswa', 'submisi__tugas__ruang_kerja'
        ).get(pk=pk)
    except model.DoesNotExist:
        raise Http404



# ====================================================================== tugas kreasi
# kerjakan_kreasi & daftar_karya_guru dipanggil dari ruang_kerja.views.detail_tugas.

def _nama_depan(siswa):
    return siswa.nama.split()[0] if siswa.nama else siswa.nama


def _lampiran_dan_refleksi(submisi, cfg):
    lampiran = list(submisi.lampiran_karya.all())
    try:
        refleksi = submisi.refleksi_karya
    except RefleksiKarya.DoesNotExist:
        refleksi = None
    return lampiran, ringkas_refleksi(refleksi, cfg)


def _baris_refleksi(cfg_ref, isian):
    """Baris isian refleksi untuk formulir (mempertahankan ketikan siswa bila ada galat)."""
    baris = []
    for kode, label in cfg_ref.get('pertanyaan', []):
        baris.append({'kode': kode, 'label': label, 'isi': isian.get(f'refleksi_{kode}', '')})
    for kode, label in cfg_ref.get('kriteria', []):
        baris.append({'kode': kode, 'label': label,
                      'skor': str(isian.get(f'refleksi_{kode}_skor', '')),
                      'alasan': isian.get(f'refleksi_{kode}_alasan', '')})
    return baris


def kerjakan_kreasi(request, tugas, ruang, siswa_obj, submisi):
    """Halaman siswa: form pengumpulan, atau tampilan hasil bila sudah dikumpulkan."""
    jenjang = ruang.get_jenjang()
    cfg = get_config(jenjang)
    if cfg is None:
        return render(request, 'kreasi/belum_diatur.html', {'tugas': tugas, 'ruang': ruang})

    ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    if submisi:
        if ajax and request.method == 'POST':   # sudah dikumpulkan (mis. klik ganda): arahkan ke halaman hasil
            return JsonResponse({'ok': True, 'url': request.path})
        lampiran, refleksi = _lampiran_dan_refleksi(submisi, cfg)
        nama = _nama_depan(siswa_obj)
        skor = SkorDimensi.objects.filter(submisi=submisi, dimensi__aktif=True).select_related('dimensi')
        baris_skor = []
        for sk in skor:
            kalimat = next((d.untuk(nama) for d in sk.dimensi.deskriptor.all() if d.level == sk.level), '')
            baris_skor.append({'nama': sk.dimensi.nama, 'level': sk.level, 'label': sk.label_level,
                               'kalimat': kalimat, 'catatan': sk.catatan})
        return render(request, 'kreasi/siswa_lihat.html', {
            'tugas': tugas, 'ruang': ruang, 'submisi': submisi, 'cfg': cfg,
            'lampiran_list': lampiran, 'refleksi': refleksi, 'baris_skor': baris_skor,
        })

    galat = []
    if request.method == 'POST':
        try:
            proses_pengumpulan(tugas, siswa_obj, cfg, request.POST, request.FILES)
            messages.success(request, 'Karyamu berhasil dikumpulkan!')
            if ajax:
                return JsonResponse({'ok': True, 'url': request.path})
            return redirect('ruang_kerja:detail_tugas', tugas_id=tugas.id)
        except KesalahanForm as e:
            galat = e.pesan
            if ajax:   # isian di browser tidak disentuh; hanya daftar galat yang dikirim balik
                return JsonResponse({'ok': False, 'galat': galat}, status=400)

    isian = request.POST if request.method == 'POST' else {}
    return render(request, 'kreasi/siswa_form.html', {
        'tugas': tugas, 'ruang': ruang, 'cfg': cfg, 'kolom': kolom_unggah(cfg),
        'refleksi_cfg': cfg['refleksi'], 'baris_refleksi': _baris_refleksi(cfg['refleksi'], isian),
        'skala': [1, 2, 3, 4], 'pakai_link': 'link' in cfg['tipe_lampiran'],
        'batas_audio': cfg.get('batas_audio_detik', 120), 'galat': galat, 'isian': isian,
    })


def daftar_karya_guru(request, tugas, ruang):
    """Halaman guru: daftar karya yang masuk beserta status penilaian rubrik."""
    if not request.user.is_staff_role() or not boleh_kelola_ruang(request.user, ruang):
        messages.error(request, 'Anda tidak memiliki akses ke tugas ini.')
        return redirect('ruang_kerja:daftar')

    jenjang = ruang.get_jenjang()
    cfg = get_config(jenjang)
    if cfg is None:
        return render(request, 'kreasi/belum_diatur.html', {'tugas': tugas, 'ruang': ruang})
    jumlah_dimensi = DimensiPenilaian.objects.filter(jenjang=jenjang, aktif=True).count()

    submisi_list = (tugas.submisi.select_related('siswa')
                    .prefetch_related('skor_dimensi', 'lampiran_karya').order_by('siswa__nama'))
    baris = []
    sudah = set()
    for sub in submisi_list:
        sudah.add(sub.siswa_id)
        jumlah_skor = sum(1 for sk in sub.skor_dimensi.all() if sk.dimensi.aktif)
        baris.append({
            'submisi': sub,
            'jumlah_lampiran': len(sub.lampiran_karya.all()),
            'jumlah_skor': jumlah_skor,
            'lengkap': jumlah_dimensi > 0 and jumlah_skor >= jumlah_dimensi,
        })
    belum = [a.siswa for a in AnggotaRuangKerja.objects.filter(ruang_kerja=ruang).select_related('siswa')
             if a.siswa_id not in sudah]
    return render(request, 'kreasi/guru_daftar.html', {
        'tugas': tugas, 'ruang': ruang, 'cfg': cfg, 'baris': baris, 'belum_kumpul': belum,
        'jumlah_dimensi': jumlah_dimensi,
    })


@login_required
def nilai_karya(request, submisi_id):
    """Halaman guru: lihat karya + refleksi satu siswa, lalu beri skor rubrik (1-4) per dimensi."""
    submisi = get_object_or_404(
        SubmisiTugas.objects.select_related('siswa', 'tugas__ruang_kerja'),
        pk=submisi_id, tugas__jenis='kreasi')
    tugas, ruang, siswa = submisi.tugas, submisi.tugas.ruang_kerja, submisi.siswa
    if not request.user.is_staff_role() or not boleh_kelola_ruang(request.user, ruang):
        messages.error(request, 'Anda tidak memiliki akses untuk menilai karya ini.')
        return redirect('ruang_kerja:daftar')

    jenjang = ruang.get_jenjang()
    cfg = get_config(jenjang)
    if cfg is None:
        return render(request, 'kreasi/belum_diatur.html', {'tugas': tugas, 'ruang': ruang})

    dimensi_list = list(DimensiPenilaian.objects.filter(jenjang=jenjang, aktif=True).prefetch_related('deskriptor'))
    skor_ada = {sk.dimensi_id: sk for sk in SkorDimensi.objects.filter(submisi=submisi)}
    nama = _nama_depan(siswa)
    galat = []

    if request.method == 'POST':
        baru = []
        for d in dimensi_list:
            mentah = request.POST.get(f'level_{d.id}', '')
            if mentah == '':
                continue
            try:
                level = int(mentah)
            except ValueError:
                level = 0
            if level not in LEVEL_LABEL:
                galat.append(f'Level untuk "{d.nama}" tidak valid.')
                continue
            baru.append((d, level, request.POST.get(f'catatan_{d.id}', '').strip()[:1000]))
        if not baru and not skor_ada:
            galat.append('Pilih level untuk minimal satu dimensi.')
        if not galat:
            for d, level, catatan in baru:
                SkorDimensi.objects.update_or_create(
                    submisi=submisi, dimensi=d,
                    defaults={'level': level, 'catatan': catatan, 'dinilai_oleh': request.user})
            submisi.feedback = request.POST.get('feedback', '').strip()
            submisi.dinilai_pada = timezone.now()
            submisi.save(update_fields=['feedback', 'dinilai_pada'])
            messages.success(request, f'Penilaian karya {siswa.nama} disimpan.')
            return redirect('ruang_kerja:detail_tugas', tugas_id=tugas.id)
        # gagal validasi: tampilkan lagi dengan pilihan yang baru diketik
        skor_ada = {}

    baris = []
    for d in dimensi_list:
        kalimat = {x.level: x.untuk(nama) for x in d.deskriptor.all()}
        if request.method == 'POST':
            terpilih = request.POST.get(f'level_{d.id}', '')
            catatan = request.POST.get(f'catatan_{d.id}', '')
        else:
            terpilih = str(skor_ada[d.id].level) if d.id in skor_ada else ''
            catatan = skor_ada[d.id].catatan if d.id in skor_ada else ''
        baris.append({
            'dimensi': d, 'catatan': catatan,
            'pilihan': [{'level': lv, 'label': lb, 'kalimat': kalimat.get(lv, ''),
                         'dipilih': terpilih == str(lv)} for lv, lb in LEVEL_LABEL.items()],
        })

    lampiran, refleksi = _lampiran_dan_refleksi(submisi, cfg)
    return render(request, 'kreasi/guru_nilai.html', {
        'tugas': tugas, 'ruang': ruang, 'submisi': submisi, 'siswa': siswa, 'cfg': cfg,
        'lampiran_list': lampiran, 'refleksi': refleksi, 'baris': baris, 'galat': galat,
        'feedback': request.POST.get('feedback', submisi.feedback) if request.method == 'POST' else submisi.feedback,
    })


@login_required
def atur_jenjang(request, ruang_id):
    """Guru menentukan jenjang ruang kerja bila sistem tidak bisa menebaknya dari nama kelas."""
    from ruang_kerja.models import RuangKerja
    from .fase_config import JENJANG_CONFIG

    ruang = get_object_or_404(RuangKerja, pk=ruang_id)
    if request.method != 'POST' or not request.user.is_staff_role() or not boleh_kelola_ruang(request.user, ruang):
        messages.error(request, 'Anda tidak memiliki akses untuk mengatur jenjang.')
        return redirect('ruang_kerja:daftar')
    jenjang = request.POST.get('jenjang', '')
    if jenjang not in JENJANG_CONFIG:
        messages.error(request, 'Jenjang tidak valid.')
    else:
        ruang.jenjang = jenjang
        ruang.save(update_fields=['jenjang'])
        messages.success(request, f'Jenjang {ruang.mapel} diatur ke {JENJANG_CONFIG[jenjang]["label"]}.')
    try:
        return redirect('ruang_kerja:detail_tugas', tugas_id=int(request.POST.get('tugas_id', '')))
    except ValueError:
        return redirect('ruang_kerja:detail', ruang_id=ruang.id)
