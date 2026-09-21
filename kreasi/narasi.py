"""
Draf narasi rapor dari skor rubrik Tugas Kreasi.

Aturannya sengaja sederhana dan bisa diperiksa guru (tanpa AI, tanpa menebak dari
foto/suara). Kalimatnya berasal dari deskriptor per dimensi per level yang bisa
diedit di halaman admin, jadi gaya bahasa sekolah tinggal disesuaikan di sana.

Hasilnya dipisah per BIDANG sesuai kolom di halaman rapor:
  * akademik      -> "Catatan Akademik"
  * fisik_motorik -> "Fisik & Motorik" (dimensi yang dipetakan di fase_config.BIDANG_DIMENSI,
                     saat ini: Motorik Halus)

Pilihan yang dipakai (ubah di sini bila sekolah ingin lain):
  * Level sebuah dimensi   = rata-rata level dari SEMUA karya yang dinilai di ruang kerja
                             ini, dibulatkan setengah ke atas (2,5 menjadi 3).
  * Kekuatan (akademik)    = dimensi berlevel 3-4, paling tinggi dulu, maksimal MAKS_KEKUATAN.
  * Area berkembang        = dimensi berlevel 1-2, paling rendah dulu, maksimal MAKS_TUMBUH.
  * Perkembangan           = level naik minimal 1 antara karya pertama dan terakhir.
  * Refleksi (akademik)    = emoji terakhir (SD 1-3) atau penanda bahwa siswa menulis refleksi.
  * Fisik & motorik        = kalimat tiap dimensinya apa adanya (tanpa pembuka/penutup).
  * Keaktifan (poin)       = TIDAK dipakai: belum ada periode dan skala yang ditetapkan sekolah.
"""
from .fase_config import BIDANG_AKADEMIK, BIDANG_DIMENSI, BIDANG_FISIK_MOTORIK, get_config
from .models import DeskriptorLevel, RefleksiKarya, SkorDimensi

MAKS_KEKUATAN = 2
MAKS_TUMBUH = 2
LEVEL_KUAT = 3          # level >= ini dianggap kekuatan
MAKS_TREN = 2

_KALIMAT_EMOJI = {
    'bangga': '{nama} mengungkapkan rasa bangga terhadap karya yang dibuatnya.',
    'senang': '{nama} merasa senang saat berkarya.',
    'sulit': '{nama} dengan jujur menyampaikan bahwa berkarya terasa agak sulit baginya, '
             'sehingga pendampingan akan sangat membantu.',
    'bingung': '{nama} dengan jujur menyampaikan bahwa ia masih merasa bingung saat berkarya, '
               'sehingga pendampingan akan sangat membantu.',
}


def _level_rata(levels):
    """Rata-rata dibulatkan setengah ke atas, dengan bilangan bulat (tanpa kesalahan float)."""
    n = len(levels)
    return (2 * sum(levels) + n) // (2 * n)


def _sambung(awalan, kalimat, nama):
    """Awali kalimat dengan `awalan`; huruf pertama dikecilkan kecuali kalimat diawali nama siswa."""
    if not awalan:
        return kalimat
    isi = kalimat if kalimat.startswith(nama) else kalimat[:1].lower() + kalimat[1:]
    return f'{awalan}{isi}'


def _gabung_nama(daftar):
    daftar = [d.lower() for d in daftar]
    return daftar[0] if len(daftar) == 1 else ' dan '.join(daftar)


def _bidang(baris):
    return BIDANG_DIMENSI.get(baris['dimensi'].kode, BIDANG_AKADEMIK)


def _yang_naik(baris):
    return sorted((b for b in baris if len(b['levels']) >= 2 and b['levels'][-1] - b['levels'][0] >= 1),
                  key=lambda b: (-(b['levels'][-1] - b['levels'][0]), b['dimensi'].urutan))[:MAKS_TREN]


def _kalimat_perkembangan(naik):
    return 'Perkembangan yang menggembirakan terlihat pada aspek ' + _gabung_nama([b['dimensi'].nama for b in naik]) + '.'


def _teks_fisik_motorik(baris, nama):
    baris = sorted(baris, key=lambda b: b['dimensi'].urutan)
    teks = [b['kalimat'] if i == 0 else _sambung('Selain itu, ', b['kalimat'], nama) for i, b in enumerate(baris)]
    naik = _yang_naik(baris)
    if naik:
        teks.append(_kalimat_perkembangan(naik))
    return ' '.join(teks)


def _teks_akademik(baris, n_karya, refleksi, nama):
    kuat = sorted((b for b in baris if b['level'] >= LEVEL_KUAT), key=lambda b: (-b['level'], b['dimensi'].urutan))[:MAKS_KEKUATAN]
    tumbuh = sorted((b for b in baris if b['level'] < LEVEL_KUAT), key=lambda b: (b['level'], b['dimensi'].urutan))[:MAKS_TUMBUH]

    teks = [f'{nama} telah menyelesaikan {n_karya} karya kreasi yang dinilai pada periode ini.']
    for i, b in enumerate(kuat):
        teks.append(_sambung('Selain itu, ' if i else '', b['kalimat'], nama))
    for i, b in enumerate(tumbuh):
        awalan = 'Selain itu, ' if i else ('Pada aspek lain, ' if kuat else '')
        teks.append(_sambung(awalan, b['kalimat'], nama))

    naik = _yang_naik(baris)
    if naik:
        teks.append(_kalimat_perkembangan(naik))

    emoji = next((r.emoji for r in refleksi if r.emoji in _KALIMAT_EMOJI), None)
    if emoji:
        teks.append(_KALIMAT_EMOJI[emoji].replace('{nama}', nama))
    elif any(r.jawaban for r in refleksi):
        teks.append(f'{nama} juga membiasakan diri merefleksikan proses berkaryanya melalui tulisan.')

    if tumbuh:
        teks.append(f'Harapannya, {nama} terus berlatih dan berani mencoba, dengan dukungan guru dan orang tua di rumah.')
    else:
        teks.append(f'Harapannya, {nama} terus mempertahankan semangat berkarya dan berani menerima tantangan yang lebih besar.')
    return ' '.join(teks)


def susun_narasi_bidang(ruang, siswa):
    """
    Kembalikan {'akademik': str, 'fisik_motorik': str}. Nilainya '' bila tidak ada bahan
    (belum ada skor rubrik untuk bidang itu di ruang kerja ini).
    """
    hasil = {BIDANG_AKADEMIK: '', BIDANG_FISIK_MOTORIK: ''}
    jenjang = ruang.get_jenjang()
    if not jenjang or get_config(jenjang) is None:
        return hasil

    skor = list(
        SkorDimensi.objects.filter(
            submisi__siswa=siswa, submisi__tugas__ruang_kerja=ruang, submisi__tugas__jenis='kreasi',
            dimensi__jenjang=jenjang, dimensi__aktif=True,
        ).select_related('dimensi', 'submisi').order_by('submisi__dikirim_pada', 'id')
    )
    if not skor:
        return hasil

    nama = siswa.nama.split()[0] if siswa.nama else siswa.nama

    per_dimensi = {}
    for sk in skor:
        per_dimensi.setdefault(sk.dimensi_id, {'dimensi': sk.dimensi, 'levels': []})['levels'].append(sk.level)

    kalimat_level = {
        (d.dimensi_id, d.level): d.untuk(nama)
        for d in DeskriptorLevel.objects.filter(dimensi_id__in=per_dimensi.keys())
    }
    baris = []
    for data in per_dimensi.values():
        level = _level_rata(data['levels'])
        kalimat = kalimat_level.get((data['dimensi'].id, level), '')
        if not kalimat:
            continue                       # deskriptor dihapus admin: lewati, jangan mengarang
        baris.append({'dimensi': data['dimensi'], 'level': level, 'kalimat': kalimat, 'levels': data['levels']})

    baris_akademik = [b for b in baris if _bidang(b) == BIDANG_AKADEMIK]
    baris_fisik = [b for b in baris if _bidang(b) == BIDANG_FISIK_MOTORIK]

    if baris_fisik:
        hasil[BIDANG_FISIK_MOTORIK] = _teks_fisik_motorik(baris_fisik, nama)
    if baris_akademik:
        refleksi = list(RefleksiKarya.objects.filter(
            submisi__siswa=siswa, submisi__tugas__ruang_kerja=ruang, submisi__tugas__jenis='kreasi',
        ).order_by('-submisi__dikirim_pada', '-id'))
        n_karya = len({sk.submisi_id for sk in skor})
        hasil[BIDANG_AKADEMIK] = _teks_akademik(baris_akademik, n_karya, refleksi, nama)
    return hasil


def susun_narasi_kreasi(ruang, siswa):
    """Bagian AKADEMIK saja (untuk kolom Catatan Akademik). '' bila belum ada skor rubrik."""
    return susun_narasi_bidang(ruang, siswa)[BIDANG_AKADEMIK]
