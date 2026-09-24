"""The pull-back test (9 September 2026): the walk-end lines with the two proposers whose fast edge bought a week or
less pulled back one and two grid steps (insured 91-week 0.45 -> 0.55; claims 45 -> 50 and 60), frozen over 1948-2026:
which calls change, which false alarms appear, and the margins in 2022-2023. Run: /opt/homebrew/bin/python3 pullback.py"""
import sys,pickle
sys.argv=['pullback.py','1962','2026','m41']
exec(open('walk40.py').read().split('# ---- the walk itself')[0])
GRID=[(n,([x for x in g if x is not None]+[None]) if n in ('wline','wline2','bshare','cD') else g) for n,g in GRID]; GD=dict(GRID)
p0=pickle.load(open('cache/w40_carry.pkl','rb'))
cut=pd.Timestamp(2026,1,1); ks=[i for i in range(13) if ANNT[i]<cut]; kt=[i for i in range(13) if TANNT[i]<cut]
def calls(q):
    r,t=build_v(q)
    pk=[(x['published'].strftime('%Y-%m-%d'),x['leg']) for x in t if x['kind']=='peak' and x['published'].year>=1962]
    tr=[(x['published'].strftime('%Y-%m-%d'),x['leg']) for x in t if x['kind']=='trough' and x['published'].year>=1962]
    return pk,tr
base=calls(p0); print('walk-end lines, frozen, peaks 1962 on:',base[0]); print('  troughs:',base[1])
for name,q in [('u45 0.55',dict(p0,u45=0.55)),('ic 50',dict(p0,ic=50)),('ic 60',dict(p0,ic=60)),('u45 0.55 + ic 60',dict(p0,u45=0.55,ic=60)),('u45 0.55 + ic 60 + vl 0.25',dict(p0,u45=0.55,ic=60,vl=0.25))]:
    c=calls(q); dp=[(a,b) for a,b in zip(base[0],c[0]) if a!=b]; dt=[(a,b) for a,b in zip(base[1],c[1]) if a!=b]
    same=(len(c[0])==len(base[0]) and len(c[1])==len(base[1]))
    print('%-28s'%name,'same number of calls' if same else 'DIFFERENT COUNT %d/%d peaks %d/%d troughs'%(len(c[0]),len(base[0]),len(c[1]),len(base[1])),'| peak changes',dp,'| trough changes',dt)
    if not same: print('   peaks:',c[0]); print('   troughs:',c[1])
print('walked record (RECORD-w40) for comparison: opens 1969-08-21 1973-09-17 1979-11-29 1981-02-26 1990-08-03 2001-03-29 2008-01-04 2020-03-26 2024-05-03')
