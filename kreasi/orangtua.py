"""
Data karya & catatan guru untuk dashboard ORANG TUA.

Aturan akses (satu-satunya tempat yang memutuskan siapa boleh melihat apa di sini):
  * hanya akun ber-role 'orangtua' yang terhubung ke seorang anak (User.anak);
  * yang ditampilkan SELALU anak dari akun yang sedang login, tidak pernah dari parameter;
  * hanya-baca;
  * catatan rapor yang tampil hanya yang SUDAH DISIMPAN guru. Draf otomatis tidak pernah
    sampai ke sini (draf hanya dibuat di halaman rapor guru).
"""
from ruang_kerja.models import CatatanRapor, SubmisiTugas

from .fase_config import get_config
from .layanan import ringkas_refleksi
from .models import DeskriptorLevel, RefleksiKarya, SkorDimensi

BATAS_KARYA = 5    # karya terbaru yang ditampilkan; sisanya lewat ?semua_karya=1 (foto asli dimuat penuh)


def _nama_depan(siswa):
    return siswa.nama.split()[0] if siswa.nama else siswa.nama


def ringkasan_untuk_orangtua(user, semua=False):
    """Kembalikan dict siap tampil, atau None bila `user` bukan orang tua yang terhubung ke seorang anak."""
    if not (getattr(user, 'is_authenticated', False) and getattr(user, 'role', None) == 'orangtua' and user.anak_id):
        return None
    siswa = user.anak
    nama = _nama_depan(siswa)

    qs = (SubmisiTugas.objects.filter(siswa=siswa, tugas__jenis='kreasi')
          .select_related('tugas__ruang_kerja').prefetch_related('lampiran_karya')
          .order_by('-dikirim_pada', '-id'))
    total = qs.count()
    subs = list(qs if semua else qs[:BATAS_KARYA])

    refleksi_map = {r.submisi_id: r for r in RefleksiKarya.objects.filter(submisi__in=subs)}
    skor_map = {}
    for sk in SkorDimensi.objects.filter(submisi__in=subs, dimensi__aktif=True).select_related('dimensi'):
        skor_map.setdefault(sk.submisi_id, []).append(sk)
    kalimat = {(d.dimensi_id, d.level): d.untuk(nama)
               for d in DeskriptorLevel.objects.filter(dimensi_id__in={sk.dimensi_id for l in skor_map.values() for sk in l})}

    ruang_map = {}   # urutan kemunculan = urutan karya terbaru dulu
    ada_tautan = False
    for sub in subs:
        ruang = sub.tugas.ruang_kerja
        cfg = get_config(ruang.get_jenjang())
        lampiran = list(sub.lampiran_karya.all())
        ada_tautan = ada_tautan or any(l.tipe == 'link' for l in lampiran)
        rows = [{'nama': sk.dimensi.nama, 'urutan': sk.dimensi.urutan, 'level': sk.level, 'label': sk.label_level,
                 'kalimat': kalimat.get((sk.dimensi_id, sk.level), ''), 'catatan': sk.catatan}
                for sk in skor_map.get(sub.id, [])]
        rows.sort(key=lambda r: r['urutan'])
        ruang_map.setdefault(ruang.id, {'ruang': ruang, 'karya': [], 'catatan': None})['karya'].append({
            'submisi': sub, 'tugas': sub.tugas, 'lampiran_list': lampiran,
            'refleksi': ringkas_refleksi(refleksi_map.get(sub.id), cfg) if cfg else None,
            'skor_rows': rows, 'feedback': sub.feedback,
        })

    for c in CatatanRapor.objects.filter(siswa=siswa).select_related('ruang_kerja'):
        isi = [(judul, teks) for judul, teks in (
            ('Catatan Akademik', c.catatan), ('Disiplin & Kebiasaan Belajar', c.catatan_disiplin),
            ('Fisik & Motorik', c.catatan_fisik_motorik)) if teks and teks.strip()]
        if isi:
            ruang_map.setdefault(c.ruang_kerja_id, {'ruang': c.ruang_kerja, 'karya': [], 'catatan': None})['catatan'] = isi

    return {
        'siswa': siswa, 'nama_depan': nama, 'ruang_list': list(ruang_map.values()),
        'total_karya': total, 'ditampilkan': len(subs), 'ada_lebih': total > len(subs),
        'semua': semua, 'bisa_diringkas': semua and total > BATAS_KARYA,
        'ada_tautan': ada_tautan,
    }
