"""
slide_unduh.py - membuat file unduhan (PDF dan video) dari slide sebuah item.

PDF   : semua gambar slide, satu halaman per slide.
Video : MP4, tiap slide tampil selama rekaman suaranya (tanpa rekaman: 4 detik).
Izin dan "tanda tangan" file disimpan di unduh.json pada folder slide, jadi tanpa migrasi.
"""
import glob
import hashlib
import json
import os
import shutil
import subprocess
import tempfile

NAMA_JSON = 'unduh.json'
SUB = 'unduh'
DETIK_TANPA_SUARA = 4


class GalatUnduh(Exception):
    pass


def _tanda(folder, dengan_suara):
    pola = ['slide-*.png'] + (['suara-*.*'] if dengan_suara else [])
    h = hashlib.sha1()
    for p in pola:
        for f in sorted(glob.glob(os.path.join(folder, p))):
            st = os.stat(f)
            h.update(('%s|%d|%d;' % (os.path.basename(f), st.st_size, int(st.st_mtime))).encode('utf-8'))
    return h.hexdigest()


def _jalur(folder, jenis):
    return os.path.join(folder, SUB, 'slide.' + ('pdf' if jenis == 'pdf' else 'mp4'))


def baca(folder):
    try:
        with open(os.path.join(folder, NAMA_JSON), encoding='utf-8') as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    d.setdefault('izin', {})
    d.setdefault('tanda', {})
    return d


def _tulis(folder, d):
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, NAMA_JSON), 'w', encoding='utf-8') as f:
        json.dump(d, f)


def cari_ffmpeg():
    ada = shutil.which('ffmpeg')
    if ada:
        return ada
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def buat_pdf(folder):
    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf
        except ImportError:
            raise GalatUnduh('PyMuPDF belum terpasang (pip install pymupdf).')
    gambar = sorted(glob.glob(os.path.join(folder, 'slide-*.png')))
    if not gambar:
        raise GalatUnduh('Tidak ada gambar slide.')
    os.makedirs(os.path.join(folder, SUB), exist_ok=True)
    tujuan = _jalur(folder, 'pdf')
    doc = pymupdf.open()
    try:
        for g in gambar:
            pix = pymupdf.Pixmap(g)
            lebar = 960.0
            tinggi = lebar * pix.height / float(pix.width)
            hal = doc.new_page(width=lebar, height=tinggi)
            hal.insert_image(pymupdf.Rect(0, 0, lebar, tinggi), filename=g)
        sementara = tujuan + '.tmp'
        doc.save(sementara, garbage=3, deflate=True)
    finally:
        doc.close()
    os.replace(sementara, tujuan)
    return tujuan


def _jalankan(perintah, cwd):
    try:
        h = subprocess.run(perintah, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
    except subprocess.TimeoutExpired:
        raise GalatUnduh('Pembuatan video terlalu lama (lebih dari 10 menit).')
    if h.returncode != 0:
        sisa = h.stderr.decode('utf-8', 'replace').strip().splitlines()[-3:]
        raise GalatUnduh('ffmpeg gagal: ' + ' | '.join(sisa))


def buat_video(folder):
    ff = cari_ffmpeg()
    if not ff:
        raise GalatUnduh('ffmpeg belum terpasang. Jalankan: pip install imageio-ffmpeg')
    folder = os.path.abspath(folder)
    gambar = sorted(glob.glob(os.path.join(folder, 'slide-*.png')))
    if not gambar:
        raise GalatUnduh('Tidak ada gambar slide.')
    os.makedirs(os.path.join(folder, SUB), exist_ok=True)
    tujuan = _jalur(folder, 'video')
    kerja = tempfile.mkdtemp(prefix='sv_', dir=os.path.join(folder, SUB))
    try:
        daftar = []
        for i, g in enumerate(gambar, 1):
            seg = 'seg-%03d.mp4' % i
            suara = sorted(glob.glob(os.path.join(folder, 'suara-%03d.*' % i)))
            vf = 'scale=1280:-2,format=yuv420p'
            enc_v = ['-c:v', 'libx264', '-preset', 'veryfast', '-tune', 'stillimage', '-crf', '28', '-r', '10']
            enc_a = ['-c:a', 'aac', '-b:a', '96k', '-ar', '44100', '-ac', '1']
            if suara:
                cmd = [ff, '-y', '-loop', '1', '-framerate', '10', '-i', g, '-i', suara[0], '-vf', vf] + enc_v + enc_a + \
                      ['-shortest', '-movflags', '+faststart', seg]
            else:
                cmd = [ff, '-y', '-loop', '1', '-framerate', '10', '-i', g, '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=mono',
                       '-vf', vf] + enc_v + enc_a + ['-t', str(DETIK_TANPA_SUARA), '-movflags', '+faststart', seg]
            _jalankan(cmd, kerja)
            daftar.append(seg)
        with open(os.path.join(kerja, 'daftar.txt'), 'w', encoding='utf-8') as f:
            for s in daftar:
                f.write("file '%s'\n" % s)
        _jalankan([ff, '-y', '-f', 'concat', '-safe', '0', '-i', 'daftar.txt', '-c', 'copy', '-movflags', '+faststart', 'hasil.mp4'], kerja)
        os.replace(os.path.join(kerja, 'hasil.mp4'), tujuan)
    finally:
        shutil.rmtree(kerja, ignore_errors=True)
    return tujuan


def terapkan(folder, pdf, video):
    """pdf/video: '' (tidak dibuat), 'guru' (hanya guru) atau 'siswa' (guru dan siswa).
    Mengembalikan (pesan, galat)."""
    d = baca(folder)
    pesan = []
    galat = []
    for jenis, mode, dgn_suara, fungsi in (('pdf', pdf, False, buat_pdf), ('video', video, True, buat_video)):
        nama = 'PDF' if jenis == 'pdf' else 'Video'
        jalur = _jalur(folder, jenis)
        if mode not in ('guru', 'siswa'):
            d['izin'][jenis] = False
            d['tanda'].pop(jenis, None)
            if os.path.isfile(jalur):
                os.remove(jalur)
            continue
        try:
            if not (os.path.isfile(jalur) and d['tanda'].get(jenis) == _tanda(folder, dgn_suara)):
                fungsi(folder)
                d['tanda'][jenis] = _tanda(folder, dgn_suara)
            d['izin'][jenis] = (mode == 'siswa')
            pesan.append('%s siap (%s).' % (nama, 'guru dan siswa' if mode == 'siswa' else 'hanya guru'))
        except GalatUnduh as e:
            d['izin'][jenis] = False
            galat.append('%s: %s' % (nama, e))
    _tulis(folder, d)
    return pesan, galat


def info(folder):
    """Status untuk form guru."""
    d = baca(folder)
    hasil = {'ffmpeg': bool(cari_ffmpeg())}
    for jenis, dgn_suara in (('pdf', False), ('video', True)):
        ada = os.path.isfile(_jalur(folder, jenis))
        izin = bool(d['izin'].get(jenis))
        basi = bool(ada and d['tanda'].get(jenis) != _tanda(folder, dgn_suara))
        hasil[jenis + '_izin'] = izin
        hasil[jenis + '_mode'] = ('siswa' if izin else 'guru') if ada else ''
        hasil[jenis + '_ada'] = ada
        hasil[jenis + '_basi'] = basi
    return hasil


def daftar_siswa(folder, base_url, judul):
    """Tautan unduhan yang boleh dilihat siswa: [{url, nama, label, ikon}]."""
    import re
    d = baca(folder)
    dasar = re.sub(r'[^A-Za-z0-9_-]+', '-', judul or 'slide').strip('-')[:60] or 'slide'
    hasil = []
    for jenis, dgn_suara, label, ikon, ekst in (('pdf', False, 'PDF', '&#128196;', 'pdf'),
                                                ('video', True, 'Video', '&#127916;', 'mp4')):
        if not d['izin'].get(jenis):
            continue
        if not os.path.isfile(_jalur(folder, jenis)):
            continue
        if d['tanda'].get(jenis) != _tanda(folder, dgn_suara):
            if jenis == 'pdf':
                try:
                    buat_pdf(folder)
                    d['tanda']['pdf'] = _tanda(folder, False)
                    _tulis(folder, d)
                except Exception:
                    continue
            else:
                continue
        hasil.append({'url': '%s%s/slide.%s' % (base_url, SUB, ekst), 'nama': '%s.%s' % (dasar, ekst),
                      'label': label, 'ikon': ikon})
    return hasil


def daftar_guru(folder, base_url, judul):
    """Semua file unduhan yang sudah dibuat (tanpa melihat izin siswa), untuk guru.
    Tiap item: {url, nama, label, ikon, basi}. basi=True kalau rekaman/slide berubah sejak file dibuat."""
    import re
    d = baca(folder)
    dasar = re.sub(r'[^A-Za-z0-9_-]+', '-', judul or 'slide').strip('-')[:60] or 'slide'
    hasil = []
    for jenis, dgn_suara, label, ikon, ekst in (('pdf', False, 'PDF', '&#128196;', 'pdf'),
                                                ('video', True, 'Video', '&#127916;', 'mp4')):
        if not os.path.isfile(_jalur(folder, jenis)):
            continue
        basi = d['tanda'].get(jenis) != _tanda(folder, dgn_suara)
        hasil.append({'url': '%s%s/slide.%s' % (base_url, SUB, ekst), 'nama': '%s.%s' % (dasar, ekst),
                      'label': label, 'ikon': ikon, 'basi': basi})
    return hasil
