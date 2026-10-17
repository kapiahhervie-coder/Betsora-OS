from django import forms

from kreasi.fase_config import BATAS_TEKS, MAKS_UKURAN_MB
from ruang_kerja.models import Materi, RuangKerja

from .models import CatatanMisi, Misi, PenugasanMisi

INPUT_CSS = (
    "w-full border border-gray-300 rounded-lg px-3 py-2 text-sm "
    "focus:outline-none focus:ring-2 focus:ring-primary-mid"
)


class _Gaya:
    """Beri kelas Tailwind yang sama ke semua field."""

    def _gaya(self):
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", INPUT_CSS)


class CatatanForm(_Gaya, forms.ModelForm):
    class Meta:
        model = CatatanMisi
        fields = ("teks", "angka", "foto")
        labels = {"teks": "Catatan pengamatan", "foto": "Foto (opsional)"}
        widgets = {
            "teks": forms.Textarea(attrs={"rows": 3, "placeholder": "Apa yang kamu lihat, dengar, atau temukan?"}),
            "foto": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    def __init__(self, *args, misi=None, **kwargs):
        super().__init__(*args, **kwargs)
        if misi is not None and misi.pakai_angka:
            label = misi.label_angka
            if misi.satuan_angka:
                label = f"{label} ({misi.satuan_angka})"
            self.fields["angka"].label = label
            self.fields["angka"].widget.attrs.update({"step": "any", "inputmode": "decimal"})
        else:
            del self.fields["angka"]
        self._gaya()

    def clean_teks(self):
        teks = self.cleaned_data.get("teks", "")
        if len(teks) > BATAS_TEKS:
            raise forms.ValidationError(f"Catatan terlalu panjang (maksimal {BATAS_TEKS} huruf).")
        return teks

    def clean_foto(self):
        foto = self.cleaned_data.get("foto")
        if foto and foto.size > MAKS_UKURAN_MB["foto"] * 1024 * 1024:
            raise forms.ValidationError(f"Foto terlalu besar (maksimal {MAKS_UKURAN_MB['foto']} MB).")
        return foto

    def clean_angka(self):
        angka = self.cleaned_data.get("angka")
        if angka is not None and angka < 0:
            raise forms.ValidationError("Angka tidak boleh negatif.")
        return angka

    def clean(self):
        data = super().clean()
        if not ((data.get("teks") or "").strip() or data.get("angka") is not None or data.get("foto")):
            raise forms.ValidationError("Isi catatan, angka, atau foto dulu ya.")
        return data


class RefleksiForm(_Gaya, forms.Form):
    refleksi = forms.CharField(
        label="Jawabanmu",
        min_length=10,
        max_length=BATAS_TEKS,
        error_messages={"min_length": "Ceritakan sedikit lebih banyak ya (minimal 10 huruf)."},
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Tulis jawabanmu di sini..."}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._gaya()


class KonfirmasiForm(_Gaya, forms.Form):
    """Nilai hanya dipakai guru dan hanya bila misi ditugaskan ke sebuah topik."""

    nilai = forms.DecimalField(
        label="Nilai formatif (opsional, 0-100)",
        required=False, min_value=0, max_value=100, max_digits=5, decimal_places=1,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._gaya()


class PenugasanForm(_Gaya, forms.ModelForm):
    class Meta:
        model = PenugasanMisi
        fields = ("misi", "ruang_kerja", "materi", "tenggat")
        labels = {"misi": "Misi", "ruang_kerja": "Ruang kerja", "materi": "Topik (opsional)", "tenggat": "Tenggat (opsional)"}
        widgets = {
            "tenggat": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        ruang = RuangKerja.objects.all()
        if user.role == "guru":
            ruang = ruang.filter(guru=user)
        self.fields["ruang_kerja"].queryset = ruang
        self.fields["materi"].queryset = Materi.objects.filter(ruang_kerja__in=ruang).select_related("ruang_kerja")
        self.fields["misi"].queryset = Misi.objects.filter(aktif=True)
        self.fields["tenggat"].input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"]
        self.fields["materi"].required = False
        self.fields["tenggat"].required = False
        self._gaya()
