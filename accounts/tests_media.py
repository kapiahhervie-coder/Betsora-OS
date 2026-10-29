"""Tes penyaji /media/ berizin (Tahap 4): berkas sekolah lain, guru lain, dan siswa lain tidak dapat diunduh."""
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from accounts.models import Sekolah, Siswa
from ruang_kerja.models import AnggotaRuangKerja, Materi, RuangKerja, SubmisiTugas, Tugas

User = get_user_model()
_MEDIA = tempfile.mkdtemp(prefix='betsora-uji-media-')


def tearDownModule():
    shutil.rmtree(_MEDIA, ignore_errors=True)


def _isi(client, url):
    r = client.get(url)
    if r.status_code == 200:
        return r.status_code, b''.join(r.streaming_content) if r.streaming else r.content, r
    return r.status_code, b'', r


def _tutup(r):
    berkas = getattr(r, 'file_to_stream', None)
    if berkas is not None:
        berkas.close()


@override_settings(MEDIA_ROOT=_MEDIA)
class MediaBerizinTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        def sekolah(nama, kode):
            s = Sekolah.objects.create(nama=nama, kode=kode)
            g1 = User.objects.create_user(f'{kode}-g1', password='x', role='guru', sekolah=s)
            g2 = User.objects.create_user(f'{kode}-g2', password='x', role='guru', sekolah=s)
            kepsek = User.objects.create_user(f'{kode}-kepsek', password='x', role='kepsek', sekolah=s)
            sis1 = Siswa.objects.create(nama=f'{kode}-sis1', nis='1', kelas='4', sekolah=s,
                                        foto=SimpleUploadedFile(f'foto-{kode}-1.png', b'\x89PNG-' + kode.encode()))
            sis2 = Siswa.objects.create(nama=f'{kode}-sis2', nis='2', kelas='4', sekolah=s)
            u1 = User.objects.create_user(f'{kode}-u1', password='x', role='siswa', sekolah=s)
            u2 = User.objects.create_user(f'{kode}-u2', password='x', role='siswa', sekolah=s)
            sis1.user, sis2.user = u1, u2
            sis1.save()
            sis2.save()
            ortu1 = User.objects.create_user(f'{kode}-ortu1', password='x', role='orangtua', sekolah=s, anak=sis1)
            r1 = RuangKerja.objects.create(mapel='IPA', kelas='4', guru=g1, sekolah=s)
            r2 = RuangKerja.objects.create(mapel='IPS', kelas='5', guru=g2, sekolah=s)
            m1 = Materi.objects.create(ruang_kerja=r1, judul='M1', file=SimpleUploadedFile(f'materi-{kode}-g1.pdf', b'%PDF-g1'))
            m2 = Materi.objects.create(ruang_kerja=r2, judul='M2', file=SimpleUploadedFile(f'materi-{kode}-g2.pdf', b'%PDF-g2'))
            html = Materi.objects.create(ruang_kerja=r1, judul='H', file=SimpleUploadedFile(f'aktif-{kode}.html', b'<script>1</script>'))
            t1 = Tugas.objects.create(ruang_kerja=r1, judul='T', instruksi='x')
            AnggotaRuangKerja.objects.create(ruang_kerja=r1, siswa=sis1)
            AnggotaRuangKerja.objects.create(ruang_kerja=r1, siswa=sis2)
            j1 = SubmisiTugas.objects.create(tugas=t1, siswa=sis1, file_jawaban=SimpleUploadedFile(f'jawab-{kode}-1.pdf', b'%PDF-j1'))
            j2 = SubmisiTugas.objects.create(tugas=t1, siswa=sis2, file_jawaban=SimpleUploadedFile(f'jawab-{kode}-2.pdf', b'%PDF-j2'))
            return dict(s=s, g1=g1, g2=g2, kepsek=kepsek, sis1=sis1, sis2=sis2, u1=u1, u2=u2, ortu1=ortu1,
                        m1=m1, m2=m2, html=html, j1=j1, j2=j2)

        cls.a = sekolah('Alfa', 'alfa')
        cls.b = sekolah('Beta', 'beta')

    def url(self, berkas):
        return '/media/' + berkas.name

    def kode(self, akun, berkas):
        self.client.force_login(akun)
        r = self.client.get(self.url(berkas))
        if r.status_code == 200 and getattr(r, 'streaming', False):
            _tutup(r)
        return r.status_code

    def test_harus_login(self):
        r = self.client.get(self.url(self.a['m1'].file))
        self.assertEqual(r.status_code, 302)
        self.assertIn('login', r['Location'])

    def test_guru_membuka_berkas_ruangnya_sendiri(self):
        self.assertEqual(self.kode(self.a['g1'], self.a['m1'].file), 200)
        self.assertEqual(self.kode(self.a['g1'], self.a['sis1'].foto), 200)
        self.assertEqual(self.kode(self.a['g1'], self.a['j1'].file_jawaban), 200)

    def test_berkas_sekolah_lain_tidak_dapat_dibuka(self):
        for pemilik in ('g1', 'kepsek', 'u1', 'ortu1'):
            for berkas in (self.b['m1'].file, self.b['sis1'].foto, self.b['j1'].file_jawaban):
                self.assertEqual(self.kode(self.a[pemilik], berkas), 404, f'{pemilik} -> {berkas.name}')
        for berkas in (self.a['m1'].file, self.a['sis1'].foto, self.a['j1'].file_jawaban):
            self.assertEqual(self.kode(self.b['g1'], berkas), 404)

    def test_guru_lain_di_sekolah_sama_tidak_membuka_materi_ruang_guru_lain(self):
        self.assertEqual(self.kode(self.a['g2'], self.a['m1'].file), 404)
        self.assertEqual(self.kode(self.a['g1'], self.a['m2'].file), 404)
        self.assertEqual(self.kode(self.a['g2'], self.a['m2'].file), 200)

    def test_kepsek_membuka_seluruh_sekolahnya(self):
        for berkas in (self.a['m1'].file, self.a['m2'].file, self.a['sis1'].foto, self.a['j2'].file_jawaban):
            self.assertEqual(self.kode(self.a['kepsek'], berkas), 200)

    def test_jawaban_tugas_hanya_untuk_pemilik_dan_gurunya(self):
        self.assertEqual(self.kode(self.a['u1'], self.a['j1'].file_jawaban), 200)
        self.assertEqual(self.kode(self.a['u1'], self.a['j2'].file_jawaban), 404)   # siswa lain sekelas
        self.assertEqual(self.kode(self.a['u2'], self.a['j1'].file_jawaban), 404)
        self.assertEqual(self.kode(self.a['ortu1'], self.a['j1'].file_jawaban), 200)  # anaknya
        self.assertEqual(self.kode(self.a['ortu1'], self.a['j2'].file_jawaban), 404)
        self.assertEqual(self.kode(self.a['g1'], self.a['j2'].file_jawaban), 200)    # guru ruang itu

    def test_berkas_tanpa_pemilik_hanya_untuk_superuser(self):
        import os
        with open(os.path.join(_MEDIA, 'sisa-lama.txt'), 'wb') as f:
            f.write(b'sisa')
        self.client.force_login(self.a['kepsek'])
        self.assertEqual(self.client.get('/media/sisa-lama.txt').status_code, 404)
        su = User.objects.create_superuser('platform', password='x')
        self.client.force_login(su)
        r = self.client.get('/media/sisa-lama.txt')
        self.assertEqual(r.status_code, 200)
        _tutup(r)

    def test_superuser_membuka_berkas_semua_sekolah(self):
        su = User.objects.create_superuser('platform2', password='x')
        for berkas in (self.a['m1'].file, self.b['m1'].file):
            self.assertEqual(self.kode(su, berkas), 200)

    def test_jalur_berbahaya_ditolak(self):
        self.client.force_login(self.a['kepsek'])
        for p in ('/media/../manage.py', '/media/materi/../../manage.py', '/media//etc/passwd', '/media/materi/..%2f..%2fmanage.py', '/media/'):
            self.assertEqual(self.client.get(p).status_code, 404, p)

    def test_berkas_aktif_dipaksa_diunduh_dan_header_aman(self):
        self.client.force_login(self.a['g1'])
        r = self.client.get(self.url(self.a['html'].file))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Disposition'], 'attachment')
        self.assertEqual(r['X-Content-Type-Options'], 'nosniff')
        _tutup(r)
        r = self.client.get(self.url(self.a['sis1'].foto))
        self.assertEqual(r['X-Content-Type-Options'], 'nosniff')
        self.assertTrue(r['Cache-Control'].startswith('private'))
        _tutup(r)

    def test_sekolah_nonaktif_tidak_dapat_membuka(self):
        s = self.a['s']
        s.aktif = False
        s.save()
        self.assertEqual(self.kode(self.a['g1'], self.a['m1'].file), 404)

    def test_bidang_berkas_terdeteksi(self):
        from accounts.media_berizin import _bidang_berkas
        nama = {(m.__name__, b) for m, b, _ in _bidang_berkas()}
        for harus in [('Siswa', 'foto'), ('Materi', 'file'), ('SubMateri', 'file'), ('Tugas', 'lampiran'),
                      ('SubmisiTugas', 'file_jawaban'), ('SumberDigital', 'file'), ('SumberDigital', 'cover'),
                      ('Audio', 'file'), ('HalamanSumber', 'gambar'), ('RefleksiSiswa', 'file')]:
            self.assertIn(harus, nama)
        self.assertNotIn(('KaryaSiswa', 'file'), nama)           # penyaji portofolio sendiri
        self.assertNotIn(('LampiranKarya', 'file'), nama)        # penyimpanan privat

