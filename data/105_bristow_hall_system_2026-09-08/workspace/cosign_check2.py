import sys,pickle,io,contextlib
sys.argv=['cosign_check2.py','1962','2026','mchk']
src=open('walk42.py').read().split('# ---- the walk itself')[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
import pandas as pd
p=pickle.load(open('cache/w42_carry.pkl','rb'))
# proposals of the claims object at 40 WITHOUT the co-signer (band 0 = every crossing fires), confirmed inside the window
def leg_ic_plain(s,pct,look=52):
    m4=s.rolling(4).mean(); rel_=(m4/m4.rolling(look,min_periods=look).min().shift(1)-1)*100
    c=[]; armed=True
    for t,v in rel_.dropna().items():
        if armed and v>=pct: c.append((rel_ic(t),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0: armed=True
    return c
G=vgap2(p['vk'],p['vb']); Hc,MX=mkpair3(p['starts'],p['half'],3,p['minw']); Hh=mkhours(p['hrs'],p['nd'])
C1=globals().get('C1')
plain=leg_ic_plain(ICfp,p['ic']); signed=leg_ic_c(ICfp,p['ic'])
print('claims proposals at 40 without co-signer, from 1962:',[(d.date().isoformat(),m.strftime('%Y-%m')) for d,m in plain if d.year>=1962])
print('claims proposals at 40 with co-signer, from 1962:',[(d.date().isoformat(),m.strftime('%Y-%m')) for d,m in signed if d.year>=1962])
m4=ICfp.dropna().rolling(4).mean(); rel_=((m4/m4.rolling(52,min_periods=52).min().shift(1)-1)*100).dropna()
w=rel_[(rel_.index>='2022-07-01')&(rel_.index<='2022-10-15')]
for t,v in w.items(): print('I',t.date(),'rel',rel_ic(t).date(),'pct %.1f'%v,'cosign',cosign(rel_ic(t)))
print('gpub 2022-23:',{k.date().isoformat():v for k,v in gpub[(gpub.index>='2022-06-01')&(gpub.index<='2023-06-01')].items()})
# was a confirmer in place for an August 2022 proposal? confirm_w over the plain proposals
try:
    conf=confirm_w(plain,C1,'month'); print('plain proposals confirmed:',[(a.date().isoformat(),b.strftime('%Y-%m'),c) for a,b,c in conf if a.year>=1962])
except Exception as e: print('confirm_w error',e)
