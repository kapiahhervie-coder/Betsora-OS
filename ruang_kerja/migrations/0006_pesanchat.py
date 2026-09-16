import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ruang_kerja', '0005_alter_materi_options_materi_urutan_submateri'),
    ]

    operations = [
        migrations.CreateModel(
            name='PesanChat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('isi', models.TextField()),
                ('dikirim_pada', models.DateTimeField(auto_now_add=True)),
                ('ruang_kerja', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pesan_chat', to='ruang_kerja.ruangkerja')),
                ('dikirim_oleh', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['dikirim_pada'],
            },
        ),
    ]
