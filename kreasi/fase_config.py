"""
Konfigurasi Tugas Kreasi per jenjang.

File ini SENGAJA berupa Python biasa (tanpa impor model) supaya bisa diimpor dari
mana saja, termasuk dari ruang_kerja.models, tanpa impor melingkar.

Kunci jenjang mengikuti konsep Betsora OS, BUKAN huruf fase resmi Kurikulum Merdeka,
karena konsep memecah Fase B menjadi SD 1-3 dan SD 4-6.

Kalimat deskriptor memakai {nama} yang diganti nama depan siswa. Deskriptor di sini
hanya nilai awal: perintah `seed_kreasi` menyalinnya ke database, lalu guru/admin
bebas mengeditnya lewat halaman admin tanpa migrasi.
"""
import re

JENJANG_CHOICES = [
    ('sd_awal', 'SD Kelas 1-3'),
    ('sd_akhir', 'SD Kelas 4-6'),
    ('smp', 'SMP / Sederajat'),
    ('sma', 'SMA / SMK / Sederajat'),
]

LEVEL_LABEL = {
    1: 'Mulai Berkembang',
    2: 'Berkembang',
    3: 'Cakap',
    4: 'Sangat Baik',
}

# Tipe lampiran yang dikenal sistem
TIPE_LAMPIRAN = ('foto', 'audio', 'video', 'dokumen', 'link')

JENJANG_CONFIG = {
    'sd_awal': {
        'label': 'SD Kelas 1-3',
        'rentang_kelas': (1, 3),
        'tipe_lampiran': ('foto', 'audio'),
        'wajib_lampiran': ('foto', 'audio'),
        'batas_audio_detik': 60,
        'refleksi': {
            'tipe': 'emoji_suara',
            'petunjuk': 'Pilih perasaanmu, lalu ceritakan karyamu dengan suara.',
            'emoji': [
                ('senang', '😊', 'Senang'),
                ('bangga', '🌟', 'Bangga'),
                ('sulit', '😅', 'Agak sulit'),
                ('bingung', '🤔', 'Bingung'),
            ],
        },
        'dimensi': [
            {
                'kode': 'keberanian_berekspresi', 'nama': 'Keberanian Berekspresi',
                'deskriptor': {
                    1: '{nama} masih perlu ditemani dan didorong dengan lembut agar berani menunjukkan karyanya dan menyampaikan idenya.',
                    2: '{nama} mulai berani menunjukkan karyanya, terutama bila diajak berbicara dengan pertanyaan sederhana.',
                    3: '{nama} berani menunjukkan karyanya dan menyampaikan idenya kepada guru dan teman.',
                    4: '{nama} sangat berani dan percaya diri mengungkapkan ide serta bangga menunjukkan karyanya kepada orang lain.',
                },
            },
            {
                'kode': 'motorik_halus', 'nama': 'Motorik Halus',
                'deskriptor': {
                    1: 'Kemampuan {nama} dalam menggunting, menempel, mewarnai, dan memegang alat tulis masih memerlukan banyak latihan dan pendampingan.',
                    2: '{nama} mulai mampu mengendalikan alat seperti gunting, lem, dan pensil warna, walaupun hasilnya belum selalu rapi.',
                    3: '{nama} cukup terampil mengendalikan alat kerja sehingga karyanya tersusun dengan rapi.',
                    4: '{nama} sangat terampil menggunakan tangan dan alat kerja sehingga karyanya rapi dan detail.',
                },
            },
            {
                'kode': 'kelancaran_lisan', 'nama': 'Kelancaran Menyampaikan Gagasan Lisan',
                'deskriptor': {
                    1: '{nama} masih menyampaikan gagasan dengan kata-kata singkat dan perlu dibantu dengan pertanyaan pancingan.',
                    2: '{nama} mulai mampu menceritakan karyanya dengan beberapa kalimat sederhana.',
                    3: '{nama} mampu menceritakan karyanya secara runtut dengan kalimat yang jelas.',
                    4: '{nama} sangat lancar bercerita tentang karyanya, lengkap dengan alasan dan perasaannya.',
                },
            },
        ],
    },

    'sd_akhir': {
        'label': 'SD Kelas 4-6',
        'rentang_kelas': (4, 6),
        'tipe_lampiran': ('foto', 'dokumen', 'audio', 'video'),
        'wajib_lampiran': ('foto',),
        'batas_audio_detik': 120,
        'refleksi': {
            'tipe': 'teks_terbimbing',
            'petunjuk': 'Jawab tiga pertanyaan singkat tentang karyamu.',
            'pertanyaan': [
                ('dibuat', 'Apa yang kamu buat?'),
                ('kesulitan', 'Apa bagian tersulit saat merancang karya ini dan bagaimana kamu mengatasinya?'),
                ('perbaikan', 'Apa yang akan kamu perbaiki kalau membuatnya lagi?'),
            ],
        },
        'dimensi': [
            {
                'kode': 'sebab_akibat', 'nama': 'Logika Sebab-Akibat',
                'deskriptor': {
                    1: '{nama} masih perlu bimbingan untuk menghubungkan langkah kerja dengan hasil yang diperoleh.',
                    2: '{nama} mulai dapat menjelaskan hubungan sederhana antara langkah yang dilakukan dan hasilnya.',
                    3: '{nama} mampu menjelaskan hubungan sebab-akibat dalam karyanya dengan runtut.',
                    4: '{nama} sangat baik dalam bernalar sebab-akibat dan mampu memperkirakan akibat dari perubahan yang ia buat.',
                },
            },
            {
                'kode': 'kreativitas_media', 'nama': 'Kreativitas dan Pemilihan Media',
                'deskriptor': {
                    1: '{nama} masih banyak meniru contoh yang diberikan dan perlu dorongan untuk mencoba cara sendiri.',
                    2: '{nama} mulai menambahkan ide sendiri pada karyanya dengan media yang sudah dikenal.',
                    3: '{nama} mampu memilih media yang sesuai dan menuangkan ide orisinal dalam karyanya.',
                    4: '{nama} sangat kreatif dalam memadukan media dan menghasilkan karya yang orisinal serta menarik.',
                },
            },
            {
                'kode': 'pemahaman_konsep', 'nama': 'Pemahaman Konsep Dasar',
                'deskriptor': {
                    1: '{nama} masih memerlukan pengulangan untuk memahami konsep dasar yang melandasi karyanya.',
                    2: '{nama} memahami sebagian konsep dasar dan mulai menerapkannya dalam karya.',
                    3: '{nama} memahami konsep dasar dan menerapkannya dengan tepat dalam karya.',
                    4: '{nama} memahami konsep dasar dengan sangat baik dan dapat menjelaskannya kembali dengan kata-katanya sendiri.',
                },
            },
        ],
    },

    'smp': {
        'label': 'SMP / Sederajat',
        'rentang_kelas': (7, 9),
        'tipe_lampiran': ('dokumen', 'video', 'audio', 'foto', 'link'),
        'wajib_lampiran': (),
        'butuh_ringkasan': True,  # rangkuman eksekutif karya, disimpan di SubmisiTugas.teks_jawaban
        'refleksi': {
            'tipe': 'matriks',
            'petunjuk': 'Nilai karyamu sendiri pada tiap aspek (1-4), lalu jelaskan alasannya.',
            'kriteria': [
                ('kekuatan', 'Kekuatan karya'),
                ('perbaikan', 'Area yang perlu diperbaiki'),
                ('relevansi', 'Relevansi dengan kehidupan nyata'),
            ],
        },
        'dimensi': [
            {
                'kode': 'pemecahan_masalah', 'nama': 'Pemecahan Masalah',
                'deskriptor': {
                    1: '{nama} masih perlu bimbingan untuk mengenali inti masalah dan menentukan langkah penyelesaiannya.',
                    2: '{nama} mampu mengenali masalah dan mengajukan solusi sederhana, namun belum mempertimbangkan alternatif lain.',
                    3: '{nama} mampu menganalisis masalah dan merancang solusi yang masuk akal beserta alasannya.',
                    4: '{nama} sangat baik dalam menganalisis masalah, membandingkan beberapa alternatif, dan memilih solusi dengan pertimbangan yang matang.',
                },
            },
            {
                'kode': 'kolaborasi', 'nama': 'Kolaborasi',
                'deskriptor': {
                    1: '{nama} masih perlu didorong untuk berkontribusi dan mendengarkan pendapat teman dalam kerja kelompok.',
                    2: '{nama} mulai berkontribusi dalam kerja kelompok bila diminta.',
                    3: '{nama} aktif berkontribusi dan menghargai pendapat teman dalam kerja kelompok.',
                    4: '{nama} sangat aktif berkolaborasi, membantu teman, dan ikut menjaga kelompok tetap kompak menuju tujuan bersama.',
                },
            },
            {
                'kode': 'integrasi_disiplin', 'nama': 'Integrasi Antardisiplin Ilmu',
                'deskriptor': {
                    1: '{nama} masih memandang karyanya dari satu bidang dan perlu bimbingan untuk mengaitkannya dengan pelajaran lain.',
                    2: '{nama} mulai mengaitkan karyanya dengan satu bidang lain di luar topik utamanya.',
                    3: '{nama} mampu memadukan pengetahuan dari beberapa mata pelajaran dalam karyanya.',
                    4: '{nama} sangat baik memadukan berbagai bidang ilmu sehingga karyanya utuh dan relevan dengan kehidupan nyata.',
                },
            },
        ],
    },

    'sma': {
        'label': 'SMA / SMK / Sederajat',
        'rentang_kelas': (10, 12),
        'tipe_lampiran': ('link', 'dokumen', 'video', 'foto', 'audio'),
        'wajib_lampiran': (),
        'refleksi': {
            'tipe': 'metakognitif',
            'petunjuk': 'Renungkan proses berpikirmu selama mengerjakan proyek ini.',
            'pertanyaan': [
                ('asumsi_awal', 'Apa asumsi atau rencana awalmu di awal proyek?'),
                ('hasil_akhir', 'Apa yang sebenarnya terjadi, dan apa yang berbeda dari asumsi awalmu?'),
                ('rencana_lanjut', 'Apa rencana pengembangan lanjutan untuk karya ini?'),
            ],
        },
        'dimensi': [
            {
                'kode': 'berpikir_kritis', 'nama': 'Berpikir Kritis',
                'deskriptor': {
                    1: '{nama} masih perlu bimbingan untuk menyertakan alasan dan bukti yang mendukung pendapatnya.',
                    2: '{nama} mulai menyertakan alasan pada pendapatnya, namun bukti pendukungnya belum kuat.',
                    3: '{nama} mampu menyusun argumen yang runtut dengan bukti yang relevan.',
                    4: '{nama} sangat kritis: mampu menguji asumsi, mempertimbangkan sudut pandang lain, dan menarik kesimpulan yang kuat.',
                },
            },
            {
                'kode': 'inovasi_karya', 'nama': 'Inovasi dan Kualitas Karya',
                'deskriptor': {
                    1: '{nama} menghasilkan karya yang masih mengikuti contoh dan perlu dikembangkan agar berfungsi dengan baik.',
                    2: '{nama} menghasilkan karya yang berfungsi dengan baik, dengan sedikit unsur pembaruan.',
                    3: '{nama} menghasilkan karya yang berfungsi baik dan memiliki unsur pembaruan yang jelas.',
                    4: '{nama} menghasilkan karya inovatif dengan kualitas yang mendekati standar profesional.',
                },
            },
            {
                'kode': 'kesiapan_portofolio', 'nama': 'Kesiapan Portofolio dan Profesionalisme',
                'deskriptor': {
                    1: '{nama} perlu melengkapi dokumentasi dan penyajian portofolionya agar dapat dipahami orang lain.',
                    2: '{nama} sudah mendokumentasikan proyeknya, namun penyajiannya perlu dirapikan.',
                    3: '{nama} menyajikan portofolio yang lengkap dan tertata sehingga mudah dipahami.',
                    4: '{nama} menyajikan portofolio yang lengkap, komunikatif, dan siap ditunjukkan untuk seleksi studi lanjut atau dunia kerja.',
                },
            },
        ],
    },
}


# ---------------------------------------------------------------- deteksi jenjang

_ROMAWI = {
    'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6,
    'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10, 'XI': 11, 'XII': 12,
}
# Urutan alternatif dari yang terpanjang agar 'XII' tidak terbaca 'X'.
_RE_ROMAWI = re.compile(r'(?<![A-Z0-9])(XII|XI|X|IX|VIII|VII|VI|IV|V|III|II|I)(?![A-Z0-9])')
_RE_ANGKA = re.compile(r'\d{1,2}')


def deteksi_tingkat(teks):
    """Ambil tingkat kelas 1-12 dari teks bebas: '3', 'Kelas III', 'X-1', 'XI IPA 2', '7A'."""
    if not teks:
        return None
    t = str(teks).upper()
    # Romawi dicoba lebih dulu: pada 'XI IPA 2' angka 2 adalah rombel, bukan tingkat.
    m = _RE_ROMAWI.search(t)
    if m:
        return _ROMAWI[m.group(1)]
    m = _RE_ANGKA.search(t)
    if m:
        n = int(m.group())
        if 1 <= n <= 12:
            return n
    return None


def jenjang_dari_tingkat(tingkat):
    if tingkat is None:
        return None
    for kunci, cfg in JENJANG_CONFIG.items():
        awal, akhir = cfg['rentang_kelas']
        if awal <= tingkat <= akhir:
            return kunci
    return None


def deteksi_jenjang(teks_kelas):
    """Kembalikan kunci jenjang, atau None bila tidak bisa dipastikan."""
    return jenjang_dari_tingkat(deteksi_tingkat(teks_kelas))


def get_config(jenjang):
    return JENJANG_CONFIG.get(jenjang)


# ---------------------------------------------------------------- batas unggahan

TIPE_LABEL = {
    'foto': 'Foto karya',
    'audio': 'Rekaman suara',
    'video': 'Video',
    'dokumen': 'Dokumen',
    'link': 'Tautan proyek',
}

# Atribut accept pada <input type="file"> (hanya membantu pemilih berkas; server tetap memvalidasi)
TIPE_ACCEPT = {
    'foto': 'image/*',
    'audio': 'audio/*',
    'video': 'video/*',
    'dokumen': '.pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt',
}

MAKS_UKURAN_MB = {'foto': 15, 'audio': 25, 'video': 100, 'dokumen': 25}
MAKS_LAMPIRAN_PER_TIPE = 10
MAKS_LINK = 5
BATAS_TEKS = 2000        # jawaban refleksi
BATAS_RINGKASAN = 3000   # ringkasan karya
