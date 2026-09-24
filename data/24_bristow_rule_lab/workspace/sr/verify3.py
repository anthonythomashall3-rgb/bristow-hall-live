import json, os, re, glob
from colx import norm
def sq(s): return re.sub(r'\s+','',s)

# build url -> text-file map from every fetch round
umap={}
for i,u,p in json.load(open('targets.json')): umap.setdefault(u,[]).extend([p+'.col.txt',p+'.txt'])
for u,p in json.load(open('htargets.json')): umap.setdefault(u,[]).append(p+'.txt')
for i,u,p in json.load(open('targets_new.json')): umap.setdefault(u,[]).extend([p+'.col.txt'])
for u,p in json.load(open('htargets_new.json')): umap.setdefault(u,[]).append(p+'.txt')
# hand-fetched extras
extra={
 'https://www.hamiltonproject.org/assets/files/Sahm_web_20190506.pdf':['src/sahm_ch2.pdf.col.txt'],
 'https://www.richmondfed.org/-/media/RichmondFedOrg/publications/research/economic_quarterly/2003/summer/pdf/stockwatsonsummer03.pdf':['src/sw2003.pdf.col.txt'],
 'https://www.princeton.edu/~mwatson/papers/Stock_Watson_Predicting_Recessions_1993.pdf':['sw1993.pdf.col.txt'],
 'https://www.brookings.edu/wp-content/uploads/1991/06/1991b_bpea_bernanke_lown_friedman.pdf':['src/bl1991.pdf.col.txt'],
 'https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/coincident/state-business-cycle-update-highlights.pdf':['pf_highlights.pdf.col.txt'],
 'https://eml.berkeley.edu/~saez/michaillat-saezOBES25.pdf':['/home/claude/michez.pdf.col.txt'],
}
for k,v in extra.items(): umap.setdefault(k,[]).extend(v)

cache={}
def body(paths):
    key=tuple(paths)
    if key not in cache:
        t=''
        for p in paths:
            if os.path.exists(p):
                try: t+='\n'+open(p).read()
                except: pass
        n=norm(t); cache[key]=(n,sq(n))
    return cache[key]

def trim(s): return s.strip().strip(' ,.;:')
entries={x['idx']:x for x in json.load(open('entries2.json'))}
res=[]
for idx in sorted(entries):
    e=entries[idx]
    if not e['quotes']: continue
    bodies=[]
    for u in e['urls']:
        ps=umap.get(u)
        if ps: bodies.append((u,)+body(ps))
    have=any(n for _,n,_ in bodies)
    for q in e['quotes']:
        parts=[x for x in re.split(r'\s*(?:\.\.\.|…)\s*', q) if x.strip()]
        st=None; src=None
        for u,n,s in bodies:
            if not n: continue
            if all(norm(x) in n for x in parts): st,src='exact',u; break
            if all(norm(trim(x)) in n for x in parts): st,src='trimmed',u; break
            if all(sq(norm(trim(x))) in s for x in parts): st,src='nospace',u; break
        res.append({'idx':idx,'quote':q,'status':st,'src':src,'have':have})
json.dump(res,open('qr3.json','w'),indent=0)
import collections
c=collections.Counter(r['status'] or ('NOSRC' if not r['have'] else 'MISS') for r in res)
print(len(res),'quotes in linked entries:',dict(c))
