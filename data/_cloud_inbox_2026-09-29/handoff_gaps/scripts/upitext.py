"""Deterministic UPI archive text extraction: headline, article-date line, body paragraphs (<p> inside the article)."""
import re, html
def upi_text(b):
    t = b.decode('utf-8', 'replace') if isinstance(b, bytes) else b
    title = re.search(r'<title>(.*?)</title>', t, re.S)
    title = html.unescape(title.group(1)).strip() if title else ''
    date = re.search(r'<div class="article-date">(.*?)</div>', t, re.S)
    date = html.unescape(re.sub(r'<[^>]+>', ' ', date.group(1))).strip() if date else ''
    i = t.find('<article')
    seg = t[i:] if i >= 0 else t
    j = seg.find('</article>')
    seg = seg[:j] if j >= 0 else seg
    paras = [html.unescape(re.sub(r'<[^>]+>', '', p)).strip() for p in re.findall(r'<p[^>]*>(.*?)</p>', seg, re.S)]
    paras = [p for p in paras if p and not p.startswith('Copyright') and 'function(' not in p]
    return title, re.sub(r'\s+', ' ', date), '\n'.join(paras)
