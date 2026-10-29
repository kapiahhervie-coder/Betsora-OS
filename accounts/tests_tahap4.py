"""Tes Tahap 4a: Django admin khusus admin platform, pengaturan per sekolah, pendaftaran sekolah."""
import importlib.util
import os
from io import StringIO

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import RequestFactory, TestCase
from django.urls import reverse

from accounts.models import Sekolah
from accounts.tenancy import TOLAK, dalam_sekolah
from pengaturan.models import PengaturanSekolah

User = get_user_model()


def _sekolah(nama, kode):
    s = Sekolah.objects.create(nama=nama, kode=kode)
    guru = User.objects.create_user(f'guru-{kode}', password='x', role='guru', sekolah=s)
    return s, guru


class PengaturanPerSekolahTest(TestCase):
    def setUp(self):
        self.a, self.ga = _sekolah('SD Alfa', 'alfa')
        self.b, self.gb = _sekolah('SMP Beta', 'beta')

    def test_tiap_sekolah_punya_pengaturan_sendiri(self):
        with dalam_sekolah(self.a):
            pa = PengaturanSekolah.get_settings()
        with dalam_sekolah(self.b):
            pb = PengaturanSekolah.get_settings()
        self.assertNotEqual(pa.pk, pb.pk)
        self.assertEqual((pa.sekolah_id, pa.nama_institusi), (self.a.id, 'SD Alfa'))
        self.assertEqual((pb.sekolah_id, pb.nama_institusi), (self.b.id, 'SMP Beta'))

    def test_perubahan_satu_sekolah_tidak_mempengaruhi_yang_lain(self):
        with dalam_sekolah(self.a):
            p = PengaturanSekolah.get_settings()
            p.nama_institusi = 'Alfa Baru'
            p.sub_judul = 'Rahasia Alfa'
            p.save()
        with dalam_sekolah(self.b):
            pb = PengaturanSekolah.get_settings()
            self.assertEqual(pb.nama_institusi, 'SMP Beta')
            self.assertEqual(pb.sub_judul, '')
        with dalam_sekolah(self.a):
            self.assertEqual(PengaturanSekolah.get_settings().nama_institusi, 'Alfa Baru')
        self.assertEqual(PengaturanSekolah.objects.count(), 2)

    def test_panggilan_berulang_tidak_membuat_baris_ganda(self):
        with dalam_sekolah(self.a):
            PengaturanSekolah.get_settings()
            PengaturanSekolah.get_settings()
        self.assertEqual(PengaturanSekolah.objects.filter(sekolah=self.a).count(), 1)

    def test_tanpa_sekolah_aktif_dan_banyak_pengaturan_tampil_netral(self):
        with dalam_sekolah(self.a):
            PengaturanSekolah.get_settings()
        with dalam_sekolah(self.b):
            PengaturanSekolah.get_settings()
        netral = PengaturanSekolah.get_settings()  # halaman login: tanpa sekolah aktif
        self.assertIsNone(netral.pk)
        self.assertNotIn('Alfa', netral.nama_institusi)
        self.assertNotIn('Beta', netral.nama_institusi)
        self.assertEqual(PengaturanSekolah.objects.count(), 2)  # tidak menulis apa pun

    def test_hanya_satu_pengaturan_dipakai_di_halaman_login(self):
        with dalam_sekolah(self.a):
            p = PengaturanSekolah.get_settings()
        self.assertEqual(PengaturanSekolah.get_settings().pk, p.pk)

    def test_sekolah_nonaktif_tampil_netral(self):
        with dalam_sekolah(self.a):
            PengaturanSekolah.get_settings()
        with dalam_sekolah(TOLAK):
            self.assertIsNone(PengaturanSekolah.get_settings().pk)

    def test_context_processor_memakai_sekolah_pengguna(self):
        from pengaturan.context_processors import pengaturan_sekolah
        req = RequestFactory().get('/')
        with dalam_sekolah(self.b):
            self.assertEqual(pengaturan_sekolah(req)['pengaturan'].nama_institusi, 'SMP Beta')

    def test_halaman_web_memakai_pengaturan_sekolah_pengguna(self):
        self.client.force_login(self.ga)
        r = self.client.get(reverse('kelas:dashboard'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['pengaturan'].nama_institusi, 'SD Alfa')
        self.client.force_login(self.gb)
        r = self.client.get(reverse('kelas:dashboard'))
        self.assertEqual(r.context['pengaturan'].nama_institusi, 'SMP Beta')

    def test_satu_pengaturan_per_sekolah_dijamin_basis_data(self):
        from django.db import IntegrityError, transaction
        PengaturanSekolah.objects.create(sekolah=self.a)
        with self.assertRaises(IntegrityError), transaction.atomic():
            PengaturanSekolah.objects.create(sekolah=self.a)


def _muat_migrasi():
    import pengaturan
    jalur = os.path.join(os.path.dirname(pengaturan.__file__), 'migrations')
    cocok = [f for f in os.listdir(jalur) if f.endswith('_tautkan_sekolah_awal.py')]
    assert len(cocok) == 1, 'migrasi tautkan_sekolah_awal tidak ditemukan'
    spek = importlib.util.spec_from_file_location('mig_tautkan', os.path.join(jalur, cocok[0]))
    modul = importlib.util.module_from_spec(spek)
    spek.loader.exec_module(modul)
    return modul


class MigrasiTautkanTest(TestCase):
    def test_pengaturan_lama_ditautkan_bila_hanya_satu_sekolah(self):
        s = Sekolah.objects.create(nama='Satu', kode='satu')
        lama = PengaturanSekolah.objects.create(nama_institusi='Satu')
        self.assertIsNone(lama.sekolah_id)
        _muat_migrasi().tautkan(apps, None)
        lama.refresh_from_db()
        self.assertEqual(lama.sekolah_id, s.id)
        _muat_migrasi().tautkan(apps, None)  # aman diulang
        self.assertEqual(PengaturanSekolah.objects.count(), 1)

    def test_dibiarkan_bila_banyak_sekolah(self):
        Sekolah.objects.create(nama='A', kode='a')
        Sekolah.objects.create(nama='B', kode='b')
        lama = PengaturanSekolah.objects.create(nama_institusi='Lama')
        _muat_migrasi().tautkan(apps, None)
        lama.refresh_from_db()
        self.assertIsNone(lama.sekolah_id)

    def test_tanpa_sekolah_tidak_error(self):
        PengaturanSekolah.objects.create(nama_institusi='Lama')
        _muat_migrasi().tautkan(apps, None)


class DjangoAdminTest(TestCase):
    def setUp(self):
        self.a, self.ga = _sekolah('SD Alfa', 'alfa')
        self.kepsek = User.objects.create_user('kepsek-a', password='x', role='kepsek', sekolah=self.a, is_staff=True)
        self.su = User.objects.create_superuser('platform', password='x')

    def test_hanya_superuser_masuk_django_admin(self):
        for u in (self.ga, self.kepsek):  # termasuk akun is_staff=True
            self.client.force_login(u)
            r = self.client.get(reverse('admin:index'))
            self.assertEqual(r.status_code, 302, u.username)
            self.assertIn('login', r['Location'])
            self.assertEqual(self.client.get(reverse('admin:accounts_sekolah_changelist')).status_code, 302)
            self.assertEqual(self.client.get(reverse('admin:accounts_user_changelist')).status_code, 302)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('admin:index')).status_code, 302)

    def test_superuser_masuk_dan_melihat_semua_sekolah(self):
        self.client.force_login(self.su)
        self.assertEqual(self.client.get(reverse('admin:index')).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:accounts_sekolah_changelist')).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:accounts_user_changelist')).status_code, 200)

    def test_form_user_memuat_kolom_sekolah(self):
        from django.contrib import admin
        from accounts.models import User as U
        ma = admin.site._registry[U]
        for fieldsets in (ma.fieldsets, ma.add_fieldsets):
            kolom = [k for _, opsi in fieldsets for k in opsi['fields']]
            self.assertIn('sekolah', kolom)
        self.assertIn('sekolah', ma.list_display)

    def test_superuser_dapat_menetapkan_sekolah_lewat_admin(self):
        self.client.force_login(self.su)
        r = self.client.post(reverse('admin:accounts_user_add'), {
            'username': 'baru-admin', 'password1': 'Sangat-Rahasia-123', 'password2': 'Sangat-Rahasia-123',
            'role': 'guru', 'sekolah': self.a.id,
        })
        self.assertEqual(r.status_code, 302, getattr(r, 'context', None) and r.context.get('errors'))
        self.assertEqual(User.objects.get(username='baru-admin').sekolah_id, self.a.id)


class BuatSekolahTest(TestCase):
    def jalankan(self, *args):
        keluar = StringIO()
        call_command('buat_sekolah', *args, stdout=keluar)
        return keluar.getvalue()

    def test_membuat_sekolah_pengaturan_dan_kepsek(self):
        teks = self.jalankan('SD Harapan', '--kode', 'harapan', '--kepsek', 'kepsek.harapan', '--nama-kepsek', 'Ibu Sari')
        s = Sekolah.objects.get(kode='harapan')
        self.assertEqual(s.nama, 'SD Harapan')
        self.assertEqual(PengaturanSekolah.objects.get(sekolah=s).nama_institusi, 'SD Harapan')
        kepsek = User.objects.get(username='kepsek.harapan')
        self.assertEqual((kepsek.role, kepsek.sekolah_id, kepsek.first_name), ('kepsek', s.id, 'Ibu Sari'))
        self.assertFalse(kepsek.is_superuser)
        sandi = teks.split('Kata sandi sementara: ')[1].split()[0]
        self.assertTrue(kepsek.check_password(sandi))
        self.assertTrue(self.client.login(username='kepsek.harapan', password=sandi))

    def test_kode_bawaan_dari_nama(self):
        self.jalankan('SMP Negeri 1', '--kepsek', 'k1')
        self.assertTrue(Sekolah.objects.filter(kode='smp-negeri-1').exists())

    def test_kode_atau_username_bentrok_ditolak_tanpa_sisa(self):
        self.jalankan('A', '--kode', 'a', '--kepsek', 'ka')
        with self.assertRaises(CommandError):
            self.jalankan('B', '--kode', 'a', '--kepsek', 'kb')
        with self.assertRaises(CommandError):
            self.jalankan('B', '--kode', 'b', '--kepsek', 'KA')
        self.assertEqual(Sekolah.objects.count(), 1)
        self.assertEqual(User.objects.count(), 1)

    def test_kode_tidak_sah_ditolak(self):
        with self.assertRaises(CommandError):
            self.jalankan('B', '--kode', 'Beta Sekolah!', '--kepsek', 'kb')

    def test_dua_sekolah_terdaftar_saling_terpisah(self):
        self.jalankan('Alfa', '--kode', 'alfa', '--kepsek', 'ka')
        self.jalankan('Beta', '--kode', 'beta', '--kepsek', 'kb')
        a, b = Sekolah.objects.get(kode='alfa'), Sekolah.objects.get(kode='beta')
        with dalam_sekolah(a):
            self.assertEqual({u.username for u in User.objects.all()}, {'ka'})
            self.assertEqual(PengaturanSekolah.get_settings().nama_institusi, 'Alfa')
        with dalam_sekolah(b):
            self.assertEqual({u.username for u in User.objects.all()}, {'kb'})
            self.assertEqual(PengaturanSekolah.get_settings().nama_institusi, 'Beta')
