from django.core.management.base import BaseCommand

from misi.models import Misi

# tingkat_min/tingkat_max = tingkat kelas 1-12 (cocok dengan Siswa.kelas lewat deteksi_tingkat).
MISI_AWAL = [
    {
        "slug": "tiga-daun-berbeda", "judul": "Tiga Daun Berbeda", "kategori": Misi.SAINS,
        "ringkasan": "Cari tiga daun dengan bentuk berbeda di halaman atau sekitar rumah.",
        "langkah": "Pergi ke halaman atau taman dekat rumah bersama orang dewasa.\nCari 3 daun yang bentuknya berbeda.\nLihat dan bandingkan: bentuk, tepi, dan urat daunnya.\nCatat atau foto ketiganya (daun tidak perlu dipetik).",
        "bahan": "Kertas dan pensil, atau kamera",
        "catatan_keselamatan": "Jangan menyentuh tanaman yang tidak dikenal. Tanyakan dulu ke orang dewasa.",
        "tingkat_min": 1, "tingkat_max": 3, "durasi_menit": 20, "min_catatan": 3,
        "pertanyaan_refleksi": "Daun mana yang paling unik menurutmu, dan kenapa?",
        "judul_kartu": "Pemburu Daun", "emoji_kartu": "🍃",
    },
    {
        "slug": "detektif-tanaman", "judul": "Detektif Tanaman: Siapa Paling Cepat Tumbuh?", "kategori": Misi.SAINS,
        "ringkasan": "Ukur dua tanaman selama seminggu dan buktikan tebakanmu.",
        "langkah": "Pilih 2 tanaman di halaman atau pot.\nTebak dulu: tanaman mana yang tumbuh lebih cepat?\nUkur tinggi keduanya pada hari ke-1, 3, 5, dan 7.\nCatat angkanya setiap kali mengukur.\nBandingkan dengan tebakanmu.",
        "bahan": "Penggaris atau meteran, kertas",
        "catatan_keselamatan": "Cuci tangan setelah menyentuh tanah atau tanaman.",
        "tingkat_min": 3, "tingkat_max": 7, "durasi_menit": 15, "min_catatan": 3,
        "label_angka": "Tinggi tanaman", "satuan_angka": "cm",
        "pertanyaan_refleksi": "Tebakanmu benar? Menurutmu kenapa tanaman itu tumbuh lebih cepat?",
        "judul_kartu": "Ilmuwan Cilik", "emoji_kartu": "🔬",
    },
    {
        "slug": "ukur-lima-benda", "judul": "Ukur Lima Benda di Rumah", "kategori": Misi.MATEMATIKA,
        "ringkasan": "Ukur benda dengan jengkal lalu dengan penggaris, dan bandingkan hasilnya.",
        "langkah": "Pilih 5 benda di rumah (buku, sendok, remote, dan lain-lain).\nUkur tiap benda dengan jengkal tanganmu.\nUkur lagi dengan penggaris dalam sentimeter.\nCatat hasilnya setiap kali.",
        "bahan": "Penggaris, kertas",
        "tingkat_min": 1, "tingkat_max": 5, "durasi_menit": 25, "min_catatan": 5,
        "label_angka": "Panjang benda", "satuan_angka": "cm",
        "pertanyaan_refleksi": "Kenapa ukuran jengkalmu dan jengkal temanmu bisa berbeda?",
        "judul_kartu": "Jagoan Ukur", "emoji_kartu": "📏",
    },
    {
        "slug": "wawancara-kakek-nenek", "judul": "Wawancara Kakek atau Nenek", "kategori": Misi.BAHASA,
        "ringkasan": "Tanyakan permainan apa yang dimainkan kakek atau nenek waktu kecil.",
        "langkah": "Pilih satu anggota keluarga yang lebih tua.\nSiapkan 3 pertanyaan, misalnya: \"Waktu kecil, permainan apa yang paling Kakek suka?\"\nDengarkan jawabannya dengan sabar.\nCatat cerita yang paling menarik.",
        "bahan": "Kertas dan pensil",
        "catatan_keselamatan": "Wawancara hanya dengan anggota keluarga atau orang yang dikenal baik.",
        "tingkat_min": 2, "tingkat_max": 7, "durasi_menit": 30, "min_catatan": 1, "misi_keluarga": True,
        "pertanyaan_refleksi": "Apa yang paling mengejutkan dari cerita mereka?",
        "judul_kartu": "Penjaga Cerita", "emoji_kartu": "🎙️",
    },
    {
        "slug": "resep-makanan-daerah", "judul": "Resep Makanan Khas Keluarga", "kategori": Misi.BUDAYA,
        "ringkasan": "Tanyakan nama makanan khas daerah dan cara membuatnya.",
        "langkah": "Tanyakan ke orang tua atau kakek-nenek: makanan khas apa yang sering dibuat keluarga?\nCatat nama makanan dan bahan utamanya.\nTanyakan cerita atau acara yang biasanya ada makanan itu.\nBantu menyiapkan bahan yang aman untukmu.",
        "bahan": "Kertas dan pensil",
        "catatan_keselamatan": "Pisau, kompor, dan minyak panas hanya dipegang orang dewasa.",
        "tingkat_min": 1, "tingkat_max": 7, "durasi_menit": 30, "min_catatan": 1, "misi_keluarga": True,
        "pertanyaan_refleksi": "Kenapa makanan ini penting bagi keluarga atau daerahmu?",
        "judul_kartu": "Penjelajah Rasa", "emoji_kartu": "🍲",
    },
    {
        "slug": "hitung-sampah-plastik", "judul": "Hitung Sampah Plastik Sehari", "kategori": Misi.LINGKUNGAN,
        "ringkasan": "Hitung berapa sampah plastik yang keluar dari rumahmu dalam satu hari.",
        "langkah": "Siapkan satu wadah khusus untuk sampah plastik hari ini.\nSetiap ada sampah plastik, masukkan ke wadah.\nMalam hari, hitung jumlahnya dan kelompokkan: kemasan, kantong, botol.\nCatat jumlahnya.",
        "bahan": "Wadah, kertas",
        "catatan_keselamatan": "Pakai sarung tangan atau cuci tangan sesudahnya. Jangan menyentuh benda tajam.",
        "tingkat_min": 2, "tingkat_max": 7, "durasi_menit": 20, "min_catatan": 1,
        "label_angka": "Jumlah sampah plastik", "satuan_angka": "buah",
        "pertanyaan_refleksi": "Sampah plastik mana yang bisa kita kurangi? Bagaimana caranya?",
        "judul_kartu": "Penjaga Bumi", "emoji_kartu": "🌍",
    },
    {
        "slug": "alat-musik-barang-bekas", "judul": "Alat Musik dari Barang Bekas", "kategori": Misi.KREATIF,
        "ringkasan": "Buat alat musik dari barang bekas yang aman, lalu foto atau ceritakan bunyinya.",
        "langkah": "Kumpulkan barang bekas yang aman (botol, kardus, karet gelang, biji-bijian).\nRancang alat musikmu: bagaimana bunyinya dihasilkan?\nBuat dan coba mainkan.\nFoto alatmu dan catat bahan yang dipakai.",
        "bahan": "Barang bekas bersih dan aman",
        "catatan_keselamatan": "Minta bantuan orang dewasa untuk memotong. Jangan memakai kaleng bertepi tajam.",
        "tingkat_min": 1, "tingkat_max": 7, "durasi_menit": 40, "min_catatan": 1,
        "pertanyaan_refleksi": "Apa yang membuat bunyi alat musikmu berubah-ubah?",
        "judul_kartu": "Musisi Kreatif", "emoji_kartu": "🎵",
    },
    {
        "slug": "kabar-senang-keluarga", "judul": "Kabar Senang Keluarga", "kategori": Misi.EMOSI,
        "ringkasan": "Tanyakan ke tiga anggota keluarga: apa yang bikin mereka senang hari ini?",
        "langkah": "Pilih 3 anggota keluarga.\nTanyakan satu per satu: \"Apa yang bikin kamu senang hari ini?\"\nDengarkan tanpa memotong.\nCatat jawaban masing-masing.",
        "bahan": "Kertas dan pensil",
        "tingkat_min": 1, "tingkat_max": 7, "durasi_menit": 15, "min_catatan": 3, "misi_keluarga": True,
        "pertanyaan_refleksi": "Apa yang kamu rasakan setelah mendengar kabar senang mereka?",
        "judul_kartu": "Pendengar Baik", "emoji_kartu": "💛",
    },
    {
        "slug": "serangga-di-sekitar", "judul": "Penjelajah Serangga", "kategori": Misi.SAINS,
        "ringkasan": "Amati serangga di sekitar rumah dari jarak aman dan gambar yang kamu lihat.",
        "langkah": "Duduk tenang di halaman selama 10 menit bersama orang dewasa.\nAmati serangga yang lewat tanpa menyentuhnya.\nGambar satu serangga: berapa kakinya, apa warnanya?\nCatat di mana dan apa yang sedang dilakukannya.",
        "bahan": "Kertas, pensil warna",
        "catatan_keselamatan": "Jangan menangkap atau menyentuh serangga. Beberapa bisa menggigit atau menyengat.",
        "tingkat_min": 1, "tingkat_max": 5, "durasi_menit": 20, "min_catatan": 1,
        "pertanyaan_refleksi": "Menurutmu, apa manfaat serangga itu bagi tanaman atau alam?",
        "judul_kartu": "Pengamat Serangga", "emoji_kartu": "🐞",
    },
    {
        "slug": "suhu-rumah-seharian", "judul": "Suhu Rumah Seharian", "kategori": Misi.MATEMATIKA,
        "ringkasan": "Catat suhu ruangan pada pagi, siang, dan malam lalu lihat polanya.",
        "langkah": "Minta izin memakai termometer ruangan.\nBaca suhu di tempat yang sama pada pagi, siang, dan malam.\nCatat angkanya setiap kali.\nLihat grafiknya: kapan paling panas, kapan paling dingin?",
        "bahan": "Termometer ruangan digital",
        "catatan_keselamatan": "Jangan memakai termometer kaca berisi raksa. Pakai termometer digital.",
        "tingkat_min": 4, "tingkat_max": 7, "durasi_menit": 10, "min_catatan": 3,
        "label_angka": "Suhu ruangan", "satuan_angka": "°C",
        "pertanyaan_refleksi": "Kenapa suhu rumah berubah sepanjang hari?",
        "judul_kartu": "Pengamat Cuaca", "emoji_kartu": "🌡️",
    },
    {
        "slug": "peta-rumah-sederhana", "judul": "Peta Rumah Sederhana", "kategori": Misi.MATEMATIKA,
        "ringkasan": "Gambar peta satu ruangan di rumahmu lengkap dengan ukuran langkah.",
        "langkah": "Pilih satu ruangan, misalnya kamar atau ruang tamu.\nHitung langkah kakimu untuk panjang dan lebar ruangan.\nGambar denah ruangan di kertas, tandai pintu dan perabot.\nCatat jumlah langkah untuk panjang dan lebarnya.",
        "bahan": "Kertas, pensil",
        "tingkat_min": 2, "tingkat_max": 6, "durasi_menit": 30, "min_catatan": 2,
        "label_angka": "Jumlah langkah", "satuan_angka": "langkah",
        "pertanyaan_refleksi": "Kalau langkah kakimu lebih besar, apa yang akan berubah dari petamu?",
        "judul_kartu": "Pembuat Peta", "emoji_kartu": "🗺️",
    },
    {
        "slug": "bahasa-daerah-hari-ini", "judul": "Kata Baru dari Bahasa Daerah", "kategori": Misi.BUDAYA,
        "ringkasan": "Pelajari tiga kata bahasa daerah dari anggota keluarga dan pakai dalam kalimat.",
        "langkah": "Tanyakan ke anggota keluarga tiga kata dalam bahasa daerah.\nCatat kata, arti, dan cara membacanya.\nPakai masing-masing kata dalam satu kalimat.\nAjarkan satu kata itu kepada orang lain di rumah.",
        "bahan": "Kertas dan pensil",
        "tingkat_min": 1, "tingkat_max": 7, "durasi_menit": 20, "min_catatan": 3, "misi_keluarga": True,
        "pertanyaan_refleksi": "Kata mana yang paling kamu suka, dan kenapa?",
        "judul_kartu": "Penjaga Bahasa", "emoji_kartu": "🗣️",
    },
]


class Command(BaseCommand):
    help = "Isi atau perbarui 12 misi awal. Aman dijalankan berulang kali."

    def handle(self, *args, **options):
        dibuat = diperbarui = 0
        for data in MISI_AWAL:
            data = dict(data)
            slug = data.pop("slug")
            _, baru = Misi.objects.update_or_create(slug=slug, defaults=data)
            dibuat += baru
            diperbarui += not baru
        self.stdout.write(self.style.SUCCESS(f"Misi: {dibuat} dibuat, {diperbarui} diperbarui."))
