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
// 1c. NAVIGATION
// ==========================================

function switchView(viewName) {
  playSound('click');
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

function changePresetQuiz(val) {
  activePresetKey = val;
  currentQuestions = val === 'custom' ? customQuestions : PRESETS[val];
  if (playMode === 'millionaire') startMillionaireGame();
  if (playMode === 'kahoot') resetKahootGame();
}

function setPlayMode(mode) {
  playSound('click');
  playMode = mode;
  document.getElementById('btnModeMillionaire').className = mode === 'millionaire'
    ? 'flex-1 md:flex-initial px-4 py-2 rounded-lg text-xs font-bold transition flex items-center justify-center space-x-2 bg-amber-500 text-slate-950 shadow-md'
    : 'flex-1 md:flex-initial px-4 py-2 rounded-lg text-xs font-bold transition flex items-center justify-center space-x-2 text-slate-400 hover:text-white';
  document.getElementById('btnModeKahoot').className = mode === 'kahoot'
    ? 'flex-1 md:flex-initial px-4 py-2 rounded-lg text-xs font-bold transition flex items-center justify-center space-x-2 bg-purple-600 text-white shadow-md'
    : 'flex-1 md:flex-initial px-4 py-2 rounded-lg text-xs font-bold transition flex items-center justify-center space-x-2 text-slate-400 hover:text-white';

  if (mode === 'millionaire') {
    document.getElementById('playMillionaire').classList.remove('hidden');
    document.getElementById('playKahoot').classList.add('hidden');
    startMillionaireGame();
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

function startMillionaireGame() {
  currentQuestions = activePresetKey === 'custom' ? customQuestions : PRESETS[activePresetKey];
  if (!currentQuestions || currentQuestions.length === 0) return;

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

function loadMillionaireQuestion() {
  closeLifelineBox();
  clearInterval(timerInterval);

  const total = getMillionaireTotal();
  if (currentQIdx >= total) {
    showResultModal("SELAMAT! ANDA JUTAWAN!", mCurrentPrize, `Sempurna! Berhasil menjawab seluruh ${total} level!`);
    return;
  }

  const q = currentQuestions[currentQIdx];
  const ladderIdx = getLadderIdx(currentQIdx);
  document.getElementById('mLevelNum').innerText = currentQIdx + 1;
  document.getElementById('mQuestionText').innerText = q.q;
  document.getElementById('mCategoryBadge').innerText = 'Kategori: ' + (CATEGORY_NAMES[activePresetKey] || '-');

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

  let timeLeft = 30;
  document.getElementById('mTimer').innerText = timeLeft;
  timerInterval = setInterval(() => {
    timeLeft--;
    document.getElementById('mTimer').innerText = timeLeft;
    if (timeLeft <= 5) playSound('tick');
    if (timeLeft <= 0) {
      clearInterval(timerInterval);
      gameOverMillionaire("Waktu Habis!");
    }
  }, 1000);
}

function selectMillionaireAnswer(selectedIdx) {
  clearInterval(timerInterval);
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
  if (!mLifelines[type]) return;
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
  if (confirm(`Apakah Anda yakin ingin berhenti sekarang dan mengamankan ${mCurrentPrize}?`)) {
    gameOverMillionaire("Anda Memutuskan Berhenti!");
  }
}

function gameOverMillionaire(reason) {
  clearInterval(timerInterval);
  const quit = reason.includes("Berhenti");
  const finalPrize = quit ? mCurrentPrize : mSafePrize;
  showResultModal(reason, finalPrize, `Pencapaian: Level ${currentQIdx + 1} dari ${getMillionaireTotal()}`);
}

// ==========================================
// 3. LIVE QUIZ BATTLE (KAHOOT STYLE)
// ==========================================

function resetKahootGame() {
  clearInterval(timerInterval);
  kScore = 0;
  kStreak = 0;
  currentQIdx = 0;
  document.getElementById('kScore').innerText = '0';
  document.getElementById('kStreakBadge').classList.add('hidden');
  document.getElementById('kQuestionText').innerText = "Klik 'MULAI LIVE BATTLE' untuk mensimulasikan permainan Kahoot!";
  document.getElementById('lbUserPoints').innerText = '0 Pts';
}

function startKahootGame() {
  currentQuestions = activePresetKey === 'custom' ? customQuestions : PRESETS[activePresetKey];
  if (!currentQuestions || currentQuestions.length === 0) return;

  currentQIdx = 0;
  kScore = 0;
  kStreak = 0;
  document.getElementById('kScore').innerText = '0';
  loadKahootQuestion();
}

function loadKahootQuestion() {
  clearInterval(timerInterval);

  if (currentQIdx >= currentQuestions.length) {
    playSound('correct');
    confetti({ particleCount: 100, spread: 70 });
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

  kTimeLeft = 15;
  document.getElementById('kTimer').innerText = kTimeLeft;
  const timerBar = document.getElementById('kTimerBar');
  timerBar.style.width = '100%';

  timerInterval = setInterval(() => {
    kTimeLeft--;
    document.getElementById('kTimer').innerText = kTimeLeft;
    timerBar.style.width = `${(kTimeLeft / 15) * 100}%`;

    if (kTimeLeft <= 3) playSound('tick');

    if (kTimeLeft <= 0) {
      clearInterval(timerInterval);
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

function selectKahootAnswer(selectedIdx) {
  clearInterval(timerInterval);
  playSound('click');
  const q = currentQuestions[currentQIdx];

  for (let i = 0; i < 4; i++) document.getElementById(`kAns${i}`).disabled = true;

  if (selectedIdx === q.correct) {
    playSound('correct');
    kStreak++;
    const speedBonus = kTimeLeft * 40;
    const streakBonus = Math.min(kStreak * 100, 500);
    const earned = 500 + speedBonus + streakBonus;

    kScore += earned;
    document.getElementById('kScore').innerText = kScore.toLocaleString();
    document.getElementById('lbUserPoints').innerText = `${kScore.toLocaleString()} Pts`;
    confetti({ particleCount: 25, spread: 40 });
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

function saveCustomQuiz() {
  if (customQuestions.length === 0) {
    alert("Tambahkan minimal 1 soal sebelum menyimpan!");
    return;
  }
  playSound('correct');
  const customOpt = document.getElementById('customQuizOption');
  customOpt.disabled = false;
  customOpt.innerText = `Kuis Kustom Saya (${customQuestions.length} Soal)`;
  document.getElementById('presetQuizSelector').value = 'custom';
  changePresetQuiz('custom');
  alert("Kuis Kustom Berhasil Disimpan! Siap dimainkan di mode Simulator.");
  switchView('play');
}

function exportQuizJSON() {
  if (customQuestions.length === 0) {
    alert("Tidak ada soal kustom untuk diekspor!");
    return;
  }
  const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(customQuestions, null, 2));
  const a = document.createElement('a');
  a.setAttribute("href", dataStr);
  a.setAttribute("download", "betsora_quiz_preset.json");
  document.body.appendChild(a);
  a.click();
  a.remove();
}

function importQuizJSON(event) {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = function (e) {
    try {
      const imported = JSON.parse(e.target.result);
      if (!Array.isArray(imported)) throw new Error("Bukan array");

      const clean = imported
        .filter(it =>
          it && typeof it.q === 'string' && it.q.trim() &&
          Array.isArray(it.a) && it.a.length === 4 &&
          it.a.every(x => typeof x === 'string' && x.trim()) &&
          Number.isInteger(it.correct) && it.correct >= 0 && it.correct <= 3
        )
        .map(it => ({
          q: it.q.trim(),
          a: it.a.map(x => x.trim()),
          correct: it.correct,
          hint: typeof it.hint === 'string' && it.hint.trim() ? it.hint.trim() : "Perhatikan pilihan jawaban dengan teliti."
        }));

      if (clean.length === 0) throw new Error("Tidak ada soal valid");

      customQuestions = clean;
      renderCustomBuilderList();
      const skipped = imported.length - clean.length;
      alert(`Berhasil mengimpor ${clean.length} soal.` + (skipped ? ` ${skipped} soal dilewati karena format tidak valid.` : ''));
    } catch (err) {
      alert("Format file JSON tidak valid!");
    }
    event.target.value = '';
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
  if (playMode === 'millionaire') startMillionaireGame();
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
    startMillionaireGame();
    clearInterval(timerInterval); // timer tidak jalan di belakang Game Builder
    switchView('builder');
  } else {
    startMillionaireGame();
  }
}

// ==========================================
// 8. INITIALIZER
// ==========================================

window.onload = function () {
  showWelcomeModal(); // game baru dimulai setelah pengguna memilih mode
};