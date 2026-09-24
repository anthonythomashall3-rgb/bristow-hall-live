"""Every monthly end of all thirteen chronologies on one denominator.

The nine chronologies the configuration was chosen on are dated exactly as tool_check.py
dates them (same panels, same skip set, same shipped configuration); the four held-out
chronologies are read from lab/cmp/rulings_heldout.csv, which rulings_heldout.py writes from
the four held-out scripts run live.  Quarterly-dated contractions are left out (they are
scored in quarters, memo section 1); the five walls of the nine chronologies (Japan 1951 both
ends, Canada 1947 both ends, the Japan 1964 peak) are left out of the reachable rows and
counted in the raw row, exactly as memo section 1 does.

Prints, for peaks and troughs separately: n, exact month, within one, within two, within
three, mean absolute error - for the nine (reachable and raw), for the four held out, and for
all thirteen together.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import bristow_rule_v3 as B
import pandas as pd, numpy as np
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.ABSTAIN=True
CONC={'United States':'level','United States (interwar)':'level','Canada':'level','Brazil':'level',
      'Euro area':'level','Spain':'level','France':'level','Japan':'diffusion','Korea':'growth'}
WALL_P={('Japan','1951-06'),('Canada','1947-08'),('Japan','1964-10')}
WALL_T={('Japan','1951-06'),('Canada','1947-08')}
def nine():
    P=[];T=[]   # (country, peak label, signed error or None, is_wall)
    for c in ALL:
        cfg=PANELS[c]; chs=[(nm,s) for nm,s in channels(c) if nm not in bench.SKIP]
        for _e in cfg['chrono']:
            pk_off,tr_off,freq=ep3(_e,cfg['freq'])
            if freq!='M': continue
            pkm=ts(pk_off); trm=ts(tr_off)
            w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
            use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
            if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=trm and s.index.max()>=trm]
            if not use: use=chs
            vol=quantity(c,use) or use
            r=B.date_turning_points(use,w0,w1,volume_channels=vol,concept=CONC[c],
                                    lam=500000.0,band_trough=0.12,band_peak=0.01,peak_cap=18,
                                    smooth=3,lookback=12,dating_series=dating_series(c,w0,trm))
            ep=md(r['peak'],pkm) if r['peak'] is not None else None
            et=md(r['trough'],trm) if r['trough'] is not None else None
            P.append((c,pk_off,ep,(c,pk_off[:7]) in WALL_P)); T.append((c,pk_off,et,(c,pk_off[:7]) in WALL_T))
    return P,T
def stat(errs, label):
    """errs: list of signed errors; None = undated (counted as a miss at every band)"""
    n=len(errs); e=np.array([x for x in errs if x is not None],dtype=float)
    f=lambda k: int((np.abs(e)<=k).sum())
    mae=float(np.abs(e).mean()) if len(e) else float('nan')
    print(f'{label:58s} n {n:3d}  exact {f(0):3d}  w1 {f(1):3d}  w2 {f(2):3d}  w3 {f(3):3d}  mae {mae:.2f}')
    return n,f(0),f(1),f(2),f(3),mae
if __name__=='__main__':
    P,T=nine()
    print('the nine chronologies, monthly ends')
    stat([e for c,k,e,w in P if not w],'peaks, reachable (walls out)')
    stat([e for c,k,e,w in T if not w],'troughs, reachable (walls out)')
    stat([e for c,k,e,w in P],'peaks, raw (walls in, undated = miss)')
    stat([e for c,k,e,w in T],'troughs, raw (walls in, undated = miss)')
    h=pd.read_csv('/home/claude/lab/cmp/rulings_heldout.csv')
    hp=[float(x) for x in h[h.kind=='P'].rule_err]; ht=[float(x) for x in h[h.kind=='T'].rule_err]
    print('the four held out (South Africa, Taiwan, Germany, Mexico), from rulings_heldout.csv')
    stat(hp,'peaks'); stat(ht,'troughs')
    print('all thirteen chronologies, every monthly end, reachable')
    ap=[e for c,k,e,w in P if not w]+hp; at=[e for c,k,e,w in T if not w]+ht
    stat(ap,'peaks, all monthly ends'); stat(at,'troughs, all monthly ends')
    print('all thirteen chronologies, every monthly end, raw')
    stat([e for c,k,e,w in P]+hp,'peaks, all monthly ends, walls in')
    stat([e for c,k,e,w in T]+ht,'troughs, all monthly ends, walls in')
