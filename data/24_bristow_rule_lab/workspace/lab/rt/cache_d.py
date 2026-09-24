"""Precompute the as-of composite deviation D on every vintage day, per panel and smoothing."""
import sys, pickle, pandas as pd
sys.path.insert(0, '/home/claude'); sys.path.insert(0, '/home/claude/lab/rt')
import bristow_rule_v3 as br, alfred as al, replay as rp

def build(panel, smooth, lookback=12, min_channels=2, t0='1962-01-01', t1='2026-08-31'):
    spec = rp.PANELS[panel]; out = {}
    for T in rp.vintage_days(spec, pd.Timestamp(t0), pd.Timestamp(t1)):
        ch = rp.panel_asof(spec, T)
        if len(ch) < min_channels: continue
        out[T] = br.composite_deviation(ch, lookback, smooth, min_channels).dropna()
    with open(f'/home/claude/lab/rt/D_{panel}_s{smooth}.pkl', 'wb') as f: pickle.dump(out, f)
    print(panel, smooth, len(out), 'days')

if __name__ == '__main__':
    build(sys.argv[1], int(sys.argv[2]))
