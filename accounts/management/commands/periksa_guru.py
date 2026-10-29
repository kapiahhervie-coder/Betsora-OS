"""Laporan: siapa guru yang melihat siapa. Jalankan sebelum dan sesudah memasang Tahap 3.

    python manage.py periksa_guru
    python manage.py periksa_guru --sekolah betsora-os

Hanya membaca database, tidak mengubah apa pun.
"""
from django.core.management.base import BaseCommand

from accounts.models import Siswa, Sekolah, User
from accounts.tenancy import PeranGuru
from ruang_kerja.models import RuangKerja


class Command(BaseCommand):
    help = 'Melaporkan jumlah ruang kerja dan siswa yang terlihat oleh tiap guru, serta data yatim.'

    def add_arguments(self, parser):
        parser.add_argument('--sekolah', help='Kode sekolah (bawaan: semua sekolah)')

    def handle(self, *args, **opts):
        daftar = Sekolah.objects.all()
        if opts.get('sekolah'):
            daftar = daftar.filter(kode=opts['sekolah'])
        if not daftar.exists():
            self.stdout.write('Tidak ada sekolah.')
            return
        for s in daftar:
            self.stdout.write(self.style.MIGRATE_HEADING(f'[{s.kode}] {s.nama}'))
            semua = set(Siswa._base_manager.filter(sekolah=s).values_list('pk', flat=True))
            terlihat_guru = set()
            for g in User._base_manager.filter(sekolah=s, role='guru').order_by('username'):
                ruang = RuangKerja._base_manager.filter(sekolah=s, guru=g).count()
                ids = PeranGuru(g.pk, s.pk).siswa_ids
                terlihat_guru |= ids
                peringatan = '   <- tidak melihat siapa pun' if not ids else ''
                self.stdout.write(f'  guru {g.username}: {ruang} ruang kerja, {len(ids)} siswa terlihat{peringatan}')
            tanpa_guru = RuangKerja._base_manager.filter(sekolah=s, guru__isnull=True)
            if tanpa_guru.exists():
                self.stdout.write(self.style.WARNING(
                    f'  {tanpa_guru.count()} ruang kerja TANPA guru (hanya terlihat kepala sekolah/admin): '
                    + ', '.join(str(r) for r in tanpa_guru[:10])))
            yatim = Siswa._base_manager.filter(pk__in=semua - terlihat_guru)
            if yatim.exists():
                self.stdout.write(self.style.WARNING(
                    f'  {yatim.count()} siswa tidak terlihat oleh guru mana pun (hanya kepala sekolah/admin): '
                    + ', '.join(f'{x.nama} ({x.kelas})' for x in yatim[:15])))
            self.stdout.write(f'  total siswa: {len(semua)}')
