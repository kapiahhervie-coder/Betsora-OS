from django.db import migrations
from django.utils.text import slugify

# Model yang dimiliki sebuah sekolah dan perlu ditandai. Pengguna ditangani terpisah (superuser tidak ikut).
MODEL_SEKOLAH = [
    ('accounts', 'Siswa'),
    ('ruang_kerja', 'Kelas'),
    ('ruang_kerja', 'RuangKerja'),
    ('ruang_kerja', 'MataPelajaran'),
    ('penilaian', 'SesiPenilaian'),
    ('perpustakaan', 'Zona'),
    ('perpustakaan', 'AlbumAudio'),
    ('perpustakaan', 'Lencana'),
]


def isi_sekolah_awal(apps, schema_editor):
    """Data yang sudah ada (milik satu sekolah) ditandai sebagai "sekolah awal".

    Hanya berjalan bila memang ada data. Database kosong (instalasi baru, database uji) tidak dibuatkan sekolah.
    Akun superuser tetap tanpa sekolah: itu admin platform.
    """
    Sekolah = apps.get_model('accounts', 'Sekolah')
    User = apps.get_model('accounts', 'User')

    ada_data = User.objects.filter(is_superuser=False).exists() or any(
        apps.get_model(app, nama).objects.exists() for app, nama in MODEL_SEKOLAH
    )
    if not ada_data:
        return

    if Sekolah.objects.count() > 1:
        # Sudah ada beberapa sekolah: pemilik data tanpa sekolah tidak bisa ditebak. Dibiarkan kosong
        # (tidak terlihat oleh sekolah mana pun); tangani manual lewat perintah periksa_sekolah.
        return

    sekolah = Sekolah.objects.first()
    if sekolah is None:
        Pengaturan = apps.get_model('pengaturan', 'PengaturanSekolah')
        p = Pengaturan.objects.filter(pk=1).first()
        nama = (p.nama_institusi if p and p.nama_institusi else 'Sekolah Awal')
        kode = slugify(nama)[:30] or 'awal'
        sekolah = Sekolah.objects.create(nama=nama, kode=kode)

    User.objects.filter(sekolah__isnull=True, is_superuser=False).update(sekolah=sekolah)
    for app, nama in MODEL_SEKOLAH:
        apps.get_model(app, nama).objects.filter(sekolah__isnull=True).update(sekolah=sekolah)
    apps.get_model('pengaturan', 'PengaturanSekolah').objects.filter(pk=1, sekolah__isnull=True).update(sekolah=sekolah)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_sekolah_alter_siswa_nis_siswa_sekolah_user_sekolah_and_more'),
        ('ruang_kerja', '0023_alter_ruangkerja_unique_together_kelas_sekolah_and_more'),
        ('penilaian', '0002_sesipenilaian_sekolah'),
        ('perpustakaan', '0008_albumaudio_sekolah_lencana_sekolah_zona_sekolah'),
        ('pengaturan', '0002_pengaturansekolah_sekolah')
    ]

    operations = [
        migrations.RunPython(isi_sekolah_awal, migrations.RunPython.noop),
    ]
