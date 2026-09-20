from django.db.models import Count
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from .izin import adalah_staf, staf_required
from .models import AlbumAudio, Audio, Zona, Lencana, SumberDigital, RefleksiSiswa, LencanaDiperoleh


@login_required
def daftar_album(request):
    album_list = AlbumAudio.objects.all()
    return render(request, 'perpustakaan/daftar_album.html', {
        'album_list': album_list,
    })


@login_required
@staf_required('Hanya guru yang dapat membuat album.')
def buat_album(request):
    if request.method == 'POST':
        judul = request.POST.get('judul', '').strip()
        if not judul:
            messages.error(request, 'Judul album tidak boleh kosong.')
            return redirect('perpustakaan:buat')
        AlbumAudio.objects.create(
            judul=judul[:150],
            deskripsi=request.POST.get('deskripsi', ''),
            dibuat_oleh=request.user,
        )
        messages.success(request, 'Album berhasil dibuat.')
        return redirect('perpustakaan:daftar')
    return render(request, 'perpustakaan/buat_album.html')


@login_required
def detail_album(request, album_id):
    album = get_object_or_404(AlbumAudio, id=album_id)
    if request.method == 'POST':
        if not adalah_staf(request.user):
            messages.error(request, 'Hanya guru yang dapat menambah audio.')
            return redirect('perpustakaan:detail', album_id=album.id)
        judul = request.POST.get('judul', '').strip()
        berkas = request.FILES.get('file')
        if not judul or not berkas:
            messages.error(request, 'Judul dan file audio wajib diisi.')
            return redirect('perpustakaan:detail', album_id=album.id)
        Audio.objects.create(
            album=album,
            judul=judul[:150],
            file=berkas,
            urutan=album.audio_list.count(),
            diunggah_oleh=request.user,
        )
        messages.success(request, 'Audio berhasil ditambahkan.')
        return redirect('perpustakaan:detail', album_id=album.id)
    return render(request, 'perpustakaan/detail_album.html', {
        'album': album,
    })


@login_required
@require_POST
@staf_required('Hanya guru yang dapat menghapus album.')
def hapus_album(request, album_id):
    album = get_object_or_404(AlbumAudio, id=album_id)
    album.delete()
    messages.success(request, 'Album berhasil dihapus.')
    return redirect('perpustakaan:daftar')


@login_required
@require_POST
def hapus_audio(request, audio_id):
    audio = get_object_or_404(Audio, id=audio_id)
    album_id = audio.album_id
    if not adalah_staf(request.user):
        messages.error(request, 'Hanya guru yang dapat menghapus audio.')
    else:
        audio.delete()
        messages.success(request, 'Audio berhasil dihapus.')
    return redirect('perpustakaan:detail', album_id=album_id)


def get_siswa_obj(user):
    return getattr(user, 'profil_siswa', None)


@login_required
def peta_perpustakaan(request):
    zona_list = Zona.objects.annotate(jumlah=Count('sumber_list'))
    siswa_obj = get_siswa_obj(request.user) if request.user.role == 'siswa' else None
    lencana_saya = []
    if siswa_obj:
        lencana_saya = LencanaDiperoleh.objects.filter(siswa=siswa_obj).select_related('lencana')
    return render(request, 'perpustakaan/peta.html', {
        'zona_list': zona_list,
        'lencana_saya': lencana_saya,
    })


@login_required
@staf_required('Hanya guru yang dapat menambah zona.', ke='perpustakaan:peta')
def tambah_zona(request):
    if request.method == 'POST':
        nama = request.POST.get('nama', '').strip()
        if not nama:
            messages.error(request, 'Nama zona tidak boleh kosong.')
            return redirect('perpustakaan:tambah_zona')
        Zona.objects.create(
            nama=nama[:100],
            ikon=request.POST.get('ikon', ''),
            warna=request.POST.get('warna', '#0B3D26'),
            deskripsi=request.POST.get('deskripsi', ''),
            urutan=Zona.objects.count(),
            dibuat_oleh=request.user,
        )
        messages.success(request, 'Zona berhasil dibuat.')
        return redirect('perpustakaan:peta')
    return render(request, 'perpustakaan/tambah_zona.html')


@login_required
@require_POST
@staf_required('Hanya guru yang dapat menghapus zona.', ke='perpustakaan:peta')
def hapus_zona(request, zona_id):
    zona = Zona.objects.filter(id=zona_id).first()
    if not zona:
        messages.error(request, 'Zona ini sudah tidak tersedia (mungkin sudah dihapus).')
        return redirect('perpustakaan:peta')
    zona.delete()
    messages.success(request, 'Zona berhasil dihapus.')
    return redirect('perpustakaan:peta')


@login_required
def detail_zona(request, zona_id):
    zona = Zona.objects.filter(id=zona_id).first()
    if not zona:
        messages.error(request, 'Zona ini sudah tidak tersedia (mungkin sudah dihapus).')
        return redirect('perpustakaan:peta')
    jenis_aktif = request.GET.get('jenis', '')
    sumber_list = zona.sumber_list.all()
    if jenis_aktif in ('TEKS', 'AUDIO', 'VIDEO'):
        if jenis_aktif == 'AUDIO':
            from django.db.models import Q
            sumber_list = sumber_list.filter(Q(jenis='AUDIO') | ~Q(teks_baca=''))
        else:
            sumber_list = sumber_list.filter(jenis=jenis_aktif)
    else:
        jenis_aktif = ''
    return render(request, 'perpustakaan/detail_zona.html', {
        'zona': zona,
        'sumber_list': sumber_list,
        'jenis_aktif': jenis_aktif,
    })


@login_required
def tambah_sumber(request, zona_id):
    zona = Zona.objects.filter(id=zona_id).first()
    if not zona:
        messages.error(request, 'Zona ini sudah tidak tersedia (mungkin sudah dihapus).')
        return redirect('perpustakaan:peta')
    if not adalah_staf(request.user):
        messages.error(request, 'Hanya guru yang dapat menambah sumber digital.')
        return redirect('perpustakaan:detail_zona', zona_id=zona.id)
    lencana_list = Lencana.objects.all()
    if request.method == 'POST':
        lencana_id = request.POST.get('lencana_hadiah') or None
        SumberDigital.objects.create(
            zona=zona,
            judul=request.POST.get('judul'),
            deskripsi=request.POST.get('deskripsi', ''),
            jenis=request.POST.get('jenis', 'TEKS'),
            cover=request.FILES.get('cover'),
            file=request.FILES.get('file'),
            link_url=request.POST.get('link_url') or None,
            teks_baca=request.POST.get('teks_baca', '').strip(),
            lencana_hadiah_id=lencana_id,
            diunggah_oleh=request.user,
        )
        messages.success(request, 'Sumber digital berhasil ditambahkan.')
        return redirect('perpustakaan:detail_zona', zona_id=zona.id)
    return render(request, 'perpustakaan/tambah_sumber.html', {
        'zona': zona,
        'lencana_list': lencana_list,
    })


@login_required
@require_POST
def hapus_sumber(request, sumber_id):
    sumber = SumberDigital.objects.filter(id=sumber_id).first()
    if not sumber:
        messages.error(request, 'Koleksi ini sudah tidak tersedia (mungkin sudah dihapus).')
        return redirect('perpustakaan:peta')
    zona_id = sumber.zona_id
    if not adalah_staf(request.user):
        messages.error(request, 'Hanya guru yang dapat menghapus sumber digital.')
    else:
        sumber.delete()
        messages.success(request, 'Sumber digital berhasil dihapus.')
    return redirect('perpustakaan:detail_zona', zona_id=zona_id)


MAKS_UKURAN = 10 * 1024 * 1024  # 10 MB


@login_required
def detail_sumber(request, sumber_id):
    sumber = SumberDigital.objects.filter(id=sumber_id).first()
    if not sumber:
        messages.error(request, 'Koleksi ini sudah tidak tersedia (mungkin sudah dihapus).')
        return redirect('perpustakaan:peta')
    siswa_obj = get_siswa_obj(request.user) if request.user.role == 'siswa' else None

    if request.method == 'POST' and siswa_obj:
        jenis = request.POST.get('jenis', 'TEKS')
        teks = request.POST.get('teks', '').strip()
        berkas = None
        error = None

        if jenis == 'TEKS':
            if not teks:
                error = 'Tulis dulu refleksimu ya.'
        elif jenis in ('AUDIO', 'FOTO'):
            berkas = request.FILES.get('file_audio' if jenis == 'AUDIO' else 'file_foto')
            awalan = 'audio/' if jenis == 'AUDIO' else 'image/'
            if not berkas:
                error = 'Rekam suara atau pilih foto dulu ya.'
            elif berkas.size > MAKS_UKURAN:
                error = 'Ukuran file maksimal 10 MB.'
            elif not (berkas.content_type or '').startswith(awalan):
                error = 'Jenis file tidak sesuai.'
        else:
            error = 'Jenis refleksi tidak valid.'

        if error:
            messages.error(request, error)
            return redirect('perpustakaan:detail_sumber', sumber_id=sumber.id)

        refleksi = RefleksiSiswa.objects.create(
            siswa=siswa_obj, sumber=sumber, jenis=jenis,
            teks=teks, file=berkas,
        )
        if request.POST.get('simpan_portofolio') and jenis in ('AUDIO', 'FOTO') and refleksi.file:
            try:
                from portofolio.models import KaryaSiswa
                KaryaSiswa.objects.create(
                    siswa=siswa_obj,
                    judul=('Rekaman: ' if jenis == 'AUDIO' else 'Foto karya: ') + sumber.judul[:150],
                    deskripsi='Dari Perpustakaan Digital',
                    file=refleksi.file.name,
                    video_url='',
                    dibagikan=False,
                    refleksi=teks,
                )
                messages.info(request, 'Karya juga tersimpan di Portofolio kamu.')
            except Exception:
                messages.warning(request, 'Refleksi terkirim, tetapi belum bisa disimpan ke Portofolio.')
        if sumber.lencana_hadiah:
            _, baru = LencanaDiperoleh.objects.get_or_create(
                siswa=siswa_obj, lencana=sumber.lencana_hadiah, sumber=sumber
            )
            if baru:
                messages.success(request, 'Refleksi terkirim. Lencana baru diperoleh!')
            else:
                messages.success(request, 'Refleksi terkirim, terima kasih!')
        else:
            messages.success(request, 'Refleksi terkirim, terima kasih!')
        return redirect('perpustakaan:detail_sumber', sumber_id=sumber.id)

    refleksi_list = batasi_kelas(request.user, sumber.refleksi_list.select_related('siswa'))[:20]
    halaman_data = [
        {'gambar': h.gambar.url, 'teks': h.teks}
        for h in sumber.halaman_list.all()
    ]
    return render(request, 'perpustakaan/detail_sumber.html', {
        'sumber': sumber,
        'siswa_obj': siswa_obj,
        'refleksi_list': refleksi_list,
        'halaman_data': halaman_data,
    })


def batasi_kelas(user, qs):
    # guru/kepsek/admin: semua kelas. siswa & orang tua: hanya kelas sendiri.
    if user.role == 'siswa':
        siswa = get_siswa_obj(user)
        kelas = siswa.kelas if siswa else None
    elif user.role == 'orangtua':
        kelas = user.anak.kelas if getattr(user, 'anak', None) else None
    else:
        return qs
    if not kelas:
        return qs.none()
    return qs.filter(siswa__kelas=kelas)


@login_required
def galeri_karya(request):
    from django.utils import timezone
    semua = request.GET.get('semua') == '1'
    qs = RefleksiSiswa.objects.exclude(jenis='TEKS').select_related('siswa', 'sumber')
    qs = batasi_kelas(request.user, qs)
    if not semua:
        qs = qs.filter(dibuat_pada__date=timezone.localdate())
    return render(request, 'perpustakaan/galeri_karya.html', {
        'refleksi_list': qs[:30],
        'semua': semua,
    })


@login_required
def edit_zona(request, zona_id):
    import re
    zona = Zona.objects.filter(id=zona_id).first()
    if not zona:
        messages.error(request, 'Zona ini sudah tidak tersedia (mungkin sudah dihapus).')
        return redirect('perpustakaan:peta')
    if not adalah_staf(request.user):
        messages.error(request, 'Hanya guru yang dapat mengedit zona.')
        return redirect('perpustakaan:detail_zona', zona_id=zona.id)
    if request.method == 'POST':
        nama = request.POST.get('nama', '').strip()
        if not nama:
            messages.error(request, 'Nama zona tidak boleh kosong.')
            return redirect('perpustakaan:edit_zona', zona_id=zona.id)
        warna = request.POST.get('warna', '')
        zona.nama = nama[:100]
        zona.ikon = request.POST.get('ikon', '').strip()[:10]
        if re.match(r'^#[0-9a-fA-F]{6}$', warna):
            zona.warna = warna
        zona.deskripsi = request.POST.get('deskripsi', '').strip()
        zona.save()
        messages.success(request, 'Zona berhasil diperbarui.')
        return redirect('perpustakaan:detail_zona', zona_id=zona.id)
    return render(request, 'perpustakaan/edit_zona.html', {'zona': zona})


@login_required
def edit_sumber(request, sumber_id):
    sumber = SumberDigital.objects.filter(id=sumber_id).first()
    if not sumber:
        messages.error(request, 'Koleksi ini sudah tidak tersedia (mungkin sudah dihapus).')
        return redirect('perpustakaan:peta')
    if not adalah_staf(request.user):
        messages.error(request, 'Hanya guru yang dapat mengedit koleksi.')
        return redirect('perpustakaan:detail_sumber', sumber_id=sumber.id)
    if request.method == 'POST':
        judul = request.POST.get('judul', '').strip()
        if not judul:
            messages.error(request, 'Judul tidak boleh kosong.')
            return redirect('perpustakaan:edit_sumber', sumber_id=sumber.id)
        jenis = request.POST.get('jenis', '')
        if jenis in ('TEKS', 'AUDIO', 'VIDEO'):
            sumber.jenis = jenis
        zid = request.POST.get('zona', '')
        if zid.isdigit():
            zona_baru = Zona.objects.filter(id=int(zid)).first()
            if zona_baru:
                sumber.zona = zona_baru
        lid = request.POST.get('lencana_hadiah', '')
        sumber.lencana_hadiah = Lencana.objects.filter(id=int(lid)).first() if lid.isdigit() else None
        sumber.judul = judul[:200]
        sumber.deskripsi = request.POST.get('deskripsi', '').strip()
        sumber.link_url = request.POST.get('link_url', '').strip() or None
        sumber.teks_baca = request.POST.get('teks_baca', '').strip()
        if request.FILES.get('cover'):
            sumber.cover = request.FILES['cover']
        elif request.POST.get('hapus_cover'):
            sumber.cover = None
        if request.FILES.get('file'):
            sumber.file = request.FILES['file']
        sumber.save()
        messages.success(request, 'Koleksi berhasil diperbarui.')
        return redirect('perpustakaan:detail_sumber', sumber_id=sumber.id)
    return render(request, 'perpustakaan/edit_sumber.html', {
        'sumber': sumber,
        'zona_list': Zona.objects.all(),
        'lencana_list': Lencana.objects.all(),
    })


@login_required
def ekstrak_teks(request, sumber_id):
    sumber = SumberDigital.objects.filter(id=sumber_id).first()
    if not sumber:
        messages.error(request, 'Koleksi ini sudah tidak tersedia (mungkin sudah dihapus).')
        return redirect('perpustakaan:peta')
    if not adalah_staf(request.user) or request.method != 'POST':
        messages.error(request, 'Tidak diizinkan.')
        return redirect('perpustakaan:detail_sumber', sumber_id=sumber.id)
    kembali = redirect('perpustakaan:edit_sumber', sumber_id=sumber.id)
    if not sumber.file or not sumber.file.name.lower().endswith('.pdf'):
        messages.error(request, 'Fitur ini hanya untuk file PDF. Teks bisa diketik atau ditempel manual.')
        return kembali
    try:
        from pypdf import PdfReader
    except ImportError:
        messages.error(request, 'Pustaka pypdf belum terpasang. Jalankan: pip install pypdf')
        return kembali
    try:
        reader = PdfReader(sumber.file.path)
        bagian = [(h.extract_text() or '').strip() for h in reader.pages]
        teks = '\n\n'.join(b for b in bagian if b)
    except Exception:
        messages.error(request, 'PDF tidak bisa dibaca. Coba ketik atau tempel teks manual.')
        return kembali
    if not teks.strip():
        messages.warning(request, 'Tidak ada teks terbaca (mungkin PDF berupa gambar hasil scan). Ketik atau tempel teks manual.')
    else:
        sumber.teks_baca = teks
        sumber.save(update_fields=['teks_baca'])
        messages.success(request, 'Teks diambil dari PDF (%d karakter). Periksa dan rapikan bila perlu.' % len(teks))
    return kembali

@login_required
def ekstrak_halaman(request, sumber_id):
    from .models import HalamanSumber
    sumber = SumberDigital.objects.filter(id=sumber_id).first()
    if not sumber:
        messages.error(request, 'Koleksi ini sudah tidak tersedia (mungkin sudah dihapus).')
        return redirect('perpustakaan:peta')
    if not adalah_staf(request.user) or request.method != 'POST':
        messages.error(request, 'Tidak diizinkan.')
        return redirect('perpustakaan:detail_sumber', sumber_id=sumber.id)
    kembali = redirect('perpustakaan:detail_sumber', sumber_id=sumber.id)
    if not sumber.file or not sumber.file.name.lower().endswith('.pdf'):
        messages.error(request, 'Fitur ini hanya untuk file PDF.')
        return kembali
    try:
        import fitz
    except ImportError:
        messages.error(request, 'Pustaka PyMuPDF belum terpasang. Jalankan: pip install pymupdf')
        return kembali

    teks_per_halaman = []
    try:
        from pypdf import PdfReader
        reader = PdfReader(sumber.file.path)
        teks_per_halaman = [(h.extract_text() or '').strip() for h in reader.pages]
    except Exception:
        teks_per_halaman = []

    try:
        from django.core.files.base import ContentFile
        doc = fitz.open(sumber.file.path)
        sumber.halaman_list.all().delete()
        total = 0
        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes('png')
            teks_hal = teks_per_halaman[i] if i < len(teks_per_halaman) else ''
            halaman = HalamanSumber(sumber=sumber, nomor=i + 1, teks=teks_hal)
            halaman.gambar.save('hal_%d.png' % (i + 1), ContentFile(img_bytes), save=False)
            halaman.save()
            total += 1
        doc.close()
        messages.success(request, 'Berhasil membuat %d halaman gambar dari PDF.' % total)
    except Exception as e:
        messages.error(request, 'Gagal mengekstrak halaman PDF: ' + str(e))
    return kembali
