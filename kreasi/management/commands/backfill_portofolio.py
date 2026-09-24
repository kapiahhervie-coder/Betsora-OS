from django.core.management.base import BaseCommand
from ruang_kerja.models import Tugas
from kreasi.models import LampiranKarya
from portofolio.models import KaryaSiswa


class Command(BaseCommand):
    help = 'Backfill karya Tugas Kreasi lama ke Portofolio'

    def handle(self, *args, **options):
        jumlah = 0
        for tugas in Tugas.objects.filter(jenis='kreasi'):
            for submisi in tugas.submisi.all():
                item_lampiran = list(LampiranKarya.objects.filter(submisi=submisi))
                if item_lampiran:
                    for i, lp in enumerate(item_lampiran, start=1):
                        if len(item_lampiran) == 1:
                            judul_karya = tugas.judul[:150]
                        else:
                            judul_karya = (tugas.judul + ' (' + str(i) + '/' + str(len(item_lampiran)) + ')')[:150]
                        sudah_ada = KaryaSiswa.objects.filter(siswa=submisi.siswa, judul=judul_karya).exists()
                        if not sudah_ada:
                            KaryaSiswa.objects.create(
                                siswa=submisi.siswa, judul=judul_karya,
                                deskripsi='Tugas Kreasi: ' + tugas.ruang_kerja.mapel,
                                file=lp.file.name if lp.file else '',
                                video_url=lp.url if lp.tipe == 'link' else '',
                                dibagikan=False, refleksi=submisi.teks_jawaban,
                            )
                            jumlah += 1
                else:
                    judul_karya = tugas.judul[:150]
                    sudah_ada = KaryaSiswa.objects.filter(siswa=submisi.siswa, judul=judul_karya).exists()
                    if not sudah_ada:
                        KaryaSiswa.objects.create(
                            siswa=submisi.siswa, judul=judul_karya,
                            deskripsi='Tugas Kreasi: ' + tugas.ruang_kerja.mapel,
                            dibagikan=False, refleksi=submisi.teks_jawaban,
                        )
                        jumlah += 1
        self.stdout.write(self.style.SUCCESS('Karya ditambahkan ke Portofolio: ' + str(jumlah)))
