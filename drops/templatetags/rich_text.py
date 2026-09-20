from django import template
from django.utils.safestring import mark_safe

from drops.rich_text import sanitize_rich_text

register = template.Library()


@register.filter
def render_rich_text(value):
    """Sanitize again at the final rendering boundary as defense in depth."""
    return mark_safe(sanitize_rich_text(value))
