"""Aturan siapa yang boleh melihat dan menilai karya & refleksi seorang siswa."""


def boleh_kelola_ruang(user, ruang):
    """Guru pemilik ruang kerja, atau kepsek/admin/superuser."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    role = getattr(user, 'role', None)
    if role in ('kepsek', 'admin'):
        return True
    return role == 'guru' and ruang.guru_id == user.id


def boleh_lihat_submisi(user, submisi):
    """
    - siswa    : hanya miliknya sendiri
    - orangtua : hanya anaknya (User.anak)
    - guru     : hanya guru pemilik RuangKerja tempat tugas itu berada
    - kepsek / admin / superuser : semua
    """
    if not user.is_authenticated:
        return False
    role = getattr(user, 'role', None)
    if role == 'siswa' and not user.is_superuser:
        return submisi.siswa.user_id == user.id
    if role == 'orangtua' and not user.is_superuser:
        return user.anak_id is not None and user.anak_id == submisi.siswa_id
    return boleh_kelola_ruang(user, submisi.tugas.ruang_kerja)
