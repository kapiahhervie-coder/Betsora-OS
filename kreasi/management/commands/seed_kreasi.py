from django.core.management.base import BaseCommand
from django.db import transaction

from kreasi.fase_config import JENJANG_CONFIG
from kreasi.models import DeskriptorLevel, DimensiPenilaian


class Command(BaseCommand):
    help = 'Isi dimensi & deskriptor bawaan per jenjang. Aman dijalankan berulang: tidak menimpa hasil edit.'

    @transaction.atomic
    def handle(self, *args, **opts):
        dimensi_baru = deskriptor_baru = 0
        for kunci, cfg in JENJANG_CONFIG.items():
            for urutan, d in enumerate(cfg['dimensi'], start=1):
                dim, dibuat = DimensiPenilaian.objects.get_or_create(
                    jenjang=kunci, kode=d['kode'],
                    defaults={'nama': d['nama'], 'urutan': urutan},
                )
                dimensi_baru += dibuat
                for level, kalimat in d['deskriptor'].items():
                    _, dibuat = DeskriptorLevel.objects.get_or_create(
                        dimensi=dim, level=level, defaults={'kalimat': kalimat},
                    )
                    deskriptor_baru += dibuat
        self.stdout.write(self.style.SUCCESS(
            f'Selesai: {dimensi_baru} dimensi baru, {deskriptor_baru} deskriptor baru.'
        ))
