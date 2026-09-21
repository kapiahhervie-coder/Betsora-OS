"""
Draf narasi rapor dari skor rubrik Tugas Kreasi.

Aturannya sengaja sederhana dan bisa diperiksa guru (tanpa AI, tanpa menebak dari
foto/suara). Kalimatnya berasal dari deskriptor per dimensi per level yang bisa
diedit di halaman admin, jadi gaya bahasa sekolah tinggal disesuaikan di sana.

Pilihan yang dipakai (ubah di sini bila sekolah ingin lain):
  * Level sebuah dimensi   = rata-rata level dari SEMUA karya yang dinilai di ruang kerja
                             ini, dibulatkan setengah ke atas (2,5 menjadi 3).
  * Kekuatan               = dimensi berlevel 3-4, paling tinggi dulu, maksimal MAKS_KEKUATAN.
  * Area berkembang        = dimensi berlevel 1-2, paling rendah dulu, maksimal MAKS_TUMBUH.
  * Perkembangan           = level naik minimal 1 antara karya pertama dan terakhir.
  * Refleksi               = emoji terakhir (SD 1-3) atau penanda bahwa siswa menulis refleksi.
  * Keaktifan (poin)       = TIDAK dipakai: belum ada periode dan skala yang ditetapkan sekolah.
"""
from ruang_kerja.models import SubmisiTugas

from .fase_config import get_config
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


def susun_narasi_kreasi(ruang, siswa):
    """Kembalikan paragraf narasi, atau '' bila belum ada skor rubrik untuk siswa ini di ruang kerja ini."""
    jenjang = ruang.get_jenjang()
    if not jenjang or get_config(jenjang) is None:
        return ''

    skor = list(
        SkorDimensi.objects.filter(
            submisi__siswa=siswa, submisi__tugas__ruang_kerja=ruang, submisi__tugas__jenis='kreasi',
            dimensi__jenjang=jenjang, dimensi__aktif=True,
        ).select_related('dimensi', 'submisi').order_by('submisi__dikirim_pada', 'id')
    )
    if not skor:
        return ''

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
    if not baris:
        return ''

    kuat = sorted((b for b in baris if b['level'] >= LEVEL_KUAT), key=lambda b: (-b['level'], b['dimensi'].urutan))[:MAKS_KEKUATAN]
    tumbuh = sorted((b for b in baris if b['level'] < LEVEL_KUAT), key=lambda b: (b['level'], b['dimensi'].urutan))[:MAKS_TUMBUH]
    naik = sorted((b for b in baris if len(b['levels']) >= 2 and b['levels'][-1] - b['levels'][0] >= 1),
                  key=lambda b: (-(b['levels'][-1] - b['levels'][0]), b['dimensi'].urutan))[:MAKS_TREN]

    n_karya = len({sk.submisi_id for sk in skor})
    teks = [f'{nama} telah menyelesaikan {n_karya} karya kreasi yang dinilai pada periode ini.']

    for i, b in enumerate(kuat):
        teks.append(_sambung('Selain itu, ' if i else '', b['kalimat'], nama))
    for i, b in enumerate(tumbuh):
        awalan = ('Selain itu, ' if i else ('Pada aspek lain, ' if kuat else ''))
        teks.append(_sambung(awalan, b['kalimat'], nama))

    if naik:
        teks.append('Perkembangan yang menggembirakan terlihat pada aspek '
                    + _gabung_nama([b['dimensi'].nama for b in naik]) + '.')

    refleksi = list(RefleksiKarya.objects.filter(
        submisi__siswa=siswa, submisi__tugas__ruang_kerja=ruang, submisi__tugas__jenis='kreasi',
    ).order_by('-submisi__dikirim_pada', '-id'))
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
