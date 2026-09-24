exec(open("stage17_loo.py").read().split('print("\\nLEAVE-ONE-OUT')[0])
print("\nRECURSIVE (expanding-window) SELECTION: for recession k, choose the config using only recessions before k and only data before k's peak-2 months;")
print("criteria: zero false episodes so far, fewest onsets outside +-2 so far, then smallest sum|lag|, then fewest channels. Apply to recession k.")
def false_before(eps, cutoff, targets):
    res,false=score_eps(eps,targets); return [f for f in false if pd.Timestamp(f)<cutoff]
for k in range(3,9):
    train=list(range(k)); cutoff=(P(EPS[k][0])-2).to_timestamp()
    best=None
    for cfg in grid:
        res,false=score_eps(cache[cfg],EPS)
        L=[res[i]["lag"] for i in train]
        if any(l is None for l in L): continue
        nf=len([f for f in false if pd.Timestamp(f)<cutoff]); nchan=1+sum(x is not None and x is not False for x in cfg[1:])
        key=(nf, sum(abs(l)>2 for l in L), sum(abs(l) for l in L), nchan)
        if best is None or key<best[0]: best=(key,cfg)
    cfg=best[1]; res,false=score_eps(cache[cfg],EPS); r=res[k]
    nf_after=len([f for f in false if pd.Timestamp(f)>=cutoff and pd.Timestamp(f)<=(P(EPS[k][1])+12).to_timestamp()])
    print(f"  {EPS[k][0]}: trained on {k} recessions -> {cfg}; held-out onset {r['onset']} lag {r['lag']:+d}, end lag {r['end_lag']:+d}, trough err {r['tr_err']:+d}; false episodes in its window {nf_after}")
