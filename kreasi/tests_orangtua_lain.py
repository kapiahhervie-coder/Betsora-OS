"""Absensi, Tugas (status saja), dan Portofolio pada dashboard orang tua."""
import datetime

from django.urls import reverse
from django.utils import timezone

from kelas.models import Absensi
from portofolio.models import KaryaSiswa
from ruang_kerja.models import AnggotaRuangKerja, RuangKerja, SubmisiTugas, Tugas

from .orangtua_lain import ringkasan_absensi_untuk_orangtua, ringkasan_portofolio_untuk_orangtua, ringkasan_tugas_untuk_orangtua
from .tests_orangtua import DasarOrangTua


class AksesUmumTest(DasarOrangTua):
    def test_bukan_orangtua_atau_tanpa_anak_hasilnya_none(self):
        from django.contrib.auth.models import AnonymousUser
        from accounts.models import User
        tanpa_anak = User.objects.create_user('kosong2', password='x', role='orangtua')
        for u in [self.guru, self.u_a, AnonymousUser(), tanpa_anak]:
            self.assertIsNone(ringkasan_absensi_untuk_orangtua(u))
            self.assertIsNone(ringkasan_tugas_untuk_orangtua(u))
            self.assertIsNone(ringkasan_portofolio_untuk_orangtua(u))


class AbsensiTest(DasarOrangTua):
    def test_tanpa_data(self):
        b = ringkasan_absensi_untuk_orangtua(self.ortu_a)
        self.assertEqual(b['total'], 0)
        self.assertIsNone(b['persen_hadir'])
        r = self.dashboard(self.ortu_a)
        self.assertContains(r, 'Belum ada data kehadiran')

    def test_persen_dan_status_kosong_dihitung_benar(self):
        Absensi.objects.create(siswa=self.s_a, tanggal=datetime.date(2026, 9, 1), status='hadir')
        Absensi.objects.create(siswa=self.s_a, tanggal=datetime.date(2026, 9, 2), status='izin')
        Absensi.objects.create(siswa=self.s_a, tanggal=datetime.date(2026, 9, 3), status='')
        b = ringkasan_absensi_untuk_orangtua(self.ortu_a)
        self.assertEqual(b['total'], 3)
        self.assertEqual(b['persen_hadir'], 33)
        self.assertEqual(b['hitung'], {'hadir': 1, 'izin': 1, 'sakit': 0, 'alpha': 0, 'kosong': 1})
        r = self.dashboard(self.ortu_a)
        self.assertContains(r, '33%')
        self.assertContains(r, 'Belum diisi')

    def test_hanya_anak_sendiri(self):
        Absensi.objects.create(siswa=self.s_b, tanggal=datetime.date(2026, 9, 1), status='hadir')
        self.assertEqual(ringkasan_absensi_untuk_orangtua(self.ortu_a)['total'], 0)

    def test_batas_dan_urutan_terbaru_dulu(self):
        for i in range(1, 18):
            Absensi.objects.create(siswa=self.s_a, tanggal=datetime.date(2026, 1, i), status='hadir')
        b = ringkasan_absensi_untuk_orangtua(self.ortu_a)
        self.assertEqual(b['total'], 17)
        self.assertEqual(len(b['daftar']), 15)
        self.assertTrue(b['ada_lebih'])
        self.assertEqual(b['daftar'][0]['tanggal'], datetime.date(2026, 1, 17))


class TugasTest(DasarOrangTua):
    """self.s_a sudah menjadi anggota self.ruang lewat DasarKreasi.setUpTestData."""

    def test_belum_ada_tugas(self):
        # self.s_a sudah anggota self.ruang (yang punya 1 tugas bawaan dari DasarKreasi), jadi
        # untuk menguji keadaan "kosong" dipakai siswa & orang tua baru yang belum jadi anggota ruang mana pun.
        from accounts.models import Siswa, User
        u = User.objects.create_user('siswa_baru', password='x', role='siswa')
        s = Siswa.objects.create(user=u, nama='Citra Baru', nis='9', kelas='3')
        ortu = User.objects.create_user('ortu_baru', password='x', role='orangtua', anak=s)
        r = self.dashboard(ortu)
        self.assertContains(r, 'Belum ada tugas yang diberikan.')

    def test_ruang_tanpa_tugas_tidak_ditampilkan(self):
        kosong = RuangKerja.objects.create(mapel='Ruang Kosong', kelas='3', guru=self.guru)
        AnggotaRuangKerja.objects.create(ruang_kerja=kosong, siswa=self.s_a)
        self.assertNotContains(self.dashboard(self.ortu_a), 'Ruang Kosong')

    def test_status_sudah_dan_belum_tanpa_nilai(self):
        t1 = Tugas.objects.create(ruang_kerja=self.ruang, jenis='esai', judul='Esai A', instruksi='x')
        t2 = Tugas.objects.create(ruang_kerja=self.ruang, jenis='pilihan_ganda', judul='Kuis B', instruksi='x')
        SubmisiTugas.objects.create(tugas=t1, siswa=self.s_a, nilai=95, feedback='Rahasia nilai & feedback guru')
        r = self.dashboard(self.ortu_a)
        self.assertContains(r, 'Esai A')
        self.assertContains(r, 'Sudah dikumpulkan')
        self.assertContains(r, 'Kuis B')
        self.assertContains(r, 'Belum dikumpulkan')
        self.assertNotContains(r, '95')
        self.assertNotContains(r, 'Rahasia nilai')

    def test_lewat_batas_waktu(self):
        Tugas.objects.create(ruang_kerja=self.ruang, jenis='esai', judul='Telat', instruksi='x',
                             deadline=timezone.now() - datetime.timedelta(days=1))
        self.assertContains(self.dashboard(self.ortu_a), 'Lewat batas waktu')

    def test_tugas_kreasi_ikut_muncul_sebagai_baris_biasa(self):
        self.buat_karya(judul='Maket Kreasi')
        html = self.dashboard(self.ortu_a).content.decode()
        self.assertIn('Maket Kreasi', html)
        self.assertGreaterEqual(html.count('Maket Kreasi'), 2)   # muncul di Tugas & di Karya

    def test_status_tidak_tertukar_dengan_submisi_siswa_lain(self):
        # s_a dan s_b sama-sama anggota self.ruang (didaftarkan di DasarKreasi.setUpTestData).
        t = Tugas.objects.create(ruang_kerja=self.ruang, jenis='esai', judul='Tugas Bersama', instruksi='x')
        SubmisiTugas.objects.create(tugas=t, siswa=self.s_b)   # hanya Budi yang mengumpulkan
        html = self.dashboard(self.ortu_a).content.decode()
        i = html.index('Tugas Bersama')
        self.assertIn('Belum dikumpulkan', html[i:i + 400])
        self.assertNotIn('Sudah dikumpulkan', html[i:i + 400])

    def test_hanya_ruang_anak_terdaftar(self):
        lain = RuangKerja.objects.create(mapel='Rahasia', kelas='3', guru=self.guru)
        Tugas.objects.create(ruang_kerja=lain, jenis='esai', judul='Tugas anak lain', instruksi='x')
        self.assertNotContains(self.dashboard(self.ortu_a), 'Tugas anak lain')

    def test_jumlah_query_tetap(self):
        for i in range(5):
            Tugas.objects.create(ruang_kerja=self.ruang, jenis='esai', judul=f'T{i}', instruksi='x')
        with self.assertNumQueries(3):
            ringkasan_tugas_untuk_orangtua(self.ortu_a)


class PortofolioTest(DasarOrangTua):
    def test_kosong(self):
        self.assertContains(self.dashboard(self.ortu_a), 'Belum ada karya yang diunggah ke portofolio.')

    def test_gambar_tampil_dokumen_jadi_tautan(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        KaryaSiswa.objects.create(siswa=self.s_a, judul='Lukisanku', file=SimpleUploadedFile('l.png', b'\x89PNG'))
        KaryaSiswa.objects.create(siswa=self.s_a, judul='Laporanku', file=SimpleUploadedFile('l.pdf', b'%PDF'))
        html = self.dashboard(self.ortu_a).content.decode()
        self.assertIn('<img src=', html)
        self.assertIn('Lihat berkas', html)

    def test_video_youtube_di_embed_lainnya_jadi_tautan(self):
        KaryaSiswa.objects.create(siswa=self.s_a, judul='Video A', video_url='https://youtu.be/abc123')
        KaryaSiswa.objects.create(siswa=self.s_a, judul='Video B', video_url='https://contoh-mencurigakan.test/x')
        html = self.dashboard(self.ortu_a).content.decode()
        self.assertIn('<iframe src="https://www.youtube.com/embed/abc123"', html)
        self.assertNotIn('<iframe src="https://contoh-mencurigakan.test', html)
        self.assertIn('contoh-mencurigakan.test', html)   # tetap tampil, sebagai tautan biasa

    def test_karya_belum_dibagikan_tetap_tampil_ke_orangtua(self):
        KaryaSiswa.objects.create(siswa=self.s_a, judul='Privat', dibagikan=False, deskripsi='hanya utk guru')
        self.assertContains(self.dashboard(self.ortu_a), 'Privat')

    def test_refleksi_dan_deskripsi_tidak_dieksekusi(self):
        KaryaSiswa.objects.create(siswa=self.s_a, judul='X', deskripsi='<script>alert(1)</script>', refleksi='<b>y</b>')
        html = self.dashboard(self.ortu_a).content.decode()
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html)

    def test_hanya_anak_sendiri(self):
        KaryaSiswa.objects.create(siswa=self.s_b, judul='Punya Budi')
        self.assertNotContains(self.dashboard(self.ortu_a), 'Punya Budi')

    def test_batas_dan_tampilkan_semua(self):
        for i in range(14):
            KaryaSiswa.objects.create(siswa=self.s_a, judul=f'Karya {i}')
        r = self.dashboard(self.ortu_a)
        self.assertContains(r, 'Tampilkan semua karya (14)')
        r2 = self.client.get(reverse('accounts:dashboard_orangtua') + '?semua_portofolio=1')
        for i in range(14):
            self.assertContains(r2, f'Karya {i}')


class UrutanBagianTest(DasarOrangTua):
    """Urutan tampilan sesuai permintaan: Absensi, Tugas, Karya, Portofolio."""

    def test_urutan_bagian_di_halaman(self):
        Absensi.objects.create(siswa=self.s_a, tanggal=datetime.date(2026, 9, 1), status='hadir')
        Tugas.objects.create(ruang_kerja=self.ruang, jenis='esai', judul='Esai Urutan', instruksi='x')
        self.buat_karya(judul='Karya Urutan')
        KaryaSiswa.objects.create(siswa=self.s_a, judul='Portofolio Urutan')
        html = self.dashboard(self.ortu_a).content.decode()
        i_absensi = html.index('>📅 Absensi<')
        i_tugas = html.index('>📝 Tugas<')
        i_karya = html.index('Karya &amp; Perkembangan')
        i_portofolio = html.index('>🖼️ Portofolio')
        self.assertTrue(i_absensi < i_tugas < i_karya < i_portofolio,
                        (i_absensi, i_tugas, i_karya, i_portofolio))
