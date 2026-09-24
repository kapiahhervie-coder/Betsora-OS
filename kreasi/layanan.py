"""
Logika pengumpulan Tugas Kreasi: validasi masukan, penyimpanan atomik, dan
penyusunan tampilan refleksi. Dipisah dari view agar mudah diuji.
"""
import os

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import IntegrityError, transaction

from ruang_kerja.models import SubmisiTugas

from .fase_config import (
    BATAS_RINGKASAN, BATAS_TEKS, MAKS_LAMPIRAN_PER_TIPE, MAKS_LINK, MAKS_UKURAN_MB,
    TIPE_ACCEPT, TIPE_LABEL,
)
from .models import LampiranKarya, RefleksiKarya

_URL = URLValidator(schemes=['http', 'https'])  # blokir javascript:, ftp:, dll.


class KesalahanForm(Exception):
    def __init__(self, pesan):
        self.pesan = list(pesan)
        super().__init__('; '.join(self.pesan))


# ------------------------------------------------------------------ bentuk formulir

def kolom_unggah(cfg):
    """Kolom unggah berkas untuk template, sesuai jenjang."""
    kolom = []
    for tipe in cfg['tipe_lampiran']:
        if tipe == 'link':
            continue
        kolom.append({
            'tipe': tipe,
            'label': TIPE_LABEL[tipe],
            'nama': f'lampiran_{tipe}',
            'accept': TIPE_ACCEPT[tipe],
            'multiple': tipe != 'audio',        # satu rekaman suara per karya
            'wajib': tipe in cfg['wajib_lampiran'],
            'rekam': tipe == 'audio',
            'batas_mb': MAKS_UKURAN_MB[tipe],
        })
    return kolom


# ------------------------------------------------------------------ validasi

def _cek_berkas(f, tipe, galat):
    if f.size == 0:
        galat.append(f'Berkas "{f.name}" kosong.')
    elif f.size > MAKS_UKURAN_MB[tipe] * 1024 * 1024:
        galat.append(f'Berkas "{f.name}" terlalu besar (maksimal {MAKS_UKURAN_MB[tipe]} MB).')
    elif LampiranKarya.deteksi_tipe(f.name, tipe) != tipe:
        galat.append(f'Berkas "{f.name}" bukan jenis {TIPE_LABEL[tipe].lower()} yang diizinkan.')
    else:
        return True
    return False


def _baca_refleksi(cfg_ref, post, files, galat):
    tipe = cfg_ref['tipe']
    emoji, jawaban, audio = '', {}, None

    if tipe == 'emoji_suara':
        kunci = {k for k, _, _ in cfg_ref['emoji']}
        emoji = post.get('refleksi_emoji', '')
        if emoji not in kunci:
            galat.append('Pilih dulu perasaanmu setelah membuat karya.')
            emoji = ''
        audio = files.get('refleksi_audio')
        if audio and not _cek_berkas(audio, 'audio', galat):
            audio = None

    elif tipe in ('teks_terbimbing', 'metakognitif'):
        for kode, label in cfg_ref['pertanyaan']:
            teks = post.get(f'refleksi_{kode}', '').strip()
            if not teks:
                galat.append(f'Jawab pertanyaan refleksi: "{label}"')
            jawaban[kode] = teks[:BATAS_TEKS]

    elif tipe == 'matriks':
        for kode, label in cfg_ref['kriteria']:
            try:
                skor = int(post.get(f'refleksi_{kode}_skor', ''))
            except ValueError:
                skor = None
            if skor not in (1, 2, 3, 4):
                galat.append(f'Beri nilai 1-4 untuk "{label}".')
                skor = None
            jawaban[kode] = {
                'skor': skor,
                'alasan': post.get(f'refleksi_{kode}_alasan', '').strip()[:BATAS_TEKS],
            }
    return emoji, jawaban, audio


# ------------------------------------------------------------------ penyimpanan

def proses_pengumpulan(tugas, siswa, cfg, post, files):
    """Validasi lalu simpan karya + refleksi secara atomik. Raise KesalahanForm bila ada yang salah."""
    galat, unggahan, tautan = [], [], []

    for tipe in cfg['tipe_lampiran']:
        if tipe == 'link':
            continue
        daftar = files.getlist(f'lampiran_{tipe}')
        if len(daftar) > MAKS_LAMPIRAN_PER_TIPE:
            galat.append(f'{TIPE_LABEL[tipe]}: maksimal {MAKS_LAMPIRAN_PER_TIPE} berkas.')
            continue
        for f in daftar:
            if _cek_berkas(f, tipe, galat):
                unggahan.append((tipe, f))

    if 'link' in cfg['tipe_lampiran']:
        for u in post.getlist('lampiran_link')[:MAKS_LINK]:
            u = u.strip()
            if not u:
                continue
            try:
                _URL(u)
                tautan.append(u[:500])
            except ValidationError:
                galat.append(f'Tautan tidak valid: "{u[:60]}" (harus diawali http:// atau https://).')

    punya = {t for t, _ in unggahan} | ({'link'} if tautan else set())
    for tipe in cfg['wajib_lampiran']:
        if tipe not in punya:
            galat.append(f'Karya harus menyertakan {TIPE_LABEL[tipe].lower()}.')

    ringkasan = post.get('ringkasan', '').strip()[:BATAS_RINGKASAN]
    if cfg.get('butuh_ringkasan') and not ringkasan:
        galat.append('Tulis rangkuman singkat tentang karyamu.')
    if not unggahan and not tautan and not ringkasan:
        galat.append('Tambahkan minimal satu karya (berkas atau tautan) atau tulis ringkasannya.')

    emoji, jawaban, audio_refleksi = _baca_refleksi(cfg['refleksi'], post, files, galat)

    if galat:
        raise KesalahanForm(dict.fromkeys(galat))  # buang duplikat, urutan terjaga

    tersimpan = []  # untuk membersihkan berkas bila transaksi gagal
    try:
        with transaction.atomic():
            try:
                submisi = SubmisiTugas.objects.create(tugas=tugas, siswa=siswa, teks_jawaban=ringkasan)
            except IntegrityError:
                raise KesalahanForm(['Tugas ini sudah pernah dikumpulkan.'])
            urutan = 0
            for tipe, f in unggahan:
                tersimpan.append(LampiranKarya.objects.create(
                    submisi=submisi, tipe=tipe, file=f,
                    nama_asli=os.path.basename(f.name)[:255], urutan=urutan))
                urutan += 1
            for u in tautan:
                tersimpan.append(LampiranKarya.objects.create(
                    submisi=submisi, tipe='link', url=u, urutan=urutan))
                urutan += 1
            tersimpan.append(RefleksiKarya.objects.create(
                submisi=submisi, tipe=cfg['refleksi']['tipe'], emoji=emoji,
                jawaban=jawaban, audio=audio_refleksi))

            try:
                from portofolio.models import KaryaSiswa
                item_lampiran = [obj for obj in tersimpan if isinstance(obj, LampiranKarya)]
                if item_lampiran:
                    for i, lp in enumerate(item_lampiran, start=1):
                        if len(item_lampiran) == 1:
                            judul_karya = tugas.judul[:150]
                        else:
                            judul_karya = (tugas.judul + ' (' + str(i) + '/' + str(len(item_lampiran)) + ')')[:150]
                        KaryaSiswa.objects.create(
                            siswa=siswa,
                            judul=judul_karya,
                            deskripsi='Tugas Kreasi: ' + tugas.ruang_kerja.mapel,
                            file=lp.file.name if lp.file else '',
                            video_url=lp.url if lp.tipe == 'link' else '',
                            dibagikan=False,
                            refleksi=ringkasan,
                        )
                else:
                    KaryaSiswa.objects.create(
                        siswa=siswa,
                        judul=tugas.judul[:150],
                        deskripsi='Tugas Kreasi: ' + tugas.ruang_kerja.mapel,
                        refleksi=ringkasan,
                    )
            except Exception:
                pass
    except Exception:
        for obj in tersimpan:  # basis data sudah di-rollback; hapus berkas yatim
            berkas = getattr(obj, 'file', None) or getattr(obj, 'audio', None)
            if berkas:
                berkas.delete(save=False)
        raise
    return submisi


# ------------------------------------------------------------------ tampilan

def ringkas_refleksi(refleksi, cfg):
    """Ubah RefleksiKarya menjadi struktur siap tampil (label pertanyaan, glyph emoji, dst.)."""
    if refleksi is None:
        return None
    ref = cfg['refleksi']
    hasil = {'tipe': refleksi.tipe, 'emoji': None, 'butir': [], 'audio_url': refleksi.url_audio,
             'transkrip': refleksi.transkrip}
    if refleksi.emoji:
        for kunci, glyph, label in ref.get('emoji', []):
            if kunci == refleksi.emoji:
                hasil['emoji'] = {'glyph': glyph, 'label': label}
    for kode, label in ref.get('pertanyaan', []):
        hasil['butir'].append({'label': label, 'teks': refleksi.jawaban.get(kode, '')})
    for kode, label in ref.get('kriteria', []):
        j = refleksi.jawaban.get(kode) or {}
        hasil['butir'].append({'label': label, 'skor': j.get('skor'), 'teks': j.get('alasan', '')})
    return hasil
