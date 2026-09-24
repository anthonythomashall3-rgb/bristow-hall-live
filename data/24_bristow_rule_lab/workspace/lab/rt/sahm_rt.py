"""Paper 1's Bristow Rule - the month the Sahm indicator peaks, confirmed by the first decline -
replayed on the unemployment rate exactly as first published (ALFRED UNRATE vintages)."""
import sys, pandas as pd, numpy as np
sys.path.insert(0, '/home/claude/lab/rt'); import alfred as al, replay as rp
import bristow_rule_v3 as br

def sahm(u):
    m3 = u.rolling(3).mean()
    return m3 - m3.shift(1).rolling(12).min()   # Sahm: 3-mo mean minus its min over prior 12 months

def run(arm=0.50, confirm=1, verbose=True):
    calls = []; state = 'quiet'; peak_m = None; peak_v = None; declines = 0; called_at = None
    for T in al.vintages('UNRATE'):
        u = al.asof('UNRATE', T); s = sahm(u).dropna()
        if len(s) < 24: continue
        cur = s.index[-1]; v = float(s.iloc[-1])
        if state == 'quiet':
            if v >= arm:
                state = 'armed'; peak_m = cur; peak_v = v; declines = 0
            continue
        if state == 'armed':
            # re-evaluate the peak on the as-of data since arming
            seg = s[s.index >= peak_m - pd.DateOffset(months=0)] if False else s
            # peak = max since the arming crossing on THIS vintage
            armed_seg = s[s.index >= arm_start(s, arm, cur)]
            pm = armed_seg.idxmax(); pv = float(armed_seg.max())
            if cur > pm:
                after = armed_seg[armed_seg.index > pm]
                if len(after) >= confirm and all(after.iloc[k] < (after.iloc[k-1] if k>0 else pv) for k in range(len(after))):
                    calls.append((T, pm)); state = 'called'; called_at = pm
                    if verbose: print(f'  call {T.date()}: trough {pm:%Y-%m} (indicator {pv:.2f}), data through {cur:%Y-%m}')
            continue
        if state == 'called':
            # return to quiet when the indicator has fallen below arm again
            if v < arm: state = 'quiet'
            continue
    return calls

def arm_start(s, arm, cur):
    """First month of the current run at or above `arm` that ends before `cur` (the crossing)."""
    above = s >= arm
    # find the latest crossing from below within the last 36 months
    idx = s.index
    for i in range(len(s)-1, 0, -1):
        if above.iloc[i] and not above.iloc[i-1]: return idx[i]
    return idx[0]

if __name__ == '__main__':
    calls = run()
    rp.score(calls, 'Paper 1 rule on first-print UNRATE (arm 0.50, one decline)')
