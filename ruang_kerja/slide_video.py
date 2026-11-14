"""
Mengambil video yang tertanam di file PowerPoint (.pptx) supaya bisa diputar di penampil slide.

Gambar slide hanya foto, jadi video ditemukan lewat isi file .pptx (yang sebenarnya berkas zip):
  - posisi video di slide dibaca dari XML slide
  - berkas videonya disalin ke folder slide item sebagai video-<slide>-<urutan>.<ekstensi>
  - daftar hasilnya ditulis di video.json (juga sebagai tanda bahwa pemeriksaan sudah dilakukan)

Video yang berupa tautan (misalnya YouTube) dicatat sebagai tautan.
"""
import glob
import json
import os
import posixpath
import shutil
import zipfile
import xml.etree.ElementTree as ET

NS_P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
NS_A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
NS_R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
NS_REL = 'http://schemas.openxmlformats.org/package/2006/relationships'

EKSTENSI_BROWSER = ('.mp4', '.m4v', '.webm', '.ogv', '.mov')
MAKS_BYTE_VIDEO = 400 * 1024 * 1024
NAMA_JSON = 'video.json'


def _rel_dari(z, bagian):
    """Baca file .rels milik sebuah bagian: {id: (target_lengkap_atau_url, eksternal)}."""
    folder, nama = posixpath.split(bagian)
    jalur = posixpath.join(folder, '_rels', nama + '.rels')
    hasil = {}
    try:
        akar = ET.fromstring(z.read(jalur))
    except KeyError:
        return hasil
    for r in akar.findall('{%s}Relationship' % NS_REL):
        target = r.get('Target', '')
        luar = r.get('TargetMode') == 'External'
        if not luar:
            target = target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join(folder, target))
        hasil[r.get('Id')] = (target, luar)
    return hasil


def _urutan_slide(z):
    """Daftar bagian slide sesuai urutan tampil, tanpa slide tersembunyi (LibreOffice tidak ikut mencetaknya)."""
    pres = 'ppt/presentation.xml'
    akar = ET.fromstring(z.read(pres))
    rel = _rel_dari(z, pres)
    daftar = akar.find('{%s}sldIdLst' % NS_P)
    hasil = []
    if daftar is None:
        return hasil, 9144000, 6858000
    for s in daftar.findall('{%s}sldId' % NS_P):
        rid = s.get('{%s}id' % NS_R)
        if rid in rel and not rel[rid][1]:
            hasil.append(rel[rid][0])
    ukuran = akar.find('{%s}sldSz' % NS_P)
    cx = int(ukuran.get('cx')) if ukuran is not None else 9144000
    cy = int(ukuran.get('cy')) if ukuran is not None else 6858000
    return hasil, cx or 9144000, cy or 6858000


def _kotak(pic, cx, cy):
    """Posisi video sebagai pecahan 0..1 dari lebar/tinggi slide. Kalau tidak ada, pakai seluruh slide."""
    xf = pic.find('{%s}spPr/{%s}xfrm' % (NS_P, NS_A))
    if xf is not None:
        off, ext = xf.find('{%s}off' % NS_A), xf.find('{%s}ext' % NS_A)
        if off is not None and ext is not None:
            x, y = int(off.get('x', 0)), int(off.get('y', 0))
            w, h = int(ext.get('cx', 0)), int(ext.get('cy', 0))
            if w > 0 and h > 0:
                return {'x': round(x / cx, 5), 'y': round(y / cy, 5), 'w': round(w / cx, 5), 'h': round(h / cy, 5)}
    return {'x': 0.0, 'y': 0.0, 'w': 1.0, 'h': 1.0}


def _tulis(folder, slides):
    with open(os.path.join(folder, NAMA_JSON), 'w', encoding='utf-8') as f:
        json.dump({'slides': slides}, f)


def ekstrak_video(jalur_pptx, folder_out):
    """Salin video dari pptx ke folder_out dan tulis video.json. Mengembalikan {nomor_slide: [video, ...]}."""
    os.makedirs(folder_out, exist_ok=True)
    for lama in glob.glob(os.path.join(folder_out, 'video-*')) + glob.glob(os.path.join(folder_out, NAMA_JSON)):
        try:
            os.remove(lama)
        except OSError:
            pass
    slides = {}
    try:
        with zipfile.ZipFile(jalur_pptx) as z:
            bagian_slide, cx, cy = _urutan_slide(z)
            nomor = 0
            for bagian in bagian_slide:
                akar = ET.fromstring(z.read(bagian))
                if akar.get('show') == '0':
                    continue
                nomor += 1
                rel = _rel_dari(z, bagian)
                urut = 0
                for pic in akar.iter('{%s}pic' % NS_P):
                    vf = pic.find('.//{%s}videoFile' % NS_A)
                    if vf is None:
                        continue
                    rid = vf.get('{%s}link' % NS_R)
                    if rid not in rel:
                        continue
                    target, luar = rel[rid]
                    item = _kotak(pic, cx, cy)
                    if luar:
                        item.update({'t': 'link', 'u': target})
                    else:
                        ext = posixpath.splitext(target)[1].lower()
                        if ext not in EKSTENSI_BROWSER:
                            item.update({'t': 'tidakdukung', 'e': ext or '?'})
                        else:
                            try:
                                info = z.getinfo(target)
                            except KeyError:
                                continue
                            if info.file_size > MAKS_BYTE_VIDEO:
                                item.update({'t': 'tidakdukung', 'e': 'terlalu besar'})
                            else:
                                urut += 1
                                nama = 'video-%03d-%d%s' % (nomor, urut, ext)
                                with z.open(target) as sumber, open(os.path.join(folder_out, nama), 'wb') as tujuan:
                                    shutil.copyfileobj(sumber, tujuan)
                                item.update({'t': 'file', 'f': nama})
                    slides.setdefault(str(nomor), []).append(item)
    except (zipfile.BadZipFile, KeyError, ET.ParseError, OSError):
        slides = {}
    _tulis(folder_out, slides)
    return slides
