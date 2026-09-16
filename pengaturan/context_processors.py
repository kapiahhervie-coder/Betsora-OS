from .models import PengaturanSekolah


def pengaturan_sekolah(request):
    return {"pengaturan": PengaturanSekolah.get_settings()}


def notifikasi_belum_dibaca(request):
    if not request.user.is_authenticated:
        return {}
    from ruang_kerja.models import RuangKerja, PesanChat, Pengumuman, StatusBaca

    if getattr(request.user, "role", None) == "siswa" and hasattr(request.user, "profil_siswa"):
        kelas_siswa = request.user.profil_siswa.kelas
        ruang_list = RuangKerja.objects.filter(kelas=kelas_siswa)
    else:
        ruang_list = RuangKerja.objects.all()

    status_map = {sb.ruang_kerja_id: sb.terakhir_dibaca for sb in StatusBaca.objects.filter(user=request.user)}

    total = 0
    for r in ruang_list:
        terakhir = status_map.get(r.id)
        q_pesan = PesanChat.objects.filter(ruang_kerja=r)
        q_peng = Pengumuman.objects.filter(ruang_kerja=r)
        if terakhir:
            q_pesan = q_pesan.filter(dikirim_pada__gt=terakhir)
            q_peng = q_peng.filter(dibuat_pada__gt=terakhir)
        total += q_pesan.count() + q_peng.count()

    return {"total_belum_dibaca": total}
