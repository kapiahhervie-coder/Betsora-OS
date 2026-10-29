from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count

MODEL = [
    ('accounts', 'Siswa'),
    ('ruang_kerja', 'Kelas'),
    ('ruang_kerja', 'RuangKerja'),
    ('ruang_kerja', 'MataPelajaran'),
    ('penilaian', 'SesiPenilaian'),
    ('perpustakaan', 'Zona'),
    ('perpustakaan', 'AlbumAudio'),
    ('perpustakaan', 'Lencana'),
]


class Command(BaseCommand):
    help = 'Memeriksa data tanpa sekolah (yatim) dan menghitung data per sekolah. Gunakan --ketat sebelum deploy.'

    def add_arguments(self, parser):
        parser.add_argument('--ketat', action='store_true', help='Gagal (kode keluar 1) bila ada data tanpa sekolah')

    def handle(self, *args, **opsi):
        Sekolah = apps.get_model('accounts', 'Sekolah')
        User = apps.get_model('accounts', 'User')
        yatim = {}

        yatim['accounts.User (bukan superuser)'] = User.objects.filter(sekolah__isnull=True, is_superuser=False).count()
        for app, nama in MODEL:
            yatim[f'{app}.{nama}'] = apps.get_model(app, nama).objects.filter(sekolah__isnull=True).count()

        self.stdout.write('Data TANPA sekolah:')
        total = 0
        for k, v in yatim.items():
            total += v
            self.stdout.write(f'  {k}: {v}')

        self.stdout.write('')
        self.stdout.write('Data per sekolah:')
        for s in Sekolah.objects.all().order_by('nama'):
            baris = [f'pengguna={User.objects.filter(sekolah=s).count()}']
            for app, nama in MODEL:
                baris.append(f"{nama.lower()}={apps.get_model(app, nama).objects.filter(sekolah=s).count()}")
            self.stdout.write(f'  [{s.kode}] {s.nama}: ' + ', '.join(baris))
        if not Sekolah.objects.exists():
            self.stdout.write('  (belum ada sekolah)')

        if total and opsi['ketat']:
            raise CommandError(f'{total} baris data belum punya sekolah.')
        self.stdout.write(self.style.SUCCESS('Selesai.' if not total else f'Selesai: {total} baris tanpa sekolah.'))
