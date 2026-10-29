"""Menautkan pengaturan lama (satu baris, tanpa sekolah) ke sekolah awal bila hanya ada satu sekolah."""
from django.db import migrations


def tautkan(apps, schema_editor):
    Sekolah = apps.get_model('accounts', 'Sekolah')
    Pengaturan = apps.get_model('pengaturan', 'PengaturanSekolah')
    sekolah = list(Sekolah.objects.all()[:2])
    if len(sekolah) != 1:
        return  # nol sekolah: tidak ada yang ditautkan; banyak sekolah: ambigu, dibiarkan
    lama = Pengaturan.objects.filter(sekolah__isnull=True).order_by('pk').first()
    if lama is not None and not Pengaturan.objects.filter(sekolah=sekolah[0]).exists():
        lama.sekolah = sekolah[0]
        lama.save(update_fields=['sekolah'])


class Migration(migrations.Migration):
    dependencies = [
        ('pengaturan', '0002_pengaturansekolah_sekolah'),
        ('accounts', '0005_isi_sekolah_awal'),
    ]
    operations = [migrations.RunPython(tautkan, migrations.RunPython.noop)]
