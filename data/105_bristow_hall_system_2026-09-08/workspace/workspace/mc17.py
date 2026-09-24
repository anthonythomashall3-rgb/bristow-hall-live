"""WHY Q MISSES 1970, 1975 AND 2024, AND WHAT BINDS T IN 2024."""
import sys
sys.argv=['x','1962','2026']
src=open('walk25.py').read().split('BASE15=dict(BASE)')[0].replace("out=open('walk25_%s.out'%sys.argv[1],'w')","out=open('mc17.out','w')")
exec(src)
TR9=[pd.Timestamp(x) for x in ['1970-11-01','1975-03-01','1980-07-01','1982-11-01','1991-03-01','2001-11-01','2009-06-01','2020-04-01','2024-08-01']]
raw=_wsettle((-_ICW).rolling(4).mean().dropna(),8,156,5)
P("Q, the weekly claims settle before the date is attached and before the confirmations:")
for p_,w in raw: P(f"   settled {p_:%Y-%m-%d}  weekly month {w:%Y-%m}  monthly date {_bris_date(p_)}")
P("\nQ after dating and confirmation:")
for p_,d_ in TLH['Q']: P(f"   {p_:%Y-%m-%d} dated {d_:%Y-%m}")
P("\nT, the starts settle, raw:")
for p_,d_ in _settle_starts(): 
    if p_>=pd.Timestamp('1968-01-01'): P(f"   {p_:%Y-%m-%d} dated {d_:%Y-%m}")
P("\nT after the unemployment-rate guard:")
for p_,d_ in TLH['T']: P(f"   {p_:%Y-%m-%d} dated {d_:%Y-%m}")
P("\nthe monthly insured rate, three-month mean, around the misses (value and the month it is published):")
for a,b in [('1970-06','1971-06'),('1974-10','1975-12'),('2023-06','2025-06')]:
    seg=_MIm[(_MIm.index>=a)&(_MIm.index<=b)]
    P(f"   {a}..{b}: "+", ".join(f"{m:%Y-%m}={v:.3f}" for m,v in seg.items()))
out.close()
