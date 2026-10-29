"""Aturan portofolio antarsiswa: karya dibagikan -> terlihat siswa lain; tidak ada yang dibagikan -> tertutup."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import Sekolah, Siswa
from portofolio.models import KaryaSiswa

User = get_user_model()


class PortofolioAntarSiswaTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        s = Sekolah.objects.create(nama='Alfa', kode='alfa')
        b = Sekolah.objects.create(nama='Beta', kode='beta')

        def siswa(n):
            sis = Siswa.objects.create(nama=f'Siswa-{n}', nis=n, kelas='4', sekolah=s)
            u = User.objects.create_user(f'u{n}', password='x', role='siswa', sekolah=s)
            sis.user = u
            sis.save()
            return sis, u

        cls.s1, cls.u1 = siswa('1')
        cls.s2, cls.u2 = siswa('2')
        cls.sb = Siswa.objects.create(nama='Siswa-B', nis='9', kelas='4', sekolah=b)

    def buka(self, akun, siswa):
        self.client.force_login(akun)
        return self.client.get(f'/portofolio/{siswa.id}/')

    def test_pemilik_boleh_membuka_portofolio_sendiri(self):
        self.assertEqual(self.buka(self.u1, self.s1).status_code, 200)

    def test_tanpa_karya_dibagikan_siswa_lain_ditolak(self):
        self.assertEqual(self.buka(self.u1, self.s2).status_code, 403)

    def test_karya_tidak_dibagikan_tetap_tertutup(self):
        KaryaSiswa.objects.create(siswa=self.s2, judul='Pribadi', video_url='https://www.youtube.com/watch?v=abcdefghijk', dibagikan=False)
        self.assertEqual(self.buka(self.u1, self.s2).status_code, 403)

    def test_karya_dibagikan_terlihat_dan_yang_pribadi_tidak(self):
        KaryaSiswa.objects.create(siswa=self.s2, judul='Pribadi', video_url='https://www.youtube.com/watch?v=abcdefghijk', dibagikan=False)
        KaryaSiswa.objects.create(siswa=self.s2, judul='Dibagi', video_url='https://www.youtube.com/watch?v=abcdefghijk', dibagikan=True)
        r = self.buka(self.u1, self.s2)
        self.assertEqual(r.status_code, 200)
        judul = [k.judul for k in r.context['karya_list']]
        self.assertEqual(judul, ['Dibagi'])

    def test_tertutup_lagi_bila_karya_tidak_lagi_dibagikan(self):
        k = KaryaSiswa.objects.create(siswa=self.s2, judul='Dibagi', video_url='https://www.youtube.com/watch?v=abcdefghijk', dibagikan=True)
        self.assertEqual(self.buka(self.u1, self.s2).status_code, 200)
        k.dibagikan = False
        k.save()
        self.assertEqual(self.buka(self.u1, self.s2).status_code, 403)

    def test_siswa_sekolah_lain_tidak_pernah_terbuka(self):
        KaryaSiswa.objects.create(siswa=self.sb, judul='Dibagi', video_url='https://www.youtube.com/watch?v=abcdefghijk', dibagikan=True)
        self.assertIn(self.buka(self.u1, self.sb).status_code, (403, 404))
