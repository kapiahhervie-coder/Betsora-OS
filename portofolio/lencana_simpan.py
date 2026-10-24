"""Menyimpan lencana yang sudah diraih supaya tidak hilang saat data berubah.

`hitung_lencana` (jenjang.py) tetap menghitung dari data terkini. Di sini hasilnya digabung
dengan catatan di tabel LencanaDiraih: lencana yang pernah diraih tetap dianggap diraih,
lengkap dengan tanggal pertama kali diraih. Aman dipanggil berulang (tidak membuat dobel).
"""
from .models import LencanaDiraih


def gabung_lencana(siswa, lencana):
    tersimpan = dict(LencanaDiraih.objects.filter(siswa=siswa).values_list('kode', 'diraih_pada'))
    baru = [LencanaDiraih(siswa=siswa, kode=l['kode']) for l in lencana
            if l['diraih'] and l['kode'] not in tersimpan]
    if baru:
        LencanaDiraih.objects.bulk_create(baru, ignore_conflicts=True)
        tersimpan = dict(LencanaDiraih.objects.filter(siswa=siswa).values_list('kode', 'diraih_pada'))
    hasil = []
    for l in lencana:
        tanggal = tersimpan.get(l['kode'])
        item = dict(l)
        item['tanggal'] = tanggal
        item['diraih'] = bool(l['diraih'] or tanggal)
        hasil.append(item)
    return hasil
