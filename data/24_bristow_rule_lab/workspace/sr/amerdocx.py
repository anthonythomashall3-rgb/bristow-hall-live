import re, sys
sys.path.insert(0,'/home/claude')
from amer import MAP
EXTRA = [(r'\bstabiliser\b','stabilizer'), (r'\bstabilisers\b','stabilizers'),
         (r'\bcharacterisation\b','characterization'),
         (r'\bcolour\b','color'), (r'\bneighbours\b','neighbors'), (r'\bneighbouring\b','neighboring'),
         (r'\bminimise\b','minimize'), (r'\bminimising\b','minimizing'),
         (r'\bcriticises\b','criticizes'), (r'\bfavours\b','favors')]
RULES = MAP + EXTRA
# never touch: 'characteristics' (already US), 'programmed' (already US)
def quote_spans(t):
    sp=[]
    for m in re.finditer(r'[“"]([^“”"]{2,1500})[”"]', t): sp.append((m.start(1), m.end(1)))
    for m in re.finditer(r'‘([^’]{2,1500})’', t): sp.append((m.start(1), m.end(1)))
    for m in re.finditer(r'https?://\S+', t): sp.append((m.start(), m.end()))
    return sp
def replace_across_runs(p, start, end, new):
    runs=p.runs; pos=0; done=False
    for r in runs:
        a,b=pos,pos+len(r.text); pos=b
        if b<=start or a>=end: continue
        s=max(a,start)-a; e=min(b,end)-a
        if not done: r.text=r.text[:s]+new+r.text[e:]; done=True
        else: r.text=r.text[:s]+r.text[e:]
    return done
def fix_para(p):
    n=0
    while True:
        t=''.join(r.text for r in p.runs)
        sp=quote_spans(t)
        hit=None
        for pat,rep in RULES:
            for m in re.finditer(pat, t):
                if any(a<=m.start()<b for a,b in sp): continue
                hit=(m.start(), m.end(), rep); break
            if hit: break
        if not hit: return n
        if not replace_across_runs(p, *hit): return n
        n+=1
