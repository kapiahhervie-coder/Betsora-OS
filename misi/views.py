import mimetypes

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

from kreasi.fase_config import deteksi_tingkat

from .forms import CatatanForm, KonfirmasiForm, PenugasanForm, RefleksiForm
from .izin import (
    PERAN_PENUH,
    PERAN_STAF,
    anak_dari_user,
    boleh_konfirmasi,
    boleh_lihat,
    peran_wajib,
    siswa_dari_user,
)
from .models import CatatanMisi, Misi, PengerjaanMisi, PenugasanMisi
from .ringkasan import nama_level


def _level(jumlah_selesai):
    return nama_level(jumlah_selesai)


def _grafik(pengerjaan):
    """Batang sederhana dari angka yang dicatat siswa."""
    baris = [c for c in pengerjaan.catatan.all() if c.angka is not None]
    if not baris:
        return []
    puncak = max(float(c.angka) for c in baris) or 1
    return [
        {"nomor": i, "nilai": c.angka, "persen": round(float(c.angka) / puncak * 100)}
        for i, c in enumerate(baris, start=1)
    ]


def _siswa_atau_403(request):
    siswa = siswa_dari_user(request.user)
    if siswa is None:
        raise PermissionDenied("Akun siswa ini belum terhubung ke data siswa.")
    return siswa


def _pengerjaan_dilihat(request, pk):
    """Ambil pengerjaan, hanya bila pengguna berhak melihat siswanya. Selain itu 404."""
    pengerjaan = get_object_or_404(PengerjaanMisi.objects.select_related("siswa", "misi", "penugasan__materi"), pk=pk)
    if not boleh_lihat(request.user, pengerjaan.siswa):
        raise Http404
    return pengerjaan


@login_required
def home(request):
    if request.user.role == "siswa":
        return redirect("misi:papan")
    if request.user.role == "orangtua":
        return redirect("misi:panel_orangtua")
    if request.user.role in PERAN_STAF:
        return redirect("misi:panel_guru")
    raise PermissionDenied


# ------------------------------------------------------------------ siswa


@peran_wajib("siswa")
def papan(request):
    siswa = _siswa_atau_403(request)
    tingkat = deteksi_tingkat(siswa.kelas)
    kategori = request.GET.get("kategori", "")
    pengerjaan = {p.misi_id: p for p in siswa.pengerjaan_misi.all()}

    tugas_guru = list(
        PenugasanMisi.objects.filter(ruang_kerja__anggota__siswa=siswa, misi__aktif=True)
        .select_related("misi", "ruang_kerja")
        .distinct()
    )
    tugas = [{"penugasan": t, "pengerjaan": pengerjaan.get(t.misi_id)} for t in tugas_guru]

    misi = [m for m in Misi.objects.filter(aktif=True) if m.cocok_untuk(tingkat)]
    if kategori in dict(Misi.KATEGORI_CHOICES):
        misi = [m for m in misi if m.kategori == kategori]
    kartu = [{"misi": m, "pengerjaan": pengerjaan.get(m.pk)} for m in misi]

    selesai = sum(1 for p in pengerjaan.values() if p.status == PengerjaanMisi.SELESAI)
    return render(request, "misi/papan.html", {
        "siswa": siswa, "kartu": kartu, "tugas": tugas, "kategori_list": Misi.KATEGORI_CHOICES,
        "kategori": kategori, "selesai": selesai, "level": _level(selesai),
    })


@peran_wajib("siswa")
def detail_misi(request, slug):
    siswa = _siswa_atau_403(request)
    misi = get_object_or_404(Misi, slug=slug, aktif=True)
    pengerjaan = PengerjaanMisi.objects.filter(siswa=siswa, misi=misi).first()
    penugasan = PenugasanMisi.objects.filter(
        misi=misi, ruang_kerja__anggota__siswa=siswa
    ).first()

    if request.method == "POST":
        cocok = misi.cocok_untuk(deteksi_tingkat(siswa.kelas))
        if not cocok and penugasan is None:
            messages.error(request, "Misi ini belum cocok untuk kelasmu.")
            return redirect("misi:papan")
        pengerjaan, _ = PengerjaanMisi.objects.get_or_create(
            siswa=siswa, misi=misi, defaults={"penugasan": penugasan}
        )
        if pengerjaan.penugasan_id is None and penugasan is not None:
            pengerjaan.penugasan = penugasan
            pengerjaan.save(update_fields=["penugasan"])
        return redirect("misi:kerjakan", pk=pengerjaan.pk)

    return render(request, "misi/detail.html", {
        "siswa": siswa, "misi": misi, "pengerjaan": pengerjaan, "penugasan": penugasan,
    })


def _halaman_kerjakan(request, pengerjaan, status=200, **ekstra):
    siswa_sendiri = siswa_dari_user(request.user) == pengerjaan.siswa
    bisa_konfirmasi = pengerjaan.status == PengerjaanMisi.MENUNGGU and boleh_konfirmasi(
        request.user, pengerjaan.siswa
    )
    ada_topik = bool(pengerjaan.penugasan_id and pengerjaan.penugasan.materi_id)
    konteks = {
        "pengerjaan": pengerjaan,
        "misi": pengerjaan.misi,
        "siswa": pengerjaan.siswa,
        "catatan": pengerjaan.catatan.all(),
        "grafik": _grafik(pengerjaan) if pengerjaan.misi.pakai_angka else [],
        "siswa_sendiri": siswa_sendiri,
        "bisa_ubah": siswa_sendiri and pengerjaan.status == PengerjaanMisi.BERJALAN,
        "bisa_konfirmasi": bisa_konfirmasi,
        "pakai_nilai": bisa_konfirmasi and ada_topik and request.user.role in PERAN_STAF,
        "catatan_form": CatatanForm(misi=pengerjaan.misi),
        "refleksi_form": RefleksiForm(),
        "konfirmasi_form": KonfirmasiForm(),
    }
    konteks.update(ekstra)
    return render(request, "misi/kerjakan.html", konteks, status=status)


@login_required
def kerjakan(request, pk):
    return _halaman_kerjakan(request, _pengerjaan_dilihat(request, pk))


@peran_wajib("siswa")
@require_POST
def tambah_catatan(request, pk):
    pengerjaan = _pengerjaan_dilihat(request, pk)
    if siswa_dari_user(request.user) != pengerjaan.siswa:
        raise PermissionDenied
    if pengerjaan.status != PengerjaanMisi.BERJALAN:
        messages.error(request, "Misi ini sudah dikirim, catatan tidak bisa ditambah.")
        return redirect("misi:kerjakan", pk=pk)
    form = CatatanForm(request.POST, request.FILES, misi=pengerjaan.misi)
    if form.is_valid():
        catatan = form.save(commit=False)
        catatan.pengerjaan = pengerjaan
        catatan.save()
        messages.success(request, "Catatan tersimpan. Bagus sekali!")
        return redirect("misi:kerjakan", pk=pk)
    return _halaman_kerjakan(request, pengerjaan, status=400, catatan_form=form)


@peran_wajib("siswa")
@require_POST
def kirim_refleksi(request, pk):
    pengerjaan = _pengerjaan_dilihat(request, pk)
    if siswa_dari_user(request.user) != pengerjaan.siswa:
        raise PermissionDenied
    if not pengerjaan.bisa_refleksi:
        if pengerjaan.status != PengerjaanMisi.BERJALAN:
            messages.error(request, "Refleksi misi ini sudah dikirim.")
        else:
            messages.error(request, f"Catat dulu {pengerjaan.kurang_catatan} pengamatan lagi sebelum refleksi.")
        return redirect("misi:kerjakan", pk=pk)
    form = RefleksiForm(request.POST)
    if form.is_valid():
        pengerjaan.kirim_refleksi(form.cleaned_data["refleksi"].strip())
        messages.success(request, "Hebat! Tunjukkan ke orang tua atau gurumu untuk dikonfirmasi.")
        return redirect("misi:kerjakan", pk=pk)
    return _halaman_kerjakan(request, pengerjaan, status=400, refleksi_form=form)


@peran_wajib("siswa")
def koleksi(request):
    siswa = _siswa_atau_403(request)
    return _halaman_koleksi(request, siswa)


@login_required
def koleksi_siswa(request, siswa_id):
    from accounts.models import Siswa

    siswa = get_object_or_404(Siswa, pk=siswa_id)
    if not boleh_lihat(request.user, siswa):
        raise Http404
    return _halaman_koleksi(request, siswa)


def _halaman_koleksi(request, siswa):
    selesai = siswa.pengerjaan_misi.filter(status=PengerjaanMisi.SELESAI).select_related("misi")
    return render(request, "misi/koleksi.html", {
        "siswa": siswa, "selesai": selesai, "level": _level(selesai.count()),
    })


# ------------------------------------------------------------------ konfirmasi


@login_required
@require_POST
def konfirmasi(request, pk):
    pengerjaan = _pengerjaan_dilihat(request, pk)
    if not boleh_konfirmasi(request.user, pengerjaan.siswa):
        raise PermissionDenied
    if pengerjaan.status != PengerjaanMisi.MENUNGGU:
        messages.error(request, "Misi ini tidak sedang menunggu konfirmasi.")
        return redirect("misi:kerjakan", pk=pk)
    nilai = None
    if request.user.role in PERAN_STAF:
        form = KonfirmasiForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Nilai harus berupa angka 0 sampai 100.")
            return redirect("misi:kerjakan", pk=pk)
        nilai = form.cleaned_data["nilai"]
    pengerjaan.konfirmasi(request.user, nilai=nilai)
    messages.success(request, f"Misi \"{pengerjaan.misi.judul}\" dikonfirmasi. {pengerjaan.siswa.nama} mendapat kartu baru.")
    if request.user.role == "orangtua":
        return redirect("misi:panel_orangtua")
    return redirect("misi:panel_guru")


# ------------------------------------------------------------------ orang tua


@peran_wajib("orangtua")
def panel_orangtua(request):
    anak = anak_dari_user(request.user)
    menunggu = selesai = []
    if anak is not None:
        semua = anak.pengerjaan_misi.select_related("misi").order_by("-refleksi_pada")
        menunggu = [p for p in semua if p.status == PengerjaanMisi.MENUNGGU]
        selesai = [p for p in semua if p.status == PengerjaanMisi.SELESAI][:10]
    return render(request, "misi/panel_orangtua.html", {"anak": anak, "menunggu": menunggu, "selesai": selesai})


# ------------------------------------------------------------------ guru / kepsek / admin


def _pengerjaan_staf(user):
    qs = PengerjaanMisi.objects.select_related("siswa", "misi", "penugasan__materi")
    if user.role not in PERAN_PENUH:
        qs = qs.filter(siswa__ruang_kerja_diikuti__ruang_kerja__guru=user).distinct()
    return qs


@peran_wajib(*PERAN_STAF)
def panel_guru(request):
    qs = _pengerjaan_staf(request.user)
    menunggu = list(qs.filter(status=PengerjaanMisi.MENUNGGU).order_by("refleksi_pada"))
    berjalan = list(qs.filter(status=PengerjaanMisi.BERJALAN).order_by("-mulai_pada")[:30])
    penugasan = PenugasanMisi.objects.select_related("misi", "ruang_kerja", "materi")
    if request.user.role not in PERAN_PENUH:
        penugasan = penugasan.filter(Q(ruang_kerja__guru=request.user))
    return render(request, "misi/panel_guru.html", {
        "menunggu": menunggu, "berjalan": berjalan, "penugasan": penugasan[:30],
    })


@peran_wajib(*PERAN_STAF)
def tugaskan(request):
    form = PenugasanForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        tugas = form.save(commit=False)
        tugas.ditugaskan_oleh = request.user
        tugas.save()
        messages.success(request, f"Misi \"{tugas.misi.judul}\" ditugaskan ke {tugas.ruang_kerja}.")
        return redirect("misi:panel_guru")
    return render(request, "misi/tugaskan.html", {"form": form}, status=400 if request.method == "POST" else 200)


# ------------------------------------------------------------------ foto privat


@login_required
def foto(request, pk):
    catatan = get_object_or_404(CatatanMisi.objects.select_related("pengerjaan__siswa"), pk=pk)
    if not catatan.foto or not boleh_lihat(request.user, catatan.pengerjaan.siswa):
        raise Http404
    tipe = mimetypes.guess_type(catatan.foto.name)[0] or "application/octet-stream"
    respons = FileResponse(catatan.foto.open("rb"), content_type=tipe)
    respons["X-Content-Type-Options"] = "nosniff"
    respons["Cache-Control"] = "private, max-age=300"
    return respons
