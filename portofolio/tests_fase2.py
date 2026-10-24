"""Tes Fase 2a: lencana tersimpan dan karya unggulan."""
from django.urls import reverse

from accounts.models import Siswa
from kelas.models import Absensi, Keaktifan
from penilaian.models import Nilai

from . import jenjang
from .lencana_simpan import gabung_lencana
from .models import KaryaSiswa, LencanaDiraih
from .tests import DasarPortofolio, TANPA_BATASAN_ORTU, buat_user
from .views import MAKS_UNGGULAN


def kode_diraih(lencana):
    return {l["kode"]: l["diraih"] for l in lencana}


class LencanaTersimpanTests(DasarPortofolio):
    def test_lencana_diraih_dicatat_sekali(self):
        self.buka_detail(self.guru)
        awal = set(LencanaDiraih.objects.filter(siswa=self.a).values_list("kode", flat=True))
        self.assertTrue({"hadir", "nilai", "karya1"} <= awal)  # sesuai data dasar tes
        self.buka_detail(self.guru)
        self.buka_detail(self.user_a)
        self.assertEqual(LencanaDiraih.objects.filter(siswa=self.a).count(), len(awal))

    def test_tanggal_pertama_tidak_berubah(self):
        self.buka_detail(self.guru)
        satu = LencanaDiraih.objects.get(siswa=self.a, kode="hadir")
        self.buka_detail(self.guru)
        dua = LencanaDiraih.objects.get(siswa=self.a, kode="hadir")
        self.assertEqual(satu.diraih_pada, dua.diraih_pada)
        self.assertEqual(satu.pk, dua.pk)

    def test_lencana_tetap_diraih_walau_data_berubah(self):
        self.buka_detail(self.guru)
        Nilai.objects.filter(siswa=self.a).delete()
        Absensi.objects.filter(siswa=self.a).delete()
        KaryaSiswa.objects.filter(siswa=self.a).delete()
        resp = self.buka_detail(self.guru)
        kode = kode_diraih(resp.context["lencana"])
        self.assertTrue(kode["nilai"])
        self.assertTrue(kode["hadir"])
        self.assertTrue(kode["karya1"])
        # Lencana yang tidak pernah diraih tetap terkunci.
        self.assertFalse(kode["karya3"])
        self.assertEqual(resp.context["jumlah_lencana"], sum(kode.values()))

    def test_tanggal_tampil_di_semua_tema(self):
        self.buka_detail(self.guru)
        for tema in ("sd", "smp", "sma"):
            resp = self.client.get(reverse("portofolio:detail", args=[self.a.id]) + f"?tema={tema}")
            self.assertContains(resp, "iraih ", msg_prefix=tema)  # "Diraih ..." atau "diraih ..."

    def test_siswa_lain_tidak_menulis_atau_melihat_lencana(self):
        resp = self.buka_detail(self.user_b)
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("lencana", resp.context)
        self.assertEqual(LencanaDiraih.objects.filter(siswa=self.a).count(), 0)

    def test_gabung_lencana_murni_tanpa_data_baru(self):
        kosong = Siswa.objects.create(nama="Kosong", nis="888", kelas="3")
        hasil = gabung_lencana(kosong, jenjang.hitung_lencana(0, 0, None, 0, 0, False))
        self.assertFalse(any(l["diraih"] for l in hasil))
        self.assertEqual(LencanaDiraih.objects.filter(siswa=kosong).count(), 0)

    def test_dihapus_bersama_siswa(self):
        self.buka_detail(self.guru)
        self.assertTrue(LencanaDiraih.objects.filter(siswa=self.a).exists())
        KaryaSiswa.objects.filter(siswa=self.a).delete()
        self.a.delete()
        self.assertEqual(LencanaDiraih.objects.count(), 0)


class KaryaUnggulanTests(DasarPortofolio):
    def url(self, karya):
        return reverse("portofolio:unggulkan_karya", args=[karya.id])

    def tambah(self, n):
        return [KaryaSiswa.objects.create(siswa=self.a, judul=f"K{i}", dibagikan=True) for i in range(n)]

    def test_pemilik_menandai_dan_melepas(self):
        self.client.force_login(self.user_a)
        r = self.client.post(self.url(self.karya_publik))
        self.assertRedirects(r, reverse("portofolio:detail", args=[self.a.id]), fetch_redirect_response=False)
        self.karya_publik.refresh_from_db()
        self.assertTrue(self.karya_publik.unggulan)
        self.client.post(self.url(self.karya_publik))
        self.karya_publik.refresh_from_db()
        self.assertFalse(self.karya_publik.unggulan)

    def test_guru_boleh(self):
        self.client.force_login(self.guru)
        self.client.post(self.url(self.karya_publik))
        self.karya_publik.refresh_from_db()
        self.assertTrue(self.karya_publik.unggulan)

    def test_siswa_lain_dan_anonim_ditolak(self):
        self.client.force_login(self.user_b)
        self.client.post(self.url(self.karya_publik))
        self.karya_publik.refresh_from_db()
        self.assertFalse(self.karya_publik.unggulan)
        self.client.logout()
        r = self.client.post(self.url(self.karya_publik))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r["Location"])
        self.karya_publik.refresh_from_db()
        self.assertFalse(self.karya_publik.unggulan)

    @TANPA_BATASAN_ORTU
    def test_orang_tua_tidak_boleh_mengatur(self):
        self.client.force_login(self.ortu_a)
        self.client.post(self.url(self.karya_publik))
        self.karya_publik.refresh_from_db()
        self.assertFalse(self.karya_publik.unggulan)

    def test_hanya_post(self):
        self.client.force_login(self.user_a)
        self.assertEqual(self.client.get(self.url(self.karya_publik)).status_code, 405)

    def test_batas_maksimal(self):
        karya = self.tambah(MAKS_UNGGULAN + 1)
        self.client.force_login(self.user_a)
        for k in karya:
            self.client.post(self.url(k))
        self.assertEqual(KaryaSiswa.objects.filter(siswa=self.a, unggulan=True).count(), MAKS_UNGGULAN)
        # Setelah melepas satu, boleh menandai yang lain.
        pertama = KaryaSiswa.objects.filter(siswa=self.a, unggulan=True).first()
        self.client.post(self.url(pertama))
        sisa = KaryaSiswa.objects.filter(siswa=self.a, unggulan=False).exclude(pk=pertama.pk).first()
        self.client.post(self.url(sisa))
        self.assertEqual(KaryaSiswa.objects.filter(siswa=self.a, unggulan=True).count(), MAKS_UNGGULAN)

    def test_batas_per_siswa_tidak_saling_mengganggu(self):
        for k in self.tambah(MAKS_UNGGULAN):
            KaryaSiswa.objects.filter(pk=k.pk).update(unggulan=True)
        punya_b = KaryaSiswa.objects.create(siswa=self.b, judul="B1", dibagikan=True)
        self.client.force_login(self.user_b)
        self.client.post(self.url(punya_b))
        punya_b.refresh_from_db()
        self.assertTrue(punya_b.unggulan)

    def test_unggulan_tampil_paling_atas_di_semua_tema(self):
        lama = KaryaSiswa.objects.create(siswa=self.a, judul="PALING-LAMA", dibagikan=True, unggulan=True)
        KaryaSiswa.objects.filter(pk=lama.pk).update(diunggah_pada="2000-01-01T00:00:00Z")
        for tema in ("sd", "smp", "sma"):
            self.client.force_login(self.guru)
            resp = self.client.get(reverse("portofolio:detail", args=[self.a.id]) + f"?tema={tema}")
            self.assertEqual(resp.context["karya_list"][0].judul, "PALING-LAMA", msg=tema)
            self.assertContains(resp, 'data-pf="unggulan"', msg_prefix=tema)

    def test_siswa_lain_melihat_unggulan_hanya_jika_dibagikan(self):
        KaryaSiswa.objects.filter(pk=self.karya_privat.pk).update(unggulan=True)
        resp = self.buka_detail(self.user_b)
        self.assertNotContains(resp, "Karya Privat A")
        self.assertNotContains(resp, "Jadikan unggulan")  # tombol hanya untuk pemilik/staf

    def test_tombol_hanya_untuk_pemilik_dan_staf(self):
        self.assertContains(self.buka_detail(self.user_a), "Jadikan unggulan")
        self.assertContains(self.buka_detail(self.guru), "Jadikan unggulan")
