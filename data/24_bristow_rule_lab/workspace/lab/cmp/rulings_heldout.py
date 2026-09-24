"""The rule against ECRI on the four chronologies held out entirely (South Africa, Germany,
Mexico, Taiwan), the counterpart of rulings_all.py for the nine.

The rule's dates come from the four held-out scripts, run live (zaf_full.py, twn_test.py,
deu_test.py, mex/mex_test.py), the committee's date and the rule's error parsed from each
script's per-episode table.  ECRI's dates are the July 2021 table (ecri_chronology_2021.json;
ECRI_TABLE=2010 in the environment selects the September 2010 table).  A committee end is 'dated by ECRI' when ECRI lists a turn of the
same kind within twelve months of it; the comparison is like-for-like on those ends only.
Errors are in months, signed (rule or ECRI minus the committee), and the rule's error against
ECRI is the rule's date minus ECRI's.
"""
import sys, re, json, subprocess
import pandas as pd, numpy as np
LAB='/home/claude/lab'
import os
ECRI_TABLE=os.environ.get('ECRI_TABLE','2021')
ECRI=json.load(open(f'{LAB}/cmp/ecri_chronology_{ECRI_TABLE}.json'))
def md(a,b): return (a.year-b.year)*12+(a.month-b.month)
def run(script, cwd=LAB):
    r=subprocess.run([sys.executable,script],cwd=cwd,capture_output=True,text=True,timeout=3600)
    if r.returncode: print(r.stderr[-600:]); raise RuntimeError(script)
    return r.stdout
def table(text, header):
    """rows after the line starting with `header`, until a blank line: (peak, err, trough, err)"""
    out=[]; on=False
    for ln in text.splitlines():
        if ln.strip().startswith(header): on=True; continue
        if on:
            if not ln.strip(): break
            m=re.findall(r'(\d{4}-\d{2}|None)\s+(?:err\s+)?(-?\d+|None)',ln)
            if len(m)==2:
                (p,ep),(t,et)=m
                out.append((None if p=='None' else pd.Timestamp(p+'-01'), None if ep=='None' else int(ep),
                            pd.Timestamp(t+'-01'), int(et)))
    return out
HELD={}
HELD['South Africa']=table(run('zaf_full.py'),'per episode, the committee object')
HELD['Taiwan']=table(run('twn_test.py'),"per episode, the committee's own detrended index")
HELD['Germany']=table(run('deu_test.py'),'per episode, the four channels the Council itself names')
HELD['Mexico']=table(run('mex_test.py',cwd=f'{LAB}/mex'),'per episode:')
def near(lst, kind, ref, tol=12):
    c=[pd.Timestamp(d+'-01') for k,d in lst if k==kind]
    c=[d for d in c if abs(md(d,ref))<=tol]
    return min(c,key=lambda d:abs(md(d,ref))) if c else None
rows=[]
for name,eps in HELD.items():
    for p,ep,t,et in eps:
        for kind,cm,err in (('P',p,ep),('T',t,et)):
            if cm is None: continue
            e=near(ECRI[name],kind,cm)
            rows.append(dict(country=name,kind=kind,committee=cm.strftime('%Y-%m'),
                             rule_err=err, ecri=None if e is None else e.strftime('%Y-%m'),
                             ecri_err=None if e is None else md(e,cm),
                             rule_vs_ecri=None if e is None else err-md(e,cm)))
df=pd.DataFrame(rows)
print(df.to_string(index=False))
def cnt(e):
    e=np.array([x for x in e if x is not None and not (isinstance(x,float) and np.isnan(x))],dtype=float)
    return f'n {len(e)} exact {int((e==0).sum())} w1 {int((np.abs(e)<=1).sum())} w3 {int((np.abs(e)<=3).sum())} mean {np.abs(e).mean():.2f}'
both=df[df.ecri.notna()]
print()
print('ends the committees date:', len(df), '| of them dated by ECRI within twelve months:', len(both))
print('ECRI against the committees, those ends   :', cnt(both.ecri_err))
print('the rule against the committees, same ends:', cnt(both.rule_err))
print('the rule against ECRI, same ends          :', cnt(both.rule_vs_ecri))
print('the rule against the committees, all ends :', cnt(df.rule_err))
print('committee ends ECRI does not date:', [(r.country,r.kind,r.committee,r.rule_err) for r in df[df.ecri.isna()].itertuples()])
# ECRI turns with no committee counterpart within twelve months
extra=[]
for name,eps in HELD.items():
    cms=[(k,d) for p,ep,t,et in eps for k,d in (('P',p),('T',t)) if d is not None]
    for k,d in ECRI[name]:
        dd=pd.Timestamp(d+'-01')
        if not any(kk==k and abs(md(dd,c))<=12 for kk,c in cms): extra.append((name,k,d))
print('ECRI turns with no committee counterpart:', extra)
df.to_csv(f'{LAB}/cmp/rulings_heldout.csv',index=False)
