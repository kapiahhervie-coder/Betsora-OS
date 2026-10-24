"""Ringkasan misi dunia nyata untuk halaman portofolio.

Hanya MEMBACA data app misi dan tidak membutuhkan migrasi. Yang ditampilkan sengaja sama
dengan rapor (misi/ringkasan.py): judul, kategori, tanggal konfirmasi, dan nilai. Isi
refleksi, catatan, dan foto siswa TIDAK ikut, karena itu hanya boleh dibuka lewat halaman
misi yang punya aturan izin sendiri.

Bila app misi tidak terpasang, fungsi mengembalikan None dan portofolio tampil seperti biasa.
"""
from django.apps import apps

MAKS_DAFTAR = 6


def _nama_level(jumlah, daftar_level):
    for batas, nama in daftar_level:
        if jumlah >= batas:
            return nama
    return daftar_level[-1][1]


def ringkasan_misi(siswa):
    if not apps.is_installed('misi'):
        return None
    from misi.models import PengerjaanMisi

    semua = list(PengerjaanMisi.objects.filter(siswa=siswa).select_related('misi'))
    selesai = [p for p in semua if p.status == PengerjaanMisi.SELESAI]
    selesai.sort(key=lambda p: (p.dikonfirmasi_pada is None, p.dikonfirmasi_pada or p.mulai_pada), reverse=True)

    nilai = [float(p.nilai) for p in selesai if p.nilai is not None]
    per_kategori = {}
    for p in selesai:
        nama = p.misi.get_kategori_display()
        per_kategori[nama] = per_kategori.get(nama, 0) + 1

    return {
        'total_selesai': len(selesai),
        'menunggu': sum(1 for p in semua if p.status == PengerjaanMisi.MENUNGGU),
        'berjalan': sum(1 for p in semua if p.status == PengerjaanMisi.BERJALAN),
        'level': _nama_level(len(selesai), PengerjaanMisi.LEVEL),
        'rata2_nilai': round(sum(nilai) / len(nilai), 1) if nilai else None,
        'per_kategori': sorted(per_kategori.items(), key=lambda x: (-x[1], x[0])),
        'daftar': [
            {
                'judul': p.misi.judul,
                'kategori': p.misi.get_kategori_display(),
                'emoji': p.misi.emoji_kartu,
                'tanggal': p.dikonfirmasi_pada,
                'nilai': p.nilai,
            }
            for p in selesai[:MAKS_DAFTAR]
        ],
    }
