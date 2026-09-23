# -*- coding: utf-8 -*-
"""
PASANG PERPUSTAKAAN v2  (Classio / Sakala Learning Centre)

Cara pakai (dari folder proyek, yang berisi manage.py):
    python pasang_perpustakaan_v2.py
    python manage.py makemigrations perpustakaan
    python manage.py migrate
    python manage.py check

Yang dipasang:
  1. Pembaca interaktif: flipbook (pdf.js + StPageFlip), audio sinkron halaman,
     Mode Teks (reflow), Sepia/Gelap, Panel Insight (cari + kata kunci + glosarium),
     ulasan suara satu klik.
  2. Progres baca per siswa + lanjut dari halaman terakhir + lencana otomatis
     saat buku selesai dibaca.
  3. Glosarium buatan guru per buku.
  4. Filter Baca/Dengar/Tonton + usia + pencarian/topik di halaman zona.
  5. Kartu "Bacaan Perpustakaan" di Dashboard Siswa dan Dashboard Orang Tua.

Aman dijalankan berulang: bagian yang sudah ada dicetak SUDAH. Semua file yang
diubah dicadangkan dulu ke folder _cadangan_perpustakaan_v2/.
"""
import ast
import datetime
import os
import re
import shutil
import sys

CAD = os.path.join('_cadangan_perpustakaan_v2', datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
_sudah_cadangan = set()
HASIL = {'OK': 0, 'SUDAH': 0, 'SKIP': 0}


def lapor(status, label):
    HASIL[status] = HASIL.get(status, 0) + 1
    print('%-6s %s' % (status, label))


def read(p):
    with open(p, encoding='utf-8-sig') as f:
        return f.read().replace('\r\n', '\n')


def cadangkan(p):
    if p in _sudah_cadangan or not os.path.exists(p):
        return
    tujuan = os.path.join(CAD, p)
    os.makedirs(os.path.dirname(tujuan), exist_ok=True)
    shutil.copy2(p, tujuan)
    _sudah_cadangan.add(p)


def write(p, s):
    cadangkan(p)
    d = os.path.dirname(p)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        f.write(s)


# ---------------------------------------------------------------------------
# KODE YANG DISISIPKAN
# ---------------------------------------------------------------------------

MODEL_FIELD_BARU = (
    "usia_min = models.PositiveSmallIntegerField(default=0, help_text='Usia minimal (0 = semua umur)')\n"
    "usia_maks = models.PositiveSmallIntegerField(default=0, help_text='Usia maksimal (0 = tanpa batas)')\n"
    "topik = models.CharField(max_length=200, blank=True, default='', help_text='Kata kunci minat, pisahkan dengan koma')\n"
)

MODEL_PROGRES = '''class ProgresBaca(models.Model):
    siswa = models.ForeignKey('accounts.Siswa', on_delete=models.CASCADE, related_name='progres_baca')
    sumber = models.ForeignKey(SumberDigital, on_delete=models.CASCADE, related_name='progres_list')
    halaman_terakhir = models.PositiveIntegerField(default=1)
    total_halaman = models.PositiveIntegerField(default=0)
    selesai = models.BooleanField(default=False)
    diperbarui_pada = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('siswa', 'sumber')
        ordering = ['-diperbarui_pada']

    def __str__(self):
        return self.siswa.nama + ' - ' + self.sumber.judul
'''

MODEL_GLOSARIUM = '''class Glosarium(models.Model):
    sumber = models.ForeignKey(SumberDigital, on_delete=models.CASCADE, related_name='glosarium_list')
    istilah = models.CharField(max_length=100)
    arti = models.TextField()

    class Meta:
        unique_together = ('sumber', 'istilah')
        ordering = ['istilah']

    def __str__(self):
        return self.istilah
'''

VIEW_DETAIL_ZONA = '''@login_required
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
'''

VIEW_BARU = '''# ======================================================================
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
'''

URL_BARU = [
    ('baca_sumber', "path('sumber/<int:sumber_id>/baca/', views.baca_sumber, name='baca_sumber'),"),
    ('simpan_progres', "path('sumber/<int:sumber_id>/progres/', views.simpan_progres, name='simpan_progres'),"),
    ('glosarium', "path('sumber/<int:sumber_id>/glosarium/', views.glosarium_sumber, name='glosarium'),"),
    ('hapus_glosarium', "path('glosarium/<int:glos_id>/hapus/', views.hapus_glosarium, name='hapus_glosarium'),"),
]

# ---------------------------------------------------------------------------
# TEMPLATE
# ---------------------------------------------------------------------------

TPL_BACA = r"""{% extends 'base.html' %}
{% block title %}Baca: {{ sumber.judul }}{% endblock %}
{% block page_title %}{{ sumber.judul }}{% endblock %}
{% block content %}
<style>
  #rd { --bg:#ffffff; --fg:#1f2937; --line:#e5e7eb; --btn:#f3f4f6; background:var(--bg); color:var(--fg); border:1px solid var(--line); border-radius:16px; padding:14px; }
  #rd.th-sepia { --bg:#F4ECD8; --fg:#5B4636; --line:#E0D3B5; --btn:#EADFC4; }
  #rd.th-gelap { --bg:#111827; --fg:#E5E7EB; --line:#374151; --btn:#1F2937; }
  #rd.th-sepia #book canvas { filter:sepia(.45); }
  #rd.th-gelap #book canvas { filter:invert(.9) hue-rotate(180deg); }
  .rd-bar { display:flex; gap:6px; flex-wrap:wrap; align-items:center; margin-bottom:12px; }
  .rb { border:1px solid var(--line); background:var(--btn); color:var(--fg); border-radius:8px; padding:7px 12px; font-size:12.5px; font-weight:600; cursor:pointer; }
  .rb.utama { background:#0B3D26; color:#fff; border-color:#0B3D26; }
  .rd-bar select, #rd input[type=text] { border:1px solid var(--line); background:var(--btn); color:var(--fg); border-radius:8px; padding:6px 8px; font-size:12.5px; }
  .rd-main { display:flex; gap:16px; flex-wrap:wrap; align-items:flex-start; }
  .rd-col { flex:1 1 320px; min-width:0; }
  #bookwrap { display:flex; justify-content:center; padding:6px 0; }
  #book { margin:0 auto; }
  .pg { background:#fff; overflow:hidden; }
  .pg canvas { width:100%; height:100%; display:block; }
  #txtview { display:none; max-width:680px; margin:0 auto; font-size:18px; line-height:1.9; min-height:280px; padding:6px 4px; }
  #txtview h4 { font-size:12px; opacity:.65; margin:0 0 10px; text-transform:uppercase; letter-spacing:.06em; }
  .kal { cursor:pointer; border-radius:4px; }
  .kal.on { background:#FDE68A; color:#111827; }
  .rd-nav { display:flex; justify-content:center; align-items:center; gap:14px; margin-top:12px; }
  #rd-status, #rd-astat { font-size:12.5px; opacity:.8; margin:0 0 8px; }
  #rd-selesai { display:none; margin-top:14px; padding:12px 14px; border-radius:12px; background:#FBF3E3; color:#92702E; border:1px dashed #D9B860; font-size:13px; }
  #rd-panel { flex:0 0 270px; max-width:100%; border:1px solid var(--line); border-radius:12px; padding:12px; }
  #rd-panel h4 { font-size:12px; font-weight:700; margin:0 0 6px; text-transform:uppercase; letter-spacing:.05em; opacity:.75; }
  .rd-hasil-item { display:block; width:100%; text-align:left; border:none; background:var(--btn); color:var(--fg); border-radius:8px; padding:6px 8px; margin-top:5px; font-size:12px; cursor:pointer; }
  .rd-chip { display:inline-block; border:1px solid var(--line); background:var(--btn); color:var(--fg); border-radius:99px; padding:3px 10px; margin:0 4px 4px 0; font-size:12px; cursor:pointer; }
  .rd-glos-item { padding:6px 0; border-bottom:1px solid var(--line); font-size:12.5px; line-height:1.5; }
</style>

<div class="mb-3"><a href="{% url 'perpustakaan:detail_sumber' sumber.id %}" class="text-sm text-[#0B3D26] hover:underline">&larr; Kembali ke koleksi</a></div>

<input type="hidden" id="rd-csrf" value="{{ csrf_token }}">

<div id="rd" class="th-terang"
     data-pdf="{{ sumber.file.url }}"
     data-progres-url="{% url 'perpustakaan:simpan_progres' sumber.id %}"
     data-sumber-url="{% url 'perpustakaan:detail_sumber' sumber.id %}"
     data-simpan="{% if bisa_simpan %}1{% else %}0{% endif %}"
     data-mulai="{{ halaman_mulai }}">
  <div class="rd-bar">
    <button type="button" class="rb" id="b-mode">Mode Teks</button>
    <button type="button" class="rb utama" id="b-audio">&#127911; Dengarkan</button>
    <select id="s-rate" title="Kecepatan suara">
      <option value="0.75">Pelan</option>
      <option value="0.9" selected>Sedang</option>
      <option value="1.1">Cepat</option>
    </select>
    <button type="button" class="rb" id="b-kecil">A-</button>
    <button type="button" class="rb" id="b-besar">A+</button>
    <select id="s-tema" title="Tema">
      <option value="terang">Terang</option>
      <option value="sepia">Sepia</option>
      <option value="gelap">Gelap</option>
    </select>
    <button type="button" class="rb" id="b-panel">Insight</button>
    <button type="button" class="rb" id="b-full">Layar penuh</button>
  </div>

  <div class="rd-main">
    <div class="rd-col">
      <p id="rd-status">Memuat buku...</p>
      <p id="rd-astat"></p>
      <div id="bookwrap"><div id="book"></div></div>
      <div id="txtview"></div>
      <div class="rd-nav">
        <button type="button" class="rb" id="b-prev">&larr; Sebelumnya</button>
        <span id="rd-hal" style="font-size:13px; font-weight:600;"></span>
        <button type="button" class="rb" id="b-next">Berikutnya &rarr;</button>
      </div>
      <div id="rd-selesai">
        &#127881; Kamu sampai di halaman terakhir! Sekarang ceritakan bagian favoritmu.
        <a href="{% url 'perpustakaan:detail_sumber' sumber.id %}" style="font-weight:700; color:#92702E;">Kirim refleksi &rarr;</a>
      </div>

      {% if bisa_simpan %}
      <div id="vr-bar" style="margin-top:16px; border-top:1px dashed var(--line); padding-top:12px;">
        <strong style="font-size:13px;">&#127908; Ulasan suara</strong>
        <p style="font-size:12px; opacity:.75; margin:4px 0 8px;">Ceritakan bagian favoritmu dengan suaramu sendiri.</p>
        <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center;">
          <button type="button" class="rb utama" id="vr-rekam">&#127908; Rekam</button>
          <button type="button" class="rb" id="vr-stop" style="display:none;">&#9209; Berhenti</button>
          <button type="button" class="rb" id="vr-kirim" style="display:none;">Kirim ulasan</button>
          <label style="font-size:12px;"><input type="checkbox" id="vr-porto"> Simpan juga ke Portofolio</label>
        </div>
        <audio id="vr-preview" controls style="display:none; width:100%; margin-top:8px;"></audio>
        <p id="vr-status" style="font-size:12px; opacity:.8; margin:6px 0 0;"></p>
      </div>
      {% endif %}
    </div>

    <aside id="rd-panel">
      <h4>Cari di buku</h4>
      <input type="text" id="rd-cari" placeholder="Ketik kata..." style="width:100%; box-sizing:border-box;">
      <div id="rd-hasil"></div>
      <h4 style="margin-top:14px;">Kata kunci</h4>
      <div id="rd-kata" style="font-size:12px; opacity:.7;">Menyiapkan...</div>
      <h4 style="margin-top:14px;">Glosarium</h4>
      <div id="rd-glos-ini"></div>
      <details id="rd-glos-semua" style="margin-top:6px; font-size:12.5px;">
        <summary style="cursor:pointer; opacity:.8;">Semua istilah</summary>
        <div id="rd-glos-list"></div>
      </details>
      <p id="rd-idx" style="font-size:11px; opacity:.6; margin:10px 0 0;"></p>
    </aside>
  </div>
</div>

{{ glosarium|json_script:"glos-data" }}

{% verbatim %}
<script>
(function () {
  var root = document.getElementById('rd');
  var PDF_URL = root.getAttribute('data-pdf');
  var URL_PROGRES = root.getAttribute('data-progres-url');
  var URL_SUMBER = root.getAttribute('data-sumber-url');
  var SIMPAN = root.getAttribute('data-simpan') === '1';
  var MULAI = parseInt(root.getAttribute('data-mulai') || '0', 10) || 0;
  var CSRF = document.getElementById('rd-csrf').value;
  var CDN_PDF = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
  var CDN_WORKER = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
  var CDN_FLIP = 'https://cdn.jsdelivr.net/npm/page-flip@2.0.7/dist/js/page-flip.browser.js';
  var $ = function (id) { return document.getElementById(id); };

  var GLOS = [];
  try { GLOS = JSON.parse($('glos-data').textContent) || []; } catch (e) { GLOS = []; }

  var pdf = null, pf = null, n = 0, cur = -1, mode = 'buku', fs = 18, siap = false;
  var texts = [], teksJanji = [], diGambar = [], canvases = [];
  var audioOn = false, token = 0, kal = [], si = 0, halAudio = -1;
  var dilihat = {}, dilihatN = 0, tSimpan = null;

  function muatSkrip(src) {
    return new Promise(function (res, rej) {
      var s = document.createElement('script');
      s.src = src; s.onload = res;
      s.onerror = function () { rej(new Error('Gagal memuat ' + src)); };
      document.head.appendChild(s);
    });
  }

  function pecah(teks) {
    var t = (teks || '').replace(/\s+/g, ' ').trim();
    if (!t) return [];
    var m = t.match(/[^.!?\u2026]+[.!?\u2026]*\s*/g) || [t];
    var out = [];
    m.forEach(function (k) {
      while (k.length > 200) {
        var c = k.lastIndexOf(',', 200);
        if (c < 60) c = k.lastIndexOf(' ', 200);
        if (c < 1) c = 200;
        out.push(k.slice(0, c + 1));
        k = k.slice(c + 1);
      }
      if (k.trim()) out.push(k);
    });
    return out;
  }

  function dapatTeks(i) {
    if (teksJanji[i]) return teksJanji[i];
    teksJanji[i] = pdf.getPage(i + 1)
      .then(function (pg) { return pg.getTextContent(); })
      .then(function (tc) {
        var t = tc.items.map(function (it) { return it.str; }).join(' ').replace(/\s+/g, ' ').trim();
        texts[i] = t;
        return t;
      })
      .catch(function () { texts[i] = ''; return ''; });
    return teksJanji[i];
  }

  function gambar(i) {
    if (i < 0 || i >= n || diGambar[i]) return;
    diGambar[i] = true;
    pdf.getPage(i + 1).then(function (page) {
      var v0 = page.getViewport({ scale: 1 });
      var sc = Math.min(2, 900 / v0.width);
      var vp = page.getViewport({ scale: sc });
      var cv = canvases[i];
      cv.width = vp.width;
      cv.height = vp.height;
      return page.render({ canvasContext: cv.getContext('2d'), viewport: vp }).promise;
    }).catch(function () { diGambar[i] = false; });
  }
  function renderAround(p) {
    for (var i = Math.max(0, p - 1); i <= Math.min(n - 1, p + 4); i++) gambar(i);
  }

  // ---------- progres baca ----------
  function catat(p) {
    if (!dilihat[p]) { dilihat[p] = 1; dilihatN++; }
  }
  function bodyProgres() {
    var b = new URLSearchParams();
    b.set('csrfmiddlewaretoken', CSRF);
    b.set('halaman', String(cur + 1));
    b.set('total', String(n));
    b.set('dilihat', String(dilihatN));
    return b;
  }
  function jadwalSimpan() {
    if (!SIMPAN) return;
    clearTimeout(tSimpan);
    tSimpan = setTimeout(kirimProgres, 1200);
  }
  function kirimProgres() {
    if (!SIMPAN || !n || cur < 0) return;
    fetch(URL_PROGRES, {
      method: 'POST', body: bodyProgres(), credentials: 'same-origin',
      headers: { 'X-CSRFToken': CSRF }
    })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) { if (d && d.selesai && d.baru) tampilSelesai(d); })
      .catch(function () {});
  }
  function tampilSelesai(d) {
    var el = $('rd-selesai');
    el.textContent = '';
    var pesan = '\uD83C\uDF89 Selamat! Kamu menyelesaikan buku ini.';
    if (d.lencana_baru && d.lencana_nama) {
      pesan += ' Lencana baru: ' + (d.lencana_ikon || '') + ' ' + d.lencana_nama + '.';
    }
    el.appendChild(document.createTextNode(pesan + ' '));
    var a = document.createElement('a');
    a.href = URL_SUMBER;
    a.style.fontWeight = '700';
    a.style.color = '#92702E';
    a.textContent = 'Kirim refleksi \u2192';
    el.appendChild(a);
    el.style.display = 'block';
  }

  // ---------- halaman aktif ----------
  function setCur(p) {
    var ganti = (p !== cur);
    cur = p;
    catat(p);
    $('rd-hal').textContent = 'Halaman ' + (p + 1) + ' / ' + n;
    $('rd-selesai').style.display = (p === n - 1) ? 'block' : 'none';
    renderAround(p);
    if (ganti) { perbaruiTeks(); jadwalSimpan(); }
  }
  function pergi(p, animasi) {
    if (p < 0 || p >= n || p === cur) return;
    if (pf) {
      if (animasi && mode === 'buku') { pf.flip(p); }
      else { pf.turnToPage(p); }
    }
    setCur(p);
  }

  function perbaruiTeks() {
    var p = cur;
    return dapatTeks(p).then(function (t) {
      if (p !== cur) return;
      var box = $('txtview');
      box.textContent = '';
      var h = document.createElement('h4');
      h.textContent = 'Halaman ' + (p + 1) + ' dari ' + n;
      box.appendChild(h);
      var ks = pecah(t);
      if (!ks.length) {
        var m = document.createElement('p');
        m.textContent = 'Halaman ini tidak berisi teks (mungkin berupa gambar).';
        box.appendChild(m);
      }
      ks.forEach(function (k, i) {
        var s = document.createElement('span');
        s.className = 'kal';
        s.textContent = k;
        s.addEventListener('click', function () { mulaiAudio(p, i); });
        box.appendChild(s);
      });
      perbaruiGlosarium(t);
      if (audioOn) sorot(si);
    });
  }

  function sorot(i) {
    var els = document.querySelectorAll('#txtview .kal');
    for (var j = 0; j < els.length; j++) els[j].classList.toggle('on', j === i);
    if (mode === 'teks' && els[i] && els[i].scrollIntoView) els[i].scrollIntoView({ block: 'nearest' });
  }

  // ---------- audio ----------
  function suara() {
    var l = speechSynthesis.getVoices().filter(function (v) { return /^id/i.test(v.lang); });
    return l.length ? l[0] : null;
  }
  function statusAudio(t) { $('rd-astat').textContent = t; }
  function labelAudio() { $('b-audio').innerHTML = audioOn ? '&#9208; Jeda' : '&#127911; Dengarkan'; }

  function bacaHalaman(p, mulai) {
    token++;
    var my = token;
    speechSynthesis.cancel();
    dapatTeks(p).then(function (t) {
      if (my !== token) return;
      kal = pecah(t);
      si = mulai || 0;
      halAudio = p;
      if (p !== cur) pergi(p, true);
      if (!kal.length) {
        statusAudio('Halaman ' + (p + 1) + ' tidak ada teks, dilewati.');
        setTimeout(function () { lanjutHalaman(my); }, 700);
        return;
      }
      statusAudio('Membacakan halaman ' + (p + 1) + '...');
      bicara(my);
    });
  }
  function lanjutHalaman(my) {
    if (my !== token || !audioOn) return;
    if (cur + 1 < n) { bacaHalaman(cur + 1, 0); }
    else { hentikanAudio(); statusAudio('Selesai membaca. Ceritakan bagian favoritmu!'); }
  }
  function bicara(my) {
    if (my !== token || !audioOn) return;
    if (si >= kal.length) { lanjutHalaman(my); return; }
    sorot(si);
    var u = new SpeechSynthesisUtterance(kal[si].trim());
    u.lang = 'id-ID';
    var v = suara();
    if (v) u.voice = v;
    u.rate = parseFloat($('s-rate').value);
    var lanjut = function () { if (my === token) { si++; bicara(my); } };
    u.onend = lanjut;
    u.onerror = lanjut;
    speechSynthesis.speak(u);
  }
  function mulaiAudio(p, i) {
    if (!('speechSynthesis' in window)) {
      statusAudio('Browser ini belum mendukung suara otomatis. Coba Chrome atau Edge.');
      return;
    }
    if (!pdf) { statusAudio('Buku masih dimuat, tunggu sebentar.'); return; }
    audioOn = true;
    labelAudio();
    bacaHalaman(p, i);
  }
  function hentikanAudio() {
    audioOn = false;
    token++;
    if ('speechSynthesis' in window) speechSynthesis.cancel();
    labelAudio();
  }

  // ---------- insight ----------
  var STOP = ('yang dan di ke dari ini itu untuk pada dengan adalah dalam tidak akan juga atau ada saya kamu aku kita mereka dia ia oleh karena sebagai bisa dapat lebih sudah telah para bahwa yaitu saat ketika seperti kami anda pun lagi masih hanya mau ingin harus sangat banyak semua setiap bila jika maka agar supaya sebuah suatu satu dua tiga buku halaman').split(' ');
  function kataKunci() {
    var f = {};
    texts.forEach(function (t) {
      (t || '').toLowerCase().split(/[^a-z]+/).forEach(function (w) {
        if (w.length < 4 || STOP.indexOf(w) > -1) return;
        f[w] = (f[w] || 0) + 1;
      });
    });
    var arr = Object.keys(f).filter(function (w) { return f[w] >= 2; })
      .sort(function (a, b) { return f[b] - f[a]; }).slice(0, 15);
    var box = $('rd-kata');
    box.textContent = '';
    if (!arr.length) { box.textContent = 'Belum ada kata kunci (buku mungkin berupa gambar).'; return; }
    arr.forEach(function (w) {
      var c = document.createElement('span');
      c.className = 'rd-chip';
      c.textContent = w;
      c.addEventListener('click', function () { $('rd-cari').value = w; cari(w); });
      box.appendChild(c);
    });
  }
  function cari(q) {
    var out = $('rd-hasil');
    out.textContent = '';
    q = (q || '').trim().toLowerCase();
    if (q.length < 2) return;
    var c = 0;
    for (var i = 0; i < n && c < 30; i++) {
      var t = texts[i] || '';
      var k = t.toLowerCase().indexOf(q);
      if (k > -1) {
        c++;
        var a = document.createElement('button');
        a.type = 'button';
        a.className = 'rd-hasil-item';
        var s = Math.max(0, k - 30);
        a.textContent = 'Hal ' + (i + 1) + ': ...' + t.slice(s, k + q.length + 40) + '...';
        (function (pp) { a.addEventListener('click', function () { pergi(pp, true); }); })(i);
        out.appendChild(a);
      }
    }
    if (!c) out.textContent = siap ? 'Tidak ditemukan.' : 'Tidak ditemukan (teks masih disiapkan...).';
  }
  function indeks() {
    var i = 0;
    function langkah() {
      if (i >= n) {
        siap = true;
        $('rd-idx').textContent = 'Teks seluruh buku siap dicari.';
        kataKunci();
        return;
      }
      dapatTeks(i).then(function () {
        i++;
        if (i % 5 === 0) $('rd-idx').textContent = 'Menyiapkan pencarian: ' + i + ' / ' + n;
        langkah();
      });
    }
    langkah();
  }

  // ---------- glosarium ----------
  function itemGlos(g) {
    var d = document.createElement('div');
    d.className = 'rd-glos-item';
    var b = document.createElement('strong');
    b.textContent = g.istilah;
    var s = document.createElement('span');
    s.textContent = ' \u2014 ' + g.arti;
    d.appendChild(b);
    d.appendChild(s);
    return d;
  }
  function isiGlosarium() {
    var list = $('rd-glos-list');
    list.textContent = '';
    if (!GLOS.length) {
      $('rd-glos-semua').style.display = 'none';
      return;
    }
    GLOS.forEach(function (g) { list.appendChild(itemGlos(g)); });
  }
  function perbaruiGlosarium(t) {
    var box = $('rd-glos-ini');
    box.textContent = '';
    if (!GLOS.length) {
      box.style.opacity = '.7';
      box.style.fontSize = '12px';
      box.textContent = 'Belum ada glosarium untuk buku ini.';
      return;
    }
    var low = (t || '').toLowerCase();
    var ada = GLOS.filter(function (g) { return low.indexOf(g.istilah.toLowerCase()) > -1; });
    if (!ada.length) {
      box.style.opacity = '.7';
      box.style.fontSize = '12px';
      box.textContent = 'Tidak ada istilah khusus di halaman ini.';
      return;
    }
    box.style.opacity = '1';
    ada.forEach(function (g) { box.appendChild(itemGlos(g)); });
  }

  // ---------- tampilan ----------
  function setMode(m) {
    mode = m;
    $('bookwrap').style.display = (m === 'buku') ? 'flex' : 'none';
    $('txtview').style.display = (m === 'teks') ? 'block' : 'none';
    $('b-mode').textContent = (m === 'buku') ? 'Mode Teks' : 'Mode Buku';
    if (m === 'buku' && pf && cur > -1) pf.turnToPage(cur);
    if (cur > -1) perbaruiTeks();
  }

  // ---------- ulasan suara ----------
  var recMedia = null, recChunks = [], recBlob = null;
  function pasangUlasan() {
    if (!$('vr-rekam')) return;
    var st = $('vr-status');
    $('vr-rekam').addEventListener('click', function () {
      if (!navigator.mediaDevices || !window.MediaRecorder) {
        st.textContent = 'Perekam suara tidak didukung di browser ini.';
        return;
      }
      hentikanAudio();
      navigator.mediaDevices.getUserMedia({ audio: true }).then(function (stream) {
        recChunks = [];
        recBlob = null;
        recMedia = new MediaRecorder(stream);
        recMedia.addEventListener('dataavailable', function (e) {
          if (e.data && e.data.size) recChunks.push(e.data);
        });
        recMedia.addEventListener('stop', function () {
          stream.getTracks().forEach(function (t) { t.stop(); });
          recBlob = new Blob(recChunks, { type: recMedia.mimeType || 'audio/webm' });
          var pv = $('vr-preview');
          pv.src = URL.createObjectURL(recBlob);
          pv.style.display = 'block';
          $('vr-kirim').style.display = 'inline-block';
          $('vr-rekam').style.display = 'inline-block';
          $('vr-stop').style.display = 'none';
          st.textContent = 'Dengarkan dulu, lalu kirim.';
        });
        recMedia.start();
        $('vr-rekam').style.display = 'none';
        $('vr-stop').style.display = 'inline-block';
        $('vr-kirim').style.display = 'none';
        $('vr-preview').style.display = 'none';
        st.textContent = 'Sedang merekam...';
      }).catch(function (err) {
        st.textContent = 'Tidak bisa memakai mikrofon: ' + err.message;
      });
    });
    $('vr-stop').addEventListener('click', function () {
      if (recMedia && recMedia.state !== 'inactive') recMedia.stop();
    });
    $('vr-kirim').addEventListener('click', function () {
      if (!recBlob) return;
      st.textContent = 'Mengirim...';
      var fd = new FormData();
      fd.append('csrfmiddlewaretoken', CSRF);
      fd.append('jenis', 'AUDIO');
      fd.append('teks', '');
      fd.append('file_audio', new File([recBlob], 'ulasan.webm', { type: recBlob.type || 'audio/webm' }));
      if ($('vr-porto').checked) fd.append('simpan_portofolio', '1');
      fetch(URL_SUMBER, { method: 'POST', body: fd, credentials: 'same-origin' })
        .then(function (r) {
          if (!r.ok) throw new Error('status ' + r.status);
          st.textContent = 'Ulasan suaramu terkirim, terima kasih!';
          $('vr-kirim').style.display = 'none';
          recBlob = null;
        })
        .catch(function () { st.textContent = 'Gagal mengirim. Coba lagi.'; });
    });
  }

  function pasangKontrol() {
    $('b-prev').addEventListener('click', function () { pergi(cur - 1, true); });
    $('b-next').addEventListener('click', function () { pergi(cur + 1, true); });
    $('b-mode').addEventListener('click', function () { setMode(mode === 'buku' ? 'teks' : 'buku'); });
    $('b-audio').addEventListener('click', function () {
      if (audioOn) { hentikanAudio(); statusAudio('Dijeda.'); }
      else { mulaiAudio(cur < 0 ? 0 : cur, (halAudio === cur) ? si : 0); }
    });
    $('b-besar').addEventListener('click', function () {
      fs = Math.min(34, fs + 2); $('txtview').style.fontSize = fs + 'px';
      if (mode === 'buku') setMode('teks');
    });
    $('b-kecil').addEventListener('click', function () {
      fs = Math.max(13, fs - 2); $('txtview').style.fontSize = fs + 'px';
      if (mode === 'buku') setMode('teks');
    });
    $('s-tema').addEventListener('change', function () { root.className = 'th-' + this.value; });
    $('b-panel').addEventListener('click', function () {
      var p = $('rd-panel');
      p.style.display = (p.style.display === 'none') ? 'block' : 'none';
    });
    $('b-full').addEventListener('click', function () {
      if (document.fullscreenElement) document.exitFullscreen();
      else if (root.requestFullscreen) root.requestFullscreen();
    });
    var timer = null;
    $('rd-cari').addEventListener('input', function () {
      var v = this.value;
      clearTimeout(timer);
      timer = setTimeout(function () { cari(v); }, 250);
    });
    document.addEventListener('keydown', function (e) {
      var tag = (e.target.tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'select' || tag === 'textarea') return;
      if (e.key === 'ArrowRight') pergi(cur + 1, true);
      else if (e.key === 'ArrowLeft') pergi(cur - 1, true);
    });
    window.addEventListener('pagehide', function () {
      if ('speechSynthesis' in window) speechSynthesis.cancel();
      if (SIMPAN && n && cur > -1 && navigator.sendBeacon) navigator.sendBeacon(URL_PROGRES, bodyProgres());
    });
    pasangUlasan();
  }

  function gagal(e) {
    var st = $('rd-status');
    st.textContent = 'Pembaca interaktif gagal dimuat (' + (e && e.message ? e.message : 'kesalahan') + '). Pembaca ini butuh koneksi internet untuk memuat pustakanya. ';
    var a = document.createElement('a');
    a.href = PDF_URL; a.target = '_blank';
    a.textContent = 'Buka PDF biasa';
    a.style.fontWeight = '700';
    st.appendChild(a);
  }

  function mulai() {
    pasangKontrol();
    muatSkrip(CDN_PDF)
      .then(function () { return muatSkrip(CDN_FLIP); })
      .then(function () { return fetch(CDN_WORKER); })
      .then(function (r) { return r.blob(); })
      .then(function (b) {
        pdfjsLib.GlobalWorkerOptions.workerSrc = URL.createObjectURL(b);
        return pdfjsLib.getDocument({ url: PDF_URL }).promise;
      })
      .then(function (doc) { pdf = doc; n = doc.numPages; return doc.getPage(1); })
      .then(function (pg) {
        var p1 = pg.getViewport({ scale: 1 });
        var ratio = p1.height / p1.width;
        var w = Math.max(280, Math.min(460, $('bookwrap').clientWidth || 460));
        var h = Math.round(w * ratio);
        var bookEl = $('book');
        bookEl.style.width = w + 'px';
        bookEl.style.height = h + 'px';
        for (var i = 0; i < n; i++) {
          var d = document.createElement('div');
          d.className = 'pg';
          d.setAttribute('data-density', (i === 0 || i === n - 1) ? 'hard' : 'soft');
          var cv = document.createElement('canvas');
          d.appendChild(cv);
          bookEl.appendChild(d);
          canvases.push(cv);
        }
        pf = new St.PageFlip(bookEl, {
          width: w, height: h, size: 'fixed', showCover: true,
          maxShadowOpacity: 0.4, mobileScrollSupport: false, flippingTime: 650
        });
        pf.loadFromHTML(bookEl.querySelectorAll('.pg'));
        pf.on('flip', function (e) {
          var p = e.data;
          if (p === cur) return;
          setCur(p);
          if (audioOn) bacaHalaman(p, 0);
        });

        var start = Math.min(Math.max(MULAI, 0), n - 1);
        for (var k = 0; k <= start; k++) catat(k);
        if (start > 0) pf.turnToPage(start);
        $('rd-status').textContent = start > 0 ? 'Melanjutkan dari halaman ' + (start + 1) + '.' : '';
        setCur(start);
        isiGlosarium();
        indeks();
      })
      .catch(gagal);
  }
  mulai();
})();
</script>
{% endverbatim %}
{% endblock %}
"""

TPL_GLOSARIUM = r"""{% extends 'base.html' %}
{% block title %}Glosarium: {{ sumber.judul }}{% endblock %}
{% block page_title %}Glosarium{% endblock %}
{% block content %}
<div class="max-w-2xl">
<div class="mb-4"><a href="{% url 'perpustakaan:detail_sumber' sumber.id %}" class="text-sm text-[#0B3D26] hover:underline">&larr; {{ sumber.judul }}</a></div>

<div class="card p-5 mb-5">
  <h3 class="font-semibold text-gray-800 text-sm mb-3">Istilah ({{ daftar|length }})</h3>
  {% for g in daftar %}
  <div style="display:flex; justify-content:space-between; gap:10px; padding:10px 0; border-bottom:1px solid #f3f4f6;">
    <div>
      <strong style="font-size:14px; color:#1f2937;">{{ g.istilah }}</strong>
      <p style="margin:2px 0 0; font-size:13px; color:#4b5563;">{{ g.arti }}</p>
    </div>
    <form method="POST" action="{% url 'perpustakaan:hapus_glosarium' g.id %}" onsubmit="return confirm('Hapus {{ g.istilah|escapejs }}?')" style="margin:0;">
      {% csrf_token %}
      <button type="submit" style="font-size:10px; background:#fee2e2; color:#dc2626; border:none; padding:3px 8px; border-radius:6px; cursor:pointer;">Hapus</button>
    </form>
  </div>
  {% empty %}
  <p style="color:#9ca3af; font-size:13px; margin:0;">Belum ada istilah. Tambahkan di bawah.</p>
  {% endfor %}
</div>

<div class="card p-5">
  <h3 class="font-semibold text-gray-800 text-sm mb-3">Tambah istilah</h3>
  <form method="POST" class="space-y-3">
    {% csrf_token %}
    <input type="text" name="istilah" maxlength="100" placeholder="Istilah, contoh: fotosintesis" class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm">
    <textarea name="arti" rows="2" placeholder="Arti dengan bahasa yang mudah dipahami anak" class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"></textarea>
    <details>
      <summary style="cursor:pointer; font-size:12px; color:#6b7280;">Tempel banyak sekaligus</summary>
      <textarea name="massal" rows="6" placeholder="Satu istilah per baris, format: istilah = arti" class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" style="margin-top:8px;"></textarea>
    </details>
    <button type="submit" class="btn-primary">Simpan</button>
  </form>
</div>
</div>
{% endblock %}
"""

TPL_PROGRES = r"""<div class="card p-5 mb-5">
  <h3 style="font-size:12px; font-weight:700; color:#0B3D26; letter-spacing:.06em; text-transform:uppercase; margin:0 0 10px;">&#128218; Bacaan Perpustakaan</h3>
  {% if progres_list %}
  {% for p in progres_list %}
  <div style="margin-bottom:10px;">
    <div style="display:flex; justify-content:space-between; gap:8px; font-size:13px; color:#374151;">
      <span>{{ p.sumber.judul }}</span>
      <span>{% if p.selesai %}<b style="color:#15803d;">Selesai &#10003;</b>{% else %}Hal {{ p.halaman_terakhir }} / {{ p.total_halaman }}{% endif %}</span>
    </div>
    <div style="height:6px; background:#e5e7eb; border-radius:99px; overflow:hidden; margin-top:4px;">
      <div style="height:100%; width:{% if p.selesai %}100{% else %}{% widthratio p.halaman_terakhir p.total_halaman 100 %}{% endif %}%; background:#16a34a;"></div>
    </div>
  </div>
  {% endfor %}
  {% else %}
  <p style="font-size:13px; color:#9ca3af; margin:0;">Belum ada buku yang dibaca.</p>
  {% endif %}
</div>
"""

FILTER_ZONA = r"""<div class="tab-filter">
  <a href="?usia={{ usia_aktif }}&q={{ q|urlencode }}" class="{% if not jenis_aktif %}on{% endif %}">Semua</a>
  <a href="?jenis=TEKS&usia={{ usia_aktif }}&q={{ q|urlencode }}" class="{% if jenis_aktif == 'TEKS' %}on{% endif %}">&#128214; Baca</a>
  <a href="?jenis=AUDIO&usia={{ usia_aktif }}&q={{ q|urlencode }}" class="{% if jenis_aktif == 'AUDIO' %}on{% endif %}">&#127911; Dengar</a>
  <a href="?jenis=VIDEO&usia={{ usia_aktif }}&q={{ q|urlencode }}" class="{% if jenis_aktif == 'VIDEO' %}on{% endif %}">&#127916; Tonton</a>
</div>
<form method="get" id="filter-form" style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:16px;">
  <input type="hidden" name="jenis" value="{{ jenis_aktif }}">
  <input type="text" name="q" value="{{ q }}" placeholder="Cari judul atau topik..." style="border:1px solid #e5e7eb; border-radius:8px; padding:7px 12px; font-size:13px; min-width:200px;">
  <select name="usia" style="border:1px solid #e5e7eb; border-radius:8px; padding:7px 10px; font-size:13px;">
    <option value="">Semua usia</option>
    <option value="6-8" {% if usia_aktif == '6-8' %}selected{% endif %}>6-8 tahun</option>
    <option value="9-11" {% if usia_aktif == '9-11' %}selected{% endif %}>9-11 tahun</option>
    <option value="12-18" {% if usia_aktif == '12-18' %}selected{% endif %}>12 tahun ke atas</option>
  </select>
  <button type="submit" class="btn-primary" style="padding:7px 16px; font-size:13px;">Cari</button>
  {% if q or usia_aktif %}<a href="?jenis={{ jenis_aktif }}" style="font-size:12px; color:#6b7280; align-self:center;">Hapus filter</a>{% endif %}
</form>
"""

FORM_SUMBER_TAMBAH = r"""    <div style="display:flex; gap:12px;">
      <div style="flex:1;">
        <label class="block text-xs font-semibold text-gray-500 uppercase mb-1">Usia minimal</label>
        <input type="number" name="usia_min" min="0" max="99" value="0" class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm">
      </div>
      <div style="flex:1;">
        <label class="block text-xs font-semibold text-gray-500 uppercase mb-1">Usia maksimal</label>
        <input type="number" name="usia_maks" min="0" max="99" value="0" class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm">
      </div>
    </div>
    <p style="font-size:11px; color:#9ca3af; margin:0;">Isi 0 untuk semua umur.</p>
    <div>
      <label class="block text-xs font-semibold text-gray-500 uppercase mb-1">Topik / minat (opsional)</label>
      <input type="text" name="topik" maxlength="200" placeholder="Contoh: hewan, antariksa, persahabatan" class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm">
    </div>
"""

FORM_SUMBER_EDIT = FORM_SUMBER_TAMBAH.replace('value="0" class', 'value="{{ sumber.usia_min }}" class', 1) \
    .replace('value="0" class', 'value="{{ sumber.usia_maks }}" class', 1) \
    .replace('name="topik" maxlength', 'name="topik" value="{{ sumber.topik }}" maxlength', 1)


# ---------------------------------------------------------------------------
# LANGKAH-LANGKAH
# ---------------------------------------------------------------------------

def ganti_fungsi(s, nama, kode):
    tree = ast.parse(s)
    baris = s.split('\n')
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and n.name == nama:
            segmen = ast.get_source_segment(s, n) or ''
            if 'usia_aktif' in segmen:
                return s, 'SUDAH'
            awal = (n.decorator_list[0].lineno if n.decorator_list else n.lineno) - 1
            akhir = n.end_lineno
            baris[awal:akhir] = kode.rstrip('\n').split('\n')
            return '\n'.join(baris), 'OK'
    return s, 'HILANG'


def langkah_model():
    p = 'perpustakaan/models.py'
    s = read(p)
    if 'usia_min' in s:
        lapor('SUDAH', 'models: field usia_min, usia_maks, topik')
    else:
        m = re.search(r'^([ \t]+)teks_baca\s*=\s*models\.TextField\([^\n]*\n', s, re.M)
        if m:
            ind = m.group(1)
            tambah = ''.join(ind + baris + '\n' for baris in MODEL_FIELD_BARU.strip('\n').split('\n'))
            s = s[:m.end()] + tambah + s[m.end():]
            lapor('OK', 'models: field usia_min, usia_maks, topik di SumberDigital')
        else:
            lapor('SKIP', 'models: baris teks_baca tidak ditemukan. Tambahkan manual 3 field ini di SumberDigital:\n' + MODEL_FIELD_BARU)
    if 'class ProgresBaca' in s:
        lapor('SUDAH', 'models: ProgresBaca')
    else:
        s = s.rstrip('\n') + '\n\n\n' + MODEL_PROGRES
        lapor('OK', 'models: ProgresBaca')
    if 'class Glosarium' in s:
        lapor('SUDAH', 'models: Glosarium')
    else:
        s = s.rstrip('\n') + '\n\n\n' + MODEL_GLOSARIUM
        lapor('OK', 'models: Glosarium')
    write(p, s)


def langkah_views():
    p = 'perpustakaan/views.py'
    s = read(p)
    try:
        s, st = ganti_fungsi(s, 'detail_zona', VIEW_DETAIL_ZONA)
        lapor(st if st != 'HILANG' else 'SKIP', 'views: detail_zona (filter jenis + usia + pencarian)')
    except SyntaxError as e:
        lapor('SKIP', 'views: views.py punya kesalahan sintaks (%s), perbaiki dulu' % e)
        return

    if 'usia_min=_angka' in s:
        lapor('SUDAH', 'views: tambah_sumber menyimpan usia + topik')
    else:
        s, n1 = re.subn(
            r"^([ \t]+)(teks_baca=request\.POST\.get\('teks_baca', ''\)\.strip\(\),\n)",
            lambda m: m.group(0) + (
                m.group(1) + "usia_min=_angka(request.POST.get('usia_min')),\n" +
                m.group(1) + "usia_maks=_angka(request.POST.get('usia_maks')),\n" +
                m.group(1) + "topik=request.POST.get('topik', '').strip()[:200],\n"),
            s, count=1, flags=re.M)
        lapor('OK' if n1 else 'SKIP', 'views: tambah_sumber menyimpan usia + topik')

    if 'sumber.usia_min = _angka' in s:
        lapor('SUDAH', 'views: edit_sumber menyimpan usia + topik')
    else:
        s, n2 = re.subn(
            r"^([ \t]+)(sumber\.teks_baca = request\.POST\.get\('teks_baca', ''\)\.strip\(\)\n)",
            lambda m: m.group(0) + (
                m.group(1) + "sumber.usia_min = _angka(request.POST.get('usia_min'))\n" +
                m.group(1) + "sumber.usia_maks = _angka(request.POST.get('usia_maks'))\n" +
                m.group(1) + "sumber.topik = request.POST.get('topik', '').strip()[:200]\n"),
            s, count=1, flags=re.M)
        lapor('OK' if n2 else 'SKIP', 'views: edit_sumber menyimpan usia + topik')

    if 'def baca_sumber' in s:
        lapor('SUDAH', 'views: baca_sumber, simpan_progres, glosarium')
    else:
        s = s.rstrip('\n') + '\n\n\n' + VIEW_BARU
        lapor('OK', 'views: baca_sumber, simpan_progres, glosarium_sumber, hapus_glosarium')
    write(p, s)


def langkah_urls():
    p = 'perpustakaan/urls.py'
    s = read(p)
    baru = [b for nama, b in URL_BARU if ("name='%s'" % nama) not in s and ('name="%s"' % nama) not in s]
    if not baru:
        lapor('SUDAH', 'urls: semua rute baru')
        return
    m = re.search(r'urlpatterns\s*=\s*\[\n', s)
    if not m:
        lapor('SKIP', 'urls: urlpatterns tidak ditemukan. Tambahkan manual:\n' + '\n'.join('    ' + b for b in baru))
        return
    s = s[:m.end()] + ''.join('    ' + b + '\n' for b in baru) + s[m.end():]
    write(p, s)
    lapor('OK', 'urls: %d rute baru' % len(baru))


def langkah_template_baru():
    write('templates/perpustakaan/baca_sumber.html', TPL_BACA)
    lapor('OK', 'template: baca_sumber.html (pembaca interaktif)')
    p = 'templates/perpustakaan/glosarium.html'
    if os.path.exists(p) and read(p) == TPL_GLOSARIUM:
        lapor('SUDAH', 'template: glosarium.html')
    else:
        write(p, TPL_GLOSARIUM)
        lapor('OK', 'template: glosarium.html')
    write('templates/perpustakaan/_progres_baca.html', TPL_PROGRES)
    lapor('OK', 'template: _progres_baca.html')


def sisip_sebelum(path, anchor, blok, tanda, label):
    if not os.path.exists(path):
        lapor('SKIP', '%s (file tidak ada: %s)' % (label, path))
        return
    s = read(path)
    if tanda in s:
        lapor('SUDAH', label)
        return
    if s.count(anchor) < 1:
        lapor('SKIP', '%s (pola tidak cocok di %s)' % (label, path))
        return
    write(path, s.replace(anchor, blok + anchor, 1))
    lapor('OK', label)


def langkah_form_sumber():
    anchor = '    <div class="flex gap-3 pt-2">\n'
    sisip_sebelum('templates/perpustakaan/tambah_sumber.html', anchor, FORM_SUMBER_TAMBAH,
                  'name="usia_min"', 'form tambah koleksi: usia + topik')
    sisip_sebelum('templates/perpustakaan/edit_sumber.html', anchor, FORM_SUMBER_EDIT,
                  'name="usia_min"', 'form edit koleksi: usia + topik')


def langkah_filter_zona():
    p = 'templates/perpustakaan/detail_zona.html'
    if not os.path.exists(p):
        lapor('SKIP', 'filter zona (detail_zona.html tidak ada)')
        return
    s = read(p)
    if 'id="filter-form"' in s:
        lapor('SUDAH', 'detail_zona.html: filter usia + pencarian')
        return
    baru, n = re.subn(r'<div class="tab-filter">.*?</div>\n', lambda m: FILTER_ZONA, s, count=1, flags=re.S)
    if n:
        write(p, baru)
        lapor('OK', 'detail_zona.html: filter usia + pencarian')
    else:
        lapor('SKIP', 'detail_zona.html: blok tab-filter tidak ditemukan')


def langkah_detail_sumber():
    p = 'templates/perpustakaan/detail_sumber.html'
    if not os.path.exists(p):
        lapor('SKIP', 'detail_sumber.html tidak ada')
        return
    s = read(p)
    diubah = False
    if 'perpustakaan:baca_sumber' in s:
        lapor('SUDAH', 'detail_sumber.html: tombol Baca Interaktif')
    else:
        lama = '<a href="{{ sumber.file.url }}" target="_blank" class="btn-primary">Buka / Unduh E-Book</a>'
        baru = ('{% if sumber.file.name|slice:"-4:"|lower == ".pdf" %}'
                '<a href="{% url \'perpustakaan:baca_sumber\' sumber.id %}" class="btn-primary">&#128214; Baca Interaktif</a> {% endif %}'
                '<a href="{{ sumber.file.url }}" target="_blank" class="btn-primary" style="background:#6b7280;">Buka / Unduh PDF</a>')
        if lama in s:
            s = s.replace(lama, baru, 1)
            diubah = True
            lapor('OK', 'detail_sumber.html: tombol Baca Interaktif')
        else:
            lapor('SKIP', 'detail_sumber.html: tombol "Buka / Unduh E-Book" tidak ditemukan')
    if 'perpustakaan:glosarium' in s:
        lapor('SUDAH', 'detail_sumber.html: tautan Kelola glosarium')
    else:
        lama = 'Edit koleksi ini</a></p>'
        baru = ('Edit koleksi ini</a> &middot; <a href="{% url \'perpustakaan:glosarium\' sumber.id %}" '
                'style="font-size:12px; color:#0369a1;">Kelola glosarium</a></p>')
        if lama in s:
            s = s.replace(lama, baru, 1)
            diubah = True
            lapor('OK', 'detail_sumber.html: tautan Kelola glosarium')
        else:
            lapor('SKIP', 'detail_sumber.html: tautan "Edit koleksi ini" tidak ditemukan')
    if diubah:
        write(p, s)


def langkah_dashboard():
    p = 'accounts/views.py'
    if os.path.exists(p):
        s = read(p)
        if 'ProgresBaca' in s:
            lapor('SUDAH', 'accounts/views.py: progres baca di dashboard')
        else:
            s = s.replace('from perpustakaan.models import LencanaDiperoleh\n',
                          'from perpustakaan.models import LencanaDiperoleh, ProgresBaca\n')
            a1 = "{'siswa': siswa, 'lencana_list': lencana_list})"
            b1 = ("{'siswa': siswa, 'lencana_list': lencana_list,\n"
                  "        'progres_list': ProgresBaca.objects.filter(siswa=siswa).select_related('sumber')[:8]})")
            a2 = "        'lencana_list': lencana_list,\n    })"
            b2 = ("        'lencana_list': lencana_list,\n"
                  "        'progres_list': ProgresBaca.objects.filter(siswa=siswa).select_related('sumber')[:8],\n    })")
            ok1 = a1 in s
            ok2 = a2 in s
            s = s.replace(a1, b1, 1).replace(a2, b2, 1)
            write(p, s)
            lapor('OK' if ok1 else 'SKIP', 'accounts/views.py: dashboard_siswa membawa progres_list')
            lapor('OK' if ok2 else 'SKIP', 'accounts/views.py: dashboard_orangtua membawa progres_list')
    else:
        lapor('SKIP', 'accounts/views.py tidak ditemukan')

    inc = "{% include 'perpustakaan/_lencana_kartu.html' %}\n"
    for t in ('templates/accounts/dashboard_siswa.html', 'templates/accounts/dashboard_orangtua.html'):
        sisip_setelah(t, inc, "{% include 'perpustakaan/_progres_baca.html' %}\n",
                      '_progres_baca.html', 'dashboard: kartu progres ' + os.path.basename(t))


def sisip_setelah(path, anchor, blok, tanda, label):
    if not os.path.exists(path):
        lapor('SKIP', '%s (file tidak ada: %s)' % (label, path))
        return
    s = read(path)
    if tanda in s:
        lapor('SUDAH', label)
        return
    if anchor not in s:
        lapor('SKIP', '%s (baris include lencana tidak ditemukan; tambahkan manual: %s)' % (label, blok.strip()))
        return
    write(path, s.replace(anchor, anchor + blok, 1))
    lapor('OK', label)


def langkah_admin():
    p = 'perpustakaan/admin.py'
    if not os.path.exists(p):
        lapor('SKIP', 'admin.py tidak ada')
        return
    s = read(p)
    if 'ProgresBaca' in s:
        lapor('SUDAH', 'admin.py: ProgresBaca, Glosarium')
        return
    s = s.rstrip('\n') + ('\n\n\nfrom .models import ProgresBaca, Glosarium\n\n'
                          'admin.site.register(ProgresBaca)\nadmin.site.register(Glosarium)\n')
    write(p, s)
    lapor('OK', 'admin.py: ProgresBaca, Glosarium')


def main():
    if not (os.path.exists('manage.py') and os.path.isdir('perpustakaan')):
        print('Jalankan skrip ini dari folder proyek (yang berisi manage.py dan folder perpustakaan).')
        sys.exit(1)
    print('Cadangan file yang diubah: %s\n' % CAD)
    langkah_model()
    langkah_views()
    langkah_urls()
    langkah_template_baru()
    langkah_form_sumber()
    langkah_filter_zona()
    langkah_detail_sumber()
    langkah_dashboard()
    langkah_admin()
    print('\nRingkasan: %(OK)d OK, %(SUDAH)d SUDAH, %(SKIP)d SKIP' % HASIL)
    print('\nSelanjutnya jalankan:')
    print('    python manage.py makemigrations perpustakaan')
    print('    python manage.py migrate')
    print('    python manage.py check')
    if HASIL['SKIP']:
        print('\nAda baris SKIP. Kirim seluruh output ini ke asisten supaya bisa disesuaikan.')


if __name__ == '__main__':
    main()
