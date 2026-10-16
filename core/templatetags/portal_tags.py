import re
from django import template
from django.utils.safestring import mark_safe
from core.sanitizer import sanitize_rich_text

register = template.Library()


@register.filter(name='rich_format')
def rich_format(value):
    """
    Sanitizes HTML content, preserving paragraphs, headings, colors,
    lists, code blocks, and marks it safe for rendering in templates.
    """
    if not value:
        return ''
    cleaned = sanitize_rich_text(value, wrap_plain_text=True)
    return mark_safe(cleaned)


@register.filter(name='strip_html_preview')
def strip_html_preview(value, max_chars=80):
    """
    Strips HTML tags to generate a clean, one-line preview string for tables and lists.
    """
    if not value:
        return ''
    # Remove HTML tags
    clean_text = re.sub(r'<[^>]+>', ' ', str(value))
    clean_text = ' '.join(clean_text.split())
    if len(clean_text) > max_chars:
        return clean_text[:max_chars] + '...'
    return clean_text
