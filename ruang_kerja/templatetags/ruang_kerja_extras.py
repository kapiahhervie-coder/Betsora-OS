from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Ambil value dari dict pakai key berupa variable (bukan literal), contoh:
    {{ refleksi_map|get_item:topik.id }}
    """
    if not dictionary:
        return None
    return dictionary.get(key)