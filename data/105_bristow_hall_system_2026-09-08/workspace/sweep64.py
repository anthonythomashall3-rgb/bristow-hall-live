"""The second-condition hunt, re-run at the CORRECTED window.

Every previous sweep priced candidates over a window reaching no months
forward. The window now reaches four, and the exposure ranking is not the same
-- ETA 5159 went from free to x1.21 under exactly that change. So the shelf is
swept again, and the target is specific: the claims side already reaches
January 1980 at -14 days, March 2001 at -9 and December 2007 at -3, and the
second condition is sitting on all three. An object that releases them at ZERO
added exposure is free speed; nothing else is admissible under Rule 21.
"""
exec(open('hazard_v5.py').read().split('print("CONTROL')[0])
import glob, os, csv
AL=os.path.expanduser("~/mnt/")+"Onset Detector Data/onset-detector-new-2026-08-23/27_realtime_vintages/alfred_all_vintages/"
BASE=[S,V,P3h,H]
base_e,_=win_expo(BASE,7,5)
print(f"the shipped confirming set's exposure at (6 back, 4 forward): {base_e:.2f}%")
print("target months, on first prints:  1979-12/1980-01   2001-02/2001-03   2007-11/2007-12\n")
TGT=[('1979-11','1980-02'),('2001-01','2001-04'),('2007-10','2008-01')]
def hits_at(o,l):
    o=o.dropna()
    return [any((o.index>=pd.Timestamp(a+'-01'))&(o.index<=pd.Timestamp(b+'-01'))&(o.values>=l))
            for a,b in TGT]
names=[os.path.basename(f).replace('_all_vintages.csv','') for f in sorted(glob.glob(AL+'*.csv'))]
SKIP={'USREC','RECPROUSM156N','SAHMCURRENT','SAHMREALTIME','GDPNOW','UNRATE','HOUST','PAYEMS','AWHMAN'}
out=[]
for nm in names:
    if nm in SKIP: continue
    try: v=first_prints(nm)
    except Exception: continue
    v=v.dropna()
    if len(v)<300 or v.index[0]>pd.Timestamp('1970-01-01'): continue
    forms={'fall from trailing 12-month max, %':(v.rolling(12).max()/v-1)*100,
           'fall from trailing 6-month max, %':(v.rolling(6).max()/v-1)*100,
           '3-month fall, %':-(v/v.shift(3)-1)*100,
           'rise over trailing 12-month min, level':v-v.rolling(12).min(),
           '3-month mean less 12-month min, level':v.rolling(3).mean()-v.rolling(12).min().shift(1)}
    for fn,o in forms.items():
        o=o.dropna()
        if len(o)<300: continue
        oq=o[quiet(o.index).reindex(o.index).fillna(False)]
        if len(oq)<200: continue
        for pct in (99.0,99.5,99.8,100.0):
            line=float(np.percentile(oq.values,pct))
            if not np.isfinite(line): continue
            got=hits_at(o,line)
            if sum(got)==0: continue
            h=(o>=line).reindex(pd.date_range('1949-01-01','2026-07-01',freq='MS')).fillna(False)
            e,_=win_expo(BASE+[h],7,5)
            if e<=base_e+1e-9:
                out.append((sum(got),nm,fn,round(line,3),round(pct,1),e,got))
out.sort(key=lambda r:(-r[0],r[5]))
seen=set(); n=0
print(f"{'series':12}{'form':40}{'line':>10}{'pct':>6}{'expo':>7}  releases 1980/2001/2007")
for g,nm,fn,line,pct,e,got in out:
    k=(nm,fn)
    if k in seen: continue
    seen.add(k); n+=1
    if n>25: break
    print(f"{nm:12}{fn:40}{line:10.3f}{pct:6.1f}{e:6.2f}%  " + ' '.join('YES' if x else ' - ' for x in got))
print(f"\n{len(out)} (series, form, line) combinations add ZERO exposure and release at least one wall.")
