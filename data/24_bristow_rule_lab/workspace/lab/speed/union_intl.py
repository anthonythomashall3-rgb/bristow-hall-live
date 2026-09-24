"""The union rule of section 8f applied outside the United States, at the trough: every
object the record holds for an economy read at once, the earliest publication the call.

Objects, each with its own record already in the memo, read from the logs beside them (the
line named is the one the memo cites; nothing is re-chosen here):
  euro area  member-state breadth of industry confidence (breadth_ec_EA.log, 'best with no
             other call k=1 q=90 r=1', the industry-confidence block); the tool's own trough
             clause on D (twostage_ec_EA.log)
  Germany    the tool's clause on D; the Commission's industry-and-consumer confidence after D
             (twostage_ec_DE.log, a=8 r=1, the setting that calls all four); the daily
             truck-toll index (maut_de.log, arm 15 run 4 drop 1, the two troughs it can see)
  Japan      the Economy Watchers Survey after D (twostage_jp.log, national DI a=8 r=1); the
             tool's clause on D
  Mexico     INEGI's business survey after D (twostage_mx.log, IAT domestic demand a=8 r=1);
             the tool's clause on D
Publication months are the logs' 'pub' months (the survey month itself for the zero-lag
surveys, +2 for the activity clause); the toll index's are its dates.  A trough's call is the
earliest publication among the objects whose date lies within six months of the committee's;
in-month = publication month no later than the month after the trough month; other calls are
each object's, distinct episodes once (calls within six months of each other merged).
"""
import re, sys
import pandas as pd
S='/home/claude/lab/speed'
def md(a,b): return (a.year-b.year)*12+(a.month-b.month)
def parse(text):
    out={}
    for m in re.finditer(r"'(\d{4}-\d{2})': \('(\d{4}-\d{2})', (-?\d+), 'pub (\d{4}-\d{2})'",text): out[m[1]]=(pd.Timestamp(m[4]+'-01'),pd.Timestamp(m[2]+'-01'))
    o=re.search(r"other: \[(.*?)\]",text)
    others=[pd.Timestamp(p+'-01') for p,d in re.findall(r"\('(\d{4}-\d{2})', '(\d{4}-\d{2})'\)",o.group(1))] if o else []
    return out,others
def block(path, label, occurrence=0):
    L=open(path).read().split('\n')
    hits=[i for i,l in enumerate(L) if l.strip().startswith(label)]
    i=hits[occurrence]
    return parse('\n'.join(L[i:i+3]))
ECON={
 'euro area (CEPR, quarters as mid-months)':{'troughs':['1993-08','2009-05','2013-02','2020-05'],
    'objects':{'member-state survey breadth':block(f'{S}/breadth_ec_EA.log','best with no other call k=1 q=90 r=1',1),
               "the tool's clause on D":block(f'{S}/twostage_ec_EA.log',"the tool's own clause on D",0)}},
 'Germany (the Council)':{'troughs':['1993-07','2003-06','2009-04','2020-04'],
    'objects':{"the tool's clause on D":block(f'{S}/twostage_ec_DE.log',"the tool's own clause on D",0),
               'industry and consumer confidence after D':block(f'{S}/twostage_ec_DE.log','industry and consumer confidence a=8.0 r=1',0),
               'daily truck-toll index':({'2009-04':(pd.Timestamp('2009-06-01'),pd.Timestamp('2009-04-01')),'2020-04':(pd.Timestamp('2020-05-01'),pd.Timestamp('2020-04-01'))},[])}},
 'Japan (ESRI)':{'troughs':['2002-01','2009-03','2012-11','2020-05'],
    'objects':{'Economy Watchers Survey after D':block(f'{S}/twostage_jp.log','national DI a=8 r=1',0),
               "the tool's clause on D":block(f'{S}/twostage_jp.log',"the tool's own clause on D",0)}},
 'Mexico (the committee)':{'troughs':['2009-05','2020-05'],
    'objects':{'INEGI business survey after D':block(f'{S}/twostage_mx.log','IAT domestic demand a=8 r=1',0),
               "the tool's clause on D":block(f'{S}/twostage_mx.log',"the tool's own clause on D",0)}},
}
if __name__=='__main__':
    tot=dict(n=0,called=0,inm=0,other=0)
    for name,cfg in ECON.items():
        T=[pd.Timestamp(t+'-01') for t in cfg['troughs']]
        print(f'\n=== {name}: troughs {cfg["troughs"]}')
        for k,(calls,oth) in cfg['objects'].items():
            print(f'   {k:44s} {[(t,p.strftime("%Y-%m"),d.strftime("%Y-%m")) for t,(p,d) in calls.items()]}  other {[o.strftime("%Y-%m") for o in oth]}')
        n_in=0; called=0; lines=[]
        for t in T:
            best=None
            for k,(calls,oth) in cfg['objects'].items():
                for key,(p,d) in calls.items():
                    if abs(md(d,t))<=6 and (best is None or p<best[1]): best=(k,p,d)
            if best is None: lines.append(f'   {t:%Y-%m}: not called'); continue
            called+=1; inm=md(best[1],t)<=1; n_in+=inm
            lines.append(f'   {t:%Y-%m}: called {best[1]:%Y-%m} ({md(best[1],t):+d} months) by {best[0]}, dated {best[2]:%Y-%m} ({md(best[2],t):+d}) {"IN MONTH" if inm else ""}')
        print('\n'.join(lines))
        others=sorted(set(o for calls,oth in cfg['objects'].values() for o in oth))
        eps=[]
        for o in others:
            if eps and md(o,eps[-1])<=6: continue
            eps.append(o)
        print(f'   union: {called}/{len(T)} called, {n_in} inside the month; other episodes {len(eps)}: {[e.strftime("%Y-%m") for e in eps]}')
        tot['n']+=len(T); tot['called']+=called; tot['inm']+=n_in; tot['other']+=len(eps)
    print(f"\nall four: {tot['called']}/{tot['n']} called, {tot['inm']} inside the month, {tot['other']} other episodes")
