import sys, re, unicodedata
import pdfplumber

def norm(s):
    s = unicodedata.normalize('NFKD', s)
    s = (s.replace('’',"'").replace('‘',"'").replace('“','"').replace('”','"')
           .replace('–','-').replace('—','-').replace('−','-').replace(' ',' ')
           .replace('…','...').replace('ﬁ','fi').replace('ﬂ','fl'))
    s = re.sub(r'-\s*\n\s*','',s)
    s = re.sub(r'\s+',' ',s)
    return s.lower().strip()

def load(path):
    txt=[]
    with pdfplumber.open(path) as pdf:
        for pg in pdf.pages:
            t = pg.extract_text() or ''
            txt.append(t)
    return norm('\n'.join(txt))

if __name__=='__main__':
    body = load(sys.argv[1])
    for q in sys.argv[2:]:
        # split on ellipsis: verify each fragment
        parts = [p for p in re.split(r'\s*(?:\.\.\.|…)\s*', q) if p.strip()]
        ok = all(norm(p) in body for p in parts)
        print(('PASS' if ok else 'FAIL'), '|', q[:95])
