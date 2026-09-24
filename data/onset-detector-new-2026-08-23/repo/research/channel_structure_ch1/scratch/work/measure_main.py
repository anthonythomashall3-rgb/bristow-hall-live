#!/usr/bin/env python3
"""CH1 channel-structure probe — main engine. READ-ONLY on vault; calls index_v1's own
transforms. Writes only JSON/txt into this scratch/work tree. No vault writes."""
import sys, os, json, datetime as dt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MS = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", "method_source"))
sys.path.insert(0, MS)
os.chdir(HERE)  # so RAW="raw/" (symlink) resolves; index writes index_v1_out.json here

import index_v1 as ix   # executes module: builds T, Z, MU, SD, line (WITH nowcast), etc.

OUT = {}
MEM17 = ["ICSA","IURSA","SAHM","UNRATEv","INDPRO","CMRMT","TCU","PHILLY",
         "NASDAQ","BAAAAA","BAA10Y","VIX","NFCI","PERMIT","HOUST","UMCSENT","W875"]
CH = ix.CHANNELS
DAYS = ix.DAYS

# ---------- §0.1 transformed span per member (pre-z transform dict T) ----------
span = {}
for m in MEM17:
    ks = sorted(ix.T[m])
    span[m] = {"first": ks[0].isoformat(), "last": ks[-1].isoformat(), "nonnull": len(ks)}
OUT["s0_span"] = span

# §0.2 single sample window = DAYS grid, the exact grid channel_score/zval read on.
WIN0, WIN1 = DAYS[0], DAYS[-1]
OUT["s0_window"] = {"start": WIN0.isoformat(), "end": WIN1.isoformat(),
                    "n_days": len(DAYS),
                    "excludes": "pre-1976-06-01; per-member earlier days are NaN until member's transformed start (pairwise-complete)"}

# ---------- build daily z-panel exactly as channel_score receives (zval) ----------
# NOTE: ix.Z already had nowcast fills injected at module import (edge only). To measure
# the STRUCTURE of published values we rebuild z WITHOUT nowcast is not needed here since
# fills only touch days > nowcast_from (a handful of edge days); correlations over 1976+
# are dominated by history. We use zval as-is = what the index truly serves today.
def zpanel():
    P = np.full((len(DAYS), len(MEM17)), np.nan)
    for j, m in enumerate(MEM17):
        for i, d in enumerate(DAYS):
            v = ix.zval(m, d)
            if v is not None:
                P[i, j] = v
    return P
Z = zpanel()
np.save("zpanel.npy", Z)

def pearson_pw(a, b):
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 30: return None, int(m.sum())
    x, y = a[m], b[m]
    if x.std() == 0 or y.std() == 0: return None, int(m.sum())
    return float(np.corrcoef(x, y)[0, 1]), int(m.sum())

def spearman_pw(a, b):
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 30: return None
    x = np.argsort(np.argsort(a[m])).astype(float)
    y = np.argsort(np.argsort(b[m])).astype(float)
    return float(np.corrcoef(x, y)[0, 1])

# ---------- §1.1 full 17x17 Pearson ----------
n = len(MEM17)
Pear = np.full((n, n), np.nan); Spear = np.full((n, n), np.nan); Nover = np.zeros((n, n), int)
for i in range(n):
    for jx in range(i, n):
        r, ov = pearson_pw(Z[:, i], Z[:, jx])
        s = spearman_pw(Z[:, i], Z[:, jx])
        Pear[i, jx] = Pear[jx, i] = (r if r is not None else np.nan)
        Spear[i, jx] = Spear[jx, i] = (s if s is not None else np.nan)
        Nover[i, jx] = Nover[jx, i] = ov
OUT["s1_members"] = MEM17
np.save("pearson17.npy", Pear); np.save("spearman17.npy", Spear); np.save("nover17.npy", Nover)

# §1.4 flag |r|>=0.80
flags = []
for i in range(n):
    for jx in range(i+1, n):
        if np.isfinite(Pear[i, jx]) and abs(Pear[i, jx]) >= 0.80:
            flags.append([MEM17[i], MEM17[jx], round(float(Pear[i, jx]), 3),
                          round(float(Spear[i, jx]), 3), int(Nover[i, jx])])
OUT["s1_4_collinear_ge0p80"] = sorted(flags, key=lambda x: -abs(x[2]))

# ---------- §1.2 raw-level vs transformed for the 5 named pairs ----------
# raw-level daily carry-forward panel via asof on the RAW source series
RAWSRC = {"INDPRO":"INDPRO","CMRMT":"CMRMTSPL","PERMIT":"PERMIT","HOUST":"HOUST",
          "BAA10Y":"BAA10Y","BAAAAA":None,"SAHM":"SAHMREALTIME","UNRATEv":"UNRATE",
          "IURSA":"IURSA"}
def raw_daily(memkey):
    if memkey == "BAAAAA":
        ser = ix.BAAAAA
    else:
        ser = ix.S[RAWSRC[memkey]]
    col = np.full(len(DAYS), np.nan)
    for i, d in enumerate(DAYS):
        v = ix.asof(ser, d)
        if v is not None: col[i] = v
    return col
def zcol(memkey):
    return Z[:, MEM17.index(memkey)]

pairs = [("INDPRO","CMRMT"),("PERMIT","HOUST"),("BAA10Y","BAAAAA"),
         ("SAHM","UNRATEv"),("IURSA","UNRATEv")]
p12 = []
for a, b in pairs:
    ra = raw_daily(a); rb = raw_daily(b)
    r_raw, ov_raw = pearson_pw(ra, rb)
    r_tr, ov_tr = pearson_pw(zcol(a), zcol(b))
    s_tr = spearman_pw(zcol(a), zcol(b))
    p12.append({"pair": f"{a}~{b}", "raw_r": round(r_raw,3) if r_raw is not None else None,
                "raw_n": ov_raw, "transf_r": round(r_tr,3) if r_tr is not None else None,
                "transf_n": ov_tr, "spearman_transf": round(s_tr,3) if s_tr is not None else None,
                "delta": round((r_tr-r_raw),3) if (r_tr is not None and r_raw is not None) else None})
OUT["s1_2_raw_vs_transformed"] = p12

# ---------- §2 effective-N per channel (participation ratio of eigenvalues) ----------
def eff_n(members):
    idx = [MEM17.index(m) for m in members]
    sub = Z[:, idx]
    # pairwise-complete corr among members
    k = len(idx); C = np.eye(k)
    for a in range(k):
        for b in range(a+1, k):
            r, ov = pearson_pw(sub[:, a], sub[:, b])
            C[a, b] = C[b, a] = (r if r is not None else 0.0)
    ev = np.linalg.eigvalsh(C)
    ev = np.clip(ev, 0, None)
    pr = (ev.sum()**2) / (np.sum(ev**2)) if np.sum(ev**2) > 0 else None
    return {"nominal_N": k, "eff_N_participation_ratio": round(float(pr),2) if pr else None,
            "eigenvalues": [round(float(x),3) for x in sorted(ev, reverse=True)]}
OUT["s2_effN"] = {ch: eff_n(mem) for ch,(w,mem) in CH.items() if len(mem) > 1}
# §2.3 NFCI first non-null from bytes
nfci_ks = sorted(ix.S["NFCI"])
OUT["s2_3_nfci_first"] = nfci_ks[0].isoformat()
OUT["s2_effN_formula"] = "participation ratio PR = (sum lambda)^2 / sum(lambda^2) on pairwise-complete member Pearson corr; finconditions nominal_N=1"

# ---------- headline decomposition helpers ----------
def channel_series():
    """per-channel daily score cs_c on DAYS grid (published z, nowcast-injected edge)."""
    CS = {ch: np.full(len(DAYS), np.nan) for ch in CH}
    for i, d in enumerate(DAYS):
        for ch,(w,mem) in CH.items():
            cs = ix.channel_score(mem, d)
            if cs is not None: CS[ch][i] = cs
    return CS
CS = channel_series()

def headline_from(CS, weights, renorm=True):
    chs = list(CH.keys())
    H = np.full(len(DAYS), np.nan)
    for i in range(len(DAYS)):
        tot = 0.0; wsum = 0.0; allw = 0.0
        for ch in chs:
            allw += weights[ch]
            v = CS[ch][i]
            if np.isfinite(v):
                tot += weights[ch]*v; wsum += weights[ch]
        if wsum > 0:
            H[i] = tot/wsum if renorm else tot/allw
    return H
NOMW = {ch: w for ch,(w,mem) in CH.items()}
H = headline_from(CS, NOMW, renorm=True)

# ---------- §3 variance contribution ----------
def var_share(mask=None):
    chs = list(CH.keys())
    # days where ALL channels present (fair decomposition)
    present = np.all(np.vstack([np.isfinite(CS[ch]) for ch in chs]), axis=0)
    if mask is not None: present = present & mask
    h = H.copy()
    fin = present & np.isfinite(h)
    hv = h[fin]
    contrib = {}
    for ch in chs:
        wc = NOMW[ch]*CS[ch][fin]
        contrib[ch] = float(np.cov(wc, hv)[0,1] / np.var(hv)) if np.var(hv) > 0 else None
    return contrib, int(fin.sum())
# recession / expansion masks on DAYS
recmask = np.array([ix.in_recession(d) for d in DAYS])
expmask = np.array([ix.is_baseline(d) for d in DAYS])
sh_all, n_all = var_share()
sh_rec, n_rec = var_share(recmask)
sh_exp, n_exp = var_share(expmask)
def rnd(d): return {k: (round(v,3) if v is not None else None) for k,v in d.items()}
OUT["s3_var_share"] = {"nominal_weight": NOMW,
    "overall": {"share": rnd(sh_all), "n_days": n_all},
    "recession_only": {"share": rnd(sh_rec), "n_days": n_rec},
    "expansion_only": {"share": rnd(sh_exp), "n_days": n_exp}}
# §3.4 equal-variance-contribution weights (measurement): w ∝ 1/std(cs_c) on all-present days
chs = list(CH.keys())
present = np.all(np.vstack([np.isfinite(CS[ch]) for ch in chs]), axis=0)
inv = {ch: (1.0/np.std(CS[ch][present]) if np.std(CS[ch][present])>0 else 0) for ch in chs}
ssum = sum(inv.values())
OUT["s3_4_equal_contribution_weights"] = {ch: round(inv[ch]/ssum,3) for ch in chs}
OUT["s3_4_note"] = "w ∝ 1/std(channel_score); equalizes marginal variance ignoring cross-channel covariance. MEASUREMENT not proposal."

# ---------- §5 baseline swap ----------
def robust_stats(vals):
    a = np.array(vals, float); med = np.median(a)
    mad = np.median(np.abs(a-med)); sd = 1.4826*mad if mad>0 else (a.std() or 1.0)
    return med, sd
# current MU/SD already in ix.MU/ix.SD. Build statistical (full-dist robust median/MAD) per member.
MU2, SD2 = {}, {}
for m in MEM17:
    ser = ix.T[m]; vals = [ser[k] for k in ser]   # ALL history, no exclusions
    med, sd = robust_stats(vals)
    MU2[m], SD2[m] = med, sd
# also mean/sd full-dist variant (5.6 second estimator)
MU3, SD3 = {}, {}
for m in MEM17:
    ser = ix.T[m]; vals = np.array([ser[k] for k in ser], float)
    MU3[m], SD3[m] = float(vals.mean()), float(vals.std() or 1.0)
mu_sig = []
for m in MEM17:
    mu_sig.append({"m": m, "cur_mu": round(ix.MU[m],3), "cur_sd": round(ix.SD[m],3),
                   "stat_mu": round(MU2[m],3), "stat_sd": round(SD2[m],3),
                   "d_mu": round(MU2[m]-ix.MU[m],3), "d_sd": round(SD2[m]-ix.SD[m],3)})
OUT["s5_1_2_mu_sigma"] = mu_sig
OUT["s5_6_estimator"] = "statistical baseline = full-history median & 1.4826*MAD (robust). Second variant mean/sd reported in s5_alt."

# rebuild z under a given MU/SD and headline
def z_under(MUx, SDx):
    Zx = np.full((len(DAYS), len(MEM17)), np.nan)
    for j, m in enumerate(MEM17):
        ser, keys = ix.Z[m][0], ix.Z[m][1]  # NOTE ix.Z stores standardized; we need raw transform
    # rebuild from raw transform T instead:
    import bisect
    Zx = np.full((len(DAYS), len(MEM17)), np.nan)
    for j, m in enumerate(MEM17):
        ser = ix.T[m]; keys = sorted(ser)
        for i, d in enumerate(DAYS):
            k = bisect.bisect_right(keys, d)-1
            if k >= 0:
                Zx[i, j] = (ser[keys[k]]-MUx[m])/SDx[m]
    return Zx
def headline_z(Zx):
    H = np.full(len(DAYS), np.nan)
    chs = list(CH.keys())
    for i in range(len(DAYS)):
        tot=0.0; wsum=0.0
        for ch in chs:
            mem = CH[ch][1]; w = NOMW[ch]
            vs = [Zx[i, MEM17.index(m)] for m in mem]
            vs = [v for v in vs if np.isfinite(v)]
            if vs:
                cs = sum(vs)/len(vs); tot += w*cs; wsum += w
        if wsum>0: H[i] = tot/wsum
    return H
Zcur = z_under(ix.MU, ix.SD)   # reproduces current published (pre-nowcast) headline
Zstat = z_under(MU2, SD2)
Hcur = headline_z(Zcur); Hstat = headline_z(Zstat)
mm = np.isfinite(Hcur) & np.isfinite(Hstat)
corr = float(np.corrcoef(Hcur[mm], Hstat[mm])[0,1])
diff = np.abs(Hcur-Hstat); di = np.nanargmax(np.where(np.isfinite(diff), diff, -1))
OUT["s5_3_headline"] = {"corr": round(corr,4), "max_abs_div": round(float(diff[di]),3),
                        "max_div_date": DAYS[di].isoformat()}
# §5.4 severity ordering under both (peak sigma per RECS episode, using each baseline's exp scale)
def ordering(Hx):
    exp = Hx[expmask & np.isfinite(Hx)]
    emu, esd = exp.mean(), (exp.std() or 1.0)
    res = {}
    for nm,(a,b) in ix.RECS.items():
        w = [Hx[i] for i,d in enumerate(DAYS) if a<=d<=b and np.isfinite(Hx[i])]
        if w: res[nm] = (max(w)-emu)/esd
    return dict(sorted(res.items(), key=lambda kv:-kv[1]))
oc = ordering(Hcur); os_ = ordering(Hstat)
OUT["s5_4_ordering"] = {"current": {k: round(v,2) for k,v in oc.items()},
                        "statistical": {k: round(v,2) for k,v in os_.items()},
                        "current_rank": list(oc.keys()), "statistical_rank": list(os_.keys()),
                        "rank_changed": list(oc.keys()) != list(os_.keys())}
# §5.5 2022-24 specifically
OUT["s5_5_2022_24"] = {"episode_key": "2022-24*",
    "cur_sigma": round(oc.get("2022-24*",float('nan')),2),
    "stat_sigma": round(os_.get("2022-24*",float('nan')),2)}
# alt estimator mean/sd
Zstat3 = z_under(MU3, SD3); Hstat3 = headline_z(Zstat3)
oc3 = ordering(Hstat3)
OUT["s5_alt_meanstd_ordering_rank"] = list(oc3.keys())

# ---------- §6 missing-channel treatment ----------
Hren = headline_from(CS, NOMW, renorm=True)
Hzero = headline_from(CS, NOMW, renorm=False)
mm2 = np.isfinite(Hren) & np.isfinite(Hzero)
c2 = float(np.corrcoef(Hren[mm2], Hzero[mm2])[0,1])
d2 = np.abs(Hren-Hzero); di2 = np.nanargmax(np.where(np.isfinite(d2),d2,-1))
def ordering_series(Hx):
    exp = Hx[expmask & np.isfinite(Hx)]; emu,esd = exp.mean(),(exp.std() or 1.0)
    r={}
    for nm,(a,b) in ix.RECS.items():
        w=[Hx[i] for i,d in enumerate(DAYS) if a<=d<=b and np.isfinite(Hx[i])]
        if w: r[nm]=(max(w)-emu)/esd
    return dict(sorted(r.items(),key=lambda kv:-kv[1]))
orn = ordering_series(Hren); ozn = ordering_series(Hzero)
OUT["s6_missing_channel"] = {"corr": round(c2,4), "max_abs_div": round(float(d2[di2]),3),
    "max_div_date": DAYS[di2].isoformat(),
    "renorm_rank": list(orn.keys()), "zero_rank": list(ozn.keys()),
    "rank_changed": list(orn.keys())!=list(ozn.keys())}
# §6.4 achieved weight sum per date (sampled): report distribution of wsum
wsum_series = np.zeros(len(DAYS))
for i in range(len(DAYS)):
    s=0.0
    for ch,(w,mem) in CH.items():
        if np.isfinite(CS[ch][i]): s+=w
    wsum_series[i]=s
uniq, cnt = np.unique(np.round(wsum_series,2), return_counts=True)
OUT["s6_4_wsum_distribution"] = {str(u): int(c) for u,c in zip(uniq,cnt)}
# transition dates for wsum
trans=[]
for i in range(1,len(DAYS)):
    if round(wsum_series[i],2)!=round(wsum_series[i-1],2):
        trans.append([DAYS[i].isoformat(), round(float(wsum_series[i-1]),2), round(float(wsum_series[i]),2)])
OUT["s6_4_wsum_transitions"] = trans[:40]

with open("results_main.json","w") as f: json.dump(OUT, f, indent=1, default=str)
print("MAIN DONE keys:", list(OUT.keys()))
print("nowcast_from:", ix.nowcast_from)
