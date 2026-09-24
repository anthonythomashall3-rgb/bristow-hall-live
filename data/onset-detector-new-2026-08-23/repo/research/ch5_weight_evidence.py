#!/usr/bin/env python3
"""CH5 weight-derivation evidence (read-only, research/ only).

Reuses index_v1.py's EXACT per-member deterioration transforms + expansion-baseline
standardisation by exec'ing it in a temp raw/ dir (NOWCAST_DISABLE=1), then reads its
module globals (Z, DAYS, is_baseline, CHANNELS). Computes, on the current 17-member roster:
  (1) realized-contribution vector  RC_m = Cov(alpha_m z_m, H)/Var(H), sum_m RC_m = 1
      (CH1 §3 method: share of the composite's actual movement)
  (2) equal-risk-contribution (ERC) weights (risk parity on the member covariance)
  three ways: full / winsorized(±3sd) / ex-2020, plus rolling-10y drift of the channel
  realized vector. Nominal alpha_m = w_channel / n_members_in_channel.
"""
import os, sys, csv, json, math, datetime as dt, tempfile, shutil, runpy, io, contextlib

ROOT = os.path.abspath(os.path.dirname(__file__) + "/..")
CUR = os.path.join(ROOT, "data_archive/current_revised_and_spatial")
IDX = os.path.join(ROOT, "method_source/index_v1.py")
ALL = ["ICSA","IURSA","SAHMREALTIME","UNRATE","INDPRO","CMRMTSPL","TCU",
       "GACDFSA066MSFRBPHI","NASDAQCOM","BAA","AAA","BAA10Y","NFCI","VIXCLS","HOUST",
       "PERMIT","UMCSENT","W875RX1","GS10","GS1","USRECD",
       "RRSFS","MORTGAGE30US","PAYEMS","CCSA","DBAA","DAAA"]

# --- exec index_v1 in a temp raw/ dir; capture its module namespace ---
tmp = tempfile.mkdtemp(prefix="ch5_")
os.makedirs(os.path.join(tmp, "raw"), exist_ok=True)
for s in ALL:
    shutil.copy(os.path.join(CUR, s + ".csv"), os.path.join(tmp, "raw", s + ".csv"))
os.environ["NOWCAST_DISABLE"] = "1"
os.environ["INDEX_OUT"] = os.path.join(tmp, "out.json")
cwd0 = os.getcwd(); sys.path.insert(0, os.path.join(ROOT, "method_source"))
os.chdir(tmp)
with contextlib.redirect_stdout(io.StringIO()):
    G = runpy.run_path(IDX, run_name="ch5_idx")
os.chdir(cwd0)

Z = G["Z"]; DAYS = G["DAYS"]; is_baseline = G["is_baseline"]; CHANNELS = G["CHANNELS"]
import bisect
def zval(name, d):
    series, keys = Z[name]
    i = bisect.bisect_right(keys, d) - 1
    return series[keys[i]] if i >= 0 else None

MEMBERS = [m for _, (_, mems) in CHANNELS.items() for m in mems]
CH_OF = {m: c for c, (_, mems) in CHANNELS.items() for m in mems}
WCH = {c: w for c, (w, _) in CHANNELS.items()}
NCH = {c: len(mems) for c, (_, mems) in CHANNELS.items()}
# nominal linear coefficient of member m in H (all channels present -> denom=1.0)
ALPHA = {m: WCH[CH_OF[m]] / NCH[CH_OF[m]] for m in MEMBERS}

# --- monthly sampling (first of month) to tame daily autocorrelation; carry-forward ---
def month_grid(d0, d1):
    y, m = d0.year, d0.month; out = []
    while (y, m) <= (d1.year, d1.month):
        out.append(dt.date(y, m, 1)); m += 1
        if m > 12: y += 1; m = 1
    return out
GRID = month_grid(DAYS[0], DAYS[-1])
# rows: dates where ALL 17 members present (common support)
rows = []
for d in GRID:
    vec = {m: zval(m, d) for m in MEMBERS}
    if all(vec[m] is not None for m in MEMBERS):
        rows.append((d, vec))
D0, D1 = rows[0][0], rows[-1][0]

def winsor(series, k=3.0):
    mu = sum(series) / len(series)
    sd = (sum((x - mu) ** 2 for x in series) / len(series)) ** 0.5 or 1.0
    return [max(mu - k * sd, min(mu + k * sd, x)) for x in series]

def matrices(sub, do_winsor):
    # sub: list of (date, vec). returns member-order arrays of alpha*z and headline H
    cols = {m: [v[m] for _, v in sub] for m in MEMBERS}
    if do_winsor:
        cols = {m: winsor(cols[m]) for m in MEMBERS}
    contrib = {m: [ALPHA[m] * x for x in cols[m]] for m in MEMBERS}
    n = len(sub)
    H = [sum(contrib[m][i] for m in MEMBERS) for i in range(n)]
    return cols, contrib, H

def cov(a, b):
    n = len(a); ma = sum(a) / n; mb = sum(b) / n
    return sum((a[i] - ma) * (b[i] - mb) for i in range(n)) / n

def realized_contribution(sub, do_winsor):
    _, contrib, H = matrices(sub, do_winsor)
    vH = cov(H, H)
    rc = {m: cov(contrib[m], H) / vH for m in MEMBERS}
    return rc  # sums to 1 by construction

def erc_weights(sub, do_winsor, iters=20000, lr=0.02):
    # risk parity on the member (signed-deterioration z) covariance matrix
    cols, _, _ = matrices(sub, do_winsor)
    C = [[cov(cols[a], cols[b]) for b in MEMBERS] for a in MEMBERS]
    n = len(MEMBERS)
    x = [1.0 / n] * n
    for _ in range(iters):
        Cx = [sum(C[i][j] * x[j] for j in range(n)) for i in range(n)]
        rc = [x[i] * Cx[i] for i in range(n)]        # risk contributions
        tgt = sum(rc) / n
        g = [rc[i] - tgt for i in range(n)]
        x = [max(1e-6, x[i] - lr * g[i]) for i in range(n)]
        s = sum(x); x = [xi / s for xi in x]
    return {MEMBERS[i]: x[i] for i in range(n)}

def channelize(vec):
    out = {c: 0.0 for c in CHANNELS}
    for m in MEMBERS:
        out[CH_OF[m]] += vec[m]
    return out

# --- three-way vectors ---
full = rows
ex20 = [(d, v) for d, v in rows if not (dt.date(2020,1,1) <= d <= dt.date(2021,12,31))]
variants = {"full": (full, False), "winsor": (full, True), "ex2020": (ex20, False)}
RC = {k: realized_contribution(*variants[k]) for k in variants}
ERC = {k: erc_weights(*variants[k]) for k in variants}

# --- rolling 10y (120mo) windows, yearly step: channel realized vector drift ---
WIN = 120
starts = list(range(0, len(rows) - WIN + 1, 12))
roll_ch = []
for s in starts:
    sub = rows[s:s + WIN]
    rc = realized_contribution(sub, False)
    roll_ch.append((sub[0][0], channelize(rc)))
def drift(chan):
    vals = [rc[chan] for _, rc in roll_ch]
    mu = sum(vals) / len(vals)
    sd = (sum((v - mu) ** 2 for v in vals) / len(vals)) ** 0.5
    return mu, sd, min(vals), max(vals)

# --- FULL-SPAN channel realized vector on the TRUE renormalizing daily headline ---
# H(d) renormalizes over available channels (index_v1.headline). channel contribution
# term c(d) = w_c/wsum(d) * mean(member z). Covariance over all days both defined.
line = G["line"]                       # {date: headline}, 1976+ full span
def ch_score(members, d):
    vals = [zval(m, d) for m in members]
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None
fs_days = sorted(line)
Hf = [line[d] for d in fs_days]
fs_contrib = {}
for c, (w, mems) in CHANNELS.items():
    col = []
    for d in fs_days:
        cs = ch_score(mems, d)
        if cs is None: col.append(None); continue
        wsum = sum(WCH[cc] for cc, (_, mm) in CHANNELS.items() if ch_score(mm, d) is not None)
        col.append(w / wsum * cs)
    fs_contrib[c] = col
vHf = cov(Hf, Hf)
def cov_pair(col):                    # covariance over days where col defined
    idx = [i for i, x in enumerate(col) if x is not None]
    a = [col[i] for i in idx]; h = [Hf[i] for i in idx]
    return cov(a, h)
RC_fullspan = {c: cov_pair(fs_contrib[c]) / vHf for c in CHANNELS}

# --- write member-level CSV ---
outcsv = os.path.join(ROOT, "research/ch5_weight_evidence_v1.csv")
with open(outcsv, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["level","name","channel","nominal_alpha",
                "rc_full","rc_winsor","rc_ex2020",
                "erc_full","erc_winsor","erc_ex2020"])
    for m in MEMBERS:
        w.writerow([ "member", m, CH_OF[m], round(ALPHA[m],4),
            round(RC["full"][m],4), round(RC["winsor"][m],4), round(RC["ex2020"][m],4),
            round(ERC["full"][m],4), round(ERC["winsor"][m],4), round(ERC["ex2020"][m],4)])
    # channel rollups
    RCc = {k: channelize(RC[k]) for k in RC}
    ERCc = {k: channelize(ERC[k]) for k in ERC}
    for c in CHANNELS:
        w.writerow([ "channel", c, c, round(WCH[c],4),
            round(RCc["full"][c],4), round(RCc["winsor"][c],4), round(RCc["ex2020"][c],4),
            round(ERCc["full"][c],4), round(ERCc["winsor"][c],4), round(ERCc["ex2020"][c],4)])

# --- write rolling-drift CSV ---
rollcsv = os.path.join(ROOT, "research/ch5_rolling_drift_v1.csv")
with open(rollcsv, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["channel","nominal","rc_full","roll_mean","roll_sd","roll_min","roll_max","spread"])
    for c in CHANNELS:
        mu, sd, mn, mx = drift(c)
        w.writerow([c, round(WCH[c],3), round(RCc["full"][c],3),
                    round(mu,3), round(sd,3), round(mn,3), round(mx,3), round(mx-mn,3)])

# --- JSON summary for the brief ---
summ = {
 "support": {"start": D0.isoformat(), "end": D1.isoformat(), "n_months": len(rows),
             "roll_windows": len(roll_ch)},
 "nominal_channel": {c: WCH[c] for c in CHANNELS},
 "rc_channel": {k: {c: round(channelize(RC[k])[c],3) for c in CHANNELS} for k in RC},
 "erc_channel": {k: {c: round(channelize(ERC[k])[c],3) for c in CHANNELS} for k in ERC},
 "drift_channel": {c: dict(zip(["mean","sd","min","max"],[round(x,3) for x in drift(c)])) for c in CHANNELS},
 "rc_channel_fullspan": {c: round(RC_fullspan[c],3) for c in CHANNELS},
 "fullspan": {"start": fs_days[0].isoformat(), "end": fs_days[-1].isoformat(), "n_days": len(fs_days)},
}
json.dump(summ, open(os.path.join(ROOT,"research/ch5_weight_evidence_summary.json"),"w"), indent=1)
shutil.rmtree(tmp, ignore_errors=True)

# --- terse stdout ---
print(f"support {D0} .. {D1}  n_months={len(rows)}  roll_windows={len(roll_ch)}")
print("\nCHANNEL: nominal | rc_full rc_wins rc_ex20 | erc_full | roll[sd,min-max]")
for c in ["labor","realactivity","creditequity","finconditions","housingincome"]:
    mu,sd,mn,mx = drift(c)
    print(f"  {c:14} {WCH[c]:.2f} | {channelize(RC['full'])[c]:.3f} {channelize(RC['winsor'])[c]:.3f} "
          f"{channelize(RC['ex2020'])[c]:.3f} | {channelize(ERC['full'])[c]:.3f} | "
          f"sd={sd:.3f} [{mn:.2f},{mx:.2f}]")
print("\nFULL-SPAN channel realized (1976+, true renormalizing headline):")
for c in ["labor","realactivity","creditequity","finconditions","housingincome"]:
    print(f"  {c:14} nominal={WCH[c]:.2f}  rc_fullspan={RC_fullspan[c]:.3f}")
print("\nMEMBER nominal vs rc_full (biggest gaps):")
gaps = sorted(MEMBERS, key=lambda m: abs(RC['full'][m]-ALPHA[m]), reverse=True)
for m in gaps[:8]:
    print(f"  {m:9} {CH_OF[m]:13} nominal={ALPHA[m]:.3f} rc={RC['full'][m]:.3f} d={RC['full'][m]-ALPHA[m]:+.3f}")
print("\nwrote research/ch5_weight_evidence_v1.csv, ch5_rolling_drift_v1.csv, ch5_weight_evidence_summary.json")
