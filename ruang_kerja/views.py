from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from accounts.models import Siswa
from django.db.models import Avg
from .models import RuangKerja, Materi, SubMateri, Pengumuman, Tugas, SubmisiTugas, AnggotaRuangKerja, MataPelajaran, CatatanRapor, RefleksiTopik, PenilaianTopik, SoalPG, OpsiPG, JawabanPG


def get_kelas_siswa(user):
    if hasattr(user, 'profil_siswa'):
        return user.profil_siswa.kelas
    return None


def get_siswa_obj(user):
    return getattr(user, 'profil_siswa', None)


def is_anggota(ruang, siswa_obj):
    if not siswa_obj:
        return False
    return AnggotaRuangKerja.objects.filter(ruang_kerja=ruang, siswa=siswa_obj).exists()


@login_required
def daftar_ruang_kerja(request):
    if request.user.role == 'siswa':
        siswa_obj = get_siswa_obj(request.user)
        if siswa_obj:
            ruang_list = RuangKerja.objects.filter(anggota__siswa=siswa_obj).distinct()
        else:
            ruang_list = RuangKerja.objects.none()
    else:
        ruang_list = RuangKerja.objects.all()
    kelas_list = Siswa.objects.values_list('kelas', flat=True).distinct().order_by('kelas')
    return render(request, 'ruang_kerja/daftar.html', {'ruang_list': ruang_list, 'kelas_list': kelas_list})


@login_required
def hapus_ruang_kerja(request, ruang_id):
    ruang = get_object_or_404(RuangKerja, id=ruang_id)
    if request.user.role == 'siswa':
        messages.error(request, 'Hanya guru yang dapat menghapus ruang kerja.')
        return redirect('ruang_kerja:daftar')
    if request.method == 'POST':
        nama = f"{ruang.mapel} Kelas {ruang.kelas}"
        ruang.delete()
        messages.success(request, f'Ruang kerja "{nama}" berhasil dihapus.')
    return redirect('ruang_kerja:daftar')


@login_required
def buat_ruang_kerja(request):
    if request.user.role == 'siswa':
        messages.error(request, 'Hanya guru yang dapat membuat ruang kerja.')
        return redirect('ruang_kerja:daftar')
    kelas_list = Siswa.objects.values_list('kelas', flat=True).distinct().order_by('kelas')
    mapel_list = MataPelajaran.objects.all()
    if request.method == 'POST':
        mapel = request.POST.get('mapel')
        kelas = request.POST.get('kelas')
        if RuangKerja.objects.filter(mapel=mapel, kelas=kelas).exists():
            messages.error(request, f'Ruang kerja {mapel} Kelas {kelas} sudah ada.')
        else:
            ruang = RuangKerja.objects.create(
                mapel=mapel, kelas=kelas,
                deskripsi=request.POST.get('deskripsi', ''),
                guru=request.user
            )
            messages.success(request, 'Ruang kerja berhasil dibuat. Sekarang tambahkan anggota siswanya.')
            return redirect('ruang_kerja:kelola_anggota', ruang_id=ruang.id)
    return render(request, 'ruang_kerja/buat.html', {'kelas_list': kelas_list, 'mapel_list': mapel_list})


@login_required
def detail_ruang_kerja(request, ruang_id):
    ruang = get_object_or_404(RuangKerja, id=ruang_id)

    siswa_obj = None
    tugas_sudah_submit = set()
    refleksi_map = {}
    if request.user.role == 'siswa':
        siswa_obj = get_siswa_obj(request.user)
        if not is_anggota(ruang, siswa_obj):
            messages.error(request, 'Anda belum menjadi anggota ruang kerja ini.')
            return redirect('ruang_kerja:daftar')
        tugas_sudah_submit = set(
            SubmisiTugas.objects.filter(siswa=siswa_obj, tugas__ruang_kerja=ruang)
            .values_list('tugas_id', flat=True)
        )
        refleksi_map = {
            r.materi_id: r.isi
            for r in RefleksiTopik.objects.filter(materi__ruang_kerja=ruang, siswa=siswa_obj)
        }

    materi_list = ruang.materi.all()
    for m in materi_list:
        m.locked = m.is_locked_for(siswa_obj) if siswa_obj else False
    pengumuman_list = ruang.pengumuman.all()
    tugas_list = ruang.tugas.all()
    jumlah_anggota = ruang.anggota.count()

    from .models import StatusBaca
    StatusBaca.objects.update_or_create(ruang_kerja=ruang, user=request.user)

    return render(request, 'ruang_kerja/detail.html', {
        'ruang': ruang,
        'materi_list': materi_list,
        'pengumuman_list': pengumuman_list,
        'tugas_list': tugas_list,
        'siswa_obj': siswa_obj,
        'tugas_sudah_submit': tugas_sudah_submit,
        'jumlah_anggota': jumlah_anggota,
        'refleksi_map': refleksi_map,
    })


@login_required
def tambah_materi(request, ruang_id):
    ruang = get_object_or_404(RuangKerja, id=ruang_id)
    if request.user.role == 'siswa':
        messages.error(request, 'Hanya guru yang dapat menambah materi.')
        return redirect('ruang_kerja:detail', ruang_id=ruang.id)
    if request.method == 'POST':
        Materi.objects.create(
            ruang_kerja=ruang,
            judul=request.POST.get('judul'),
            deskripsi=request.POST.get('deskripsi', ''),
            file=request.FILES.get('file'),
            diunggah_oleh=request.user,
        )
        messages.success(request, 'Materi berhasil diunggah.')
    return redirect('ruang_kerja:detail', ruang_id=ruang.id)


@login_required
def tambah_pengumuman(request, ruang_id):
    ruang = get_object_or_404(RuangKerja, id=ruang_id)
    if request.user.role == 'siswa':
        messages.error(request, 'Hanya guru yang dapat membuat pengumuman.')
        return redirect('ruang_kerja:detail', ruang_id=ruang.id)
    if request.method == 'POST':
        Pengumuman.objects.create(
            ruang_kerja=ruang,
            isi=request.POST.get('isi'),
            diposting_oleh=request.user
        )
        messages.success(request, 'Pengumuman berhasil diposting.')
    return redirect('ruang_kerja:detail', ruang_id=ruang.id)


@login_required
def tambah_tugas(request, ruang_id):
    ruang = get_object_or_404(RuangKerja, id=ruang_id)
    if request.user.role == 'siswa':
        messages.error(request, 'Hanya guru yang dapat membuat tugas.')
        return redirect('ruang_kerja:detail', ruang_id=ruang.id)
    if request.method == 'POST':
        jenis = request.POST.get('jenis', 'esai')
        tugas = Tugas.objects.create(
            ruang_kerja=ruang,
            jenis=jenis,
            judul=request.POST.get('judul'),
            instruksi=request.POST.get('instruksi'),
            nilai_maksimal=int(request.POST.get('nilai_maksimal', 100)),
            deadline=request.POST.get('deadline') or None,
            lampiran=request.FILES.get('lampiran'),
            dibuat_oleh=request.user,
        )
        messages.success(request, 'Tugas berhasil dibuat.')
        if jenis == 'pilihan_ganda':
            return redirect('ruang_kerja:kelola_soal', tugas_id=tugas.id)
    return redirect('ruang_kerja:detail', ruang_id=ruang.id)


@login_required
def hapus_tugas(request, tugas_id):
    tugas = get_object_or_404(Tugas, id=tugas_id)
    ruang_id = tugas.ruang_kerja.id
    if not request.user.is_staff_role() and request.method == 'POST':
        tugas.delete()
        messages.success(request, 'Tugas berhasil dihapus.')
    return redirect('ruang_kerja:detail', ruang_id=ruang_id)


@login_required
def detail_tugas(request, tugas_id):
    tugas = get_object_or_404(Tugas, id=tugas_id)
    ruang = tugas.ruang_kerja

    if request.user.role == 'siswa':
        siswa_obj = get_siswa_obj(request.user)
        if not is_anggota(ruang, siswa_obj):
            messages.error(request, 'Anda tidak memiliki akses.')
            return redirect('ruang_kerja:daftar')
        submisi = tugas.get_submisi(siswa_obj)
        if tugas.jenis == 'kreasi':
            from kreasi.views import kerjakan_kreasi
            return kerjakan_kreasi(request, tugas, ruang, siswa_obj, submisi)

        if tugas.jenis == 'pilihan_ganda':
            soal_list = tugas.soal_pg.prefetch_related('opsi').all()
            jawaban_lama = {j.soal_id: j.opsi_dipilih_id for j in JawabanPG.objects.filter(siswa=siswa_obj, soal__tugas=tugas)}
            if request.method == 'POST':
                benar = 0
                total = soal_list.count()
                for soal in soal_list:
                    opsi_id = request.POST.get(f'soal_{soal.id}')
                    if opsi_id:
                        opsi = get_object_or_404(OpsiPG, id=opsi_id, soal=soal)
                        JawabanPG.objects.update_or_create(
                            soal=soal, siswa=siswa_obj,
                            defaults={'opsi_dipilih': opsi}
                        )
                        if opsi.is_benar:
                            benar += 1
                nilai_akhir = round((benar / total) * tugas.nilai_maksimal, 1) if total else 0
                SubmisiTugas.objects.update_or_create(
                    tugas=tugas, siswa=siswa_obj,
                    defaults={'nilai': nilai_akhir, 'teks_jawaban': f'Kuis: {benar}/{total} benar'}
                )
                messages.success(request, f'Kuis selesai! Skor: {nilai_akhir}/{tugas.nilai_maksimal}')
                return redirect('ruang_kerja:detail_tugas', tugas_id=tugas.id)
            return render(request, 'ruang_kerja/kerjakan_kuis.html', {
                'tugas': tugas, 'ruang': ruang, 'soal_list': soal_list,
                'jawaban_lama': jawaban_lama, 'submisi': submisi,
            })

        if request.method == 'POST' and not submisi:
            SubmisiTugas.objects.create(
                tugas=tugas,
                siswa=siswa_obj,
                teks_jawaban=request.POST.get('teks_jawaban', ''),
                file_jawaban=request.FILES.get('file_jawaban'),
            )
            messages.success(request, 'Tugas berhasil dikumpulkan!')
            return redirect('ruang_kerja:detail_tugas', tugas_id=tugas.id)
        return render(request, 'ruang_kerja/detail_tugas_siswa.html', {
            'tugas': tugas, 'ruang': ruang, 'submisi': submisi,
        })

    if tugas.jenis == 'kreasi':
        from kreasi.views import daftar_karya_guru
        return daftar_karya_guru(request, tugas, ruang)

    # Guru - lihat semua submisi
    submisi_list = tugas.submisi.select_related('siswa').all()
    return render(request, 'ruang_kerja/detail_tugas_guru.html', {
        'tugas': tugas, 'ruang': ruang, 'submisi_list': submisi_list,
    })


@login_required
def nilai_submisi(request, submisi_id):
    submisi = get_object_or_404(SubmisiTugas, id=submisi_id)
    if request.user.role == 'siswa':
        messages.error(request, 'Hanya guru yang dapat memberi nilai.')
        return redirect('ruang_kerja:daftar')
    if request.method == 'POST':
        submisi.nilai = request.POST.get('nilai')
        submisi.feedback = request.POST.get('feedback', '')
        submisi.dinilai_pada = timezone.now()
        submisi.save()
        messages.success(request, f'Nilai untuk {submisi.siswa.nama} berhasil disimpan.')
    return redirect('ruang_kerja:detail_tugas', tugas_id=submisi.tugas.id)


@login_required
def daftar_diskusi(request, ruang_id):
    from .models import PesanChat
    ruang = get_object_or_404(RuangKerja, id=ruang_id)
    if request.user.role == 'siswa':
        siswa_obj = get_siswa_obj(request.user)
        if not is_anggota(ruang, siswa_obj):
            messages.error(request, 'Anda tidak memiliki akses.')
            return redirect('ruang_kerja:daftar')
    if request.method == 'POST':
        isi = request.POST.get('isi', '').strip()
        if isi:
            PesanChat.objects.create(
                ruang_kerja=ruang,
                isi=isi,
                dikirim_oleh=request.user,
            )
        return redirect('ruang_kerja:daftar_diskusi', ruang_id=ruang.id)
    pesan_list = ruang.pesan_chat.select_related('dikirim_oleh').all()

    daftar_peserta_qs = AnggotaRuangKerja.objects.filter(ruang_kerja=ruang).select_related('siswa')
    daftar_peserta = [a.siswa.nama for a in daftar_peserta_qs]
    if ruang.guru:
        daftar_peserta.append(ruang.guru.get_full_name() or ruang.guru.username)

    return render(request, 'ruang_kerja/diskusi.html', {'ruang': ruang, 'pesan_list': pesan_list, 'daftar_peserta': daftar_peserta})


@login_required
def video_call(request, ruang_id):
    ruang = get_object_or_404(RuangKerja, id=ruang_id)
    if request.user.role == "siswa":
        siswa_obj = get_siswa_obj(request.user)
        if not is_anggota(ruang, siswa_obj):
            messages.error(request, "Anda tidak memiliki akses.")
            return redirect("ruang_kerja:daftar")
    nama_ruangan = f"SakalaLC-{ruang.mapel}-Kelas{ruang.kelas}-{ruang.id}".replace(" ", "")
    return render(request, "ruang_kerja/video_call.html", {"ruang": ruang, "nama_ruangan": nama_ruangan})


@login_required
def detail_diskusi(request, diskusi_id):
    return redirect('ruang_kerja:daftar')


@login_required
def hapus_materi(request, materi_id):
    materi = get_object_or_404(Materi, id=materi_id)
    ruang_id = materi.ruang_kerja.id
    if request.user.role == 'siswa':
        messages.error(request, 'Hanya guru yang dapat menghapus materi.')
        return redirect('ruang_kerja:detail', ruang_id=ruang_id)
    if request.method == 'POST':
        materi.delete()
        messages.success(request, 'Materi berhasil dihapus.')
    return redirect('ruang_kerja:detail', ruang_id=ruang_id)


@login_required
def duplikat_materi(request, materi_id):
    materi = get_object_or_404(Materi, id=materi_id)
    ruang_id = materi.ruang_kerja.id
    if request.user.role == 'siswa':
        messages.error(request, 'Hanya guru yang dapat menduplikat materi.')
        return redirect('ruang_kerja:detail', ruang_id=ruang_id)
    if request.method == 'POST':
        urutan_baru = materi.ruang_kerja.materi.count()
        Materi.objects.create(
            ruang_kerja=materi.ruang_kerja,
            judul=f"{materi.judul} (Salinan)",
            deskripsi=materi.deskripsi,
            link_url=materi.link_url,
            video_url=materi.video_url,
            urutan=urutan_baru,
            diunggah_oleh=request.user,
        )
        messages.success(request, 'Materi berhasil diduplikat.')
    return redirect('ruang_kerja:detail', ruang_id=ruang_id)


@login_required
def tambah_topik(request, ruang_id):
    ruang = get_object_or_404(RuangKerja, id=ruang_id)
    if request.user.role == 'siswa':
        return redirect('ruang_kerja:detail', ruang_id=ruang_id)
    if request.method == 'POST':
        judul = request.POST.get('judul', '').strip()
        if judul:
            urutan = ruang.materi.count()
            Materi.objects.create(
                ruang_kerja=ruang,
                judul=judul,
                deskripsi=request.POST.get('deskripsi', ''),
                urutan=urutan,
                diunggah_oleh=request.user,
            )
    return redirect('ruang_kerja:detail', ruang_id=ruang_id)


@login_required
def hapus_topik(request, materi_id):
    materi = get_object_or_404(Materi, id=materi_id)
    ruang_id = materi.ruang_kerja.id
    if not request.user.is_staff_role() and request.method == 'POST':
        materi.delete()
    return redirect('ruang_kerja:detail', ruang_id=ruang_id)


@login_required
def simpan_refleksi(request, materi_id):
    materi = get_object_or_404(Materi, id=materi_id)
    ruang = materi.ruang_kerja
    if not request.user.is_staff_role():
        messages.error(request, 'Hanya siswa yang dapat mengisi refleksi.')
        return redirect('ruang_kerja:detail', ruang_id=ruang.id)
    siswa_obj = get_siswa_obj(request.user)
    if not siswa_obj or not is_anggota(ruang, siswa_obj):
        messages.error(request, 'Anda tidak memiliki akses ke ruang kerja ini.')
        return redirect('ruang_kerja:daftar')
    if request.method == 'POST':
        isi = request.POST.get('isi_refleksi', '').strip()
        RefleksiTopik.objects.update_or_create(
            materi=materi, siswa=siswa_obj,
            defaults={'isi': isi}
        )
        messages.success(request, f'Refleksi untuk topik "{materi.judul}" berhasil disimpan.')
    return redirect('ruang_kerja:detail', ruang_id=ruang.id)


@login_required
def penilaian_topik(request, materi_id):
    materi = get_object_or_404(Materi, id=materi_id)
    ruang = materi.ruang_kerja
    if request.user.role == 'siswa':
        messages.error(request, 'Hanya guru yang dapat mengisi penilaian.')
        return redirect('ruang_kerja:detail', ruang_id=ruang.id)

    anggota_list = AnggotaRuangKerja.objects.filter(ruang_kerja=ruang).select_related('siswa').order_by('siswa__nama')

    formatif_map = {}
    sumatif_map = {}
    remedial_map = {}
    for p in PenilaianTopik.objects.filter(materi=materi).order_by('dibuat_pada'):
        if p.jenis == 'formatif':
            formatif_map.setdefault(p.siswa_id, []).append(p)
        elif p.jenis == 'sumatif':
            sumatif_map[p.siswa_id] = p
        elif p.jenis == 'remedial':
            remedial_map[p.siswa_id] = p

    refleksi_map = {
        r.siswa_id: r.isi
        for r in RefleksiTopik.objects.filter(materi=materi)
    }

    data = []
    for a in anggota_list:
        formatif_list = formatif_map.get(a.siswa_id, [])
        rata2_formatif = None
        nilai_formatif = [f.nilai for f in formatif_list if f.nilai is not None]
        if nilai_formatif:
            rata2_formatif = round(sum(nilai_formatif) / len(nilai_formatif), 1)
        data.append({
            'siswa': a.siswa,
            'formatif_list': formatif_list,
            'rata2_formatif': rata2_formatif,
            'sumatif': sumatif_map.get(a.siswa_id),
            'remedial': remedial_map.get(a.siswa_id),
            'refleksi': refleksi_map.get(a.siswa_id, ''),
        })

    return render(request, 'ruang_kerja/penilaian_topik.html', {
        'ruang': ruang,
        'materi': materi,
        'data': data,
    })


@login_required
def simpan_penilaian_topik(request, materi_id, siswa_id):
    """Simpan nilai Sumatif & Remedial (satu nilai per siswa per topik)."""
    materi = get_object_or_404(Materi, id=materi_id)
    ruang = materi.ruang_kerja
    siswa = get_object_or_404(Siswa, id=siswa_id)
    if request.user.role == 'siswa':
        messages.error(request, 'Hanya guru yang dapat mengisi penilaian.')
        return redirect('ruang_kerja:detail', ruang_id=ruang.id)
    if request.method == 'POST':
        for jenis in ['sumatif', 'remedial']:
            nilai = request.POST.get(f'nilai_{jenis}', '').strip()
            catatan = request.POST.get(f'catatan_{jenis}', '').strip()
            if nilai or catatan:
                existing = PenilaianTopik.objects.filter(materi=materi, siswa=siswa, jenis=jenis).first()
                if existing:
                    existing.nilai = nilai or None
                    existing.catatan = catatan
                    existing.dinilai_oleh = request.user
                    existing.save()
                else:
                    PenilaianTopik.objects.create(
                        materi=materi, siswa=siswa, jenis=jenis,
                        nilai=nilai or None, catatan=catatan, dinilai_oleh=request.user,
                    )
        messages.success(request, f'Penilaian {siswa.nama} untuk topik "{materi.judul}" disimpan.')
    return redirect('ruang_kerja:penilaian_topik', materi_id=materi.id)


@login_required
def tambah_formatif(request, materi_id, siswa_id):
    """Tambah satu entri baru nilai Formatif (boleh berkali-kali)."""
    materi = get_object_or_404(Materi, id=materi_id)
    ruang = materi.ruang_kerja
    siswa = get_object_or_404(Siswa, id=siswa_id)
    if request.user.role == 'siswa':
        messages.error(request, 'Hanya guru yang dapat mengisi penilaian.')
        return redirect('ruang_kerja:detail', ruang_id=ruang.id)
    if request.method == 'POST':
        nilai = request.POST.get('nilai_formatif', '').strip()
        catatan = request.POST.get('catatan_formatif', '').strip()
        if nilai or catatan:
            PenilaianTopik.objects.create(
                materi=materi, siswa=siswa, jenis='formatif',
                nilai=nilai or None, catatan=catatan, dinilai_oleh=request.user,
            )
            messages.success(request, f'Nilai formatif baru untuk {siswa.nama} ditambahkan.')
        else:
            messages.info(request, 'Isi nilai atau catatan dulu sebelum menambahkan.')
    return redirect('ruang_kerja:penilaian_topik', materi_id=materi.id)


@login_required
def hapus_formatif(request, penilaian_id):
    p = get_object_or_404(PenilaianTopik, id=penilaian_id, jenis='formatif')
    materi_id = p.materi_id
    if not request.user.is_staff_role() and request.method == 'POST':
        p.delete()
        messages.success(request, 'Nilai formatif dihapus.')
    return redirect('ruang_kerja:penilaian_topik', materi_id=materi_id)


@login_required
def tambah_item(request, materi_id):
    from .models import SubMateri
    materi = get_object_or_404(Materi, id=materi_id)
    ruang = materi.ruang_kerja
    if request.user.role == 'siswa':
        return redirect('ruang_kerja:detail', ruang_id=ruang.id)
    if request.method == 'POST':
        urutan = materi.sub_materi.count()
        SubMateri.objects.create(
            materi=materi,
            judul=request.POST.get('judul', ''),
            deskripsi=request.POST.get('deskripsi', ''),
            file=request.FILES.get('file'),
            link_url=request.POST.get('link_url') or None,
            video_url=request.POST.get('video_url') or None,
            urutan=urutan,
        )
        messages.success(request, 'Item berhasil ditambahkan.')
        return redirect('ruang_kerja:detail', ruang_id=ruang.id)
    return render(request, 'ruang_kerja/tambah_item.html', {
        'materi': materi,
        'ruang': ruang,
    })


@login_required
def edit_item(request, item_id):
    from .models import SubMateri
    item = get_object_or_404(SubMateri, id=item_id)
    materi = item.materi
    ruang = materi.ruang_kerja
    if request.user.role == 'siswa':
        return redirect('ruang_kerja:detail', ruang_id=ruang.id)
    if request.method == 'POST':
        item.judul = request.POST.get('judul', '')
        item.deskripsi = request.POST.get('deskripsi', '')
        if request.FILES.get('file'):
            item.file = request.FILES.get('file')
        item.link_url = request.POST.get('link_url') or None
        item.video_url = request.POST.get('video_url') or None
        item.save()
        messages.success(request, 'Item berhasil diperbarui.')
        return redirect('ruang_kerja:detail', ruang_id=ruang.id)
    return render(request, 'ruang_kerja/tambah_item.html', {
        'materi': materi,
        'ruang': ruang,
        'item': item,
    })


@login_required
def hapus_item(request, item_id):
    from .models import SubMateri
    item = get_object_or_404(SubMateri, id=item_id)
    ruang_id = item.materi.ruang_kerja.id
    if not request.user.is_staff_role() and request.method == 'POST':
        item.delete()
    return redirect('ruang_kerja:detail', ruang_id=ruang_id)


# ============================================================
# ANGGOTA RUANG KERJA (gaya Teams: guru pilih siswa terdaftar)
# ============================================================

@login_required
def kelola_anggota(request, ruang_id):
    ruang = get_object_or_404(RuangKerja, id=ruang_id)
    if request.user.role == 'siswa':
        messages.error(request, 'Hanya guru yang dapat mengelola anggota.')
        return redirect('ruang_kerja:detail', ruang_id=ruang.id)

    q = request.GET.get('q', '').strip()
    kelas_filter = request.GET.get('kelas', ruang.kelas)

    anggota_list = AnggotaRuangKerja.objects.filter(ruang_kerja=ruang).select_related('siswa').order_by('siswa__nama')
    anggota_ids = anggota_list.values_list('siswa_id', flat=True)

    calon_siswa = Siswa.objects.filter(aktif=True).exclude(id__in=anggota_ids)
    if kelas_filter:
        calon_siswa = calon_siswa.filter(kelas=kelas_filter)
    if q:
        calon_siswa = calon_siswa.filter(nama__icontains=q)
    calon_siswa = calon_siswa.order_by('nama')

    kelas_list = Siswa.objects.values_list('kelas', flat=True).distinct().order_by('kelas')

    return render(request, 'ruang_kerja/anggota.html', {
        'ruang': ruang,
        'anggota_list': anggota_list,
        'calon_siswa': calon_siswa,
        'kelas_list': kelas_list,
        'kelas_filter': kelas_filter,
        'q': q,
    })


@login_required
def tambah_anggota(request, ruang_id):
    ruang = get_object_or_404(RuangKerja, id=ruang_id)
    if request.user.role == 'siswa':
        messages.error(request, 'Hanya guru yang dapat menambah anggota.')
        return redirect('ruang_kerja:detail', ruang_id=ruang.id)
    if request.method == 'POST':
        siswa_ids = request.POST.getlist('siswa_ids')
        ditambah = 0
        for sid in siswa_ids:
            siswa = Siswa.objects.filter(id=sid).first()
            if siswa:
                _, created = AnggotaRuangKerja.objects.get_or_create(
                    ruang_kerja=ruang, siswa=siswa,
                    defaults={'ditambahkan_oleh': request.user}
                )
                if created:
                    ditambah += 1
        if ditambah:
            messages.success(request, f'{ditambah} siswa berhasil ditambahkan ke ruang kerja.')
        else:
            messages.info(request, 'Tidak ada siswa baru yang dipilih.')
    return redirect('ruang_kerja:kelola_anggota', ruang_id=ruang.id)


@login_required
def hapus_anggota(request, anggota_id):
    anggota = get_object_or_404(AnggotaRuangKerja, id=anggota_id)
    ruang_id = anggota.ruang_kerja.id
    if not request.user.is_staff_role() and request.method == 'POST':
        nama = anggota.siswa.nama
        anggota.delete()
        messages.success(request, f'{nama} dikeluarkan dari ruang kerja.')
    return redirect('ruang_kerja:kelola_anggota', ruang_id=ruang_id)


# ============================================================
# KELOLA MATA PELAJARAN (guru menentukan daftar mapel sendiri)
# ============================================================

@login_required
def kelola_mapel(request):
    if request.user.role == 'siswa':
        messages.error(request, 'Hanya guru yang dapat mengelola mata pelajaran.')
        return redirect('ruang_kerja:daftar')
    mapel_list = MataPelajaran.objects.all()
    return render(request, 'ruang_kerja/kelola_mapel.html', {'mapel_list': mapel_list})


@login_required
def tambah_mapel(request):
    if request.user.role == 'siswa':
        messages.error(request, 'Hanya guru yang dapat menambah mata pelajaran.')
        return redirect('ruang_kerja:daftar')
    if request.method == 'POST':
        nama = request.POST.get('nama', '').strip()
        if nama:
            _, created = MataPelajaran.objects.get_or_create(
                nama=nama, defaults={'dibuat_oleh': request.user}
            )
            if created:
                messages.success(request, f'Mata pelajaran "{nama}" berhasil ditambahkan.')
            else:
                messages.info(request, f'Mata pelajaran "{nama}" sudah ada.')
    return redirect('ruang_kerja:kelola_mapel')


@login_required
def hapus_mapel(request, mapel_id):
    mapel = get_object_or_404(MataPelajaran, id=mapel_id)
    if not request.user.is_staff_role() and request.method == 'POST':
        if RuangKerja.objects.filter(mapel=mapel.nama).exists():
            messages.error(request, f'"{mapel.nama}" tidak bisa dihapus karena masih dipakai di ruang kerja yang ada.')
        else:
            mapel.delete()
            messages.success(request, f'Mata pelajaran "{mapel.nama}" dihapus.')
    return redirect('ruang_kerja:kelola_mapel')


# ============================================================
# RAPOR DIGITAL (nilai otomatis dari rata-rata tugas + narasi guru)
# ============================================================

def hitung_rata_rata_nilai(ruang, siswa):
    avg = SubmisiTugas.objects.filter(
        tugas__ruang_kerja=ruang, siswa=siswa, nilai__isnull=False
    ).aggregate(a=Avg('nilai'))['a']
    return round(avg, 1) if avg is not None else None


def generate_draft_komentar(ruang, siswa, rata2):
    nama_depan = siswa.nama.split()[0] if siswa.nama else siswa.nama
    mastery_values = []
    jumlah_mastered = 0
    total_topik = 0
    for topik in ruang.materi.all():
        m = topik.hitung_mastery(siswa)
        if m is not None:
            mastery_values.append(m)
            total_topik += 1
            if topik.is_mastered(siswa):
                jumlah_mastered += 1
    rata2_mastery = round(sum(mastery_values) / len(mastery_values), 1) if mastery_values else None

    if total_topik == 0:
        return f'Penilaian topik untuk {nama_depan} belum tersedia pada periode ini.'

    jumlah_belum = total_topik - jumlah_mastered

    if jumlah_mastered > 0:
        kalimat = f'{nama_depan} mampu menuntaskan {jumlah_mastered} dari {total_topik} topik pembelajaran yang diberikan.'
    else:
        kalimat = f'{nama_depan} telah mengikuti proses pembelajaran pada {total_topik} topik yang diberikan.'

    if rata2:
        kalimat += f' Hal ini didukung dengan rata-rata nilai tugas pada angka {rata2}.'

    if jumlah_belum > 0:
        kalimat += f' Di samping itu, {nama_depan} perlu meningkatkan pemahaman pada {jumlah_belum} topik yang belum dikuasai secara tuntas.'

    if jumlah_belum == 0:
        kalimat += f' Harapannya, {nama_depan} terus mempertahankan semangat belajar dan siap menghadapi topik pembelajaran berikutnya.'
    else:
        kalimat += f' Harapannya, {nama_depan} terus berkomitmen memperkuat pemahaman melalui latihan dan pendampingan yang konsisten.'

    return kalimat

@login_required
def rapor_ruang_kerja(request, ruang_id):
    ruang = get_object_or_404(RuangKerja, id=ruang_id)
    if request.user.role == 'siswa':
        messages.error(request, 'Hanya guru yang dapat melihat halaman rapor kelas.')
        return redirect('ruang_kerja:detail', ruang_id=ruang.id)

    anggota_list = AnggotaRuangKerja.objects.filter(ruang_kerja=ruang).select_related('siswa').order_by('siswa__nama')
    catatan_map = {
        c.siswa_id: c
        for c in CatatanRapor.objects.filter(ruang_kerja=ruang)
    }

    data = []
    for a in anggota_list:
        rata2 = hitung_rata_rata_nilai(ruang, a.siswa)
        catatan_obj = catatan_map.get(a.siswa_id)
        catatan_ada = catatan_obj.catatan if catatan_obj else ''
        data.append({
            'siswa': a.siswa,
            'rata2': rata2,
            'catatan': catatan_ada,
            'catatan_disiplin': catatan_obj.catatan_disiplin if catatan_obj else '',
            'catatan_fisik_motorik': catatan_obj.catatan_fisik_motorik if catatan_obj else '',
            'draft_komentar': catatan_ada or generate_draft_komentar(ruang, a.siswa, rata2),
        })

    return render(request, 'ruang_kerja/rapor_ruang_kerja.html', {
        'ruang': ruang,
        'data': data,
    })


@login_required
def simpan_catatan_rapor(request, ruang_id, siswa_id):
    ruang = get_object_or_404(RuangKerja, id=ruang_id)
    siswa = get_object_or_404(Siswa, id=siswa_id)
    if request.user.role == 'siswa':
        messages.error(request, 'Hanya guru yang dapat mengisi catatan rapor.')
        return redirect('ruang_kerja:detail', ruang_id=ruang.id)
    if request.method == 'POST':
        catatan_text = request.POST.get('catatan', '').strip()
        catatan_disiplin_text = request.POST.get('catatan_disiplin', '').strip()
        catatan_fisik_text = request.POST.get('catatan_fisik_motorik', '').strip()
        CatatanRapor.objects.update_or_create(
            ruang_kerja=ruang, siswa=siswa,
            defaults={
                'catatan': catatan_text,
                'catatan_disiplin': catatan_disiplin_text,
                'catatan_fisik_motorik': catatan_fisik_text,
                'diperbarui_oleh': request.user,
            }
        )
        messages.success(request, f'Catatan rapor {siswa.nama} disimpan.')
    return redirect('ruang_kerja:rapor_ruang_kerja', ruang_id=ruang.id)


@login_required
def rapor_siswa(request, ruang_id, siswa_id):
    ruang = get_object_or_404(RuangKerja, id=ruang_id)
    siswa = get_object_or_404(Siswa, id=siswa_id)

    if request.user.role == 'siswa':
        siswa_obj = get_siswa_obj(request.user)
        if not siswa_obj or siswa_obj.id != siswa.id or not is_anggota(ruang, siswa_obj):
            messages.error(request, 'Anda tidak memiliki akses ke rapor ini.')
            return redirect('ruang_kerja:daftar')

    tugas_nilai = SubmisiTugas.objects.filter(
        tugas__ruang_kerja=ruang, siswa=siswa
    ).select_related('tugas').order_by('tugas__dibuat_pada')

    catatan_obj = CatatanRapor.objects.filter(ruang_kerja=ruang, siswa=siswa).first()

    penilaian_topik_list = []
    for topik in ruang.materi.all():
        penilaian_qs = PenilaianTopik.objects.filter(materi=topik, siswa=siswa).order_by('dibuat_pada')
        formatif_list = [p for p in penilaian_qs if p.jenis == 'formatif']
        sumatif = next((p for p in penilaian_qs if p.jenis == 'sumatif'), None)
        remedial = next((p for p in penilaian_qs if p.jenis == 'remedial'), None)
        nilai_formatif = [f.nilai for f in formatif_list if f.nilai is not None]
        rata2_formatif = round(sum(nilai_formatif) / len(nilai_formatif), 1) if nilai_formatif else None
        mastery = topik.hitung_mastery(siswa)
        is_mastered = topik.is_mastered(siswa)

        if formatif_list or sumatif or remedial:
            penilaian_topik_list.append({
                'topik': topik,
                'formatif_list': formatif_list,
                'rata2_formatif': rata2_formatif,
                'sumatif': sumatif,
                'remedial': remedial,
                'mastery': mastery,
                'is_mastered': is_mastered,
            })

    mastery_values = [item['mastery'] for item in penilaian_topik_list if item['mastery'] is not None]
    rata2_mastery = round(sum(mastery_values) / len(mastery_values), 1) if mastery_values else None
    jumlah_topik_mastered = sum(1 for item in penilaian_topik_list if item['is_mastered'])

    return render(request, 'ruang_kerja/rapor_siswa.html', {
        'ruang': ruang,
        'siswa': siswa,
        'tugas_nilai': tugas_nilai,
        'rata2': hitung_rata_rata_nilai(ruang, siswa),
        'catatan': catatan_obj.catatan if catatan_obj else '',
        'catatan_disiplin': catatan_obj.catatan_disiplin if catatan_obj else '',
        'catatan_fisik_motorik': catatan_obj.catatan_fisik_motorik if catatan_obj else '',
        'penilaian_topik_list': penilaian_topik_list,
        'rata2_mastery': rata2_mastery,
        'jumlah_topik_mastered': jumlah_topik_mastered,
        'total_topik_dinilai': len(penilaian_topik_list),
    })


@login_required
def kelola_soal(request, tugas_id):
    tugas = get_object_or_404(Tugas, id=tugas_id)
    if request.user.role == 'siswa':
        return redirect('ruang_kerja:detail', ruang_id=tugas.ruang_kerja.id)
    soal_list = tugas.soal_pg.prefetch_related('opsi').all()
    return render(request, 'ruang_kerja/kelola_soal.html', {
        'tugas': tugas, 'soal_list': soal_list,
    })


@login_required
def tambah_soal(request, tugas_id):
    tugas = get_object_or_404(Tugas, id=tugas_id)
    if request.user.role == 'siswa':
        return redirect('ruang_kerja:detail', ruang_id=tugas.ruang_kerja.id)
    if request.method == 'POST':
        urutan = tugas.soal_pg.count()
        soal = SoalPG.objects.create(
            tugas=tugas,
            pertanyaan=request.POST.get('pertanyaan'),
            urutan=urutan,
        )
        opsi_teks = request.POST.getlist('opsi_teks')
        jawaban_benar = request.POST.get('jawaban_benar')
        for i, teks in enumerate(opsi_teks):
            if teks.strip():
                OpsiPG.objects.create(
                    soal=soal,
                    teks=teks,
                    is_benar=(str(i) == jawaban_benar),
                )
        messages.success(request, 'Soal berhasil ditambahkan.')
    return redirect('ruang_kerja:kelola_soal', tugas_id=tugas.id)


@login_required
def hapus_soal(request, soal_id):
    soal = get_object_or_404(SoalPG, id=soal_id)
    tugas_id = soal.tugas.id
    if not request.user.is_staff_role() and request.method == 'POST':
        soal.delete()
        messages.success(request, 'Soal berhasil dihapus.')
    return redirect('ruang_kerja:kelola_soal', tugas_id=tugas_id)
