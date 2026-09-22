from django import template

from ..orangtua import ringkasan_untuk_orangtua
from ..orangtua_lain import (
    ringkasan_absensi_untuk_orangtua, ringkasan_portofolio_untuk_orangtua, ringkasan_tugas_untuk_orangtua,
)

register = template.Library()


@register.inclusion_tag('kreasi/_orangtua_karya.html', takes_context=True)
def karya_anak(context):
    """
    Bagian "Karya & Perkembangan" untuk dashboard orang tua.

    Sengaja TIDAK menerima argumen: anak yang ditampilkan selalu request.user.anak, sehingga tag ini
    tidak bisa dipakai untuk menampilkan anak lain, sekalipun salah dipasang di template lain.
    """
    request = context.get('request')
    user = getattr(request, 'user', None)
    semua = request is not None and request.GET.get('semua_karya') == '1'
    return {'bagian': ringkasan_untuk_orangtua(user, semua=semua) if user is not None else None}


@register.inclusion_tag('kreasi/_orangtua_absensi.html', takes_context=True)
def absensi_anak(context):
    """Bagian Absensi untuk dashboard orang tua. Tanpa argumen: selalu anak dari akun yang login."""
    request = context.get('request')
    user = getattr(request, 'user', None)
    return {'bagian': ringkasan_absensi_untuk_orangtua(user) if user is not None else None}


@register.inclusion_tag('kreasi/_orangtua_tugas.html', takes_context=True)
def tugas_anak(context):
    """Bagian Tugas (status kumpul saja, tanpa nilai) untuk dashboard orang tua."""
    request = context.get('request')
    user = getattr(request, 'user', None)
    return {'bagian': ringkasan_tugas_untuk_orangtua(user) if user is not None else None}


@register.inclusion_tag('kreasi/_orangtua_portofolio.html', takes_context=True)
def portofolio_anak(context):
    """Bagian Portofolio/Galeri untuk dashboard orang tua."""
    request = context.get('request')
    user = getattr(request, 'user', None)
    semua = request is not None and request.GET.get('semua_portofolio') == '1'
    return {'bagian': ringkasan_portofolio_untuk_orangtua(user, semua=semua) if user is not None else None}
