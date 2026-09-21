"""Uji pembuat draf narasi rapor dari skor rubrik Tugas Kreasi."""
import datetime
from unittest import mock

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from accounts.models import Siswa, User
from django.urls import reverse

from ruang_kerja.models import AnggotaRuangKerja, CatatanRapor, Materi, RuangKerja, SubmisiTugas, Tugas

from .models import DeskriptorLevel, DimensiPenilaian, RefleksiKarya, SkorDimensi
from .narasi import _level_rata, susun_narasi_bidang, susun_narasi_kreasi

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
        self.assertIn('Selain itu, Ani mampu menceritakan karyanya secara runtut', t)
        self.assertNotIn('cukup terampil', t)              # motorik halus pindah ke kolom Fisik & Motorik
        self.assertNotIn('Pada aspek lain', t)
        self.assertTrue(t.endswith('terus mempertahankan semangat berkarya dan berani menerima tantangan yang lebih besar.'))

    def test_campuran_kekuatan_lalu_area_berkembang(self):
        self.karya({KEB: 4, MOT: 1, LIS: 2})
        t = susun_narasi_kreasi(self.ruang, self.siswa)
        self.assertIn('Ani sangat berani dan percaya diri', t)
        self.assertIn('Pada aspek lain, Ani mulai mampu menceritakan karyanya', t)   # nama tetap kapital
        self.assertNotIn('menggunting', t)                                            # motorik ada di kolom lain
        self.assertTrue(t.endswith('dengan dukungan guru dan orang tua di rumah.'))
        self.assertLess(t.index('sangat berani'), t.index('Pada aspek lain'))

    def test_semua_rendah_tanpa_awalan_pada_aspek_lain(self):
        self.karya({KEB: 2, MOT: 1, LIS: 2})
        t = susun_narasi_kreasi(self.ruang, self.siswa)
        self.assertIn('Ani mulai berani menunjukkan karyanya', t)          # kalimat pertama: tanpa penyambung
        self.assertIn('Selain itu, Ani mulai mampu menceritakan karyanya', t)
        self.assertNotIn('Pada aspek lain', t)
        self.assertNotIn('mempertahankan semangat', t)
        self.assertTrue(t.endswith('dengan dukungan guru dan orang tua di rumah.'))

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
        self.karya({KEB: 1, MOT: 2, LIS: 1})
        self.karya({KEB: 3, MOT: 4, LIS: 3})
        t = susun_narasi_kreasi(self.ruang, self.siswa)
        self.assertIn('Perkembangan yang menggembirakan terlihat pada aspek keberanian berekspresi dan kelancaran menyampaikan gagasan lisan.', t)
        self.assertNotIn('motorik', t)         # perkembangan motorik disebut di kolom Fisik & Motorik

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
        self.assertEqual(susun_narasi_bidang(self.ruang, self.siswa), {'akademik': '', 'fisik_motorik': ''})

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
        self.assertIn('Ani mampu menceritakan karyanya secara runtut', t)
        DeskriptorLevel.objects.all().delete()
        self.assertEqual(susun_narasi_bidang(self.ruang, self.siswa), {'akademik': '', 'fisik_motorik': ''})

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


class BidangFisikMotorikTest(DasarNarasi):
    """Dimensi Motorik Halus diarahkan ke kolom Fisik & Motorik, terpisah dari Catatan Akademik."""

    def bidang(self):
        return susun_narasi_bidang(self.ruang, self.siswa)

    def test_motorik_ke_kolom_fisik_bukan_akademik(self):
        self.karya({KEB: 4, MOT: 3, LIS: 3})
        b = self.bidang()
        self.assertEqual(b['fisik_motorik'], 'Ani cukup terampil mengendalikan alat kerja sehingga karyanya tersusun dengan rapi.')
        self.assertNotIn('terampil', b['akademik'])
        self.assertEqual(susun_narasi_kreasi(self.ruang, self.siswa), b['akademik'])

    def test_fisik_apa_adanya_tanpa_pembuka_dan_penutup(self):
        self.karya({KEB: 3, MOT: 1, LIS: 3})
        f = self.bidang()['fisik_motorik']
        self.assertEqual(f, 'Kemampuan Ani dalam menggunting, menempel, mewarnai, dan memegang alat tulis '
                            'masih memerlukan banyak latihan dan pendampingan.')       # huruf kapital utuh, tanpa 'Harapannya'
        self.assertNotIn('Harapannya', f)
        self.assertNotIn('telah menyelesaikan', f)

    def test_perkembangan_motorik_disebut_di_kolom_fisik(self):
        self.karya({KEB: 3, MOT: 2, LIS: 3})
        self.karya({KEB: 3, MOT: 4, LIS: 3})
        b = self.bidang()
        self.assertTrue(b['fisik_motorik'].endswith('Perkembangan yang menggembirakan terlihat pada aspek motorik halus.'))
        self.assertNotIn('Perkembangan', b['akademik'])

    def test_hanya_motorik_yang_dinilai_akademik_kosong(self):
        self.karya({MOT: 4})
        b = self.bidang()
        self.assertEqual(b['akademik'], '')
        self.assertIn('sangat terampil', b['fisik_motorik'])

    def test_tanpa_motorik_kolom_fisik_kosong(self):
        self.karya({KEB: 3, LIS: 3})
        b = self.bidang()
        self.assertEqual(b['fisik_motorik'], '')
        self.assertNotEqual(b['akademik'], '')

    def test_motorik_nonaktif_kolom_fisik_kosong(self):
        self.karya({KEB: 3, MOT: 4, LIS: 3})
        DimensiPenilaian.objects.filter(kode=MOT).update(aktif=False)
        self.assertEqual(self.bidang()['fisik_motorik'], '')

    def test_jumlah_query_tetap_tiga(self):
        self.karya({KEB: 1, MOT: 2, LIS: 3}, emoji='senang')
        self.karya({KEB: 3, MOT: 4, LIS: 3}, emoji='bangga')
        with self.assertNumQueries(3):
            self.bidang()

    def test_jenjang_tanpa_dimensi_motorik_kolom_fisik_kosong(self):
        ruang = RuangKerja.objects.create(mapel='IPA', kelas='5', guru=self.guru)          # SD 4-6
        self.karya({'sebab_akibat': 4, 'kreativitas_media': 3, 'pemahaman_konsep': 3}, ruang=ruang)
        b = susun_narasi_bidang(ruang, self.siswa)
        self.assertEqual(b['fisik_motorik'], '')
        self.assertIn('bernalar sebab-akibat', b['akademik'])


class BatasKekuatanDanTumbuhTest(DasarNarasi):
    """Batas maksimal dua kekuatan / dua area berkembang, diuji di jenjang yang punya 3 dimensi akademik."""
    kelas = '5'
    jenjang = 'sd_akhir'

    def test_maksimal_dua_kekuatan(self):
        self.karya({'sebab_akibat': 4, 'kreativitas_media': 3, 'pemahaman_konsep': 3})
        t = susun_narasi_kreasi(self.ruang, self.siswa)
        self.assertIn('sangat baik dalam bernalar sebab-akibat', t)
        self.assertIn('Selain itu, Ani mampu memilih media yang sesuai', t)
        self.assertNotIn('memahami konsep dasar dan menerapkannya', t)      # kekuatan ketiga tidak ditampilkan

    def test_maksimal_dua_area_berkembang_yang_terendah_dulu(self):
        self.karya({'sebab_akibat': 2, 'kreativitas_media': 1, 'pemahaman_konsep': 2})
        t = susun_narasi_kreasi(self.ruang, self.siswa)
        self.assertLess(t.index('meniru contoh'), t.index('menjelaskan hubungan sederhana'))   # level 1 lebih dulu dari level 2
        self.assertNotIn('memahami sebagian konsep dasar', t)                               # area ketiga tidak ditampilkan


class HalamanRaporTest(DasarNarasi):
    """Halaman rapor guru (template asli) dan halaman rapor siswa, setelah pemasangan tahap 4."""

    def setUp(self):
        AnggotaRuangKerja.objects.create(ruang_kerja=self.ruang, siswa=self.siswa)

    def rapor_guru(self):
        self.client.force_login(self.guru)
        return self.client.get(reverse('ruang_kerja:rapor_ruang_kerja', args=[self.ruang.id]))

    def baris(self, r, siswa=None):
        return next(b for b in r.context['data'] if b['siswa'] == (siswa or self.siswa))

    def test_kolom_fisik_terisi_draf_dan_ada_keterangan(self):
        self.karya({KEB: 4, MOT: 3, LIS: 3})
        r = self.rapor_guru()
        self.assertEqual(r.status_code, 200)
        b = self.baris(r)
        self.assertEqual(b['catatan_fisik_motorik'], 'Ani cukup terampil mengendalikan alat kerja sehingga karyanya tersusun dengan rapi.')
        self.assertTrue(b['draft_fisik'])
        self.assertContains(r, 'Ani cukup terampil mengendalikan alat kerja sehingga karyanya tersusun dengan rapi.')
        self.assertContains(r, 'Draft dari rubrik kreasi')

    def test_kolom_akademik_tidak_memuat_kalimat_motorik(self):
        self.karya({KEB: 4, MOT: 3, LIS: 3})
        b = self.baris(self.rapor_guru())
        self.assertIn('Ani telah menyelesaikan 1 karya kreasi', b['draft_komentar'])
        self.assertNotIn('terampil', b['draft_komentar'])

    def test_siswa_tanpa_karya_tanpa_draf_dan_tanpa_keterangan(self):
        r = self.rapor_guru()
        b = self.baris(r)
        self.assertEqual(b['catatan_fisik_motorik'], '')
        self.assertFalse(b['draft_fisik'])
        self.assertNotContains(r, 'Draft dari rubrik kreasi')

    def test_catatan_fisik_tersimpan_tidak_ditimpa_draf(self):
        self.karya({KEB: 4, MOT: 3, LIS: 3})
        CatatanRapor.objects.create(ruang_kerja=self.ruang, siswa=self.siswa, catatan_fisik_motorik='Tulisan guru sendiri.')
        r = self.rapor_guru()
        b = self.baris(r)
        self.assertEqual(b['catatan_fisik_motorik'], 'Tulisan guru sendiri.')
        self.assertFalse(b['draft_fisik'])
        self.assertNotContains(r, 'Draft dari rubrik kreasi')

    def test_simpan_lalu_muat_ulang_memakai_yang_tersimpan(self):
        self.karya({KEB: 4, MOT: 3, LIS: 3})
        b = self.baris(self.rapor_guru())
        self.client.post(reverse('ruang_kerja:simpan_catatan_rapor', args=[self.ruang.id, self.siswa.id]), {
            'catatan': b['draft_komentar'], 'catatan_disiplin': '',
            'catatan_fisik_motorik': b['catatan_fisik_motorik'] + ' Ditambah catatan guru.'})
        b2 = self.baris(self.rapor_guru())
        self.assertTrue(b2['catatan_fisik_motorik'].endswith('Ditambah catatan guru.'))
        self.assertFalse(b2['draft_fisik'])

    def test_rapor_siswa_hanya_menampilkan_yang_sudah_disimpan_guru(self):
        self.karya({KEB: 4, MOT: 3, LIS: 3})
        self.client.force_login(self.siswa.user)
        r = self.client.get(reverse('ruang_kerja:rapor_siswa', args=[self.ruang.id, self.siswa.id]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['catatan'], '')                 # draf otomatis tidak bocor ke siswa/orang tua
        self.assertEqual(r.context['catatan_fisik_motorik'], '')
        CatatanRapor.objects.create(ruang_kerja=self.ruang, siswa=self.siswa, catatan='Disimpan guru.', catatan_fisik_motorik='Motorik disimpan guru.')
        r = self.client.get(reverse('ruang_kerja:rapor_siswa', args=[self.ruang.id, self.siswa.id]))
        self.assertEqual((r.context['catatan'], r.context['catatan_fisik_motorik']), ('Disimpan guru.', 'Motorik disimpan guru.'))

    def test_tambahan_query_per_siswa_terkendali(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        def jumlah():
            with CaptureQueriesContext(connection) as q:
                self.rapor_guru()
            return len(q)
        satu = jumlah()
        for i in range(3):
            u = User.objects.create_user(f'x{i}', password='x', role='siswa')
            s = Siswa.objects.create(user=u, nama=f'Siswa {i}', nis=f'9{i}', kelas='3')
            AnggotaRuangKerja.objects.create(ruang_kerja=self.ruang, siswa=s)
            self.karya({KEB: 3, MOT: 3, LIS: 3}, siswa=s)
        empat = jumlah()
        self.assertLessEqual((empat - satu) / 3, 20, f'{satu} query untuk 1 siswa, {empat} untuk 4')
