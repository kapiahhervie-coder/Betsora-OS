from ruang_kerja.models import Kelas


def sidebar_kelas(request):
    if request.user.is_authenticated and getattr(request.user, "role", None) != "siswa":
        return {"sidebar_kelas_list": Kelas.objects.all()}
    return {"sidebar_kelas_list": []}
