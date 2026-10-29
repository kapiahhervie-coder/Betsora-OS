from django import template

from ..ringkasan import ringkasan_untuk_orangtua

register = template.Library()


@register.inclusion_tag("misi/_orangtua_misi.html", takes_context=True)
def misi_anak(context):
    """
    Bagian "Misi Dunia Nyata" untuk dashboard orang tua.

    Sengaja TIDAK menerima argumen (sama seperti karya_anak di kreasi_tags): anak yang ditampilkan
    selalu request.user.anak, sehingga tag ini tidak bisa dipakai untuk menampilkan anak lain,
    sekalipun salah dipasang di template lain. Untuk pengguna selain orang tua, hasilnya kosong.
    """
    request = context.get("request")
    user = getattr(request, "user", None)
    return {"bagian": ringkasan_untuk_orangtua(user)}
