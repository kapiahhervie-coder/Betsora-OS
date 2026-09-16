import re
from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name="highlight_mentions")
def highlight_mentions(text):
    escaped = escape(text)
    pattern = re.compile(r"@(\w+)")

    def replace(match):
        return "<span style=\"color:#0B3D26; font-weight:600; background:#E7EFE3; padding:0 3px; border-radius:4px;\">@" + match.group(1) + "</span>"

    result = pattern.sub(replace, escaped)
    return mark_safe(result)
