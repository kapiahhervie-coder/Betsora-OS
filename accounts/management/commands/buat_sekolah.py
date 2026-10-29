"""Mendaftarkan sekolah baru beserta akun kepala sekolahnya (dilakukan admin platform, tanpa pendaftaran mandiri).

    python manage.py buat_sekolah "SD Harapan" --kode harapan --kepsek kepsek.harapan --nama-kepsek "Ibu Sari"

Mencetak kata sandi sementara SATU KALI. Kepala sekolah menggantinya lewat menu Ganti Password.
"""
import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.crypto import get_random_string
from django.utils.text import slugify

from accounts.models import Sekolah, User


class Command(BaseCommand):
    help = 'Mendaftarkan sekolah baru dan akun kepala sekolahnya.'

    def add_arguments(self, parser):
        parser.add_argument('nama', help='Nama sekolah')
        parser.add_argument('--kode', help='Singkatan unik (huruf kecil, angka, tanda minus). Bawaan: dari nama')
        parser.add_argument('--kepsek', required=True, help='Nama pengguna (username) akun kepala sekolah')
        parser.add_argument('--nama-kepsek', default='', help='Nama lengkap kepala sekolah')

    def handle(self, *args, **opts):
        nama = opts['nama'].strip()
        if not nama:
            raise CommandError('Nama sekolah wajib diisi.')
        kode = (opts['kode'] or slugify(nama))[:30]
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', kode):
            raise CommandError('Kode sekolah hanya boleh huruf kecil, angka, dan tanda minus.')
        username = opts['kepsek'].strip()
        if not username:
            raise CommandError('Nama pengguna kepala sekolah wajib diisi.')
        if Sekolah.objects.filter(kode=kode).exists():
            raise CommandError(f'Kode sekolah "{kode}" sudah dipakai.')
        if User._base_manager.filter(username__iexact=username).exists():
            raise CommandError(f'Nama pengguna "{username}" sudah dipakai.')
        from pengaturan.models import PengaturanSekolah

        password = get_random_string(10, allowed_chars='abcdefghjkmnpqrstuvwxyz23456789')
        with transaction.atomic():
            sekolah = Sekolah.objects.create(nama=nama, kode=kode)
            PengaturanSekolah._base_manager.create(sekolah=sekolah, nama_institusi=nama)
            User.objects.create_user(
                username=username, password=password, role='kepsek',
                first_name=opts['nama_kepsek'].strip(), sekolah=sekolah,
            )
        self.stdout.write(self.style.SUCCESS(f'Sekolah "{nama}" (kode {kode}) dibuat.'))
        self.stdout.write(f'Akun kepala sekolah: {username}')
        self.stdout.write(f'Kata sandi sementara: {password}   (catat sekarang, tidak ditampilkan lagi)')
