"""Deterministic text extraction for LA Times archive pages: title, dateline/pub date, story-body paragraphs."""
import re, html
def la_text(b):
    t = b.decode('utf-8', 'replace') if isinstance(b, bytes) else b
    title = re.search(r'<title>(.*?)</title>', t, re.S)
    title = html.unescape(title.group(1)).strip() if title else ''
    pub = re.search(r'"datePublished"\s*:\s*"([^"]+)"', t)
    pub = pub.group(1) if pub else ''
    i = t.find('data-element="story-body"')
    body = ''
    if i >= 0:
        seg = t[i:]
        end = re.search(r'data-element="(?:story-footer|tags|related)|<footer', seg)
        seg = seg[:end.start()] if end else seg[:200000]
        paras = re.findall(r'<p[^>]*>(.*?)</p>', seg, re.S)
        body = '\n'.join(html.unescape(re.sub(r'<[^>]+>', '', p)).strip() for p in paras)
    return title, pub, body
