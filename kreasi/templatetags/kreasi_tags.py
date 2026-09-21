from django import template

from ..orangtua import ringkasan_untuk_orangtua

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
