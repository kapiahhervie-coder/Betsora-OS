import json
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from .models import Kuis, Soal

PERAN_BOLEH_BAGIKAN = {"guru", "kepsek", "admin"}
MAKS_SOAL = 100


# ---------------------------------------------------------------
# Hak akses
# ---------------------------------------------------------------

def _peran(user):
    return getattr(user, "role", None)


def _boleh_akses(user):
    """Semua peran boleh, kecuali orang tua."""
    return _peran(user) != "orangtua"


def _boleh_bagikan(user):
    return user.is_superuser or _peran(user) in PERAN_BOLEH_BAGIKAN


def kuis_halaman(view):
    """Halaman HTML: wajib login, orang tua ditolak (403)."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not _boleh_akses(request.user):
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return login_required(wrapper)


def kuis_api(view):
    """Endpoint JSON: balas 401/403 sebagai JSON, bukan redirect."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Belum login."}, status=401)
        if not _boleh_akses(request.user):
            return JsonResponse({"error": "Tidak diizinkan."}, status=403)
        return view(request, *args, **kwargs)

    return wrapper


# ---------------------------------------------------------------
# Helper
# ---------------------------------------------------------------

def _kuis_terlihat(user):
    """Kuis milik sendiri + kuis yang dibagikan."""
    return Kuis.objects.filter(Q(pembuat=user) | Q(dibagikan=True))


def _nama_pembuat(kuis):
    return kuis.pembuat.get_full_name() or kuis.pembuat.get_username()


def _bersihkan_soal(soal_masuk):
    """Validasi dan bersihkan daftar soal dari browser."""
    if not isinstance(soal_masuk, list) or not (1 <= len(soal_masuk) <= MAKS_SOAL):
        return None, f"Kuis harus berisi 1 sampai {MAKS_SOAL} soal."

    hasil = []
    for item in soal_masuk:
        if not isinstance(item, dict):
            return None, "Format soal tidak valid."

        teks = str(item.get("q") or "").strip()
        pilihan = item.get("a")
        benar = item.get("correct")
        petunjuk = str(item.get("hint") or "").strip()[:300]

        valid = bool(
            teks
            and isinstance(pilihan, list)
            and len(pilihan) == 4
            and all(isinstance(p, str) and p.strip() for p in pilihan)
            and isinstance(benar, int)
            and not isinstance(benar, bool)
            and 0 <= benar <= 3
        )
        if not valid:
            return None, "Ada soal dengan pertanyaan, pilihan, atau jawaban yang tidak valid."

        hasil.append(
            {
                "teks": teks[:1000],
                "pilihan": [p.strip()[:300] for p in pilihan],
                "jawaban_benar": benar,
                "petunjuk": petunjuk,
            }
        )
    return hasil, None


# ---------------------------------------------------------------
# Halaman
# ---------------------------------------------------------------

@kuis_halaman
def kuis_home(request):
    return render(
        request,
        "kuis/index.html",
        {"bisa_bagikan": _boleh_bagikan(request.user)},
    )


# ---------------------------------------------------------------
# API JSON
# ---------------------------------------------------------------

@kuis_api
@require_GET
def api_daftar(request):
    qs = (
        _kuis_terlihat(request.user)
        .select_related("pembuat")
        .annotate(jumlah_soal=Count("soal"))
    )
    data = [
        {
            "id": k.id,
            "judul": k.judul,
            "dibagikan": k.dibagikan,
            "milik_saya": k.pembuat_id == request.user.id,
            "pembuat": _nama_pembuat(k),
            "jumlah_soal": k.jumlah_soal,
        }
        for k in qs
    ]
    return JsonResponse({"kuis": data})


@kuis_api
@require_GET
def api_detail(request, pk):
    kuis = get_object_or_404(
        _kuis_terlihat(request.user).select_related("pembuat"), pk=pk
    )
    soal = [
        {
            "q": s.teks,
            "a": s.pilihan,
            "correct": s.jawaban_benar,
            "hint": s.petunjuk,
        }
        for s in kuis.soal.all()
    ]
    return JsonResponse(
        {
            "id": kuis.id,
            "judul": kuis.judul,
            "dibagikan": kuis.dibagikan,
            "milik_saya": kuis.pembuat_id == request.user.id,
            "pembuat": _nama_pembuat(kuis),
            "soal": soal,
        }
    )


@kuis_api
@require_POST
def api_simpan(request):
    try:
        data = json.loads(request.body)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Data tidak valid."}, status=400)
    if not isinstance(data, dict):
        return JsonResponse({"error": "Data tidak valid."}, status=400)

    judul = str(data.get("judul") or "").strip()[:200]
    if not judul:
        return JsonResponse({"error": "Judul kuis wajib diisi."}, status=400)

    soal_bersih, galat = _bersihkan_soal(data.get("soal"))
    if galat:
        return JsonResponse({"error": galat}, status=400)

    kuis_id = data.get("id")
    if kuis_id is not None and (not isinstance(kuis_id, int) or isinstance(kuis_id, bool)):
        return JsonResponse({"error": "ID kuis tidak valid."}, status=400)

    # Hanya guru/kepsek/admin yang boleh membagikan kuis
    dibagikan = bool(data.get("dibagikan")) and _boleh_bagikan(request.user)

    with transaction.atomic():
        if kuis_id is None:
            kuis = Kuis.objects.create(
                judul=judul, pembuat=request.user, dibagikan=dibagikan
            )
        else:
            # Hanya pemilik yang boleh mengubah
            kuis = get_object_or_404(Kuis, pk=kuis_id, pembuat=request.user)
            kuis.judul = judul
            kuis.dibagikan = dibagikan
            kuis.save()
            kuis.soal.all().delete()

        Soal.objects.bulk_create(
            [Soal(kuis=kuis, urutan=i, **s) for i, s in enumerate(soal_bersih)]
        )

    return JsonResponse(
        {"id": kuis.id, "judul": kuis.judul, "dibagikan": kuis.dibagikan}
    )


@kuis_api
@require_POST
def api_hapus(request, pk):
    kuis = get_object_or_404(Kuis, pk=pk, pembuat=request.user)
    kuis.delete()
    return JsonResponse({"ok": True})