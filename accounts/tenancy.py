"""Penyekatan data antar sekolah (multi-tenant dalam satu deployment).

Cara kerja, singkat:

1. `SekolahMiddleware` menetapkan "sekolah aktif" untuk setiap permintaan dari akun yang login.
2. Setiap model yang datanya milik sekolah memakai `SekolahManager` sebagai `objects`. Manajer ini
   otomatis menambahkan filter sekolah pada SEMUA query (`Siswa.objects.all()`,
   `get_object_or_404(Tugas, id=...)`, manajer relasi seperti `ruang.tugas.all()`, dst).
   Objek milik sekolah lain tidak pernah ditemukan: hasilnya 404 / kosong, bukan "tidak berizin".
3. Saat menyimpan baris baru, sinyal `pre_save`:
   - memberi cap sekolah aktif pada model akar (yang punya kolom `sekolah`);
   - menolak baris yang merujuk (ForeignKey) ke objek sekolah lain. Ini menutup celah id mentah
     dari formulir, mis. `siswa_ids` dari sekolah lain pada `tambah_anggota`.

Nilai "sekolah aktif":
  - `BEBAS`   : tidak dibatasi. Dipakai superuser (admin platform), perintah manajemen, dan kode di luar
                permintaan web (tes, migrasi).
  - id sekolah: hanya data sekolah itu.
  - `None`    : akun tanpa sekolah. Hanya melihat baris yang juga tanpa sekolah (tidak ada di database
                produksi: `periksa_sekolah --ketat` memastikannya).
  - `TOLAK`   : tidak melihat apa pun (sekolah dinonaktifkan).

Catatan: query yang dibangun SAAT IMPOR (mis. `queryset=Siswa.objects.all()` di tingkat kelas Form)
tidak ikut tersaring, karena filter dipasang ketika query dibuat. Buat queryset di dalam fungsi/`__init__`.
"""
from contextlib import contextmanager
from contextvars import ContextVar

from django.contrib.auth.models import UserManager
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import Q
from django.db.models.signals import pre_save
from django.dispatch import receiver


class _Bebas:
    def __repr__(self):
        return 'BEBAS'


BEBAS = _Bebas()
TOLAK = -1  # id sekolah yang tidak pernah ada

_aktif = ContextVar('sekolah_aktif', default=BEBAS)


class LintasSekolah(PermissionDenied):
    """Dilempar saat ada upaya menulis/merujuk data sekolah lain (hasilnya HTTP 403)."""


def sekolah_aktif():
    return _aktif.get()


@contextmanager
def dalam_sekolah(sekolah):
    """Menjalankan blok kode dalam lingkup satu sekolah. `sekolah`: objek Sekolah, id, None, atau BEBAS."""
    nilai = sekolah if (sekolah is None or sekolah is BEBAS) else getattr(sekolah, 'pk', sekolah)
    token = _aktif.set(nilai)
    try:
        yield
    finally:
        _aktif.reset(token)


@contextmanager
def tanpa_batas():
    """Untuk kode platform yang sah lintas sekolah (perintah manajemen, laporan admin platform)."""
    with dalam_sekolah(BEBAS):
        yield


def _syarat(jalur, sekolah_id):
    q = Q()
    for j in jalur:
        q &= Q(**{j + '__isnull': True}) if sekolah_id is None else Q(**{j: sekolah_id})
    return q


class SekolahManagerMixin:
    """`jalur`: satu atau beberapa lintasan ORM menuju kolom `sekolah`, semuanya harus cocok.
    Contoh: 'sekolah' (model akar), 'siswa__sekolah', ('peserta_1__sekolah', 'peserta_2__sekolah')."""

    def __init__(self, *jalur, **kw):
        super().__init__(**kw)
        self._jalur = jalur

    @property
    def jalur(self):
        if self._jalur:
            return self._jalur
        # Manajer relasi (mis. ruang.tugas) dibuat tanpa argumen: ambil lintasan dari manajer asli model.
        asli = self.model._default_manager
        return getattr(asli, '_jalur', None) or ('sekolah',)

    def get_queryset(self):
        qs = super().get_queryset()
        sid = _aktif.get()
        if sid is BEBAS:
            return qs
        return qs.filter(_syarat(self.jalur, sid))

    @property
    def punya_kolom_sekolah(self):
        return self.jalur == ('sekolah',) and any(f.name == 'sekolah' for f in self.model._meta.concrete_fields)


class SekolahManager(SekolahManagerMixin, models.Manager):
    pass


class SekolahUserManager(SekolahManagerMixin, UserManager):
    """Pengganti UserManager bawaan Django: create_user/create_superuser tetap berfungsi.

    UserManager ikut disimpan di migrasi (use_in_migrations). Agar penyaring ini tidak memicu migrasi
    baru, manajer ini mendaftarkan dirinya ke migrasi sebagai UserManager biasa (migrasi memang tidak
    memerlukan penyaringan)."""

    def deconstruct(self):
        return (False, 'django.contrib.auth.models.UserManager', None, (), {})

    def __eq__(self, other):
        # Sama dengan UserManager biasa di mata pembanding migrasi.
        return isinstance(other, UserManager) and self._constructor_args == other._constructor_args

    __hash__ = UserManager.__hash__


# ----------------------------------------------------------------------------------------------
# Penjaga penulisan
# ----------------------------------------------------------------------------------------------

def _terscope(model):
    return isinstance(model._default_manager, SekolahManagerMixin)


@receiver(pre_save, dispatch_uid='betsora_tenancy_pre_save')
def _jaga_penulisan(sender, instance, raw=False, **kwargs):
    sid = _aktif.get()
    if sid is BEBAS or raw:
        return
    if not _terscope(sender):
        return
    mgr = sender._default_manager

    if mgr.punya_kolom_sekolah:
        if sid == TOLAK:
            raise LintasSekolah('Sekolah tidak aktif.')
        if instance.sekolah_id is None:
            if sid is not None:
                instance.sekolah_id = sid
        elif instance.sekolah_id != sid:
            raise LintasSekolah('Data milik sekolah lain.')

    if instance._state.adding:
        for f in sender._meta.concrete_fields:
            if not f.is_relation or not f.many_to_one and not f.one_to_one:
                continue
            nilai = getattr(instance, f.attname, None)
            if nilai is None:
                continue
            tujuan = f.related_model
            if tujuan is sender or not _terscope(tujuan):
                continue
            if not tujuan._default_manager.filter(pk=nilai).exists():
                raise LintasSekolah(f'{sender.__name__}.{f.name} merujuk data sekolah lain.')


# ----------------------------------------------------------------------------------------------
# Middleware
# ----------------------------------------------------------------------------------------------

class SekolahMiddleware:
    """Letakkan SETELAH AuthenticationMiddleware. Mengisi `request.sekolah` dan lingkup query."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        request.sekolah = None
        nilai = BEBAS
        if user is not None and user.is_authenticated and not user.is_superuser:
            sekolah = user.sekolah if user.sekolah_id else None
            request.sekolah = sekolah
            if sekolah is None:
                nilai = None
            elif not sekolah.aktif:
                nilai = TOLAK
            else:
                nilai = sekolah.pk
        token = _aktif.set(nilai)
        try:
            return self.get_response(request)
        finally:
            _aktif.reset(token)


# ----------------------------------------------------------------------------------------------
# Pembantu
# ----------------------------------------------------------------------------------------------

def username_unik(dasar, sekolah):
    """Nama pengguna harus unik di SELURUH platform (kolom username unik global), sedangkan NIS
    hanya unik per sekolah. Bila `dasar` sudah dipakai sekolah lain, pakai awalan kode sekolah."""
    from accounts.models import User

    def bebas(nama):
        return not User._base_manager.filter(username__iexact=nama).exists()

    if bebas(dasar):
        return dasar
    kode = sekolah.kode if sekolah is not None else 'x'
    kandidat = f'{kode}-{dasar}'
    if bebas(kandidat):
        return kandidat
    n = 2
    while not bebas(f'{kandidat}-{n}'):
        n += 1
    return f'{kandidat}-{n}'
