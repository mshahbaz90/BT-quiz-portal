import re
from html.parser import HTMLParser
from urllib.parse import urlparse

# Whitelisted formatting tags
ALLOWED_TAGS = {
    'p', 'br', 'strong', 'b', 'em', 'i', 'u', 's', 'strike', 'span',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li',
    'blockquote', 'pre', 'code', 'a', 'sub', 'sup',
    'table', 'thead', 'tbody', 'tr', 'th', 'td', 'hr', 'div'
}

# Whitelisted tag attributes
ALLOWED_ATTRS = {
    'a': {'href', 'target', 'rel', 'class', 'title'},
    'span': {'style', 'class'},
    'p': {'style', 'class'},
    'div': {'style', 'class'},
    'h1': {'style', 'class'},
    'h2': {'style', 'class'},
    'h3': {'style', 'class'},
    'h4': {'style', 'class'},
    'h5': {'style', 'class'},
    'h6': {'style', 'class'},
    'table': {'class', 'style', 'border', 'cellpadding', 'cellspacing'},
    'th': {'style', 'class', 'colspan', 'rowspan', 'scope'},
    'td': {'style', 'class', 'colspan', 'rowspan'},
    'ol': {'class', 'style', 'type', 'start'},
    'ul': {'class', 'style'},
    'li': {'class', 'style'},
    'blockquote': {'class', 'style'},
    'pre': {'class', 'style'},
    'code': {'class'},
}

# Whitelisted CSS properties for style="" attribute
ALLOWED_CSS_PROPERTIES = {
    'color', 'background-color', 'text-align', 'font-size', 'font-weight',
    'font-style', 'text-decoration', 'padding', 'padding-left', 'margin',
    'margin-left', 'line-height', 'letter-spacing'
}

SAFE_SCHEMES = {'http', 'https', 'mailto', 'tel'}


def parse_color_rgb(val):
    """Parse color string into (r, g, b) integer tuple or None."""
    if not val:
        return None
    v = val.strip().lower().replace(' ', '')
    if v in {'black', '#000', '#000000'}:
        return (0, 0, 0)
    if v in {'white', '#fff', '#ffffff'}:
        return (255, 255, 255)

    # 6-digit hex
    m6 = re.match(r'^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$', v)
    if m6:
        return (int(m6.group(1), 16), int(m6.group(2), 16), int(m6.group(3), 16))

    # 3-digit hex
    m3 = re.match(r'^#([0-9a-f])([0-9a-f])([0-9a-f])$', v)
    if m3:
        return (int(m3.group(1) * 2, 16), int(m3.group(2) * 2, 16), int(m3.group(3) * 2, 16))

    # rgb/rgba
    mrgb = re.match(r'^rgba?\((\d+),(\d+),(\d+)', v)
    if mrgb:
        return (int(mrgb.group(1)), int(mrgb.group(2)), int(mrgb.group(3)))

    return None


def is_black_or_dark_color(val):
    """
    Returns True if a CSS color value represents black or dark-gray
    that would be unreadable on a dark theme background.
    """
    v = val.strip().lower().replace(' ', '')
    if v in {
        'black', '#000', '#000000', '#111', '#111111', '#222', '#222222', '#333', '#333333',
        'rgb(0,0,0)', 'rgba(0,0,0,1)', 'rgba(0,0,0,1.0)',
        'rgb(34,34,34)', 'rgb(33,37,41)', '#212529', '#1e293b', '#0f172a',
        '#050212', '#0c0722', '#110a2f', '#12092c', '#160e38', '#1f2937', '#374151'
    }:
        return True
    rgb = parse_color_rgb(val)
    if rgb:
        r, g, b = rgb
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        saturation = max(r, g, b) - min(r, g, b)
        if lum < 35 or (lum < 55 and saturation < 30):
            return True
    return False


def is_white_or_light_color(val):
    """
    Returns True if a CSS color value represents white or near-white
    that would be unreadable on a light theme background.
    """
    v = val.strip().lower().replace(' ', '')
    if v in {
        'white', '#fff', '#ffffff', '#fafafa', '#f8fafc', '#f1f5f9',
        'rgb(255,255,255)', 'rgba(255,255,255,1)', 'rgba(255,255,255,1.0)'
    }:
        return True
    rgb = parse_color_rgb(val)
    if rgb:
        r, g, b = rgb
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        saturation = max(r, g, b) - min(r, g, b)
        if lum > 240 or (lum > 225 and saturation < 25):
            return True
    return False


def is_white_or_light_bg(val):
    """
    Returns True if a background-color is white/near-white,
    often pasted inadvertently from Word or Google Docs.
    """
    v = val.strip().lower().replace(' ', '')
    if v in {'white', '#fff', '#ffffff', 'rgb(255,255,255)', 'rgba(255,255,255,1)', 'transparent'}:
        return True
    return False


def clean_css_style(style_value):
    """Sanitize inline style declaration, allowing only safe CSS rules."""
    if not style_value:
        return ''
    cleaned_declarations = []
    # Split on semicolons
    for part in style_value.split(';'):
        if ':' not in part:
            continue
        prop, val = part.split(':', 1)
        prop = prop.strip().lower()
        val = val.strip()

        # Reject dangerous tokens
        val_lower = val.lower()
        if any(bad in val_lower for bad in ['expression', 'url', 'javascript', '@import', '-moz-binding', 'behavior']):
            continue

        if prop in ALLOWED_CSS_PROPERTIES:
            # Check value safety (only allow basic alphanumeric, colors, units)
            if re.match(r'^[#a-zA-Z0-9\s.,%()_\-]+$', val):
                # Omit black/dark and white/light text colors so text adapts to theme (white in dark mode, dark in light mode)
                if prop == 'color' and (is_black_or_dark_color(val) or is_white_or_light_color(val)):
                    continue
                # Omit white/transparent pasted background colors
                if prop == 'background-color' and is_white_or_light_bg(val):
                    continue
                cleaned_declarations.append(f"{prop}: {val}")

    return '; '.join(cleaned_declarations)


class SafeHTMLSanitizer(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []
        self.tag_stack = []

    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()
        if tag_lower not in ALLOWED_TAGS:
            return

        cleaned_attrs = []
        allowed_for_tag = ALLOWED_ATTRS.get(tag_lower, set())

        for attr, val in attrs:
            attr_lower = attr.lower()
            if attr_lower.startswith('on') or attr_lower.startswith('data-'):
                continue
            if attr_lower not in allowed_for_tag:
                continue

            if attr_lower == 'href':
                parsed = urlparse(val)
                if parsed.scheme and parsed.scheme.lower() not in SAFE_SCHEMES:
                    continue
                cleaned_attrs.append(('href', val))
                cleaned_attrs.append(('target', '_blank'))
                cleaned_attrs.append(('rel', 'noopener noreferrer'))
            elif attr_lower == 'style':
                safe_style = clean_css_style(val)
                if safe_style:
                    cleaned_attrs.append(('style', safe_style))
            elif attr_lower == 'class':
                # Strip Quill black/white color classes so text adapts to active theme
                c_val = re.sub(r'\b(ql-color-black|ql-color-white)\b', '', val).strip()
                if c_val:
                    cleaned_attrs.append(('class', c_val))
            else:
                cleaned_attrs.append((attr_lower, val))

        attr_str = ''
        if cleaned_attrs:
            # Deduplicate by attribute name
            seen = set()
            unique_attrs = []
            for k, v in cleaned_attrs:
                if k not in seen:
                    seen.add(k)
                    unique_attrs.append(f'{k}="{v}"')
            if unique_attrs:
                attr_str = ' ' + ' '.join(unique_attrs)

        if tag_lower in ['br', 'hr']:
            self.result.append(f"<{tag_lower}{attr_str}/>")
        else:
            self.result.append(f"<{tag_lower}{attr_str}>")
            self.tag_stack.append(tag_lower)

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in ALLOWED_TAGS and tag_lower not in ['br', 'hr']:
            if tag_lower in self.tag_stack:
                self.tag_stack.remove(tag_lower)
                self.result.append(f"</{tag_lower}>")

    def handle_data(self, data):
        self.result.append(data)

    def handle_entityref(self, name):
        self.result.append(f"&{name};")

    def handle_charref(self, name):
        self.result.append(f"&#{name};")

    def get_html(self):
        # Close any unclosed tags
        while self.tag_stack:
            tag = self.tag_stack.pop()
            self.result.append(f"</{tag}>")
        return ''.join(self.result)


def sanitize_rich_text(raw_html, wrap_plain_text=False):
    """
    Sanitizes HTML content, removing any XSS vectors while preserving
    headings, paragraphs, text colors, highlights, lists, and spacing.
    If wrap_plain_text is True and text has no HTML markup, formats plain newlines into paragraphs.
    """
    if not raw_html:
        return ''
    raw_str = str(raw_html).strip()
    if not raw_str:
        return ''

    # Check if text contains HTML tags
    has_html = bool(re.search(r'<[a-zA-Z\/][^>]*>', raw_str))
    if not has_html:
        if wrap_plain_text:
            escaped = raw_str.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            paragraphs = escaped.split('\n\n')
            html_paragraphs = [f"<p>{p.replace(chr(10), '<br/>')}</p>" for p in paragraphs if p.strip()]
            return ''.join(html_paragraphs)
        return raw_str

    parser = SafeHTMLSanitizer()
    parser.feed(raw_str)
    sanitized = parser.get_html()
    # Normalize redundant consecutive empty paragraphs into a single line break
    sanitized = re.sub(r'(?:<p>\s*(?:<br\s*/?>|&nbsp;|\s)*</p>\s*){2,}', '<p><br/></p>', sanitized)
    return sanitized

