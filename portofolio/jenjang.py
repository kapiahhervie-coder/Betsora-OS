"""Penentuan tema portofolio per jenjang dan perhitungan ringkasan/lencana.

Semua fungsi di sini murni (tidak menyentuh database) dan dihitung dari data yang
sudah ada, jadi tidak diperlukan migrasi. Ubah angka di bagian atas jika kebijakan
sekolah berbeda.
"""
import re

# Poin Keaktifan yang dianggap "tercapai" (bilah kemajuan penuh dan lencana Pejuang Aktif).
TARGET_POIN = 100
# Ambang lencana.
AMBANG_HADIR = 90      # persen kehadiran
AMBANG_NILAI = 85      # rata-rata nilai
AMBANG_KARYA = 3       # jumlah karya untuk lencana "Kreator Handal"

JENJANG = ('sd', 'smp', 'sma')
JENJANG_BAWAAN = 'sd'  # dipakai bila teks kelas tidak bisa dibaca

# Urutan penting: yang lebih panjang lebih dulu agar "VIIA" terbaca VII, bukan V.
_ROMAWI = (
    ('XII', 12), ('VIII', 8), ('VII', 7), ('XI', 11), ('III', 3), ('IX', 9),
    ('VI', 6), ('IV', 4), ('II', 2), ('I', 1), ('X', 10), ('V', 5),
)


def angka_kelas(kelas):
    """Angka tingkat dari teks kelas: '3' -> 3, '3A' -> 3, '10 IPA' -> 10, 'VII B' -> 7.

    Mengembalikan None bila tidak terbaca.
    """
    teks = (kelas or '').strip().upper()
    teks = re.sub(r'^KELAS\s*', '', teks)
    m = re.match(r'^(\d{1,2})', teks)
    if m:
        return int(m.group(1))
    for romawi, nilai in _ROMAWI:
        if teks.startswith(romawi):
            return nilai
    return None


def jenjang_dari_kelas(kelas):
    """'sd' (1-6), 'smp' (7-9), atau 'sma' (10-12)."""
    n = angka_kelas(kelas)
    if n is None:
        return JENJANG_BAWAAN
    if n <= 6:
        return 'sd'
    if n <= 9:
        return 'smp'
    return 'sma'


def ringkas_nilai(daftar_nilai):
    """Rata-rata per mata pelajaran dari daftar Nilai (sudah select_related('sesi'))."""
    per_mapel = {}
    for n in daftar_nilai:
        d = per_mapel.setdefault(n.sesi.mapel, {'mapel': n.sesi.mapel, 'jumlah': 0, 'total': 0.0})
        d['jumlah'] += 1
        d['total'] += float(n.skor)
    hasil = []
    for d in sorted(per_mapel.values(), key=lambda x: x['mapel'].lower()):
        rata = d['total'] / d['jumlah']
        hasil.append({
            'mapel': d['mapel'],
            'jumlah': d['jumlah'],
            'rata': round(rata, 1),
            'lebar': max(0, min(100, int(round(rata)))),
        })
    return hasil


def tren_nilai(daftar_nilai, banyak=8):
    """Skor terbaru (urut lama -> baru) beserta tinggi batang 0-100 untuk grafik mini.

    `daftar_nilai` diurutkan terbaru dulu, seperti hasil query di view.
    """
    terbaru = list(daftar_nilai)[:banyak]
    return [
        {'skor': float(n.skor), 'tinggi': max(4, min(100, int(round(float(n.skor))))), 'topik': n.sesi.topik}
        for n in reversed(terbaru)
    ]


def persen_poin(total_poin):
    if TARGET_POIN <= 0:
        return 0
    return max(0, min(100, int(total_poin * 100 // TARGET_POIN)))


def hitung_lencana(kehadiran, total_hari, avg_nilai, total_poin, jumlah_karya, ada_refleksi):
    """Daftar lencana beserta status diraih atau belum (tanpa tabel baru)."""
    return [
        {'kode': 'hadir', 'nama': 'Rajin Hadir', 'ikon': '📅',
         'ket': f'Kehadiran {AMBANG_HADIR}% atau lebih',
         'diraih': total_hari > 0 and kehadiran >= AMBANG_HADIR},
        {'kode': 'nilai', 'nama': 'Bintang Nilai', 'ikon': '⭐',
         'ket': f'Rata-rata nilai {AMBANG_NILAI} atau lebih',
         'diraih': avg_nilai is not None and avg_nilai >= AMBANG_NILAI},
        {'kode': 'aktif', 'nama': 'Pejuang Aktif', 'ikon': '⚡',
         'ket': f'Mengumpulkan {TARGET_POIN} poin keaktifan',
         'diraih': total_poin >= TARGET_POIN},
        {'kode': 'karya1', 'nama': 'Karya Pertama', 'ikon': '🎨',
         'ket': 'Mengunggah karya pertama',
         'diraih': jumlah_karya >= 1},
        {'kode': 'karya3', 'nama': 'Kreator Handal', 'ikon': '🏆',
         'ket': f'Mengunggah {AMBANG_KARYA} karya',
         'diraih': jumlah_karya >= AMBANG_KARYA},
        {'kode': 'refleksi', 'nama': 'Pemikir', 'ikon': '💭',
         'ket': 'Menulis refleksi pada sebuah karya',
         'diraih': bool(ada_refleksi)},
    ]
