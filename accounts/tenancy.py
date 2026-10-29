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

Pembatasan peran (Tahap 3), hanya untuk akun ber-role guru yang punya sekolah:
  - guru melihat ruang kerja miliknya sendiri (RuangKerja.guru) beserta seluruh isinya;
  - guru melihat siswa: (a) yang terdaftar di ruang kerjanya, (b) yang sekelas dengan salah satu ruang
    kerjanya (teks kelas cocok), dan (c) yang ada di kelas yang ia walikan (Kelas.wali_kelas);
  - sesi penilaian hanya miliknya. Data anak siswa (nilai, absensi, portofolio, ...) mengikuti siswa yang terlihat.
  Kepala sekolah, admin sekolah, dan superuser tidak dibatasi peran (tetap dibatasi sekolah).
  Akun tanpa sekolah tidak dibatasi peran: itu hanya keadaan data lama/tes, bukan produksi.

Catatan: query yang dibangun SAAT IMPOR (mis. `queryset=Siswa.objects.all()` di tingkat kelas Form)
tidak ikut tersaring, karena filter dipasang ketika query dibuat. Buat queryset di dalam fungsi/`__init__`.
"""
import re
from contextlib import contextmanager
from contextvars import ContextVar

from django.contrib.auth.models import UserManager
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver


class _Bebas:
    def __repr__(self):
        return 'BEBAS'


BEBAS = _Bebas()
TOLAK = -1  # id sekolah yang tidak pernah ada

_aktif = ContextVar('sekolah_aktif', default=BEBAS)
_peran = ContextVar('peran_aktif', default=None)  # None = tanpa pembatasan peran, atau PeranGuru


def _norm_kelas(teks):
    """'Kelas 4', ' 4 ', 'IV' dianggap kelas yang sama ('4'). Huruf besar/kecil diabaikan."""
    t = (teks or '').strip().lower()
    t = re.sub(r'^kelas\s+', '', t)
    romawi = {'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5, 'vi': 6, 'vii': 7, 'viii': 8, 'ix': 9, 'x': 10, 'xi': 11, 'xii': 12}
    if t in romawi:
        return str(romawi[t])
    return t


class PeranGuru:
    """Siapa guru yang sedang bertindak, dan siswa mana yang boleh ia lihat (dihitung sekali per permintaan)."""

    def __init__(self, user_id, sekolah_id):
        self.user_id = user_id
        self.sekolah_id = sekolah_id
        self._siswa = None

    def reset(self):
        self._siswa = None

    @property
    def siswa_ids(self):
        if self._siswa is None:
            self._siswa = self._hitung()
        return self._siswa

    def _hitung(self):
        # Memakai _base_manager (tanpa penyaring) agar tidak berputar ke dirinya sendiri.
        from accounts.models import Siswa
        from ruang_kerja.models import AnggotaRuangKerja, Kelas, RuangKerja

        ruang = RuangKerja._base_manager.filter(sekolah_id=self.sekolah_id, guru_id=self.user_id)
        ids = set(AnggotaRuangKerja._base_manager.filter(ruang_kerja__in=ruang).values_list('siswa_id', flat=True))
        nama = {_norm_kelas(k) for k in ruang.values_list('kelas', flat=True)}
        nama |= {_norm_kelas(n) for n in ruang.exclude(kelas_baru=None).values_list('kelas_baru__nama', flat=True)}
        nama |= {_norm_kelas(n) for n in Kelas._base_manager.filter(
            sekolah_id=self.sekolah_id, wali_kelas_id=self.user_id).values_list('nama', flat=True)}
        nama.discard('')
        if nama:
            for pk, kelas in Siswa._base_manager.filter(sekolah_id=self.sekolah_id).values_list('pk', 'kelas'):
                if _norm_kelas(kelas) in nama:
                    ids.add(pk)
        return ids

    def syarat(self, jenis, jalur):
        awalan = jalur + '__' if jalur else ''
        if jenis == 'ruang':
            return Q(**{awalan + 'guru_id': self.user_id})
        if jenis == 'siswa':
            return Q(**{(jalur + '__in') if jalur else 'pk__in': list(self.siswa_ids)})
        raise ValueError(jenis)


class LintasSekolah(PermissionDenied):
    """Dilempar saat ada upaya menulis/merujuk data sekolah lain (hasilnya HTTP 403)."""


def sekolah_aktif():
    return _aktif.get()


@contextmanager
def dalam_sekolah(sekolah, guru=None):
    """Menjalankan blok kode dalam lingkup satu sekolah. `sekolah`: objek Sekolah, id, None, atau BEBAS.
    `guru` (opsional, objek User atau id): terapkan juga pembatasan peran guru."""
    nilai = sekolah if (sekolah is None or sekolah is BEBAS) else getattr(sekolah, 'pk', sekolah)
    peran = None
    if guru is not None and isinstance(nilai, int) and nilai > 0:
        peran = PeranGuru(getattr(guru, 'pk', guru), nilai)
    t1 = _aktif.set(nilai)
    t2 = _peran.set(peran)
    try:
        yield
    finally:
        _peran.reset(t2)
        _aktif.reset(t1)


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

    def __init__(self, *jalur, guru=None, **kw):
        super().__init__(**kw)
        self._jalur = jalur
        self._guru = guru

    def _spek(self):
        if self._jalur:
            return self._jalur, self._guru
        # Manajer relasi (mis. ruang.tugas) dibuat tanpa argumen: ambil dari manajer asli model.
        asli = self.model._default_manager
        jalur = getattr(asli, '_jalur', None) or ('sekolah',)
        return jalur, getattr(asli, '_guru', None)

    @property
    def jalur(self):
        return self._spek()[0]

    @property
    def guru(self):
        """(jenis, lintasan) pembatas peran guru, atau None. jenis: 'ruang' (lintasan menuju RuangKerja,
        kosong bila model itu sendiri / punya kolom guru) atau 'siswa' (lintasan menuju Siswa)."""
        return self._spek()[1]

    def get_queryset(self):
        qs = super().get_queryset()
        sid = _aktif.get()
        if sid is BEBAS:
            return qs
        jalur, guru = self._spek()
        qs = qs.filter(_syarat(jalur, sid))
        peran = _peran.get()
        if peran is not None and guru:
            qs = qs.filter(peran.syarat(*guru))
        return qs

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


_MEMENGARUHI_SISWA_TERLIHAT = {'Siswa', 'RuangKerja', 'AnggotaRuangKerja', 'Kelas'}


@receiver(post_save, dispatch_uid='betsora_tenancy_post_save')
@receiver(post_delete, dispatch_uid='betsora_tenancy_post_delete')
def _segarkan_siswa_terlihat(sender, **kwargs):
    peran = _peran.get()
    if peran is not None and sender.__name__ in _MEMENGARUHI_SISWA_TERLIHAT:
        peran.reset()


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
        peran = None
        if isinstance(nilai, int) and nilai > 0 and getattr(user, 'role', None) == 'guru':
            peran = PeranGuru(user.pk, nilai)
        token = _aktif.set(nilai)
        token_peran = _peran.set(peran)
        try:
            return self.get_response(request)
        finally:
            _peran.reset(token_peran)
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
