import sys; sys.path.insert(0,'/home/claude/lab')
import pandas as pd, numpy as np
from final_rule import load, drawdown, channel_date

# ---------------- Bristow onset rule (mirror of the trough clause) ----------------
def channel_peak(level, w0, w1, band=0.02, smooth=3):
    """Last month the level stays within `band` of its cyclical high inside the window."""
    m = level.rolling(smooth).mean()[w0:w1].dropna()
    if len(m) < 4: return None
    hi = float(m.max()); i = m.idxmax()
    lo = float(m[i:].min()) if len(m[i:]) else float(m.min())
    amp = max(hi - lo, 1e-9)
    on_top = m[m >= hi - band * amp]
    return on_top.index[-1] if len(on_top) else i

def peak_date(channels, w0, w1, band=0.02):
    ds = sorted(d for d in (channel_peak(x, w0, w1, band) for x in channels) if d is not None)
    if not ds: return None
    return ds[(len(ds)-1)//2] if len(ds) % 2 == 0 else ds[len(ds)//2]

# ---------------- Bry-Boschan (monthly), the literature benchmark ----------------
def _alternate(out, v):
    """Keep strict peak-trough alternation, retaining the more extreme of any run."""
    res = []
    for i, k in out:
        if res and res[-1][1] == k:
            j, _ = res[-1]
            if (k == 'P' and v[i] > v[j]) or (k == 'T' and v[i] < v[j]): res[-1] = (i, k)
        else:
            res.append((i, k))
    return res

def bry_boschan(x, smooth=3, window=5, min_phase=5, min_cycle=15):
    """Local extrema with alternation and the standard censoring rules
    (Bry and Boschan 1971: minimum phase 5 months, minimum cycle 15 months).

    Alternation is re-imposed after every censoring pass.  Censoring can delete a
    turning point that was separating two of the same kind, and without re-imposing
    alternation the routine returns runs of consecutive peaks - which then corrupt
    any phase or diffusion series built from its output.
    """
    m = x.rolling(smooth, center=True).mean().dropna()
    v = m.values; idx = m.index
    cand = []
    for i in range(window, len(v) - window):
        seg = v[i-window:i+window+1]
        if seg.max() == seg.min(): continue
        if v[i] == seg.max(): cand.append((i, 'P'))
        elif v[i] == seg.min(): cand.append((i, 'T'))
    out = _alternate(cand, v)

    for _ in range(50):
        before = list(out)
        # censor phases shorter than min_phase
        changed = True
        while changed and len(out) > 2:
            changed = False
            for a in range(len(out) - 1):
                if out[a+1][0] - out[a][0] < min_phase:
                    keep_first = (abs(v[out[a][0]]) >= abs(v[out[a+1][0]]))
                    out.pop(a + (0 if not keep_first else 1))
                    changed = True; break
        out = _alternate(out, v)
        # censor cycles shorter than min_cycle (peak to peak, trough to trough)
        changed = True
        while changed and len(out) > 3:
            changed = False
            for a in range(len(out) - 2):
                if out[a+2][0] - out[a][0] < min_cycle:
                    out.pop(a+1); changed = True; break
        out = _alternate(out, v)
        if out == before: break
    return [(idx[i], k) for i, k in out]
