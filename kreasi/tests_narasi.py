"""Uji pembuat draf narasi rapor dari skor rubrik Tugas Kreasi."""
import datetime
from unittest import mock

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from accounts.models import Siswa, User
from ruang_kerja.models import Materi, RuangKerja, SubmisiTugas, Tugas

from .models import DeskriptorLevel, DimensiPenilaian, RefleksiKarya, SkorDimensi
from .narasi import _level_rata, susun_narasi_kreasi

KEB, MOT, LIS = 'keberanian_berekspresi', 'motorik_halus', 'kelancaran_lisan'


class DasarNarasi(TestCase):
    kelas = '3'
    jenjang = 'sd_awal'
    hari = 0          # penghitung agar setiap karya punya waktu kirim yang berurutan

    @classmethod
    def setUpTestData(cls):
        call_command('seed_kreasi', verbosity=0)
        cls.guru = User.objects.create_user('guru', password='x', role='guru')
        u = User.objects.create_user('ani', password='x', role='siswa')
        cls.siswa = Siswa.objects.create(user=u, nama='Ani Lestari', nis='1', kelas='3')
        cls.ruang = RuangKerja.objects.create(mapel='Seni', kelas=cls.kelas, guru=cls.guru)

    def karya(self, levels, emoji='', jawaban=None, ruang=None, siswa=None):
        """Satu karya kreasi yang sudah dinilai. levels = {kode_dimensi: level}."""
        ruang, siswa = ruang or self.ruang, siswa or self.siswa
        DasarNarasi.hari += 1
        tugas = Tugas.objects.create(ruang_kerja=ruang, jenis='kreasi', judul=f'Karya {DasarNarasi.hari}', instruksi='x')
        sub = SubmisiTugas.objects.create(tugas=tugas, siswa=siswa)
        SubmisiTugas.objects.filter(pk=sub.pk).update(dikirim_pada=timezone.now() + datetime.timedelta(days=DasarNarasi.hari))
        for kode, level in levels.items():
            SkorDimensi.objects.create(
                submisi=sub, level=level, dinilai_oleh=self.guru,
                dimensi=DimensiPenilaian.objects.get(jenjang=ruang.get_jenjang(), kode=kode))
        if emoji or jawaban:
            RefleksiKarya.objects.create(submisi=sub, tipe='emoji_suara', emoji=emoji, jawaban=jawaban or {})
        return sub


class AturanNarasiTest(DasarNarasi):
    def test_tanpa_skor_kosong(self):
        self.assertEqual(susun_narasi_kreasi(self.ruang, self.siswa), '')

    def test_jenjang_tidak_diketahui_kosong(self):
        ruang = RuangKerja.objects.create(mapel='Kursus', kelas='Kursus Coding', guru=self.guru)
        self.assertEqual(susun_narasi_kreasi(ruang, self.siswa), '')

    def test_semua_tinggi(self):
        self.karya({KEB: 4, MOT: 3, LIS: 3})
        t = susun_narasi_kreasi(self.ruang, self.siswa)
        self.assertTrue(t.startswith('Ani telah menyelesaikan 1 karya kreasi yang dinilai pada periode ini.'))
        self.assertIn('Ani sangat berani dan percaya diri', t)
        self.assertIn('Selain itu, Ani cukup terampil', t)              # motorik: level sama dengan lisan, urutan lebih awal
        self.assertNotIn('menceritakan karyanya secara runtut', t)      # maksimal dua kekuatan
        self.assertNotIn('Pada aspek lain', t)
        self.assertTrue(t.endswith('terus mempertahankan semangat berkarya dan berani menerima tantangan yang lebih besar.'))

    def test_campuran_kekuatan_lalu_area_berkembang(self):
        self.karya({KEB: 4, MOT: 1, LIS: 2})
        t = susun_narasi_kreasi(self.ruang, self.siswa)
        self.assertIn('Ani sangat berani dan percaya diri', t)
        self.assertIn('Pada aspek lain, kemampuan Ani dalam menggunting', t)   # huruf pertama dikecilkan, nama tetap kapital
        self.assertIn('Selain itu, Ani mulai mampu menceritakan karyanya', t)
        self.assertTrue(t.endswith('dengan dukungan guru dan orang tua di rumah.'))
        self.assertLess(t.index('sangat berani'), t.index('Pada aspek lain'))

    def test_semua_rendah_tanpa_awalan_di_sisi_lain(self):
        self.karya({KEB: 2, MOT: 1, LIS: 2})
        t = susun_narasi_kreasi(self.ruang, self.siswa)
        self.assertIn('Kemampuan Ani dalam menggunting', t)     # kalimat pertama: huruf besar dipertahankan
        self.assertIn('Selain itu, Ani mulai berani menunjukkan karyanya', t)
        self.assertNotIn('Pada aspek lain', t)
        self.assertNotIn('mempertahankan semangat', t)

    def test_pembulatan_setengah_ke_atas(self):
        for levels, harapan in [([3, 4], 4), ([2, 3], 3), ([1, 2, 2], 2), ([4, 3, 3], 3),
                                ([1], 1), ([4, 4, 3, 3], 4), ([1, 1, 2], 1), ([1, 2], 2)]:
            self.assertEqual(_level_rata(levels), harapan, levels)

    def test_rata_rata_dari_banyak_karya(self):
        self.karya({KEB: 2, MOT: 3, LIS: 3})
        self.karya({KEB: 4, MOT: 3, LIS: 3})
        t = susun_narasi_kreasi(self.ruang, self.siswa)
        self.assertIn('telah menyelesaikan 2 karya kreasi', t)
        self.assertIn('Ani berani menunjukkan karyanya dan menyampaikan idenya kepada guru dan teman.', t)   # rata-rata 3

    def test_perkembangan_disebut_bila_naik(self):
        self.karya({KEB: 1, MOT: 2, LIS: 3})
        self.karya({KEB: 3, MOT: 4, LIS: 3})
        t = susun_narasi_kreasi(self.ruang, self.siswa)
        self.assertIn('Perkembangan yang menggembirakan terlihat pada aspek keberanian berekspresi dan motorik halus.', t)

    def test_tidak_ada_kalimat_perkembangan_bila_turun_atau_datar(self):
        self.karya({KEB: 4, MOT: 3, LIS: 3})
        self.karya({KEB: 2, MOT: 3, LIS: 3})
        self.assertNotIn('Perkembangan yang menggembirakan', susun_narasi_kreasi(self.ruang, self.siswa))

    def test_satu_karya_tidak_pernah_dianggap_perkembangan(self):
        self.karya({KEB: 1, MOT: 2, LIS: 3})
        self.assertNotIn('Perkembangan', susun_narasi_kreasi(self.ruang, self.siswa))


class RefleksiDalamNarasiTest(DasarNarasi):
    def test_emoji_terbaru_yang_dipakai(self):
        self.karya({KEB: 3, MOT: 3, LIS: 3}, emoji='sulit')
        self.karya({KEB: 3, MOT: 3, LIS: 3}, emoji='bangga')
        t = susun_narasi_kreasi(self.ruang, self.siswa)
        self.assertIn('Ani mengungkapkan rasa bangga terhadap karya yang dibuatnya.', t)
        self.assertNotIn('agak sulit', t)

    def test_emoji_sulit_disampaikan_jujur_dan_lembut(self):
        self.karya({KEB: 3, MOT: 3, LIS: 3}, emoji='sulit')
        self.assertIn('Ani dengan jujur menyampaikan bahwa berkarya terasa agak sulit baginya, sehingga pendampingan akan sangat membantu.',
                      susun_narasi_kreasi(self.ruang, self.siswa))

    def test_tanpa_emoji_tidak_ada_kalimat_refleksi(self):
        self.karya({KEB: 3, MOT: 3, LIS: 3})
        t = susun_narasi_kreasi(self.ruang, self.siswa)
        self.assertNotIn('bangga', t)
        self.assertNotIn('merefleksikan', t)

    def test_refleksi_tertulis_hanya_disebut_ada_isinya_tidak_dikutip(self):
        self.karya({KEB: 3, MOT: 3, LIS: 3}, jawaban={'dibuat': 'RAHASIA ISI TULISAN ANAK'})
        t = susun_narasi_kreasi(self.ruang, self.siswa)
        self.assertIn('membiasakan diri merefleksikan proses berkaryanya melalui tulisan', t)
        self.assertNotIn('RAHASIA', t)


class SumberDataNarasiTest(DasarNarasi):
    def test_dimensi_nonaktif_diabaikan(self):
        self.karya({KEB: 4, MOT: 3, LIS: 3})
        DimensiPenilaian.objects.filter(kode=KEB).update(aktif=False)
        t = susun_narasi_kreasi(self.ruang, self.siswa)
        self.assertNotIn('sangat berani dan percaya diri', t)
        DimensiPenilaian.objects.update(aktif=False)
        self.assertEqual(susun_narasi_kreasi(self.ruang, self.siswa), '')

    def test_hanya_karya_di_ruang_kerja_ini(self):
        lain = RuangKerja.objects.create(mapel='Bahasa', kelas='3', guru=self.guru)
        self.karya({KEB: 1, MOT: 1, LIS: 1}, ruang=lain)
        self.assertEqual(susun_narasi_kreasi(self.ruang, self.siswa), '')
        self.karya({KEB: 4, MOT: 4, LIS: 4})
        t = susun_narasi_kreasi(self.ruang, self.siswa)
        self.assertIn('telah menyelesaikan 1 karya', t)
        self.assertNotIn('masih perlu ditemani', t)

    def test_hanya_siswa_yang_bersangkutan(self):
        u = User.objects.create_user('budi', password='x', role='siswa')
        budi = Siswa.objects.create(user=u, nama='Budi Santoso', nis='2', kelas='3')
        self.karya({KEB: 1, MOT: 1, LIS: 1}, siswa=budi)
        self.assertEqual(susun_narasi_kreasi(self.ruang, self.siswa), '')
        self.assertTrue(susun_narasi_kreasi(self.ruang, budi).startswith('Budi telah menyelesaikan 1 karya'))

    def test_deskriptor_dihapus_dilewati_tanpa_mengarang(self):
        self.karya({KEB: 4, MOT: 3, LIS: 3})
        DeskriptorLevel.objects.filter(dimensi__kode=KEB, level=4).delete()
        t = susun_narasi_kreasi(self.ruang, self.siswa)
        self.assertNotIn('sangat berani', t)
        self.assertIn('Ani cukup terampil', t)
        DeskriptorLevel.objects.all().delete()
        self.assertEqual(susun_narasi_kreasi(self.ruang, self.siswa), '')

    def test_edit_deskriptor_di_admin_langsung_terpakai(self):
        self.karya({KEB: 4, MOT: 3, LIS: 3})
        DeskriptorLevel.objects.filter(dimensi__kode=KEB, level=4).update(kalimat='{nama} luar biasa berani tampil.')
        self.assertIn('Ani luar biasa berani tampil.', susun_narasi_kreasi(self.ruang, self.siswa))

    def test_jumlah_query_tetap_untuk_satu_siswa(self):
        self.karya({KEB: 1, MOT: 2, LIS: 3}, emoji='senang')
        self.karya({KEB: 3, MOT: 4, LIS: 3}, emoji='bangga')
        with self.assertNumQueries(3):    # skor, deskriptor, refleksi: tidak bertambah seiring jumlah karya
            susun_narasi_kreasi(self.ruang, self.siswa)


class SMPTest(DasarNarasi):
    kelas = 'VIII B'
    jenjang = 'smp'

    def test_dimensi_smp(self):
        self.karya({'pemecahan_masalah': 4, 'kolaborasi': 3, 'integrasi_disiplin': 2})
        t = susun_narasi_kreasi(self.ruang, self.siswa)
        self.assertIn('sangat baik dalam menganalisis masalah', t)
        self.assertIn('Pada aspek lain, Ani mulai mengaitkan karyanya', t)


class DraftKomentarTerpaduTest(DasarNarasi):
    """generate_draft_komentar di ruang_kerja.views setelah dipasangi skrip pemasang."""

    def draf(self):
        from ruang_kerja.views import generate_draft_komentar
        return generate_draft_komentar(self.ruang, self.siswa, None)

    def test_kelas_tanpa_topik_dan_tanpa_karya_tetap_pesan_lama(self):
        self.assertEqual(self.draf(), 'Penilaian topik untuk Ani belum tersedia pada periode ini.')

    def test_kelas_hanya_tugas_kreasi_memakai_narasi_kreasi(self):
        self.karya({KEB: 4, MOT: 3, LIS: 3})
        d = self.draf()
        self.assertNotIn('belum tersedia', d)
        self.assertEqual(d, susun_narasi_kreasi(self.ruang, self.siswa))

    def test_ada_topik_dan_karya_digabung_dua_paragraf(self):
        Materi.objects.create(ruang_kerja=self.ruang, judul='Topik 1')
        self.karya({KEB: 4, MOT: 3, LIS: 3})
        with mock.patch('ruang_kerja.views._draft_akademik', return_value='AKADEMIK.'), \
             mock.patch.object(Materi, 'hitung_mastery', return_value=80.0):
            self.assertEqual(self.draf(), 'AKADEMIK.\n\n' + susun_narasi_kreasi(self.ruang, self.siswa))

    def test_ada_topik_tanpa_karya_tidak_berubah_dari_perilaku_lama(self):
        Materi.objects.create(ruang_kerja=self.ruang, judul='Topik 1')
        with mock.patch('ruang_kerja.views._draft_akademik', return_value='AKADEMIK.'), \
             mock.patch.object(Materi, 'hitung_mastery', return_value=80.0):
            self.assertEqual(self.draf(), 'AKADEMIK.')
