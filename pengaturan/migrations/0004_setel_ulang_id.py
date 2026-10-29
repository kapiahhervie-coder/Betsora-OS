"""Menyetel ulang penghitung id PostgreSQL untuk tabel pengaturan.

Dulu tabel ini hanya berisi satu baris yang dipaksa ber-id 1, sehingga penghitung otomatisnya tidak pernah maju
dan baris baru (sekolah kedua) bentrok dengan id 1. Aman dijalankan berulang kali."""
from django.db import migrations


def setel_ulang(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute(
        "SELECT setval(pg_get_serial_sequence('pengaturan_pengaturansekolah', 'id'), "
        "COALESCE(MAX(id), 0) + 1, false) FROM pengaturan_pengaturansekolah"
    )


class Migration(migrations.Migration):
    dependencies = [('pengaturan', '0003_tautkan_sekolah_awal')]
    operations = [migrations.RunPython(setel_ulang, migrations.RunPython.noop)]
