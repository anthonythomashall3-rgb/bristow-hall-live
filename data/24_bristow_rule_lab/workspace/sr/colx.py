import sys, os, warnings, re, unicodedata
warnings.filterwarnings('ignore')
import pdfplumber

def norm(s):
    s=unicodedata.normalize('NFKD',s)
    for a,b in [('’',"'"),('‘',"'"),('‛',"'"),('′',"'"),('“','"'),('”','"'),('„','"'),
                ('‐','-'),('‑','-'),('‒','-'),('–','-'),('—','-'),('―','-'),('−','-'),
                ('\u00a0',' '),('\u2009',' '),('\u202f',' '),('\u200a',' '),('\u2007',' '),
                ('∗','*'),('⁎','*'),('…','...'),('ﬁ','fi'),('ﬂ','fl'),('ﬀ','ff'),('ﬃ','ffi'),('ﬄ','ffl')]:
        s=s.replace(a,b)
    s=re.sub(r'-\s*\n\s*','',s); s=re.sub(r'\s+',' ',s); s=re.sub(r"['\"]",'',s)
    return s.lower().strip()

def page_text(pg):
    """Try 1-col and 2-col reading orders; return both concatenated."""
    outs=[]
    t=pg.extract_text() or ''
    outs.append(t)
    w=pg.width
    for split in (0.5,):
        left=pg.crop((0,0,w*split,pg.height)).extract_text() or ''
        right=pg.crop((w*split,0,w,pg.height)).extract_text() or ''
        outs.append(left+'\n'+right)
    return '\n'.join(outs)

def load(path):
    parts=[]
    with pdfplumber.open(path) as pdf:
        for pg in pdf.pages:
            try: parts.append(page_text(pg))
            except Exception: pass
    return norm('\n'.join(parts))

if __name__=='__main__':
    p=sys.argv[1]; out=p+'.col.txt'
    if os.path.exists(out): sys.exit(0)
    try: t=load(p)
    except Exception: t=''
    open(out,'w').write(t)
