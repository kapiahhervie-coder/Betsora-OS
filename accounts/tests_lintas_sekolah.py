"""Tahap 5 - uji lintas sekolah menyeluruh (gerbang sebelum sekolah kedua didaftarkan).

Dua sekolah (Alfa dan Beta) diisi data bertanda RAHASIA-*. Lalu SETIAP alamat URL aplikasi (diambil otomatis dari
resolver, jadi halaman baru ikut terperiksa) dibuka dengan setiap peran sekolah Alfa memakai id milik data terlarang.
Yang diuji:
  1. Tidak ada respons (halaman maupun isi berkas) yang memuat tanda data sekolah Beta, untuk siapa pun di Alfa.
  2. Di dalam Alfa: siswa A1, orang tua A1, dan guru g1 tidak pernah melihat tanda data siswa A2 / ruang guru g2.
  3. Permintaan POST (hapus/ubah/buat) dari akun Alfa tidak mengubah satu baris pun milik Beta.
  4. Pengunjung tanpa login tidak melihat tanda data mana pun.
Untuk memperluas cakupan, tambahkan data bertanda di fungsi `isi_tambahan` (lihat bagian bawah berkas).
"""
import re
import shutil
import tempfile
import uuid

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.test import Client, TestCase, override_settings
from django.urls import URLPattern, URLResolver, get_resolver

from accounts.models import Sekolah, Siswa
from accounts.tenancy import dalam_sekolah, tanpa_batas
from ruang_kerja.models import AnggotaRuangKerja, Materi, RuangKerja, SubmisiTugas, Tugas

User = get_user_model()
_MEDIA = tempfile.mkdtemp(prefix='betsora-uji-lintas-')

TANDA_BETA = 'RAHASIA-BETA'
TANDA_A2 = 'RAHASIA-A2'          # data siswa A2 / ruang guru g2 di sekolah Alfa
LEWATI_AWALAN = ('admin/', 'ckeditor/', 'media/')
LEWATI_KATA = ('logout', 'keluar')   # GET logout memutus sesi uji


def tearDownModule():
    shutil.rmtree(_MEDIA, ignore_errors=True)


def _isi_baca(r):
    """Isi respons sebagai bytes; berkas dibaca lalu ditutup tanpa r.close() (lihat tests_media)."""
    if getattr(r, 'streaming', False):
        berkas = getattr(r, 'file_to_stream', None)
        if berkas is None:
            return b''
        try:
            return berkas.read()
        finally:
            berkas.close()
    return r.content


_ABAIKAN_KUNCI = {'request', 'csrf_token', 'messages', 'perms', 'DEFAULT_MESSAGE_LEVELS', 'sekolah'}


def _kumpul_teks(nilai, keluar, dalam=0):
    """Kumpulkan semua teks dari nilai konteks (objek model, queryset, daftar, kamus, halaman)."""
    if dalam > 4 or len(keluar) > 20000:
        return
    if isinstance(nilai, str):
        keluar.append(nilai)
    elif hasattr(nilai, '_meta') and hasattr(nilai, '__dict__'):      # objek model
        keluar.append(str(nilai))
        for v in list(nilai.__dict__.values()):
            if isinstance(v, str):
                keluar.append(v)
    elif hasattr(nilai, 'object_list'):                                # halaman paginator
        _kumpul_teks(list(nilai.object_list), keluar, dalam + 1)
    elif isinstance(nilai, dict):
        for k, v in list(nilai.items())[:500]:
            if k not in _ABAIKAN_KUNCI:
                _kumpul_teks(v, keluar, dalam + 1)
    elif hasattr(nilai, '__iter__') and not isinstance(nilai, (bytes, str)):
        try:
            for i, v in enumerate(nilai):
                if i >= 500:
                    break
                _kumpul_teks(v, keluar, dalam + 1)
        except Exception:
            pass


def _isi_konteks(r):
    """Teks dari konteks templat. Dipakai selain isi HTML supaya kebocoran tetap terdeteksi walau templat berubah."""
    ctx = getattr(r, 'context', None)
    if ctx is None:
        return ''
    keluar = []
    for c in (ctx if isinstance(ctx, list) else [ctx]):
        try:
            _kumpul_teks(c.flatten(), keluar)
        except Exception:
            pass
    return '\n'.join(keluar)


def _semua_rute():
    """Semua pola URL: (templat jalur dengan {int}/{str}, jumlah param int). Pola regex dilewati."""
    hasil = []

    def jalan(daftar, awalan):
        for p in daftar:
            if isinstance(p, URLResolver):
                jalan(p.url_patterns, awalan + str(p.pattern))
            elif isinstance(p, URLPattern):
                rute = awalan + str(p.pattern)
                if '(?P' in rute or rute.startswith('^') or '$' in rute:
                    continue
                hasil.append(rute)

    jalan(get_resolver().url_patterns, '')
    bersih = []
    for r in hasil:
        if r.startswith(LEWATI_AWALAN) or any(k in r for k in LEWATI_KATA):
            continue
        bersih.append(r)
    return sorted(set(bersih))


def _bangun(rute, nilai_int):
    def ganti(m):
        konv = m.group(1) or 'str'
        if konv == 'int':
            return str(nilai_int)
        if konv == 'uuid':
            return str(uuid.UUID(int=nilai_int))
        return 'x'
    return '/' + re.sub(r'<(?:(\w+):)?\w+>', ganti, rute)


def _punya_int(rute):
    return bool(re.search(r'<int:', rute))


@override_settings(MEDIA_ROOT=_MEDIA)
class _Dasar(TestCase):
    @classmethod
    def setUpTestData(cls):
        def sekolah(nama, kode, tanda, tanda2):
            s = Sekolah.objects.create(nama=nama, kode=kode)
            g1 = User.objects.create_user(f'{kode}-g1', password='x', role='guru', sekolah=s)
            g2 = User.objects.create_user(f'{kode}-g2', password='x', role='guru', sekolah=s)
            kepsek = User.objects.create_user(f'{kode}-kepsek', password='x', role='kepsek', sekolah=s)
            sis1 = Siswa.objects.create(nama=f'{tanda}-sis1', nis='1', kelas='4', sekolah=s)
            sis2 = Siswa.objects.create(nama=f'{tanda2}-sis2', nis='2', kelas='5', sekolah=s)
            u1 = User.objects.create_user(f'{kode}-u1', password='x', role='siswa', sekolah=s)
            u2 = User.objects.create_user(f'{kode}-u2', password='x', role='siswa', sekolah=s)
            sis1.user, sis2.user = u1, u2
            sis1.save()
            sis2.save()
            ortu1 = User.objects.create_user(f'{kode}-ortu1', password='x', role='orangtua', sekolah=s, anak=sis1)
            ortu2 = User.objects.create_user(f'{kode}-ortu2', password='x', role='orangtua', sekolah=s, anak=sis2)
            r1 = RuangKerja.objects.create(mapel=f'{tanda}-IPA', kelas='4', guru=g1, sekolah=s)
            r2 = RuangKerja.objects.create(mapel=f'{tanda2}-IPS', kelas='5', guru=g2, sekolah=s)
            m1 = Materi.objects.create(ruang_kerja=r1, judul=f'{tanda}-M1',
                                       file=SimpleUploadedFile(f'm-{kode}-1.pdf', f'%PDF-{tanda}-m1'.encode()))
            m2 = Materi.objects.create(ruang_kerja=r2, judul=f'{tanda2}-M2',
                                       file=SimpleUploadedFile(f'm-{kode}-2.pdf', f'%PDF-{tanda2}-m2'.encode()))
            t1 = Tugas.objects.create(ruang_kerja=r1, judul=f'{tanda}-T1', instruksi=f'{tanda}-instruksi')
            t2 = Tugas.objects.create(ruang_kerja=r2, judul=f'{tanda2}-T2', instruksi=f'{tanda2}-instruksi')
            AnggotaRuangKerja.objects.create(ruang_kerja=r1, siswa=sis1)
            AnggotaRuangKerja.objects.create(ruang_kerja=r2, siswa=sis2)
            SubmisiTugas.objects.create(tugas=t1, siswa=sis1,
                                        file_jawaban=SimpleUploadedFile(f'j-{kode}-1.pdf', f'%PDF-{tanda}-j1'.encode()))
            SubmisiTugas.objects.create(tugas=t2, siswa=sis2,
                                        file_jawaban=SimpleUploadedFile(f'j-{kode}-2.pdf', f'%PDF-{tanda2}-j2'.encode()))
            d = dict(s=s, g1=g1, g2=g2, kepsek=kepsek, sis1=sis1, sis2=sis2, u1=u1, u2=u2, ortu1=ortu1, ortu2=ortu2,
                     r1=r1, r2=r2, m1=m1, m2=m2, t1=t1, t2=t2)
            isi_tambahan(d, tanda, tanda2)
            return d

        # Di Beta kedua tanda sama-sama TANDA_BETA; di Alfa data "milik orang lain" bertanda TANDA_A2.
        cls.a = sekolah('Alfa', 'alfa', 'RAHASIA-A1', TANDA_A2)
        cls.b = sekolah('Beta', 'beta', TANDA_BETA, TANDA_BETA)

    # -- alat bantu --
    @classmethod
    def id_terlarang(cls):
        """Semua pk dari baris sekolah Beta dan baris milik A2 (di mana pun), supaya URL diuji dengan id yang nyata."""
        ids = set()
        for sek in (cls.b['s'], cls.a['s']):
            with dalam_sekolah(sek):
                for model in apps.get_models():
                    if model._meta.app_label in ('contenttypes', 'sessions', 'auth', 'admin'):
                        continue
                    try:
                        ids.update(int(p) for p in model._default_manager.values_list('pk', flat=True)
                                   if str(p).isdigit())
                    except Exception:
                        continue
        ids.update({1, 2, 3})
        return sorted(i for i in ids if i < 10**7)

    def peran_alfa(self):
        a = self.a
        return [('kepsek', a['kepsek']), ('guru g1', a['g1']), ('siswa u1', a['u1']), ('ortu1', a['ortu1'])]

    def klien(self, akun):
        c = Client(raise_request_exception=False)
        if akun is not None:
            c.force_login(akun)
        return c

    def sapu(self, klien, metode, tanda_dilarang, id_list, bocor, hitung):
        for rute in _semua_rute():
            kandidat = id_list if _punya_int(rute) else [0]
            for i in kandidat:
                url = _bangun(rute, i)
                # Savepoint per permintaan: galat basis data pada satu alamat tidak boleh merusak transaksi tes.
                with transaction.atomic():
                    resp = getattr(klien, metode)(url, follow=False)
                    isi = b''
                    if resp.status_code == 200:
                        isi = _isi_baca(resp) + _isi_konteks(resp).encode('utf-8', 'ignore')
                hitung[0] += 1
                for tanda in tanda_dilarang:
                    if tanda.encode() in isi:
                        bocor.append(f'{metode.upper()} {url} memuat {tanda}')


def isi_tambahan(d, tanda, tanda2):
    """KAIT PERLUASAN. Tambahkan di sini data bertanda untuk model lain (portofolio, karya kreasi, kuis, misi,
    pesan, perpustakaan, rapor). Pakai `tanda` untuk data siswa 1 dan `tanda2` untuk data siswa 2 pada sekolah
    yang sama. Makin banyak model terisi, makin kuat uji sapuannya. Tidak diisi pun, uji tetap berjalan."""
    return None


class SapuGetTest(_Dasar):
    def test_alamat_ada(self):
        self.assertGreater(len(_semua_rute()), 20)

    def test_tidak_ada_halaman_alfa_yang_memuat_data_beta(self):
        ids = self.id_terlarang()
        bocor, hitung = [], [0]
        for nama, akun in self.peran_alfa():
            self.sapu(self.klien(akun), 'get', [TANDA_BETA], ids, bocor, hitung)
        self.assertGreater(hitung[0], 100)
        self.assertEqual(bocor, [], f'{len(bocor)} kebocoran dari {hitung[0]} permintaan:\n' + '\n'.join(bocor[:30]))

    def test_siswa_orangtua_dan_guru_tidak_melihat_data_siswa_lain_sekolah_sama(self):
        ids = self.id_terlarang()
        bocor, hitung = [], [0]
        for nama, akun in (('siswa u1', self.a['u1']), ('ortu1', self.a['ortu1']), ('guru g1', self.a['g1'])):
            sebelum = len(bocor)
            self.sapu(self.klien(akun), 'get', [TANDA_A2], ids, bocor, hitung)
            bocor[sebelum:] = [f'[{nama}] {b}' for b in bocor[sebelum:]]
        self.assertEqual(bocor, [], f'{len(bocor)} kebocoran:\n' + '\n'.join(bocor[:30]))

    def test_siswa_u2_dan_ortu2_tidak_melihat_data_siswa_1(self):
        ids = self.id_terlarang()
        bocor, hitung = [], [0]
        for akun in (self.a['u2'], self.a['ortu2']):
            self.sapu(self.klien(akun), 'get', ['RAHASIA-A1'], ids, bocor, hitung)
        self.assertEqual(bocor, [], '\n'.join(bocor[:30]))

    def test_tanpa_login_tidak_melihat_data_apa_pun(self):
        ids = self.id_terlarang()
        bocor, hitung = [], [0]
        self.sapu(self.klien(None), 'get', [TANDA_BETA, TANDA_A2, 'RAHASIA-A1'], ids, bocor, hitung)
        self.assertEqual(bocor, [], '\n'.join(bocor[:30]))

    def test_beta_juga_tidak_melihat_alfa(self):
        """Arah sebaliknya: akun Beta tidak melihat data Alfa."""
        ids = self.id_terlarang()
        bocor, hitung = [], [0]
        b = self.b
        for akun in (b['kepsek'], b['g1'], b['u1'], b['ortu1']):
            self.sapu(self.klien(akun), 'get', [TANDA_A2, 'RAHASIA-A1'], ids, bocor, hitung)
        self.assertEqual(bocor, [], '\n'.join(bocor[:30]))


def _potret(sekolah):
    """Potret semua baris sekolah itu (lewat manajer yang tersekat) agar perubahan sekecil apa pun terdeteksi."""
    hasil = {}
    with dalam_sekolah(sekolah):
        for model in apps.get_models():
            if model._meta.app_label in ('contenttypes', 'sessions', 'auth', 'admin'):
                continue
            try:
                qs = model._default_manager.all()
                if any(f.name == 'sekolah' for f in model._meta.fields):
                    qs = qs.filter(sekolah=sekolah)   # model tanpa penyaring otomatis (mis. pengaturan): hanya baris sekolah ini
                baris = sorted(repr(sorted(b.items())) for b in qs.values())
            except Exception:
                continue
            hasil[model._meta.label] = baris
    return hasil


class SapuTulisTest(_Dasar):
    def test_post_dari_alfa_tidak_mengubah_satu_baris_pun_milik_beta(self):
        ids = self.id_terlarang()
        sebelum = _potret(self.b['s'])
        bocor, hitung = [], [0]
        for nama, akun in self.peran_alfa():
            self.sapu(self.klien(akun), 'post', [], ids, bocor, hitung)
        sesudah = _potret(self.b['s'])
        beda = [m for m in sebelum if sebelum[m] != sesudah.get(m)]
        self.assertGreater(hitung[0], 100)
        self.assertEqual(beda, [], f'POST dari Alfa mengubah data Beta pada model: {beda}')

    def test_berkas_unggahan_beta_tetap_ada(self):
        import os
        nama = [self.b['m1'].file.name, self.b['m2'].file.name]
        ids = self.id_terlarang()
        bocor, hitung = [], [0]
        for nama_peran, akun in self.peran_alfa():
            self.sapu(self.klien(akun), 'post', [], ids, bocor, hitung)
        for n in nama:
            self.assertTrue(os.path.exists(os.path.join(_MEDIA, n)), n)
