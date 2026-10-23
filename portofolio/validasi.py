"""Aturan unggahan karya siswa. Ubah angka di sini jika kebijakan sekolah berbeda."""
import os

# 20 MB. Batas server web (mis. nginx client_max_body_size) harus sama atau lebih besar.
UKURAN_MAKS_BYTE = 20 * 1024 * 1024

# SVG dan HTML sengaja tidak diizinkan: keduanya bisa memuat skrip.
EKSTENSI_DIIZINKAN = {
    "jpg", "jpeg", "png", "gif", "webp",
    "pdf", "txt",
    "doc", "docx", "ppt", "pptx", "xls", "xlsx",
    "mp3", "mp4", "webm",
}


def accept_html():
    """Nilai atribut accept= untuk <input type=file>."""
    return ",".join("." + e for e in sorted(EKSTENSI_DIIZINKAN))


def cek_file_karya(file):
    """Kembalikan pesan galat (str) jika file ditolak, atau None jika boleh."""
    ekstensi = os.path.splitext(file.name)[1].lower().lstrip(".")
    if ekstensi not in EKSTENSI_DIIZINKAN:
        return "Jenis file tidak diizinkan. Gunakan: " + ", ".join(sorted(EKSTENSI_DIIZINKAN)) + "."
    if file.size > UKURAN_MAKS_BYTE:
        return f"Ukuran file maksimal {UKURAN_MAKS_BYTE / (1024 * 1024):g} MB."
    return None
