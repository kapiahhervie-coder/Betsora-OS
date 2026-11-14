"""
Konversi file PowerPoint (.pptx dan sejenisnya) menjadi gambar PNG per slide.

Alur: PowerPoint --(LibreOffice)--> PDF --(PyMuPDF)--> slide-001.png, slide-002.png, ...

Kebutuhan di komputer/server:
  1. LibreOffice (gratis)  : https://www.libreoffice.org/download
  2. PyMuPDF               : pip install pymupdf

Pemakaian:
    from .slide_konversi import konversi_pptx, KonversiSlideError

    try:
        daftar_png = konversi_pptx(r"D:\\...\\materi.pptx", r"D:\\...\\media\\slides\\item_12")
    except KonversiSlideError as e:
        print(e)          # pesan sudah berbahasa Indonesia dan aman ditampilkan ke guru
"""
import glob
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

try:  # nama modul baru (PyMuPDF >= 1.24.3), dengan cadangan nama lama
    import pymupdf as _pymupdf
except ImportError:  # pragma: no cover
    try:
        import fitz as _pymupdf
    except ImportError:
        _pymupdf = None

EKSTENSI_DIDUKUNG = ('.pptx', '.ppt', '.ppsx', '.pps', '.odp')

_LOKASI_SOFFICE_WINDOWS = (
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
)


class KonversiSlideError(Exception):
    """Kesalahan konversi dengan pesan yang ramah untuk guru."""


def cari_soffice():
    """Cari program LibreOffice. Mengembalikan path-nya, atau None kalau tidak ada."""
    for nama in ('soffice', 'libreoffice', 'soffice.exe'):
        jalur = shutil.which(nama)
        if jalur:
            return jalur
    for jalur in _LOKASI_SOFFICE_WINDOWS:
        if os.path.exists(jalur):
            return jalur
    return None


def periksa_isi_file(jalur):
    """
    Pastikan isi file benar-benar presentasi, bukan hanya namanya berakhiran .pptx.
    (Tanpa ini LibreOffice akan menganggap file rusak sebagai teks biasa dan tetap membuat PDF.)
    """
    pesan = 'File PowerPoint tidak bisa dibaca. Pastikan file tidak rusak dan tidak diberi kata sandi.'
    kecil = jalur.lower()
    try:
        if kecil.endswith(('.pptx', '.ppsx')):
            if not zipfile.is_zipfile(jalur):
                raise KonversiSlideError(pesan)
            with zipfile.ZipFile(jalur) as z:
                if 'ppt/presentation.xml' not in z.namelist():
                    raise KonversiSlideError(pesan)
        elif kecil.endswith(('.ppt', '.pps')):
            with open(jalur, 'rb') as f:
                if f.read(8) != b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
                    raise KonversiSlideError(pesan)
        elif kecil.endswith('.odp'):
            if not zipfile.is_zipfile(jalur):
                raise KonversiSlideError(pesan)
            with zipfile.ZipFile(jalur) as z:
                if b'presentation' not in z.read('mimetype'):
                    raise KonversiSlideError(pesan)
    except (zipfile.BadZipFile, KeyError, OSError):
        raise KonversiSlideError(pesan)


def pptx_ke_pdf(jalur_pptx, folder_kerja, batas_waktu=240):
    """Ubah file PowerPoint menjadi PDF di folder_kerja. Mengembalikan path PDF."""
    soffice = cari_soffice()
    if not soffice:
        raise KonversiSlideError(
            'LibreOffice belum terpasang di komputer ini, jadi file PowerPoint belum bisa diubah '
            'menjadi slide. Pasang dari https://www.libreoffice.org/download lalu coba lagi.'
        )

    # Profil LibreOffice terpisah: mencegah bentrok jika ada konversi lain atau LibreOffice sedang terbuka.
    profil = tempfile.mkdtemp(prefix='lo_profil_')
    try:
        perintah = [
            soffice,
            '-env:UserInstallation=' + Path(profil).as_uri(),
            '--headless', '--norestore', '--convert-to', 'pdf',
            '--outdir', folder_kerja, jalur_pptx,
        ]
        try:
            proses = subprocess.run(perintah, capture_output=True, text=True, timeout=batas_waktu)
        except subprocess.TimeoutExpired:
            raise KonversiSlideError(
                'Mengubah PowerPoint menjadi slide memakan waktu terlalu lama. '
                'Coba file yang lebih kecil atau kurangi jumlah gambar besar di dalamnya.'
            )
    finally:
        shutil.rmtree(profil, ignore_errors=True)

    pdf = os.path.join(folder_kerja, Path(jalur_pptx).stem + '.pdf')
    if proses.returncode != 0 or not os.path.exists(pdf):
        raise KonversiSlideError(
            'File PowerPoint tidak bisa dibaca. Pastikan file tidak rusak dan tidak diberi kata sandi.'
        )
    return pdf


def pdf_ke_png(jalur_pdf, folder_out, lebar_px=1600, maks_slide=200):
    """Ubah tiap halaman PDF menjadi PNG. Mengembalikan daftar path PNG berurutan."""
    if _pymupdf is None:
        raise KonversiSlideError('Pustaka PyMuPDF belum terpasang. Jalankan: pip install pymupdf')

    dokumen = _pymupdf.open(jalur_pdf)
    try:
        if dokumen.page_count == 0:
            raise KonversiSlideError('File PowerPoint ini tidak memiliki slide.')
        if dokumen.page_count > maks_slide:
            raise KonversiSlideError(
                'Jumlah slide (%d) melebihi batas %d. Pecah menjadi beberapa file.' % (dokumen.page_count, maks_slide)
            )
        hasil = []
        for nomor, halaman in enumerate(dokumen, start=1):
            skala = lebar_px / halaman.rect.width
            gambar = halaman.get_pixmap(matrix=_pymupdf.Matrix(skala, skala), alpha=False)
            jalur = os.path.join(folder_out, 'slide-%03d.png' % nomor)
            gambar.save(jalur)
            hasil.append(jalur)
        return hasil
    finally:
        dokumen.close()


def konversi_pptx(jalur_pptx, folder_out, lebar_px=1600, maks_slide=200):
    """
    Ubah file PowerPoint menjadi gambar PNG per slide di folder_out.
    Slide lama di folder itu dihapus lebih dulu, jadi aman dipakai saat guru mengunggah ulang.
    Mengembalikan daftar path PNG sesuai urutan slide.
    """
    if not os.path.isfile(jalur_pptx):
        raise KonversiSlideError('File PowerPoint tidak ditemukan.')
    if not jalur_pptx.lower().endswith(EKSTENSI_DIDUKUNG):
        raise KonversiSlideError('Format file tidak didukung. Unggah file PowerPoint (.pptx atau .ppt).')
    periksa_isi_file(jalur_pptx)

    os.makedirs(folder_out, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='slide_') as kerja:
        pdf = pptx_ke_pdf(jalur_pptx, kerja)
        for lama in glob.glob(os.path.join(folder_out, 'slide-*.png')):
            os.remove(lama)
        return pdf_ke_png(pdf, folder_out, lebar_px=lebar_px, maks_slide=maks_slide)
