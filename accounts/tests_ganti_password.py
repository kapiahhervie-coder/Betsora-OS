"""Ganti password: untuk semua role, lewat middleware & template asli."""
from django.contrib.auth import SESSION_KEY
from django.test import TestCase
from django.urls import reverse

from .models import Siswa, User


class DasarGantiPassword(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.guru = User.objects.create_user('guru1', password='PasswordLama123', role='guru')
        cls.u_siswa = User.objects.create_user('siswa1', password='PasswordLama123', role='siswa')
        cls.siswa = Siswa.objects.create(user=cls.u_siswa, nama='Ani Lestari', nis='1', kelas='3')
        cls.u_ortu = User.objects.create_user('ortu1', password='PasswordLama123', role='orangtua', anak=cls.siswa)

    def url(self):
        return reverse('accounts:ganti_password')

    def masuk(self, user):
        self.client.logout()
        self.client.force_login(user)

    def kirim(self, lama='PasswordLama123', baru='PasswordBaruAman99', konfirmasi=None):
        return self.client.post(self.url(), {
            'password_lama': lama, 'password_baru': baru,
            'konfirmasi_password': konfirmasi if konfirmasi is not None else baru,
        })


class AksesHalamanTest(DasarGantiPassword):
    def test_belum_login_diarahkan_ke_login(self):
        r = self.client.get(self.url())
        self.assertEqual(r.status_code, 302)
        self.assertIn('login', r['Location'])

    def test_semua_role_bisa_membuka_form(self):
        for u in [self.guru, self.u_siswa, self.u_ortu]:
            self.masuk(u)
            r = self.client.get(self.url())
            self.assertEqual(r.status_code, 200, u.username)
            self.assertContains(r, 'Password Lama')
            self.assertContains(r, 'name="password_baru"')

    def test_orangtua_diizinkan_middleware(self):
        """Middleware orang tua sangat ketat (hanya dashboard & logout); pastikan path ini juga diizinkan."""
        self.masuk(self.u_ortu)
        r = self.client.get(self.url())
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, 'Redirecting')

    def test_orangtua_tetap_terblokir_dari_halaman_lain(self):
        """Regresi: menambah 1 path baru tidak melonggarkan aturan untuk path lain."""
        self.masuk(self.u_ortu)
        r = self.client.get(reverse('accounts:daftar_siswa'))
        self.assertEqual(r.status_code, 302)
        self.assertIn('dashboard-orangtua', r['Location'])

    def test_link_muncul_di_sidebar_untuk_semua_role(self):
        # guru: base.html dirender lewat kelas:dashboard. Siswa & orang tua: lewat dashboard
        # masing-masing, karena kelas:dashboard mengalihkan siswa (bukan halamannya).
        for u, nama_url in [(self.guru, 'kelas:dashboard'), (self.u_siswa, 'accounts:dashboard_siswa'),
                            (self.u_ortu, 'accounts:dashboard_orangtua')]:
            self.masuk(u)
            r = self.client.get(reverse(nama_url))
            self.assertContains(r, reverse('accounts:ganti_password'), msg_prefix=u.username)
            self.assertContains(r, 'Ganti Password', msg_prefix=u.username)


class ValidasiTest(DasarGantiPassword):
    def test_password_lama_salah_ditolak(self):
        self.masuk(self.guru)
        r = self.kirim(lama='salah-total')
        self.assertContains(r, 'Password lama tidak sesuai')
        self.guru.refresh_from_db()
        self.assertTrue(self.guru.check_password('PasswordLama123'))

    def test_konfirmasi_tidak_cocok_ditolak(self):
        self.masuk(self.guru)
        r = self.kirim(baru='PasswordBaruAman99', konfirmasi='BedaSendiri99')
        self.assertContains(r, 'tidak cocok')
        self.guru.refresh_from_db()
        self.assertTrue(self.guru.check_password('PasswordLama123'))

    def test_password_terlalu_pendek_ditolak(self):
        self.masuk(self.guru)
        r = self.kirim(baru='pendek1', konfirmasi='pendek1')
        self.assertEqual(r.status_code, 200)
        self.guru.refresh_from_db()
        self.assertTrue(self.guru.check_password('PasswordLama123'))

    def test_password_terlalu_umum_ditolak(self):
        self.masuk(self.guru)
        r = self.kirim(baru='password123', konfirmasi='password123')
        self.assertEqual(r.status_code, 200)
        self.guru.refresh_from_db()
        self.assertTrue(self.guru.check_password('PasswordLama123'))

    def test_password_mirip_username_ditolak(self):
        # 'guru1abcd' (9 char, lolos syarat panjang minimal) sengaja dibuat mirip 'guru1'
        # agar TEPAT UserAttributeSimilarityValidator yang menolaknya, bukan validator lain.
        self.masuk(self.guru)
        r = self.kirim(baru='guru1abcd', konfirmasi='guru1abcd')
        self.assertEqual(r.status_code, 200)
        self.guru.refresh_from_db()
        self.assertTrue(self.guru.check_password('PasswordLama123'))

    def test_password_kosong_ditolak_bukan_error_500(self):
        self.masuk(self.guru)
        r = self.kirim(baru='', konfirmasi='')
        self.assertEqual(r.status_code, 200)
        self.guru.refresh_from_db()
        self.assertTrue(self.guru.check_password('PasswordLama123'))


class BerhasilTest(DasarGantiPassword):
    def test_password_berhasil_diganti(self):
        self.masuk(self.guru)
        r = self.kirim()
        self.assertEqual(r.status_code, 302)
        self.guru.refresh_from_db()
        self.assertTrue(self.guru.check_password('PasswordBaruAman99'))
        self.assertFalse(self.guru.check_password('PasswordLama123'))

    def test_diarahkan_sesuai_dashboard_masing_masing_role(self):
        for u, nama_url in [(self.guru, 'kelas:dashboard'), (self.u_siswa, 'accounts:dashboard_siswa'),
                            (self.u_ortu, 'accounts:dashboard_orangtua')]:
            self.masuk(u)
            r = self.kirim()
            self.assertRedirects(r, reverse(nama_url), fetch_redirect_response=False)
            u.set_password('PasswordLama123'); u.save()   # kembalikan utk role berikutnya

    def test_pesan_sukses_tampil(self):
        # Pakai alur orang tua: dashboard-nya sudah lengkap ter-wire di sandbox ini (base.html asli
        # butuh banyak namespace app lain -- pesan, perpustakaan, dst -- yang di luar cakupan tes ini).
        self.masuk(self.u_ortu)
        r = self.kirim()
        r = self.client.get(r.url)
        self.assertContains(r, 'Password berhasil diganti')

    def test_sesi_tidak_terputus_setelah_ganti(self):
        """update_session_auth_hash: user TIDAK boleh ter-logout paksa setelah ganti password."""
        self.masuk(self.guru)
        session_key_sebelum = self.client.session.get(SESSION_KEY)
        self.kirim()
        r = self.client.get(reverse('kelas:dashboard'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.client.session.get(SESSION_KEY), session_key_sebelum)

    def test_bisa_login_ulang_dengan_password_baru(self):
        self.masuk(self.guru)
        self.kirim()
        self.client.logout()
        masuk = self.client.login(username='guru1', password='PasswordBaruAman99')
        self.assertTrue(masuk)

    def test_tidak_bisa_login_lagi_dengan_password_lama(self):
        self.masuk(self.guru)
        self.kirim()
        self.client.logout()
        masuk = self.client.login(username='guru1', password='PasswordLama123')
        self.assertFalse(masuk)

    def test_orangtua_bisa_ganti_password_end_to_end(self):
        self.masuk(self.u_ortu)
        r = self.kirim()
        self.assertEqual(r.status_code, 302)
        self.client.logout()
        self.assertTrue(self.client.login(username='ortu1', password='PasswordBaruAman99'))
