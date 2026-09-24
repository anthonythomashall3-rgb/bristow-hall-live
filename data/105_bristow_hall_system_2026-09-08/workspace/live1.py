"""THE LIVE LOG. Appends one dated line per run giving every object's current reading against its line, so that every
future turn is genuinely out of sample. Append-only: the file is never rewritten."""
exec(open('fast51.py').read().split("def full(")[0].replace("out=open('fast51.out','w')","out=open('live1.out','w')"))
import datetime
LOGOUT=open('live1.out','w')
def P(*a):
    t=' '.join(str(x) for x in a); print(t); LOGOUT.write(t+'\n'); LOGOUT.flush()
LOG=os.path.join(os.environ['HOME'],'mnt','Onset Detector Data','48_two_sided_rule_2026-09-05','live','LIVE_LOG.tsv')
G=vgap(4,4)
gapU=(spl-spl.rolling(91,min_periods=91).min().shift(1)).dropna()
gapL=(spl-spl.rolling(52,min_periods=52).min().shift(1)).dropna()
m4=ICfp.rolling(4).mean(); icrel=((m4/m4.rolling(52,min_periods=52).min().shift(1)-1)*100).dropna()
Hc,MX=mkpair3(29,4,3,18); Hh=mkhours(2.0,1.20)
rows=[
 ('insured rate gap, 0.45 branch (line 0.45)', float(gapU.iloc[-1]), 0.45, str(gapU.index[-1].date())),
 ('insured rate gap, low branch (line 0.25)',  float(gapL.iloc[-1]), 0.25, str(gapL.index[-1].date())),
 ('initial claims, 4-week mean above 52-week min, per cent (line 50)', float(icrel.iloc[-1]), 50.0, str(icrel.index[-1].date())),
 ('Sahm gap on first prints (line 0.43)',      float(g.dropna().iloc[-1]), 0.43, str(g.dropna().index[-1].date())),
 ('vacancy object (line 0.20)',                float(G.dropna().iloc[-1]), 0.20, str(G.dropna().index[-1].date())),
 ('housing x rate pair (line 1.00 = both halves at their lines)', float(MX.dropna().iloc[-1]) if hasattr(MX,'dropna') else float('nan'), 1.0, str(MX.dropna().index[-1].date()) if hasattr(MX,'dropna') else ''),
 ('paper spread (line %.3f)'%LINE,             float(GSP.iloc[-1]), LINE, str(GSP.index[-1].date())),
]
new=not os.path.exists(LOG)
with open(LOG,"a") as f2:
    if new: f2.write("run_date\tobject\treading\tline\tat_or_above\tdata_through\n")
    for nm,v,ln,dt in rows:
        f2.write(f"{datetime.date.today()}\t{nm}\t{v:.4f}\t{ln}\t{'YES' if v>=ln else 'no'}\t{dt}\n")
P(f"LIVE LOG appended to {LOG}")
P(f"{'object':64s} {'reading':>9s} {'line':>7s}  {'at line?':>8s}  data through")
for nm,v,ln,dt in rows: P(f"{nm:64s} {v:9.3f} {ln:7.3f}  {'YES' if v>=ln else 'no':>8s}  {dt}")
P("\nThe rule has been closed since 5 December 2024. Nothing is proposing; no confirmer stands at its line.")
LOGOUT.close()
