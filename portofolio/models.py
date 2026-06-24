from django.db import models

# Portofolio tidak memerlukan model baru.
# Semua data diambil langsung dari model Absensi, Keaktifan (app kelas)
# dan Nilai (app penilaian) melalui query di views.py