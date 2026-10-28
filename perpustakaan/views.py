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
    semua_lencana = []
    lencana_didapat_ids = set()
    if siswa_obj:
        semua_lencana = Lencana.objects.all()
        lencana_didapat_ids = set(
            LencanaDiperoleh.objects.filter(siswa=siswa_obj).values_list('lencana_id', flat=True)
        )
    return render(request, 'perpustakaan/peta.html', {
        'zona_list': zona_list,
        'semua_lencana': semua_lencana,
        'lencana_didapat_ids': lencana_didapat_ids,
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
    from django.db.models import Q
    zona = get_object_or_404(Zona, id=zona_id)
    jenis_aktif = request.GET.get('jenis', '')
    usia_aktif = request.GET.get('usia', '')
    q = request.GET.get('q', '').strip()

    sumber_list = zona.sumber_list.all()
    if jenis_aktif == 'AUDIO':
        sumber_list = sumber_list.filter(Q(jenis='AUDIO') | ~Q(teks_baca=''))
    elif jenis_aktif in ('TEKS', 'VIDEO'):
        sumber_list = sumber_list.filter(jenis=jenis_aktif)
    else:
        jenis_aktif = ''

    rentang = {'6-8': (6, 8), '9-11': (9, 11), '12-18': (12, 99)}
    if usia_aktif in rentang:
        bawah, atas = rentang[usia_aktif]
        sumber_list = sumber_list.filter(usia_min__lte=atas).filter(Q(usia_maks=0) | Q(usia_maks__gte=bawah))
    else:
        usia_aktif = ''

    if q:
        sumber_list = sumber_list.filter(
            Q(judul__icontains=q) | Q(deskripsi__icontains=q) | Q(topik__icontains=q)
        )

    return render(request, 'perpustakaan/detail_zona.html', {
        'zona': zona,
        'sumber_list': sumber_list,
        'jenis_aktif': jenis_aktif,
        'usia_aktif': usia_aktif,
        'q': q,
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
            usia_min=_angka(request.POST.get('usia_min')),
            usia_maks=_angka(request.POST.get('usia_maks')),
            topik=request.POST.get('topik', '').strip()[:200],
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
        baru_penjelajah = False
        if jenis in ('AUDIO', 'FOTO') and refleksi.file:
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
        if jenis == 'FOTO':
            lencana_penjelajah, _ = Lencana.objects.get_or_create(
                nama='Lencana Penjelajah',
                defaults={'ikon': '\U0001F9ED', 'deskripsi': 'Diberikan saat mengunggah karya ke Perpustakaan Digital.'}
            )
            _, baru_penjelajah = LencanaDiperoleh.objects.get_or_create(
                siswa=siswa_obj, lencana=lencana_penjelajah, sumber=None
            )
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
        if baru_penjelajah:
            from django.urls import reverse
            return redirect(reverse('perpustakaan:detail_sumber', args=[sumber.id]) + '?lencana_baru=1')
        return redirect('perpustakaan:detail_sumber', sumber_id=sumber.id)

    refleksi_list = batasi_kelas(request.user, sumber.refleksi_list.select_related('siswa'))[:20]
    halaman_data = [
        {'gambar': h.gambar.url, 'teks': h.teks}
        for h in sumber.halaman_list.all()
    ]
    suara_teman = [r for r in refleksi_list if r.jenis == 'AUDIO' and r.file]
    return render(request, 'perpustakaan/detail_sumber.html', {
        'sumber': sumber,
        'siswa_obj': siswa_obj,
        'refleksi_list': refleksi_list,
        'halaman_data': halaman_data,
        'suara_teman': suara_teman,
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
        sumber.usia_min = _angka(request.POST.get('usia_min'))
        sumber.usia_maks = _angka(request.POST.get('usia_maks'))
        sumber.topik = request.POST.get('topik', '').strip()[:200]
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


@login_required
def catat_selesai_baca(request, sumber_id):
    from django.http import JsonResponse
    from .models import RiwayatBaca
    sumber = SumberDigital.objects.filter(id=sumber_id).first()
    siswa_obj = get_siswa_obj(request.user) if request.user.role == 'siswa' else None
    if sumber and siswa_obj and request.method == 'POST':
        RiwayatBaca.objects.update_or_create(siswa=siswa_obj, sumber=sumber)
        return JsonResponse({'ok': True})
    return JsonResponse({'ok': False}, status=400)


# ======================================================================
# PERPUSTAKAAN v2: pembaca interaktif, progres baca, glosarium
# ======================================================================
from django.http import JsonResponse
from django.views.decorators.http import require_POST as _post_saja
from .models import ProgresBaca, Glosarium


def _angka(nilai, default=0, maks=120):
    try:
        n = int(nilai)
    except (TypeError, ValueError):
        return default
    return max(0, min(n, maks))


@login_required
def baca_sumber(request, sumber_id):
    sumber = get_object_or_404(SumberDigital, id=sumber_id)
    if not sumber.file or not sumber.file.name.lower().endswith('.pdf'):
        messages.error(request, 'Pembaca interaktif hanya untuk e-book berformat PDF.')
        return redirect('perpustakaan:detail_sumber', sumber_id=sumber.id)
    siswa_obj = get_siswa_obj(request.user) if request.user.role == 'siswa' else None
    halaman_mulai = 0
    if siswa_obj:
        progres = ProgresBaca.objects.filter(siswa=siswa_obj, sumber=sumber).first()
        if progres and not progres.selesai:
            halaman_mulai = max(0, progres.halaman_terakhir - 1)
    return render(request, 'perpustakaan/baca_sumber.html', {
        'sumber': sumber,
        'bisa_simpan': bool(siswa_obj),
        'halaman_mulai': halaman_mulai,
        'glosarium': list(sumber.glosarium_list.values('istilah', 'arti')),
        'narasi_guru': {h.nomor - 1: h.audio_guru.url for h in sumber.halaman_list.exclude(audio_guru='').exclude(audio_guru__isnull=True)},
    })


@login_required
@_post_saja
def simpan_progres(request, sumber_id):
    sumber = get_object_or_404(SumberDigital, id=sumber_id)
    siswa_obj = get_siswa_obj(request.user) if request.user.role == 'siswa' else None
    if not siswa_obj:
        return JsonResponse({'ok': False, 'selesai': False}, status=403)
    total = _angka(request.POST.get('total'), 0, 5000)
    halaman = _angka(request.POST.get('halaman'), 1, 5000)
    dilihat = _angka(request.POST.get('dilihat'), 0, 5000)
    if total < 1:
        return JsonResponse({'ok': False, 'selesai': False}, status=400)
    halaman = max(1, min(halaman, total))

    progres, _ = ProgresBaca.objects.get_or_create(
        siswa=siswa_obj, sumber=sumber,
        defaults={'halaman_terakhir': halaman, 'total_halaman': total},
    )
    progres.halaman_terakhir = halaman
    progres.total_halaman = total

    baru = False
    syarat = -(-total * 6 // 10)  # minimal 60% halaman pernah dibuka
    if not progres.selesai and halaman >= total and dilihat >= syarat:
        progres.selesai = True
        baru = True
    progres.save()

    lencana_baru = False
    lencana_nama = ''
    lencana_ikon = ''
    if baru and sumber.lencana_hadiah:
        _, lencana_baru = LencanaDiperoleh.objects.get_or_create(
            siswa=siswa_obj, lencana=sumber.lencana_hadiah, sumber=sumber
        )
        lencana_nama = sumber.lencana_hadiah.nama
        lencana_ikon = sumber.lencana_hadiah.ikon

    return JsonResponse({
        'ok': True,
        'selesai': progres.selesai,
        'baru': baru,
        'lencana_baru': lencana_baru,
        'lencana_nama': lencana_nama,
        'lencana_ikon': lencana_ikon,
    })


@login_required
def glosarium_sumber(request, sumber_id):
    sumber = get_object_or_404(SumberDigital, id=sumber_id)
    if not adalah_staf(request.user):
        messages.error(request, 'Hanya guru yang dapat mengelola glosarium.')
        return redirect('perpustakaan:detail_sumber', sumber_id=sumber.id)
    if request.method == 'POST':
        tersimpan = 0
        istilah = request.POST.get('istilah', '').strip()
        arti = request.POST.get('arti', '').strip()
        if istilah and arti:
            Glosarium.objects.update_or_create(
                sumber=sumber, istilah=istilah[:100], defaults={'arti': arti}
            )
            tersimpan += 1
        for baris in request.POST.get('massal', '').splitlines():
            if '=' not in baris:
                continue
            i, a = baris.split('=', 1)
            i, a = i.strip(), a.strip()
            if i and a:
                Glosarium.objects.update_or_create(
                    sumber=sumber, istilah=i[:100], defaults={'arti': a}
                )
                tersimpan += 1
        if tersimpan:
            messages.success(request, '%d istilah disimpan.' % tersimpan)
        else:
            messages.error(request, 'Isi istilah dan artinya, atau tempel daftar "istilah = arti".')
        return redirect('perpustakaan:glosarium', sumber_id=sumber.id)
    return render(request, 'perpustakaan/glosarium.html', {
        'sumber': sumber,
        'daftar': sumber.glosarium_list.all(),
    })


@login_required
@_post_saja
def hapus_glosarium(request, glos_id):
    g = get_object_or_404(Glosarium, id=glos_id)
    sumber_id = g.sumber_id
    if not adalah_staf(request.user):
        messages.error(request, 'Hanya guru yang dapat menghapus istilah.')
    else:
        g.delete()
        messages.success(request, 'Istilah dihapus.')
    return redirect('perpustakaan:glosarium', sumber_id=sumber_id)


@login_required
@require_POST
def hapus_refleksi(request, refleksi_id):
    refleksi = RefleksiSiswa.objects.filter(id=refleksi_id).first()
    if not refleksi:
        messages.error(request, 'Refleksi ini sudah tidak tersedia.')
        return redirect('perpustakaan:peta')
    sumber_id = refleksi.sumber_id
    siswa_obj = get_siswa_obj(request.user) if request.user.role == 'siswa' else None
    pemilik = siswa_obj and refleksi.siswa_id == siswa_obj.id
    if not (adalah_staf(request.user) or pemilik):
        messages.error(request, 'Kamu tidak punya izin untuk menghapus ini.')
        return redirect('perpustakaan:detail_sumber', sumber_id=sumber_id)
    refleksi.delete()
    messages.success(request, 'Refleksi berhasil dihapus.')
    return redirect('perpustakaan:detail_sumber', sumber_id=sumber_id)


@login_required
def kelola_narasi(request, sumber_id):
    from .models import HalamanSumber
    from django.core.paginator import Paginator
    sumber = get_object_or_404(SumberDigital, id=sumber_id)
    if not adalah_staf(request.user):
        messages.error(request, 'Hanya guru yang dapat mengelola narasi.')
        return redirect('perpustakaan:detail_sumber', sumber_id=sumber.id)
    semua_halaman = sumber.halaman_list.all()
    if not semua_halaman.exists():
        messages.info(request, 'Buat dulu tampilan halaman dari PDF sebelum menambah narasi (tombol "Buat tampilan komik dari PDF" di halaman koleksi).')
        return redirect('perpustakaan:detail_sumber', sumber_id=sumber.id)
    paginator = Paginator(semua_halaman, 20)
    nomor_hal = request.GET.get('p', '1')
    halaman_page = paginator.get_page(nomor_hal)
    total = semua_halaman.count()
    terisi = semua_halaman.exclude(audio_guru='').exclude(audio_guru__isnull=True).count()
    return render(request, 'perpustakaan/kelola_narasi.html', {
        'sumber': sumber,
        'halaman_page': halaman_page,
        'total': total,
        'terisi': terisi,
    })


@login_required
@require_POST
def simpan_narasi(request, halaman_id):
    from .models import HalamanSumber
    halaman = get_object_or_404(HalamanSumber, id=halaman_id)
    sumber_id = halaman.sumber_id
    if not adalah_staf(request.user):
        messages.error(request, 'Hanya guru yang dapat menyimpan narasi.')
        return redirect('perpustakaan:kelola_narasi', sumber_id=sumber_id)
    berkas = request.FILES.get('audio')
    if not berkas:
        messages.error(request, 'Pilih atau rekam audio dulu sebelum menyimpan.')
    else:
        halaman.audio_guru = berkas
        halaman.save(update_fields=['audio_guru'])
        messages.success(request, 'Narasi halaman %d tersimpan.' % halaman.nomor)
    halaman_num = request.GET.get('p', '1')
    from django.shortcuts import redirect as _redirect
    from django.urls import reverse as _reverse
    return _redirect('%s?p=%s' % (_reverse('perpustakaan:kelola_narasi', args=[sumber_id]), halaman_num))


@login_required
@require_POST
def hapus_narasi(request, halaman_id):
    from .models import HalamanSumber
    halaman = get_object_or_404(HalamanSumber, id=halaman_id)
    sumber_id = halaman.sumber_id
    if not adalah_staf(request.user):
        messages.error(request, 'Hanya guru yang dapat menghapus narasi.')
    else:
        halaman.audio_guru.delete(save=False)
        halaman.audio_guru = None
        halaman.save(update_fields=['audio_guru'])
        messages.success(request, 'Narasi halaman %d dihapus.' % halaman.nomor)
    halaman_num = request.GET.get('p', '1')
    from django.urls import reverse as _reverse
    return redirect('%s?p=%s' % (_reverse('perpustakaan:kelola_narasi', args=[sumber_id]), halaman_num))
