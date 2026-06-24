# Sekolah Digital — Panduan Setup Django

Stack: Django 5 · PostgreSQL · Railway/Render · Tailwind CSS (via CDN)

---

## Fase 1: Setup project lokal

```bash
# Buat virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

# Install package awal
pip install django psycopg2-binary python-decouple gunicorn whitenoise pillow

# Buat project
django-admin startproject sekolah_digital .

# Buat apps
python manage.py startapp accounts
python manage.py startapp kelas
python manage.py startapp penilaian
python manage.py startapp portofolio
```

---

## Fase 2: Struktur folder

```
sekolah_digital/          ← folder project
├── sekolah_digital/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── accounts/             ← app: guru, siswa, login
├── kelas/                ← app: absensi, keaktifan, jadwal
├── penilaian/            ← app: nilai formatif & sumatif
├── portofolio/           ← app: portofolio otomatis
├── templates/            ← semua HTML
│   ├── base.html
│   ├── dashboard.html
│   └── ...
├── static/               ← CSS, JS
├── media/                ← file upload tugas siswa
├── .env                  ← rahasia, JANGAN di-commit
├── requirements.txt
└── manage.py
```

---

## Fase 3: settings.py penting

```python
# settings.py
from decouple import config

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost').split(',')

INSTALLED_APPS = [
    # default django...
    'django.contrib.admin',
    'django.contrib.auth',
    # apps kita:
    'accounts',
    'kelas',
    'penilaian',
    'portofolio',
]

# Database PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# Auth custom user
AUTH_USER_MODEL = 'accounts.User'

# Static & media
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Whitenoise (untuk serve static di production)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    # ...sisanya bawaan django
]

# Login redirect
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'kelas:dashboard'
```

---

## Fase 4: File .env (lokal)

```env
SECRET_KEY=ganti-dengan-string-panjang-acak
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=sekolah_digital
DB_USER=postgres
DB_PASSWORD=password_lokal_anda
DB_HOST=localhost
DB_PORT=5432
```

---

## Fase 5: Models utama

### accounts/models.py
```python
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = [
        ('guru', 'Guru'),
        ('kepsek', 'Kepala Sekolah'),
        ('admin', 'Admin'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='guru')

class Siswa(models.Model):
    nama = models.CharField(max_length=100)
    nis = models.CharField(max_length=20, unique=True)
    kelas = models.CharField(max_length=10)  # cth: "8A"
    foto = models.ImageField(upload_to='foto_siswa/', blank=True)
    aktif = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nama} ({self.kelas})"
```

### kelas/models.py
```python
from django.db import models
from accounts.models import Siswa, User

class Absensi(models.Model):
    STATUS = [('hadir','Hadir'), ('izin','Izin'), ('alpha','Alpha'), ('sakit','Sakit')]
    siswa = models.ForeignKey(Siswa, on_delete=models.CASCADE)
    tanggal = models.DateField()
    status = models.CharField(max_length=6, choices=STATUS)
    guru = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    catatan = models.TextField(blank=True)

    class Meta:
        unique_together = ['siswa', 'tanggal']

class Keaktifan(models.Model):
    siswa = models.ForeignKey(Siswa, on_delete=models.CASCADE)
    tanggal = models.DateField()
    poin = models.PositiveIntegerField(default=0)
    deskripsi = models.TextField(blank=True)  # cth: "bertanya 2x, presentasi"
    guru = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
```

### penilaian/models.py
```python
from django.db import models
from accounts.models import Siswa, User

class SesiPenilaian(models.Model):
    JENIS = [('formatif','Formatif'), ('sumatif','Sumatif')]
    mapel = models.CharField(max_length=50)
    jenis = models.CharField(max_length=10, choices=JENIS)
    topik = models.CharField(max_length=100)
    tanggal = models.DateField()
    guru = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.mapel} - {self.topik} ({self.jenis})"

class Nilai(models.Model):
    sesi = models.ForeignKey(SesiPenilaian, on_delete=models.CASCADE)
    siswa = models.ForeignKey(Siswa, on_delete=models.CASCADE)
    skor = models.DecimalField(max_digits=5, decimal_places=2)
    catatan = models.TextField(blank=True)

    class Meta:
        unique_together = ['sesi', 'siswa']
```

### portofolio/models.py
```python
# Portofolio TIDAK perlu model baru —
# cukup query dari Absensi, Keaktifan, dan Nilai
# di views.py dengan aggregation Django ORM

# Contoh di views.py nanti:
# from django.db.models import Avg, Count, Sum
# nilai_avg = Nilai.objects.filter(siswa=siswa).aggregate(Avg('skor'))
# kehadiran_pct = Absensi.objects.filter(siswa=siswa, status='hadir').count() / total * 100
```

---

## Fase 6: urls.py

### sekolah_digital/urls.py
```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('kelas.urls', namespace='kelas')),
    path('akun/', include('accounts.urls', namespace='accounts')),
    path('penilaian/', include('penilaian.urls', namespace='penilaian')),
    path('portofolio/', include('portofolio.urls', namespace='portofolio')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

---

## Fase 7: Deployment ke Railway

```bash
# 1. Buat requirements.txt
pip freeze > requirements.txt

# 2. Buat Procfile (tanpa ekstensi)
echo "web: gunicorn sekolah_digital.wsgi" > Procfile

# 3. Buat runtime.txt
echo "python-3.12.0" > runtime.txt

# 4. Push ke GitHub
git init
git add .
git commit -m "first commit"
git push origin main

# 5. Di Railway:
# - New Project → Deploy from GitHub
# - Tambah plugin PostgreSQL
# - Set environment variables (sama seperti .env, tapi DB_* dari Railway)
# - Set ALLOWED_HOSTS=nama-app.railway.app
# - Set DEBUG=False
```

---

## Urutan pengerjaan yang disarankan

1. Setup project & install — **selesai dulu, test runserver**
2. Buat model `User` custom + `Siswa` → migrate
3. Buat login/logout sederhana (pakai `django.contrib.auth`)
4. Buat dashboard + absensi
5. Buat penilaian formatif & sumatif
6. Buat keaktifan
7. Buat halaman portofolio (aggregasi dari data yang ada)
8. Deploy ke Railway
9. Tambah fitur: export PDF, notifikasi orang tua, dll

---

## Prompt-prompt yang bisa Anda tanyakan ke Claude selanjutnya

- "Buatkan views.py dan urls.py untuk absensi di Django"
- "Buatkan template HTML dashboard guru dengan Tailwind"
- "Bagaimana cara restrict halaman hanya untuk guru yang login?"
- "Buatkan form input nilai untuk semua siswa dalam satu kelas sekaligus"
- "Buatkan halaman portofolio siswa dengan query Django ORM"
- "Cara deploy Django ke Railway step by step"
