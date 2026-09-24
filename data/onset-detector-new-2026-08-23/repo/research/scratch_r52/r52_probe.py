#!/usr/bin/env python3
"""CH-R52 baseline divergence profile. Read-only. Reuses ch1_probe machinery via
method_source/index_v1 (NOWCAST_DISABLE=1). Writes JSON+CSV evidence only. No vault write."""
import os, sys, json, datetime as dt, bisect
import numpy as np

REPO = "/Users/anthonyhall/Desktop/RecessionMonitor 2/Recession Monitor V2"
MSRC = REPO + "/method_source"
WORK = REPO + "/research/channel_structure_ch1/scratch/work"
OUT  = REPO + "/research/scratch_r52"

os.environ["NOWCAST_DISABLE"] = "1"
os.environ["INDEX_OUT"] = OUT + "/index_v1_out.scratch.json"
os.chdir(WORK)
sys.path.insert(0, MSRC)
import index_v1 as m

CHAN = m.CHANNELS
CH_ORDER = list(CHAN.keys())
MEMBERS = []
for c in CH_ORDER: MEMBERS += CHAN[c][1]
DAYS = m.DAYS; START, END = m.START, m.END
T = m.T; RECS = m.RECS
W = np.array([CHAN[c][0] for c in CH_ORDER])

def asof(zdict, keys, d):
    i = bisect.bisect_right(keys, d) - 1
    return zdict[keys[i]] if i >= 0 else None

# ---- baseline mu/sd estimators (identical to ch1_probe §5) ----
def mu_current(name, ks, vals):
    base = [T[name][k] for k in ks if m.is_baseline(k)]
    mu = sum(base)/len(base); sd = (sum((x-mu)**2 for x in base)/len(base))**0.5
    return mu, sd
def mu_stat_mean(name, ks, vals):
    return float(vals.mean()), float(vals.std())
def mu_stat_median(name, ks, vals):
    med = float(np.median(vals)); mad = float(np.median(np.abs(vals-med)))*1.4826
    return med, mad
def rebuild_Z(mu_fn):
    Zalt = {}
    for name in MEMBERS + ["NFCI"]:
        ks = sorted(T[name]); vals = np.array([T[name][k] for k in ks])
        mu, sd = mu_fn(name, ks, vals)
        if sd == 0 or np.isnan(sd): sd = 1.0
        zd = {k: (T[name][k]-mu)/sd for k in ks}
        Zalt[name] = (zd, ks, mu, sd)
    return Zalt

def headline_from_CS(CS):
    line = np.full(len(DAYS), np.nan)
    for i in range(len(DAYS)):
        present = ~np.isnan(CS[i])
        if not present.any(): continue
        wsum = W[present].sum()
        line[i] = np.sum(W[present]*CS[i][present])/wsum
    return line

def build(Zalt):
    Xa = np.full((len(DAYS), len(MEMBERS)), np.nan)
    for j, name in enumerate(MEMBERS):
        zd, ks = Zalt[name][0], Zalt[name][1]
        for i, d in enumerate(DAYS):
            v = asof(zd, ks, d)
            if v is not None: Xa[i, j] = v
    CSa = np.full((len(DAYS), len(CH_ORDER)), np.nan)
    for ci, c in enumerate(CH_ORDER):
        idx = [MEMBERS.index(x) for x in CHAN[c][1]]
        sub = Xa[:, idx]
        for i in range(len(DAYS)):
            row = sub[i][~np.isnan(sub[i])]
            if len(row): CSa[i, ci] = row.mean()
    return headline_from_CS(CSa), Xa

Zc = rebuild_Z(mu_current)
Zm = rebuild_Z(mu_stat_mean)
Zd = rebuild_Z(mu_stat_median)
line_cur, Xc = build(Zc)
line_mean, Xm = build(Zm)
line_med, Xd = build(Zd)

def dist(series, label):
    ok = ~np.isnan(series)
    v = series[ok]
    dd = np.array([DAYS[i] for i in range(len(DAYS)) if ok[i]])
    sd = float(v.std())
    pct = {p: round(float(np.percentile(v, p)),4) for p in (1,5,25,50,75,95,99)}
    exc = {}
    for k in (1,2,5):
        mask = np.abs(v) > k*sd
        exc[f"gt_{k}sigma"] = {"count": int(mask.sum()),
                               "first": (dd[mask][0].isoformat() if mask.any() else None),
                               "last": (dd[mask][-1].isoformat() if mask.any() else None)}
    amax = int(np.argmax(np.abs(v)))
    return {"label": label, "n": int(ok.sum()),
            "mean": round(float(v.mean()),4), "median": round(float(np.median(v)),4),
            "sd": round(sd,4), "iqr": round(float(np.percentile(v,75)-np.percentile(v,25)),4),
            "min": round(float(v.min()),4), "min_date": dd[int(np.argmin(v))].isoformat(),
            "max": round(float(v.max()),4), "max_date": dd[int(np.argmax(v))].isoformat(),
            "max_abs": round(float(np.abs(v).max()),4), "max_abs_date": dd[amax].isoformat(),
            "pct": pct, "sigma_exceedances": exc}

# divergence = statistical - current  (signed)
div_med = line_med - line_cur
div_mean = line_mean - line_cur

prof = {"median_mad": dist(div_med, "stat_median_mad - current"),
        "mean_sd": dist(div_mean, "stat_mean - current")}

# ---- per-episode + expansion profile ----
def win_stats(series, a, b):
    idx = [i for i,d in enumerate(DAYS) if a<=d<=b and not np.isnan(series[i])]
    if not idx: return None
    v = np.array([series[i] for i in idx])
    ds = [DAYS[i] for i in idx]
    ap = int(np.argmax(np.abs(v)))
    return {"n_days": len(idx), "mean": round(float(v.mean()),4),
            "peak_signed": round(float(v[ap]),4), "peak_date": ds[ap].isoformat(),
            "sign": "positive" if v.mean()>0 else "negative"}

episodes = {}
for nm,(a,b) in RECS.items():
    episodes[nm] = {"window": [a.isoformat(), b.isoformat()],
                    "median_mad": win_stats(div_med,a,b),
                    "mean_sd": win_stats(div_mean,a,b)}

# expansions = gaps between consecutive RECS windows (sorted)
srt = sorted(RECS.items(), key=lambda kv: kv[1][0])
expansions = {}
prev_end = START
for nm,(a,b) in srt:
    if a > prev_end:
        key = f"exp_before_{nm}"
        ga, gb = prev_end, a - dt.timedelta(days=1)
        expansions[key] = {"window":[ga.isoformat(),gb.isoformat()],
                           "median_mad": win_stats(div_med,ga,gb),
                           "mean_sd": win_stats(div_mean,ga,gb)}
    prev_end = max(prev_end, b + dt.timedelta(days=1))
if prev_end < END:
    expansions["exp_after_last"] = {"window":[prev_end.isoformat(),END.isoformat()],
        "median_mad": win_stats(div_med,prev_end,END),
        "mean_sd": win_stats(div_mean,prev_end,END)}

# ---- severity-peak table (max of each own line in window) reproduce correction doc ----
def sev(line):
    o={}
    for nm,(a,b) in RECS.items():
        w=[line[i] for i,d in enumerate(DAYS) if a<=d<=b and not np.isnan(line[i])]
        o[nm]=round(float(max(w)),3) if w else None
    return o
sev_cur, sev_med, sev_mean = sev(line_cur), sev(line_med), sev(line_mean)
sev_table={}
for nm in RECS:
    c,s = sev_cur[nm], sev_med[nm]
    sev_table[nm]={"current":c,"stat_median":s,"delta":round(s-c,3),
                   "rel_pct":round(100*(s-c)/c,1) if c else None,
                   "stat_mean":sev_mean[nm]}

# ---- 1981-82 attribution: decompose divergence at the current-line peak date ----
def peak_date_in(line, a, b):
    best=None;bd=None
    for i,d in enumerate(DAYS):
        if a<=d<=b and not np.isnan(line[i]):
            if best is None or line[i]>best: best=line[i];bd=d;bi=i
    return bd, bi, best
a82,b82 = RECS["1981-82"]
pd82, pi82, _ = peak_date_in(line_cur, a82, b82)
# per-member divergence contribution to headline at that date (median/mad estimator)
def contrib_at(i, Xstat, Xcur):
    present_ch = ~np.isnan(np.array([np.nanmean([Xcur[i,MEMBERS.index(x)] for x in CHAN[c][1]]) if any(~np.isnan([Xcur[i,MEMBERS.index(x)] for x in CHAN[c][1]])) else np.nan for c in CH_ORDER]))
    wsum = W[present_ch].sum()
    rows={}
    for ci,c in enumerate(CH_ORDER):
        mem=CHAN[c][1]
        n=len(mem)
        for x in mem:
            j=MEMBERS.index(x)
            zc=Xcur[i,j]; zs=Xstat[i,j]
            if np.isnan(zc) or np.isnan(zs): continue
            # member weight in headline = channel_weight/wsum * 1/n_present_in_channel
            npr=sum(1 for y in mem if not np.isnan(Xcur[i,MEMBERS.index(y)]))
            w = W[ci]/wsum * (1.0/npr)
            rows[x]={"channel":c,"z_cur":round(float(zc),4),"z_stat":round(float(zs),4),
                     "dz":round(float(zs-zc),4),"weight":round(float(w),4),
                     "div_contrib":round(float(w*(zs-zc)),4)}
    return rows, round(float(sum(r["div_contrib"] for r in rows.values())),4)
contrib82, total82 = contrib_at(pi82, Xd, Xc)
ranked82 = sorted(contrib82.items(), key=lambda kv: kv[1]["div_contrib"])

result = {
  "batch_id":"CH-R52_BASELINE_DIVERGENCE_PROFILE","writes_vault":False,"network":False,
  "reproduced_ch1_headline":{"corr_median": float(np.corrcoef(line_cur[~np.isnan(line_cur)&~np.isnan(line_med)],line_med[~np.isnan(line_cur)&~np.isnan(line_med)])[0,1]),
     "max_abs_div_median": round(float(np.nanmax(np.abs(div_med))),4),
     "max_abs_div_median_date": DAYS[int(np.nanargmax(np.abs(div_med)))].isoformat()},
  "q1_q2_distribution": prof,
  "q3_episodes": episodes, "q3_expansions": expansions,
  "q3_severity_peak_table": sev_table,
  "q4_1981_82_attribution":{
     "current_peak_date": pd82.isoformat(),
     "divergence_at_current_peak_median": round(float(div_med[pi82]),4),
     "severity_delta_median": sev_table["1981-82"]["delta"],
     "note":"severity_delta compares each line's OWN max (possibly different dates); divergence_at_current_peak is pointwise",
     "total_div_contrib_at_peak": total82,
     "members_ranked_by_div_contrib": [{ "member":k, **v} for k,v in ranked82]},
}
json.dump(result, open(OUT+"/baseline_divergence_profile_v1.json","w"), indent=1)

# full signed series CSV
import csv
with open(OUT+"/baseline_divergence_series_v1.csv","w",newline="") as f:
    wtr=csv.writer(f)
    wtr.writerow(["date","line_current","line_stat_median_mad","line_stat_mean","div_median_mad","div_mean_sd"])
    for i,d in enumerate(DAYS):
        def r(x): return "" if np.isnan(x) else round(float(x),6)
        wtr.writerow([d.isoformat(),r(line_cur[i]),r(line_med[i]),r(line_mean[i]),r(div_med[i]),r(div_mean[i])])
print("WROTE", OUT)
print("DIST_MEDIAN", json.dumps(prof["median_mad"]))
