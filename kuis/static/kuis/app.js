// ==========================================
// 1. DATA PRESETS & STATE
// ==========================================

const PRESETS = {
  math: [
    { q: "Berapakah hasil dari 12 × 8?", a: ["86", "96", "108", "88"], correct: 1, hint: "Perkalian mendekati 100" },
    { q: "Jika 3x + 5 = 20, berapakah nilai x?", a: ["4", "5", "6", "3"], correct: 1, hint: "Kurangi 5 dari 20 lalu bagi 3" },
    { q: "Turunan pertama dari fungsi f(x) = 4x² adalah...", a: ["8x", "4x", "8x²", "2x"], correct: 0, hint: "Gunakan rumus n * ax^(n-1)" },
    { q: "Berapakah nilai dari √144 + √81?", a: ["20", "21", "22", "25"], correct: 1, hint: "12 + 9" },
    { q: "Berapa jumlah sudut dalam segitiga?", a: ["90°", "180°", "360°", "270°"], correct: 1, hint: "Setengah dari lingkaran" },
    { q: "Nilai Sin 90° adalah...", a: ["0", "1", "0.5", "√2"], correct: 1, hint: "Nilai maksimum fungsi sinus" },
    { q: "Logaritma: Berapakah ²log 8?", a: ["2", "3", "4", "8"], correct: 1, hint: "2 pangkat berapa sama dengan 8?" },
    { q: "Berapa diagonal bidang pada kubus?", a: ["6", "12", "8", "4"], correct: 1, hint: "Sama dengan jumlah rusuk kubus" },
    { q: "Matriks: Determinan matriks [[2, 3], [1, 4]] adalah...", a: ["5", "8", "11", "6"], correct: 0, hint: "(2*4) - (3*1)" },
    { q: "Modus dari data [4, 5, 5, 6, 7, 5, 8] adalah...", a: ["4", "5", "6", "7"], correct: 1, hint: "Angka yang paling sering muncul" },
    { q: "Berapakah keliling lingkaran dengan jari-jari 7 cm? (π = 22/7)", a: ["44 cm", "88 cm", "154 cm", "22 cm"], correct: 0, hint: "Gunakan rumus 2 * π * r" },
    { q: "Hasil dari 2⁵ adalah...", a: ["16", "32", "64", "128"], correct: 1, hint: "2 dikalikan 5 kali" },
    { q: "Suku ke-10 dari barisan aritmatika 2, 5, 8, 11... adalah...", a: ["27", "29", "31", "33"], correct: 1, hint: "Un = a + (n-1)b" },
    { q: "Integral dari 2x dx adalah...", a: ["x² + C", "2x² + C", "x + C", "x³ + C"], correct: 0, hint: "Turunan dari x² adalah 2x" },
    { q: "Peluang melempar 1 koin muncul angka adalah...", a: ["1/4", "1/2", "3/4", "1"], correct: 1, hint: "Ada 2 kemungkinan sisi koin" }
  ],
  general: [
    { q: "Apa ibu kota dari negara Prancis?", a: ["Lyon", "Marseille", "Paris", "Nice"], correct: 2, hint: "Kota Menara Eiffel" },
    { q: "Planet manakah yang dikenal sebagai Planet Merah?", a: ["Venus", "Mars", "Yupiter", "Saturnus"], correct: 1, hint: "Planet ke-4 dari Matahari" },
    { q: "Unsur kimia dengan lambang 'Au' adalah...", a: ["Perak", "Emas", "Aluminium", "Tembaga"], correct: 1, hint: "Logam mulia bernilai tinggi" },
    { q: "Di benua manakah Gurun Sahara berada?", a: ["Asia", "Afrika", "Australia", "Amerika"], correct: 1, hint: "Benua tempat Piramida Mesir" },
    { q: "Tahun berapakah Indonesia memproklamasikan kemerdekaannya?", a: ["1942", "1945", "1950", "1928"], correct: 1, hint: "Tahun berakhirnya PD II di Pasifik" },
    { q: "Hewan mamalia terbesar di dunia adalah...", a: ["Gajah", "Paus Biru", "Hiu Paus", "Jerapah"], correct: 1, hint: "Mamalia laut raksasa" },
    { q: "Siapa pelukis lukisan legendaris Mona Lisa?", a: ["Van Gogh", "Leonardo da Vinci", "Picasso", "Monet"], correct: 1, hint: "Genius asal Italia Renaissance" },
    { q: "Mata uang resmi negara Jepang adalah...", a: ["Yuan", "Won", "Yen", "Ringgit"], correct: 2, hint: "Berawalan huruf Y" },
    { q: "Gas paling dominan di atmosfer bumi adalah...", a: ["Oksigen", "Karbondioksida", "Nitrogen", "Hidrogen"], correct: 2, hint: "Sekitar 78% dari udara" },
    { q: "Samudera terluas di bumi adalah...", a: ["Atlantik", "Hindia", "Pasifik", "Arktik"], correct: 2, hint: "Membentang antara Asia dan Amerika" },
    { q: "Berapa jumlah provinsi di Indonesia saat ini?", a: ["34", "38", "37", "35"], correct: 1, hint: "Termasuk pemekaran Papua" },
    { q: "Penulis drama Romeo and Juliet adalah...", a: ["Shakespeare", "Dickens", "Mark Twain", "Tolstoy"], correct: 0, hint: "Sastrawan Inggris abad ke-16" },
    { q: "Alat untuk mengukur gempa bumi dinamakan...", a: ["Barometer", "Seismograf", "Termometer", "Anemometer"], correct: 1, hint: "Mencatat gelombang seismik" },
    { q: "Candi Borobudur terletak di provinsi...", a: ["Jawa Timur", "Jawa Tengah", "Yogyakarta", "Jawa Barat"], correct: 1, hint: "Dekat kota Magelang" },
    { q: "Siapakah penemu telepon pertama kali?", a: ["Thomas Edison", "Alexander Graham Bell", "Nikola Tesla", "Marconi"], correct: 1, hint: "Paten diajukan tahun 1876" }
  ],
  webdev: [
    { q: "Bahasa pemrograman native utama di web browser adalah...", a: ["Python", "Java", "JavaScript", "C++"], correct: 2, hint: "Berjalan langsung di V8 Engine" },
    { q: "Apa kepanjangan dari CSS?", a: ["Cascading Style Sheets", "Computer Style System", "Creative Sheet Styling", "Central Style Logic"], correct: 0, hint: "Digunakan untuk tampilan web" },
    { q: "Framework JavaScript React dikembangkan oleh...", a: ["Google", "Meta (Facebook)", "Microsoft", "Amazon"], correct: 1, hint: "Raksasa media sosial" },
    { q: "Protokol standar aman enkripsi web adalah...", a: ["HTTP", "HTTPS", "FTP", "SSH"], correct: 1, hint: "Menggunakan port 443" },
    { q: "Struktur data LIFO (Last In First Out) dinamakan...", a: ["Queue", "Stack", "Array", "Map"], correct: 1, hint: "Seperti tumpukan piring" },
    { q: "Method HTTP untuk mengirim data form baru adalah...", a: ["GET", "POST", "PUT", "DELETE"], correct: 1, hint: "Menciptakan resource baru" },
    { q: "Sistem kontrol versi (Version Control) terpopuler adalah...", a: ["Git", "SVN", "Mercurial", "Docker"], correct: 0, hint: "Diciptakan oleh Linus Torvalds" },
    { q: "Format pertukaran data ringan antar server & client adalah...", a: ["XML", "JSON", "CSV", "YAML"], correct: 1, hint: "JavaScript Object Notation" },
    { q: "State Management bawaan React hooks untuk state lokal adalah...", a: ["useState", "useEffect", "useContext", "useReducer"], correct: 0, hint: "Mengembalikan [state, setState]" },
    { q: "Dalam CSS, property untuk mengatur jarak di dalam elemen adalah...", a: ["margin", "padding", "gap", "border"], correct: 1, hint: "Inner spacing" },
    { q: "Database NoSQL berbasis dokumen terpopuler adalah...", a: ["PostgreSQL", "MongoDB", "MySQL", "Redis"], correct: 1, hint: "Menyimpan format BSON" },
    { q: "Database In-Memory Cache tercepat adalah...", a: ["SQLite", "Redis", "Oracle", "MariaDB"], correct: 1, hint: "Key-value store di RAM" },
    { q: "Teknologi komunikasi dua arah real-time web dinamakan...", a: ["REST API", "WebSocket", "GraphQL", "SOAP"], correct: 1, hint: "Digunakan pada Live Battle ini" },
    { q: "Command CLI Node.js untuk menginstall package adalah...", a: ["npm install", "node start", "git clone", "composer req"], correct: 0, hint: "Node Package Manager" },
    { q: "Komponen CSS utility-first populer saat ini adalah...", a: ["Bootstrap", "Tailwind CSS", "Bulma", "Foundation"], correct: 1, hint: "Digunakan pada antarmuka Betsora ini" }
  ]
};

const MILLIONAIRE_LADDER = [
  { level: 1, prize: "100 Pts", safe: false },
  { level: 2, prize: "200 Pts", safe: false },
  { level: 3, prize: "300 Pts", safe: false },
  { level: 4, prize: "500 Pts", safe: false },
  { level: 5, prize: "1,000 Pts", safe: true },
  { level: 6, prize: "2,000 Pts", safe: false },
  { level: 7, prize: "4,000 Pts", safe: false },
  { level: 8, prize: "8,000 Pts", safe: false },
  { level: 9, prize: "16,000 Pts", safe: false },
  { level: 10, prize: "32,000 Pts", safe: true },
  { level: 11, prize: "64,000 Pts", safe: false },
  { level: 12, prize: "125,000 Pts", safe: false },
  { level: 13, prize: "250,000 Pts", safe: false },
  { level: 14, prize: "500,000 Pts", safe: false },
  { level: 15, prize: "1,000,000 Pts", safe: true }
];

const CATEGORY_NAMES = {
  math: 'Matematika',
  general: 'Pengetahuan Umum',
  webdev: 'Web Development',
  custom: 'Kuis Kustom'
};

// App State
let activePresetKey = 'math';
let customQuestions = [];
let currentQuestions = [];
let playMode = 'millionaire';
let currentQIdx = 0;
let timerInterval = null;
let soundEnabled = true;
let viewAktif = 'play';       // tampilan yang sedang dibuka (play / builder / analytics / spec)

// Pengaturan waktu & status permainan.
// status: idle (belum dimulai) | running | paused | over
const WAKTU_PILIHAN = [15, 20, 30, 45, 60, 90, 120];
const WAKTU_DEFAULT = { millionaire: 30, kahoot: 15 };
const WAKTU_MIN = 5;
const WAKTU_MAKS = 600;
const WAKTU_KUNCI = 'betsora_kuis_waktu';
let waktuSetelan = muatWaktuSetelan();   // detik per soal; 0 = tanpa batas waktu
let mState = 'idle', mLimit = 30, mTimeLeft = 30, mMenjawab = false;
let kState = 'idle', kLimit = 15, kMenjawab = false;

// Millionaire State
let mLifelines = { '5050': true, hint: true, friend: true };
let mCurrentPrize = "0 Pts";
let mSafePrize = "0 Pts";

// Kahoot State
let kScore = 0;
let kStreak = 0;
let kTimeLeft = 15;

// ==========================================
// 1b. AUDIO & UTILITIES
// ==========================================

const audioCtx = new (window.AudioContext || window.webkitAudioContext)();

function playSound(type) {
  if (!soundEnabled) return;
  try {
    if (audioCtx.state === 'suspended') audioCtx.resume();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    const now = audioCtx.currentTime;

    if (type === 'click') {
      osc.frequency.setValueAtTime(500, now);
      gain.gain.setValueAtTime(0.08, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.05);
      osc.start(now); osc.stop(now + 0.05);
    } else if (type === 'correct') {
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(523.25, now);
      osc.frequency.setValueAtTime(659.25, now + 0.08);
      osc.frequency.setValueAtTime(783.99, now + 0.16);
      gain.gain.setValueAtTime(0.12, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
      osc.start(now); osc.stop(now + 0.35);
    } else if (type === 'wrong') {
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(220, now);
      osc.frequency.setValueAtTime(160, now + 0.1);
      gain.gain.setValueAtTime(0.15, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
      osc.start(now); osc.stop(now + 0.3);
    } else if (type === 'tick') {
      osc.frequency.setValueAtTime(900, now);
      gain.gain.setValueAtTime(0.02, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.03);
      osc.start(now); osc.stop(now + 0.03);
    } else if (type === 'lifeline') {
      osc.type = 'sine';
      osc.frequency.setValueAtTime(300, now);
      osc.frequency.exponentialRampToValueAtTime(800, now + 0.2);
      gain.gain.setValueAtTime(0.1, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
      osc.start(now); osc.stop(now + 0.25);
    }
  } catch (e) {
    console.log("Audio error", e);
  }
}

function toggleSound() {
  soundEnabled = !soundEnabled;
  document.getElementById('soundIcon').className = soundEnabled
    ? 'fa-solid fa-volume-high text-sm'
    : 'fa-solid fa-volume-xmark text-sm text-red-400';
}

function escapeHTML(str) {
  return String(str).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

// ==========================================
// 1c. PENGATURAN WAKTU (manual) & KONTROL TIMER
// ==========================================

function waktuValid(v) {
  return Number.isInteger(v) && (v === 0 || (v >= WAKTU_MIN && v <= WAKTU_MAKS));
}

function muatWaktuSetelan() {
  const hasil = Object.assign({}, WAKTU_DEFAULT);
  try {
    const tersimpan = JSON.parse(localStorage.getItem(WAKTU_KUNCI) || '{}');
    ['millionaire', 'kahoot'].forEach(m => { if (waktuValid(tersimpan[m])) hasil[m] = tersimpan[m]; });
  } catch (e) { /* penyimpanan browser tidak tersedia: pakai bawaan */ }
  return hasil;
}

function simpanWaktuSetelan() {
  try { localStorage.setItem(WAKTU_KUNCI, JSON.stringify(waktuSetelan)); } catch (e) { /* abaikan */ }
}

function labelWaktu(detik) {
  return detik === 0 ? 'Tanpa batas waktu' : detik + ' detik per soal';
}

function setWaktu(mode, detik) {
  if (!waktuValid(detik)) return;
  playSound('click');
  waktuSetelan[mode] = detik;
  simpanWaktuSetelan();
  renderTimePickers();
}

function setWaktuKustom(mode, inputId) {
  const el = document.getElementById(inputId);
  const detik = parseInt(el.value, 10);
  if (!waktuValid(detik) || detik === 0) {
    alert(`Isi waktu antara ${WAKTU_MIN} dan ${WAKTU_MAKS} detik.`);
    el.focus();
    return;
  }
  setWaktu(mode, detik);
}

function renderTimePicker(containerId, mode) {
  const box = document.getElementById(containerId);
  if (!box) return;
  const aktif = waktuSetelan[mode];
  const warna = mode === 'kahoot'
    ? 'bg-purple-600 text-white border-purple-400'
    : 'bg-amber-500 text-slate-950 border-amber-400';
  const chip = (nilai, label) => {
    const kelas = aktif === nilai
      ? warna
      : 'bg-slate-900 text-slate-300 border-slate-700 hover:border-slate-400';
    return `<button type="button" onclick="setWaktu('${mode}', ${nilai})" class="px-3 py-1.5 rounded-lg border text-xs font-bold transition ${kelas}">${label}</button>`;
  };
  const inputId = containerId + 'Kustom';
  const kustomNilai = (aktif !== 0 && !WAKTU_PILIHAN.includes(aktif)) ? aktif : '';
  box.innerHTML = `
    <div class="flex flex-wrap gap-1.5">
      ${WAKTU_PILIHAN.map(n => chip(n, n + ' dtk')).join('')}
      ${chip(0, '∞ Tanpa batas')}
    </div>
    <div class="flex items-center gap-2 mt-2">
      <input type="number" id="${inputId}" min="${WAKTU_MIN}" max="${WAKTU_MAKS}" value="${kustomNilai}" placeholder="Kustom (detik)"
        onkeydown="if(event.key==='Enter'){setWaktuKustom('${mode}','${inputId}')}"
        class="w-36 bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-white text-xs focus:outline-none focus:border-indigo-500">
      <button type="button" onclick="setWaktuKustom('${mode}','${inputId}')" class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold transition">Pakai</button>
    </div>
    <p class="text-[11px] text-slate-400 mt-2">Dipilih: <strong class="text-white">${labelWaktu(aktif)}</strong></p>`;
}

function renderTimePickers() {
  renderTimePicker('mTimePicker', 'millionaire');
  renderTimePicker('kTimePicker', 'kahoot');
}

function stopTimer() {
  clearInterval(timerInterval);
  timerInterval = null;
}

// Jeda: dipakai tombol Jeda dan otomatis saat pengguna pindah ke Game Builder / Analytics / Spec.
function pauseGame() {
  if (playMode === 'millionaire' && mState === 'running' && !mMenjawab) {
    stopTimer();
    mState = 'paused';
    syncMUi();
  } else if (playMode === 'kahoot' && kState === 'running' && !kMenjawab) {
    stopTimer();
    kState = 'paused';
    syncKUi();
  }
}

function lanjutkanGame() {
  playSound('click');
  if (playMode === 'millionaire' && mState === 'paused') {
    mState = 'running';
    syncMUi();
    jalankanTimerM();
  } else if (playMode === 'kahoot' && kState === 'paused') {
    kState = 'running';
    syncKUi();
    jalankanTimerK();
  }
}

// ==========================================
// 1d. NAVIGATION
// ==========================================

function switchView(viewName) {
  playSound('click');
  viewAktif = viewName;
  if (viewName !== 'play') pauseGame();   // timer tidak boleh jalan saat mengedit kuis
  ['viewPlay', 'viewBuilder', 'viewAnalytics', 'viewSpec'].forEach(v => {
    document.getElementById(v).classList.add('hidden');
  });

  const navBtns = { play: 'navPlay', builder: 'navBuilder', analytics: 'navAnalytics', spec: 'navSpec' };
  Object.keys(navBtns).forEach(k => {
    const btn = document.getElementById(navBtns[k]);
    if (k === viewName) {
      btn.className = "nav-tab px-3.5 py-1.5 rounded-lg text-xs font-semibold transition flex items-center space-x-2 bg-indigo-600 text-white shadow-md";
    } else {
      btn.className = "nav-tab px-3.5 py-1.5 rounded-lg text-xs font-semibold transition flex items-center space-x-2 text-slate-400 hover:text-white hover:bg-slate-800";
    }
  });

  if (viewName === 'play') document.getElementById('viewPlay').classList.remove('hidden');
  if (viewName === 'builder') document.getElementById('viewBuilder').classList.remove('hidden');
  if (viewName === 'analytics') {
    document.getElementById('viewAnalytics').classList.remove('hidden');
    initCharts();
  }
  if (viewName === 'spec') document.getElementById('viewSpec').classList.remove('hidden');
}

function toggleMobileMenu() {
  document.getElementById('mobileMenu').classList.toggle('hidden');
}


function setPlayMode(mode) {
  playSound('click');
  playMode = mode;
  stopTimer();
  mState = 'idle';
  kState = 'idle';
  document.getElementById('btnModeMillionaire').className = mode === 'millionaire'
    ? 'flex-1 md:flex-initial px-4 py-2 rounded-lg text-xs font-bold transition flex items-center justify-center space-x-2 bg-amber-500 text-slate-950 shadow-md'
    : 'flex-1 md:flex-initial px-4 py-2 rounded-lg text-xs font-bold transition flex items-center justify-center space-x-2 text-slate-400 hover:text-white';
  document.getElementById('btnModeKahoot').className = mode === 'kahoot'
    ? 'flex-1 md:flex-initial px-4 py-2 rounded-lg text-xs font-bold transition flex items-center justify-center space-x-2 bg-purple-600 text-white shadow-md'
    : 'flex-1 md:flex-initial px-4 py-2 rounded-lg text-xs font-bold transition flex items-center justify-center space-x-2 text-slate-400 hover:text-white';

  if (mode === 'millionaire') {
    document.getElementById('playMillionaire').classList.remove('hidden');
    document.getElementById('playKahoot').classList.add('hidden');
    siapkanMillionaire();
  } else {
    document.getElementById('playMillionaire').classList.add('hidden');
    document.getElementById('playKahoot').classList.remove('hidden');
    resetKahootGame();
  }
}

// ==========================================
// 2. MILLIONAIRE CHALLENGE ENGINE
// ==========================================

function getMillionaireTotal() {
  return Math.min(currentQuestions.length, 15);
}

// Petakan indeks soal -> indeks tangga hadiah (0-14)
function getLadderIdx(qIdx) {
  const n = getMillionaireTotal();
  if (n >= 15) return qIdx;
  if (n <= 1) return 14;
  return Math.round(qIdx * 14 / (n - 1));
}

function updateMTimerLabel() {
  document.getElementById('mTimer').innerText = mLimit ? mTimeLeft : '∞';
  document.getElementById('mTimerUnit').innerText = mLimit ? 's' : '';
}

// Menyesuaikan layar dengan status permainan: layar "Siap", layar "Dijeda", atau soal terbuka.
function syncMUi() {
  const ov = document.getElementById('mOverlay');
  const siap = mState === 'idle';
  if (siap || mState === 'paused') {
    document.getElementById('mOverlayTitle').innerText = siap ? 'Siap Bermain?' : 'Game Dijeda';
    document.getElementById('mOverlayIcon').className = siap ? 'fa-solid fa-circle-play' : 'fa-solid fa-pause';
    document.getElementById('mOverlayBtn').innerText = siap ? '▶ MULAI GAME' : '▶ LANJUTKAN';
    document.getElementById('mTimeSetting').classList.toggle('hidden', !siap);
    document.getElementById('mOverlayHint').innerText = siap
      ? 'Timer baru berjalan setelah tombol Mulai ditekan.'
      : 'Waktu berhenti. Sisa waktu soal ini tetap tersimpan.';
    document.getElementById('mOverlayInfo').innerText =
      `${getActiveCategory()} · ${getMillionaireTotal()} soal`;
    ov.classList.remove('hidden');
  } else {
    ov.classList.add('hidden');
  }
  document.getElementById('mPauseBtn').classList.toggle('hidden', mState !== 'running');
}

function aksiOverlayMillionaire() {
  if (mState === 'idle') mulaiMillionaire();
  else lanjutkanGame();
}

// Menyiapkan permainan baru. TIDAK menjalankan timer: timer baru jalan setelah tombol Mulai.
function siapkanMillionaire() {
  stopTimer();
  currentQuestions = getActiveQuestions();
  mState = 'idle';
  mMenjawab = false;
  mLimit = waktuSetelan.millionaire;
  mTimeLeft = mLimit;
  renderTimePickers();

  if (!currentQuestions || currentQuestions.length === 0) {
    syncMUi();
    return;
  }

  currentQIdx = 0;
  mLifelines = { '5050': true, hint: true, friend: true };
  mCurrentPrize = "0 Pts";
  mSafePrize = "0 Pts";
  document.getElementById('mLevelTotal').innerText = getMillionaireTotal();

  ['life5050', 'lifeHint', 'lifeFriend'].forEach(id => {
    const btn = document.getElementById(id);
    btn.disabled = false;
    btn.classList.remove('opacity-30', 'line-through');
  });

  renderLadder();
  loadMillionaireQuestion();
  syncMUi();
}

function mulaiMillionaire() {
  if (!currentQuestions || currentQuestions.length === 0) {
    alert('Kuis ini belum punya soal.');
    return;
  }
  playSound('click');
  mLimit = waktuSetelan.millionaire;   // batas waktu dikunci saat game dimulai
  mTimeLeft = mLimit;
  mState = 'running';
  syncMUi();
  jalankanTimerM();
}

function jalankanTimerM() {
  stopTimer();
  updateMTimerLabel();
  if (!mLimit) return;   // tanpa batas waktu
  timerInterval = setInterval(() => {
    mTimeLeft--;
    updateMTimerLabel();
    if (mTimeLeft <= 5 && mTimeLeft > 0) playSound('tick');
    if (mTimeLeft <= 0) {
      stopTimer();
      gameOverMillionaire("Waktu Habis!");
    }
  }, 1000);
}

function renderLadder() {
  const container = document.getElementById('mLadderContainer');
  container.innerHTML = '';
  MILLIONAIRE_LADDER.forEach((item, idx) => {
    const row = document.createElement('div');
    row.id = `mLadderRow_${idx}`;
    row.className = `flex justify-between items-center px-3 py-1 rounded-lg border transition ${
      item.safe ? 'border-amber-500/40 text-amber-400 bg-amber-500/5' : 'border-transparent text-slate-400'
    }`;
    row.innerHTML = `<span>L${item.level}.</span><span>${item.prize}</span>`;
    container.appendChild(row);
  });
}

// Menampilkan soal. Timer hanya ikut berjalan bila game sedang berstatus "running".
function loadMillionaireQuestion() {
  closeLifelineBox();
  stopTimer();
  mMenjawab = false;

  const total = getMillionaireTotal();
  if (currentQIdx >= total) {
    mState = 'over';
    syncMUi();
    showResultModal("SELAMAT! ANDA JUTAWAN!", mCurrentPrize, `Sempurna! Berhasil menjawab seluruh ${total} level!`);
    return;
  }

  const q = currentQuestions[currentQIdx];
  const ladderIdx = getLadderIdx(currentQIdx);
  document.getElementById('mLevelNum').innerText = currentQIdx + 1;
  document.getElementById('mQuestionText').innerText = q.q;
  document.getElementById('mCategoryBadge').innerText = 'Kategori: ' + getActiveCategory();

  MILLIONAIRE_LADDER.forEach((_, idx) => {
    const row = document.getElementById(`mLadderRow_${idx}`);
    if (!row) return;
    if (idx === ladderIdx) {
      row.className = "flex justify-between items-center px-3 py-1 rounded-lg font-black bg-amber-500 text-slate-950 shadow scale-105 transition";
    } else if (idx < ladderIdx) {
      row.className = "flex justify-between items-center px-3 py-1 rounded-lg text-emerald-400 font-bold opacity-60";
    } else {
      const isSafe = MILLIONAIRE_LADDER[idx].safe;
      row.className = `flex justify-between items-center px-3 py-1 rounded-lg ${isSafe ? 'border border-amber-500/40 text-amber-400' : 'text-slate-400'}`;
    }
  });

  q.a.forEach((opt, idx) => {
    const btn = document.getElementById(`mAns${idx}`);
    btn.disabled = false;
    btn.style.visibility = 'visible';
    btn.className = "m-ans-btn group p-4 rounded-2xl bg-slate-900/80 border border-slate-800 hover:border-amber-400 hover:bg-indigo-950/50 text-left transition flex items-center space-x-3";
    btn.querySelector('.m-ans-text').innerText = opt;
  });

  mTimeLeft = mLimit;
  updateMTimerLabel();
  if (mState === 'running') {
    if (viewAktif !== 'play') {   // pemain sedang di Game Builder: tahan timer sampai kembali
      mState = 'paused';
      syncMUi();
    } else {
      jalankanTimerM();
    }
  }
}

function selectMillionaireAnswer(selectedIdx) {
  if (mState !== 'running' || mMenjawab) return;
  mMenjawab = true;
  stopTimer();
  playSound('click');
  const q = currentQuestions[currentQIdx];
  const selectedBtn = document.getElementById(`mAns${selectedIdx}`);

  for (let i = 0; i < 4; i++) document.getElementById(`mAns${i}`).disabled = true;

  selectedBtn.className = "m-ans-btn group p-4 rounded-2xl bg-amber-500/20 border-2 border-amber-400 text-amber-300 text-left flex items-center space-x-3 animate-pulse";

  setTimeout(() => {
    if (selectedIdx === q.correct) {
      playSound('correct');
      selectedBtn.className = "m-ans-btn group p-4 rounded-2xl bg-emerald-500/20 border-2 border-emerald-400 text-emerald-300 text-left flex items-center space-x-3";
      const reached = MILLIONAIRE_LADDER[getLadderIdx(currentQIdx)];
      mCurrentPrize = reached.prize;
      if (reached.safe) mSafePrize = reached.prize;

      setTimeout(() => {
        currentQIdx++;
        loadMillionaireQuestion();
      }, 1200);
    } else {
      playSound('wrong');
      selectedBtn.className = "m-ans-btn group p-4 rounded-2xl bg-red-500/20 border-2 border-red-500 text-red-300 text-left flex items-center space-x-3";
      document.getElementById(`mAns${q.correct}`).className = "m-ans-btn group p-4 rounded-2xl bg-emerald-500/20 border-2 border-emerald-400 text-emerald-300 text-left flex items-center space-x-3";

      setTimeout(() => {
        gameOverMillionaire("Jawaban Kurang Tepat!");
      }, 1500);
    }
  }, 1200);
}

function useLifeline(type) {
  if (mState !== 'running' || !mLifelines[type]) return;
  mLifelines[type] = false;
  playSound('lifeline');

  const btnMap = { '5050': 'life5050', hint: 'lifeHint', friend: 'lifeFriend' };
  document.getElementById(btnMap[type]).disabled = true;
  document.getElementById(btnMap[type]).classList.add('opacity-30', 'line-through');

  const q = currentQuestions[currentQIdx];

  if (type === '5050') {
    let indices = [0, 1, 2, 3].filter(i => i !== q.correct);
    indices.sort(() => Math.random() - 0.5);
    indices.slice(0, 2).forEach(i => {
      document.getElementById(`mAns${i}`).style.visibility = 'hidden';
    });
  } else if (type === 'hint') {
    showLifelineBox("Petunjuk Soal (AI Hint)", `💡 ${escapeHTML(q.hint || 'Perhatikan opsi dengan cermat!')}`);
  } else if (type === 'friend') {
    const optionLetter = ['A', 'B', 'C', 'D'][q.correct];
    showLifelineBox("Tanya Teman / Diskusi", `💬 Teman sekelas Anda berbisik: "Saya yakin 85% jawabannya adalah opsi <strong>${optionLetter}</strong> (${escapeHTML(q.a[q.correct])})!"`);
  }
}

function showLifelineBox(title, content) {
  document.getElementById('lifelineTitle').innerHTML = title;
  document.getElementById('lifelineContent').innerHTML = content;
  document.getElementById('lifelineBox').classList.remove('hidden');
}

function closeLifelineBox() {
  document.getElementById('lifelineBox').classList.add('hidden');
}

function quitMillionaireEarly() {
  if (mState !== 'running') return;
  if (confirm(`Apakah Anda yakin ingin berhenti sekarang dan mengamankan ${mCurrentPrize}?`)) {
    gameOverMillionaire("Anda Memutuskan Berhenti!");
  }
}

function gameOverMillionaire(reason) {
  stopTimer();
  mState = 'over';
  syncMUi();
  const quit = reason.includes("Berhenti");
  const finalPrize = quit ? mCurrentPrize : mSafePrize;
  showResultModal(reason, finalPrize, `Pencapaian: Level ${currentQIdx + 1} dari ${getMillionaireTotal()}`);
}

// ==========================================
// 3. LIVE QUIZ BATTLE (KAHOOT STYLE)
// ==========================================

function updateKTimerLabel() {
  document.getElementById('kTimer').innerText = kLimit ? kTimeLeft : '∞';
  document.getElementById('kTimerBar').style.width = kLimit ? `${(kTimeLeft / kLimit) * 100}%` : '100%';
}

function syncKUi() {
  document.getElementById('kSetupBar').classList.toggle('hidden', kState !== 'idle');
  document.getElementById('kOverlay').classList.toggle('hidden', kState !== 'paused');
  document.getElementById('kPauseBtn').classList.toggle('hidden', kState !== 'running');
  const mulai = document.getElementById('kStartBtn');
  mulai.disabled = kState !== 'idle';
  mulai.classList.toggle('opacity-40', kState !== 'idle');
  mulai.classList.toggle('pointer-events-none', kState !== 'idle');
}

function resetKahootGame() {
  stopTimer();
  kScore = 0;
  kStreak = 0;
  currentQIdx = 0;
  kState = 'idle';
  kMenjawab = false;
  kLimit = waktuSetelan.kahoot;
  kTimeLeft = kLimit;
  document.getElementById('kScore').innerText = '0';
  document.getElementById('kStreakBadge').classList.add('hidden');
  document.getElementById('kQuestionText').innerText = "Atur waktu per soal, lalu klik 'MULAI LIVE BATTLE' untuk mensimulasikan permainan Kahoot bersama siswa!";
  document.getElementById('lbUserPoints').innerText = '0 Pts';
  for (let i = 0; i < 4; i++) document.getElementById(`kAns${i}`).disabled = true;
  updateKTimerLabel();
  renderTimePickers();
  syncKUi();
}

function startKahootGame() {
  if (kState !== 'idle') return;
  currentQuestions = getActiveQuestions();
  if (!currentQuestions || currentQuestions.length === 0) {
    alert('Kuis ini belum punya soal.');
    return;
  }
  playSound('click');
  kLimit = waktuSetelan.kahoot;   // batas waktu dikunci saat game dimulai
  currentQIdx = 0;
  kScore = 0;
  kStreak = 0;
  kState = 'running';
  document.getElementById('kScore').innerText = '0';
  document.getElementById('lbUserPoints').innerText = '0 Pts';
  updateKahootStreak();
  syncKUi();
  loadKahootQuestion();
}

function jalankanTimerK() {
  stopTimer();
  updateKTimerLabel();
  if (!kLimit) return;   // tanpa batas waktu
  timerInterval = setInterval(() => {
    kTimeLeft--;
    updateKTimerLabel();
    if (kTimeLeft <= 3 && kTimeLeft > 0) playSound('tick');

    if (kTimeLeft <= 0) {
      stopTimer();
      kMenjawab = true;
      playSound('wrong');
      kStreak = 0;
      updateKahootStreak();
      setTimeout(() => {
        currentQIdx++;
        loadKahootQuestion();
      }, 1200);
    }
  }, 1000);
}

function loadKahootQuestion() {
  stopTimer();
  kMenjawab = false;

  if (currentQIdx >= currentQuestions.length) {
    kState = 'over';
    syncKUi();
    playSound('correct');
    if (typeof confetti === 'function') confetti({ particleCount: 100, spread: 70 });
    showResultModal("LIVE BATTLE SELESAI!", `${kScore.toLocaleString()} Pts`, "Selamat! Seluruh soal kuis berhasil diselesaikan!");
    return;
  }

  const q = currentQuestions[currentQIdx];
  document.getElementById('kQuestionNum').innerText = `${currentQIdx + 1}/${currentQuestions.length}`;
  document.getElementById('kQuestionText').innerText = q.q;

  q.a.forEach((opt, idx) => {
    const btn = document.getElementById(`kAns${idx}`);
    btn.disabled = false;
    btn.querySelector('.k-ans-text').innerText = opt;
  });

  kTimeLeft = kLimit;
  updateKTimerLabel();
  if (kState === 'running') {
    if (viewAktif !== 'play') {   // pemain sedang di Game Builder: tahan timer sampai kembali
      kState = 'paused';
      syncKUi();
    } else {
      jalankanTimerK();
    }
  }
}

function selectKahootAnswer(selectedIdx) {
  if (kState !== 'running' || kMenjawab) return;
  kMenjawab = true;
  stopTimer();
  playSound('click');
  const q = currentQuestions[currentQIdx];

  for (let i = 0; i < 4; i++) document.getElementById(`kAns${i}`).disabled = true;

  if (selectedIdx === q.correct) {
    playSound('correct');
    kStreak++;
    // Bonus kecepatan maksimum 600 poin; menyesuaikan batas waktu yang dipilih. Tanpa batas waktu: tanpa bonus.
    const speedBonus = kLimit ? Math.round((kTimeLeft / kLimit) * 15 * 40) : 0;
    const streakBonus = Math.min(kStreak * 100, 500);
    const earned = 500 + speedBonus + streakBonus;

    kScore += earned;
    document.getElementById('kScore').innerText = kScore.toLocaleString();
    document.getElementById('lbUserPoints').innerText = `${kScore.toLocaleString()} Pts`;
    if (typeof confetti === 'function') confetti({ particleCount: 25, spread: 40 });
  } else {
    playSound('wrong');
    kStreak = 0;
  }

  updateKahootStreak();

  setTimeout(() => {
    currentQIdx++;
    loadKahootQuestion();
  }, 1200);
}

function updateKahootStreak() {
  const badge = document.getElementById('kStreakBadge');
  if (kStreak >= 2) {
    document.getElementById('kStreakCount').innerText = kStreak;
    badge.classList.remove('hidden');
    badge.classList.add('flex');
  } else {
    badge.classList.add('hidden');
    badge.classList.remove('flex');
  }
}

// ==========================================
// 4. QUIZ BUILDER & JSON EXPORT/IMPORT
// ==========================================

function addQuestionToCustomBuilder() {
  const qText = document.getElementById('bQuestionInput').value.trim();
  const hintText = document.getElementById('bHintInput').value.trim();
  const opt0 = document.getElementById('bOpt0').value.trim();
  const opt1 = document.getElementById('bOpt1').value.trim();
  const opt2 = document.getElementById('bOpt2').value.trim();
  const opt3 = document.getElementById('bOpt3').value.trim();
  const correctIdx = parseInt(document.getElementById('bCorrectOpt').value);

  if (!qText || !opt0 || !opt1 || !opt2 || !opt3) {
    alert("Harap lengkapi pertanyaan dan seluruh 4 pilihan jawaban!");
    return;
  }

  playSound('click');
  customQuestions.push({
    q: qText,
    a: [opt0, opt1, opt2, opt3],
    correct: correctIdx,
    hint: hintText || "Perhatikan pilihan jawaban dengan teliti."
  });

  ['bQuestionInput', 'bHintInput', 'bOpt0', 'bOpt1', 'bOpt2', 'bOpt3'].forEach(id => {
    document.getElementById(id).value = '';
  });

  renderCustomBuilderList();
}

function removeCustomQuestion(index) {
  playSound('click');
  customQuestions.splice(index, 1);
  renderCustomBuilderList();
}

function renderCustomBuilderList() {
  const container = document.getElementById('builderQuestionsList');
  document.getElementById('bQuestionCount').innerText = customQuestions.length;

  if (customQuestions.length === 0) {
    container.innerHTML = `<p class="text-slate-500 text-xs text-center py-6">Belum ada soal kustom. Tambahkan soal di atas!</p>`;
    return;
  }

  container.innerHTML = '';
  customQuestions.forEach((item, idx) => {
    const div = document.createElement('div');
    div.className = "flex items-center justify-between p-3 bg-slate-900 rounded-xl border border-slate-800 text-xs";
    div.innerHTML = `
      <div class="space-y-0.5 overflow-hidden pr-2">
        <p class="font-bold text-slate-200 truncate">${idx + 1}. ${escapeHTML(item.q)}</p>
        <p class="text-[10px] text-emerald-400">Jawaban Benar: ${['A', 'B', 'C', 'D'][item.correct]} (${escapeHTML(item.a[item.correct])})</p>
      </div>
      <button onclick="removeCustomQuestion(${idx})" class="p-1.5 text-slate-500 hover:text-red-400 transition">
        <i class="fa-solid fa-trash"></i>
      </button>
    `;
    container.appendChild(div);
  });
}


function exportQuizJSON() {
  if (customQuestions.length === 0) {
    alert("Tidak ada soal kustom untuk diekspor!");
    return;
  }
  const judulEl = document.getElementById('bQuizTitle');
  const judul = (judulEl && judulEl.value.trim()) || 'Kuis Betsora';
  const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify({ judul, soal: customQuestions }, null, 2));
  const a = document.createElement('a');
  a.setAttribute("href", dataStr);
  a.setAttribute("download", "betsora_quiz_preset.json");
  document.body.appendChild(a);
  a.click();
  a.remove();
}

// Mengubah satu butir soal dari berbagai penulisan menjadi {q, a, correct, hint}.
// Mengembalikan { soal } bila valid, atau { alasan } bila tidak.
function normalisasiSoal(it) {
  if (!it || typeof it !== 'object') return { alasan: 'bukan objek soal' };
  const teks = it.q ?? it.question ?? it.pertanyaan;
  const pilihan = it.a ?? it.options ?? it.pilihan;
  let benar = it.correct ?? it.answer ?? it.jawaban ?? it.jawaban_benar;
  const petunjuk = it.hint ?? it.petunjuk;

  if (typeof teks !== 'string' || !teks.trim()) return { alasan: 'teks pertanyaan ("q") kosong' };
  if (!Array.isArray(pilihan) || pilihan.length !== 4) return { alasan: 'pilihan ("a") harus tepat 4' };
  if (!pilihan.every(x => (typeof x === 'string' || typeof x === 'number') && String(x).trim())) {
    return { alasan: 'ada pilihan yang kosong' };
  }
  if (typeof benar === 'string') {
    const t = benar.trim().toUpperCase();
    if (/^[A-D]$/.test(t)) benar = t.charCodeAt(0) - 65;
    else if (/^[0-3]$/.test(t)) benar = parseInt(t, 10);
  }
  if (!Number.isInteger(benar) || benar < 0 || benar > 3) {
    return { alasan: '"correct" harus angka 0-3 (0=A, 1=B, 2=C, 3=D)' };
  }
  return {
    soal: {
      q: teks.trim(),
      a: pilihan.map(x => String(x).trim()),
      correct: benar,
      hint: typeof petunjuk === 'string' && petunjuk.trim() ? petunjuk.trim() : "Perhatikan pilihan jawaban dengan teliti."
    }
  };
}

function importQuizJSON(event) {
  const input = event.target;
  const file = input.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onerror = function () {
    alert('Berkas tidak bisa dibaca. Coba pilih ulang berkasnya.');
    input.value = '';
  };
  reader.onload = function (e) {
    input.value = '';   // supaya berkas yang sama bisa dipilih lagi setelah diperbaiki
    const teks = String(e.target.result || '').replace(/^﻿/, '');

    let isi;
    try {
      isi = JSON.parse(teks);
    } catch (err) {
      alert('Berkas ini bukan JSON yang valid, jadi belum bisa diimpor.\n\n' +
        'Penyebab yang paling sering:\n' +
        '• berkas berisi teks perintah/terminal, bukan JSON murni\n' +
        '• tanda kutip lengkung (“ ”) dari Word/WhatsApp\n' +
        '• koma berlebih sesudah soal terakhir\n\n' +
        'Detail: ' + err.message);
      return;
    }

    // Dua bentuk diterima: daftar soal [ ... ] atau objek {"judul": "...", "soal": [ ... ]}
    let daftar = isi;
    let judul = '';
    if (isi && !Array.isArray(isi) && typeof isi === 'object') {
      daftar = isi.soal ?? isi.questions;
      if (typeof isi.judul === 'string') judul = isi.judul.trim();
    }
    if (!Array.isArray(daftar)) {
      alert('Struktur JSON tidak dikenali.\n\nGunakan daftar soal:\n[ { "q": "...", "a": ["A","B","C","D"], "correct": 0 } ]\n\natau:\n{ "judul": "...", "soal": [ ... ] }');
      return;
    }

    const bersih = [];
    const masalah = [];
    daftar.forEach((it, i) => {
      const hasil = normalisasiSoal(it);
      if (hasil.soal) bersih.push(hasil.soal);
      else masalah.push(`Soal ${i + 1}: ${hasil.alasan}`);
    });

    if (bersih.length === 0) {
      alert('Tidak ada soal yang valid di berkas ini.\n\n' + masalah.slice(0, 5).join('\n'));
      return;
    }

    const batas = 100;
    const dipotong = bersih.length > batas;
    customQuestions = bersih.slice(0, batas);
    editingQuizId = null;
    const judulEl = document.getElementById('bQuizTitle');
    if (judulEl && judul) judulEl.value = judul.slice(0, 200);
    renderCustomBuilderList();
    updateBuilderInfo();

    let pesan = `Berhasil mengimpor ${customQuestions.length} soal.`;
    if (dipotong) pesan += `\nHanya ${batas} soal pertama yang dipakai (batas maksimum).`;
    if (masalah.length) {
      pesan += `\n\n${masalah.length} soal dilewati:\n` + masalah.slice(0, 5).join('\n');
      if (masalah.length > 5) pesan += `\n...dan ${masalah.length - 5} lainnya.`;
    }
    pesan += '\n\nKlik "Simpan Kuis" untuk menyimpan ke database.';
    alert(pesan);
  };
  reader.readAsText(file);
}

// ==========================================
// 5. LEARNING ANALYTICS CHARTS
// ==========================================

let chartTopicInstance = null;
let chartHardestInstance = null;

function initCharts() {
  if (chartTopicInstance) chartTopicInstance.destroy();
  if (chartHardestInstance) chartHardestInstance.destroy();

  const ctxTopic = document.getElementById('analyticsTopicChart').getContext('2d');
  chartTopicInstance = new Chart(ctxTopic, {
    type: 'bar',
    data: {
      labels: ['Aritmatika', 'Aljabar', 'Geometri', 'Trigonometri', 'Statistika'],
      datasets: [{
        label: 'Penguasaan (%)',
        data: [92, 85, 78, 64, 88],
        backgroundColor: 'rgba(99, 102, 241, 0.6)',
        borderColor: '#6366f1',
        borderWidth: 1,
        borderRadius: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { beginAtZero: true, max: 100, grid: { color: 'rgba(255,255,255,0.05)' } },
        x: { grid: { display: false } }
      },
      plugins: { legend: { display: false } }
    }
  });

  const ctxHardest = document.getElementById('analyticsHardestChart').getContext('2d');
  chartHardestInstance = new Chart(ctxHardest, {
    type: 'doughnut',
    data: {
      labels: ['Trigonometri Lanjut', 'Integral Subtitusi', 'Logaritma', 'Lainnya'],
      datasets: [{
        data: [42, 28, 18, 12],
        backgroundColor: ['#f59e0b', '#ef4444', '#8b5cf6', '#64748b']
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8', font: { size: 10 } } } }
    }
  });
}

// ==========================================
// 6. RESULT MODAL
// ==========================================

function showResultModal(title, score, subtitle) {
  document.getElementById('resTitle').innerText = title;
  document.getElementById('resScoreValue').innerText = score;
  document.getElementById('resSubtitle').innerText = subtitle;
  document.getElementById('resultModal').classList.remove('hidden');
}

function closeResultModal() {
  document.getElementById('resultModal').classList.add('hidden');
  if (playMode === 'millionaire') siapkanMillionaire();
  if (playMode === 'kahoot') resetKahootGame();
}

// ==========================================
// 7. WELCOME POP-UP (dibuat via JavaScript)
// ==========================================

function showWelcomeModal() {
  if (document.getElementById('welcomeOverlay')) return;

  const overlay = document.createElement('div');
  overlay.id = 'welcomeOverlay';
  overlay.className = 'fixed inset-0 z-[60] flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-md';
  overlay.innerHTML = `
    <div class="glass-panel p-8 rounded-3xl max-w-md w-full text-center space-y-5 border border-indigo-500/30 glow-indigo">
      <div class="w-16 h-16 rounded-2xl bg-gradient-to-tr from-indigo-600 via-violet-600 to-amber-500 mx-auto flex items-center justify-center text-white font-black text-3xl shadow-lg">B</div>
      <div>
        <h2 class="text-2xl font-black text-white">Selamat Datang di Betsora OS</h2>
        <p class="text-xs text-slate-400 mt-1">Pilih mode permainan untuk memulai.</p>
      </div>
      <div class="grid grid-cols-1 gap-3">
        <button onclick="chooseWelcome('millionaire')" class="py-3 bg-amber-500 hover:bg-amber-400 text-slate-950 font-extrabold rounded-xl text-xs transition">🏆 Millionaire Challenge</button>
        <button onclick="chooseWelcome('kahoot')" class="py-3 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-extrabold rounded-xl text-xs transition">⚡ Live Quiz Battle</button>
        <button onclick="chooseWelcome('builder')" class="py-3 bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold rounded-xl text-xs transition">✏️ Buat Kuis Sendiri</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);
}

function chooseWelcome(mode) {
  const overlay = document.getElementById('welcomeOverlay');
  if (overlay) overlay.remove();

  if (mode === 'kahoot') {
    setPlayMode('kahoot');
  } else if (mode === 'builder') {
    siapkanMillionaire();   // hanya menyiapkan; timer tidak jalan di belakang Game Builder
    switchView('builder');
  } else {
    siapkanMillionaire();
  }
}

// ==========================================
// 8. DATABASE (KUIS TERSIMPAN)
// ==========================================

const CFG = window.KUIS_CONFIG || {};
let savedQuizzes = [];   // daftar kuis (metadata) dari server
let dbQuizCache = {};    // id -> { judul, soal: [...] }
let editingQuizId = null; // id kuis yang sedang diedit di Builder (null = kuis baru)

function apiUrl(base, id) {
  return base.replace('/0/', '/' + id + '/');
}

async function apiFetch(url, options = {}) {
  const opts = Object.assign({ credentials: 'same-origin' }, options);
  opts.headers = Object.assign({ 'X-CSRFToken': CFG.csrfToken }, opts.headers || {});
  const res = await fetch(url, opts);
  let data = {};
  try { data = await res.json(); } catch (e) { /* bukan JSON */ }
  if (!res.ok) throw new Error(data.error || ('Permintaan gagal (' + res.status + ')'));
  return data;
}

function getActiveQuestions() {
  if (activePresetKey === 'custom') return customQuestions;
  if (activePresetKey.startsWith('db:')) {
    const q = dbQuizCache[activePresetKey.slice(3)];
    return q ? q.soal : [];
  }
  return PRESETS[activePresetKey] || [];
}

function getActiveCategory() {
  if (activePresetKey.startsWith('db:')) {
    const q = dbQuizCache[activePresetKey.slice(3)];
    return q ? q.judul : 'Kuis Tersimpan';
  }
  return CATEGORY_NAMES[activePresetKey] || '-';
}

async function changePresetQuiz(val) {
  if (val.startsWith('db:')) {
    const id = val.slice(3);
    if (!dbQuizCache[id]) {
      try {
        dbQuizCache[id] = await apiFetch(apiUrl(CFG.apiDetail, id));
      } catch (e) {
        alert('Gagal memuat kuis: ' + e.message);
        document.getElementById('presetQuizSelector').value = activePresetKey;
        return;
      }
    }
  }
  activePresetKey = val;
  currentQuestions = getActiveQuestions();
  if (playMode === 'millionaire') siapkanMillionaire();
  if (playMode === 'kahoot') resetKahootGame();
}

async function refreshSavedQuizzes() {
  if (!CFG.apiDaftar) return;
  try {
    const data = await apiFetch(CFG.apiDaftar);
    savedQuizzes = data.kuis || [];
  } catch (e) {
    console.error('Gagal memuat daftar kuis:', e);
    savedQuizzes = [];
  }
  renderPresetGroup();
  renderSavedQuizList();
  updateBuilderInfo();
}

function renderPresetGroup() {
  const group = document.getElementById('savedQuizGroup');
  const sel = document.getElementById('presetQuizSelector');
  if (!group || !sel) return;

  group.innerHTML = '';
  savedQuizzes.forEach(q => {
    const opt = document.createElement('option');
    opt.value = 'db:' + q.id;
    opt.textContent = q.judul + ' (' + q.jumlah_soal + ' Soal)' + (q.milik_saya ? '' : ' - ' + q.pembuat);
    group.appendChild(opt);
  });
  group.hidden = savedQuizzes.length === 0;
  sel.value = activePresetKey;
}

function renderSavedQuizList() {
  const box = document.getElementById('savedQuizList');
  if (!box) return;

  if (savedQuizzes.length === 0) {
    box.innerHTML = '<p class="text-slate-500 text-xs text-center py-6">Belum ada kuis tersimpan.</p>';
    return;
  }

  box.innerHTML = '';
  savedQuizzes.forEach(q => {
    const row = document.createElement('div');
    row.className = 'flex items-center justify-between p-3 bg-slate-900 rounded-xl border border-slate-800 text-xs gap-2';

    const badge = q.dibagikan
      ? '<span class="ml-1 px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[10px] font-bold">Dibagikan</span>'
      : '';
    const ownerButtons = q.milik_saya
      ? `<button onclick="editSavedQuiz(${q.id})" class="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg font-bold transition">Edit</button>
         <button onclick="deleteSavedQuiz(${q.id})" class="px-2.5 py-1 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg font-bold transition">Hapus</button>`
      : '';

    row.innerHTML = `
      <div class="overflow-hidden pr-2">
        <p class="font-bold text-slate-200 truncate">${escapeHTML(q.judul)}${badge}</p>
        <p class="text-[10px] text-slate-400">${q.jumlah_soal} soal &middot; ${escapeHTML(q.pembuat)}</p>
      </div>
      <div class="flex items-center gap-1.5 shrink-0">
        <button onclick="playSavedQuiz(${q.id})" class="px-2.5 py-1 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-bold transition">Mainkan</button>
        ${ownerButtons}
      </div>
    `;
    box.appendChild(row);
  });
}

function updateBuilderInfo() {
  const el = document.getElementById('bEditInfo');
  if (!el) return;
  if (editingQuizId === null) {
    el.textContent = 'Kuis baru (belum disimpan)';
    return;
  }
  const q = savedQuizzes.find(x => x.id === editingQuizId);
  el.textContent = 'Mengedit kuis: ' + (q ? q.judul : '#' + editingQuizId);
}

function newQuizBuilder() {
  playSound('click');
  customQuestions = [];
  editingQuizId = null;
  const title = document.getElementById('bQuizTitle');
  const share = document.getElementById('bShare');
  if (title) title.value = '';
  if (share) share.checked = false;
  renderCustomBuilderList();
  updateBuilderInfo();
}

async function playSavedQuiz(id) {
  playSound('click');
  await changePresetQuiz('db:' + id);
  document.getElementById('presetQuizSelector').value = activePresetKey;
  switchView('play');
}

async function editSavedQuiz(id) {
  playSound('click');
  try {
    const data = await apiFetch(apiUrl(CFG.apiDetail, id));
    customQuestions = data.soal.map(q => ({ q: q.q, a: q.a.slice(), correct: q.correct, hint: q.hint }));
    editingQuizId = data.id;
    const title = document.getElementById('bQuizTitle');
    const share = document.getElementById('bShare');
    if (title) title.value = data.judul;
    if (share) share.checked = !!data.dibagikan;
    renderCustomBuilderList();
    updateBuilderInfo();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  } catch (e) {
    alert('Gagal memuat kuis: ' + e.message);
  }
}

async function deleteSavedQuiz(id) {
  const q = savedQuizzes.find(x => x.id === id);
  if (!confirm('Hapus kuis "' + (q ? q.judul : '#' + id) + '"? Tindakan ini tidak bisa dibatalkan.')) return;
  try {
    await apiFetch(apiUrl(CFG.apiHapus, id), { method: 'POST' });
  } catch (e) {
    alert('Gagal menghapus kuis: ' + e.message);
    return;
  }
  delete dbQuizCache[id];
  if (editingQuizId === id) newQuizBuilder();
  if (activePresetKey === 'db:' + id) {
    activePresetKey = 'math';
    await changePresetQuiz('math');
  }
  await refreshSavedQuizzes();
}

async function saveCustomQuiz() {
  if (customQuestions.length === 0) {
    alert("Tambahkan minimal 1 soal sebelum menyimpan!");
    return;
  }

  // Mode mandiri (tanpa backend Django): simpan di memori browser saja
  if (!CFG.apiSimpan) {
    playSound('correct');
    const customOpt = document.getElementById('customQuizOption');
    customOpt.disabled = false;
    customOpt.innerText = `Kuis Kustom Saya (${customQuestions.length} Soal)`;
    document.getElementById('presetQuizSelector').value = 'custom';
    changePresetQuiz('custom');
    alert("Kuis Kustom Berhasil Disimpan! Siap dimainkan di mode Simulator.");
    switchView('play');
    return;
  }

  const titleInput = document.getElementById('bQuizTitle');
  const shareBox = document.getElementById('bShare');
  const judul = titleInput ? titleInput.value.trim() : '';
  const dibagikan = shareBox ? shareBox.checked : false;

  if (!judul) {
    alert('Isi judul kuis terlebih dahulu.');
    if (titleInput) titleInput.focus();
    return;
  }

  try {
    const res = await apiFetch(CFG.apiSimpan, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: editingQuizId, judul, dibagikan, soal: customQuestions })
    });

    editingQuizId = res.id;
    dbQuizCache[res.id] = {
      id: res.id,
      judul: res.judul,
      dibagikan: res.dibagikan,
      milik_saya: true,
      soal: customQuestions.map(q => ({ q: q.q, a: q.a.slice(), correct: q.correct, hint: q.hint }))
    };

    playSound('correct');
    activePresetKey = 'db:' + res.id;
    await refreshSavedQuizzes();
    await changePresetQuiz(activePresetKey);
    alert('Kuis "' + res.judul + '" berhasil disimpan ke database.');
    switchView('play');
  } catch (e) {
    alert('Gagal menyimpan kuis: ' + e.message);
  }
}

// ==========================================
// 9. INITIALIZER
// ==========================================

window.onload = function () {
  showWelcomeModal(); // game baru dimulai setelah pengguna memilih mode
  refreshSavedQuizzes(); // muat kuis tersimpan dari database
};