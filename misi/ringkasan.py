"""
Jembatan app misi ke bagian lain Betsora OS: rapor (ruang_kerja) dan dashboard orang tua.

Berkas ini HANYA MEMBACA data misi. Ia tidak menulis apa pun dan tidak mengubah model
accounts, ruang_kerja, atau kreasi. Nilai formatif sudah ditulis ke PenilaianTopik oleh
PengerjaanMisi.konfirmasi(); rapor menampilkannya lewat topik seperti biasa.

Yang ditambahkan di sini adalah hal yang belum terlihat di rapor:
  * daftar misi yang selesai di sebuah ruang kerja (termasuk yang tanpa nilai),
  * satu paragraf narasi untuk draf komentar rapor,
  * ringkasan singkat untuk dashboard orang tua.

Yang SENGAJA tidak ditampilkan di rapor maupun dashboard: isi refleksi, catatan, dan foto siswa.
Itu tetap hanya bisa dibuka lewat halaman misi, yang punya aturan izin sendiri (misi/izin.py).
"""
from .izin import anak_dari_user
from .models import PengerjaanMisi


def nama_level(jumlah_selesai):
    for batas, nama in PengerjaanMisi.LEVEL:
        if jumlah_selesai >= batas:
            return nama
    return PengerjaanMisi.LEVEL[-1][1]


def misi_selesai(siswa, ruang=None):
    """
    Misi berstatus SELESAI milik siswa. Bila `ruang` diberikan, hanya misi yang ditugaskan guru
    ke ruang kerja itu. Misi yang dikerjakan mandiri (tanpa penugasan) tidak termasuk, karena
    rapor dibuat per ruang kerja (mata pelajaran).
    """
    qs = (
        PengerjaanMisi.objects.filter(siswa=siswa, status=PengerjaanMisi.SELESAI)
        .select_related("misi", "penugasan__materi")
        .order_by("dikonfirmasi_pada", "pk")
    )
    if ruang is not None:
        qs = qs.filter(penugasan__ruang_kerja=ruang)
    return qs


def ringkasan_rapor(siswa, ruang):
    """Data untuk partial misi/_rapor_misi.html di halaman rapor siswa."""
    daftar = list(misi_selesai(siswa, ruang))
    nilai = [float(p.nilai) for p in daftar if p.nilai is not None]
    return {
        "daftar": daftar,
        "jumlah": len(daftar),
        "rata2_nilai": round(sum(nilai) / len(nilai), 1) if nilai else None,
    }


def _gabung(item):
    if len(item) <= 1:
        return "".join(item)
    if len(item) == 2:
        return f"{item[0]} dan {item[1]}"
    return ", ".join(item[:-1]) + f", dan {item[-1]}"


def narasi_misi(siswa, ruang):
    """
    Satu paragraf untuk draf komentar rapor. String kosong bila tidak ada misi selesai,
    sehingga pemanggil bisa memakai `if narasi:` tanpa cabang khusus.
    """
    daftar = list(misi_selesai(siswa, ruang))
    if not daftar:
        return ""
    kata = (siswa.nama or "").split()
    nama = kata[0] if kata else "Siswa"
    judul = [f'"{p.misi.judul}"' for p in daftar]
    if len(daftar) == 1:
        kalimat = (
            f"Di luar kelas, {nama} menuntaskan misi dunia nyata {judul[0]} dengan refleksi tertulis, "
            "dan hasilnya telah dikonfirmasi orang tua atau guru."
        )
    else:
        pengantar = "yaitu" if len(daftar) <= 3 else "antara lain"
        kalimat = (
            f"Di luar kelas, {nama} menuntaskan {len(daftar)} misi dunia nyata ({pengantar} {_gabung(judul[:3])}), "
            "masing-masing dengan refleksi tertulis, dan hasilnya telah dikonfirmasi orang tua atau guru."
        )
    rata2 = ringkasan_rapor(siswa, ruang)["rata2_nilai"]
    if rata2 is not None:
        kalimat += f" Rata-rata nilai formatif dari misi tersebut adalah {rata2}."
    return kalimat


def ringkasan_untuk_orangtua(user):
    """
    Ringkasan untuk dashboard orang tua. Selalu anak dari akun yang login (user.anak); fungsi ini
    sengaja tidak menerima siswa lain. None bila pengguna bukan orang tua atau belum terhubung ke anak.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    anak = anak_dari_user(user)
    if anak is None:
        return None
    semua = anak.pengerjaan_misi.select_related("misi")
    selesai = semua.filter(status=PengerjaanMisi.SELESAI)
    total = selesai.count()
    return {
        "anak": anak,
        "menunggu": semua.filter(status=PengerjaanMisi.MENUNGGU).count(),
        "selesai": list(selesai.order_by("-dikonfirmasi_pada")[:3]),
        "total_selesai": total,
        "level": nama_level(total),
    }
