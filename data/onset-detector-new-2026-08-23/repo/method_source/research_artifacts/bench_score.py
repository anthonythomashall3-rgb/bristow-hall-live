#!/usr/bin/env python3
"""Episode-level benchmark scoring of recession predictors against BOTH
chronologies (NBER from raw/USRECD.csv; ours from geo/recpage.json io/ie).
Light compute only: monthly/quarterly/weekly series, closed-form AUC.
Run: python3 bench_score.py  (writes benchmark_scores.json next to itself)"""
import csv, json, os
from datetime import date, timedelta

R = '/Users/anthonyhall/Desktop/RecessionMonitor/'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'benchmark_scores.json')

# ---------- helpers ----------
def madd(m, n):                       # 'YYYY-MM' + n months
    y, mm = int(m[:4]), int(m[5:7]) - 1 + n
    return f"{y + mm//12:04d}-{mm%12+1:02d}"
def mdiff(a, b):                      # a - b in months
    return (int(a[:4])-int(b[:4]))*12 + int(a[5:7])-int(b[5:7])
def q_of(m):                          # 'YYYY-MM' -> 'YYYYQn'
    return f"{m[:4]}Q{(int(m[5:7])-1)//3+1}"
def qorder(k):
    y, q = k.split('Q'); return int(y)*4 + int(q) - 1
def qadd(k, n):
    i = qorder(k) + n; return f"{i//4}Q{i%4+1}"
def first_friday_next_month(m):       # publication date for obs month m
    y, mm = int(m[:4]), int(m[5:7]) + 1
    if mm == 13: y, mm = y+1, 1
    d = date(y, mm, 1)
    return d + timedelta((4 - d.weekday()) % 7)
def auc_pairs(pos, neg):              # exact Mann-Whitney AUC with tie=0.5
    if not pos or not neg: return None
    s = sum((1.0 if p > n else 0.5 if p == n else 0.0) for p in pos for n in neg)
    return round(s / (len(pos)*len(neg)), 3)

# ---------- chronology 1: NBER (USRECD daily -> monthly/quarterly) ----------
usrecd = {}
for r in csv.reader(open(R+'raw/USRECD.csv')):
    if r and r[0][:1].isdigit(): usrecd[r[0]] = int(r[1])
nber_m = {}
for d, v in usrecd.items():
    nber_m[d[:7]] = max(nber_m.get(d[:7], 0), v)
NBER_LAST = '2026-06'                 # USRECD runs to 2026-07-05; 2026-07 partial
nber_m = {m: v for m, v in nber_m.items() if m <= NBER_LAST}

def month_runs(ind):
    runs, cur, prev = [], None, None
    for m in sorted(ind):
        if ind[m] == 1 and cur is None: cur = m
        if ind[m] == 0 and cur is not None: runs.append((cur, prev)); cur = None
        prev = m
    if cur is not None: runs.append((cur, prev))
    return runs
nber_eps = [e for e in month_runs(nber_m) if e[0] >= '1957-01']

# ---------- chronology 2: ours (recpage.json io/ie; 1980+1981-82 share io -> merge) ----------
rp = json.load(open(R+'geo/recpage.json'))
merged = {}
for row in rp['rows']:
    io, ie = row['io'], row['ie']
    merged[io] = max(merged.get(io, ie), ie)
ours_eps = sorted(merged.items())
OURS_LAST = '2026-06'
ours_m = {}
m = '1957-01'
while m <= OURS_LAST:
    ours_m[m] = 1 if any(io <= m <= ie for io, ie in ours_eps) else 0
    m = madd(m, 1)

def q_ind(mind, last_m):              # monthly -> quarterly (any month in q)
    out = {}
    for m, v in mind.items():
        k = q_of(m); out[k] = max(out.get(k, 0), v)
    # keep only fully-observed quarters
    lastq = q_of(last_m)
    if int(last_m[5:7]) % 3 != 0: lastq = qadd(lastq, -1)
    return {k: v for k, v in out.items() if qorder(k) <= qorder(lastq)}, lastq
nber_q, NBER_LASTQ = q_ind(nber_m, NBER_LAST)
ours_q, OURS_LASTQ = q_ind(ours_m, OURS_LAST)
CHRON = {'nber': dict(m=nber_m, q=nber_q, eps=nber_eps, lastq=NBER_LASTQ),
         'ours': dict(m=ours_m, q=ours_q, eps=ours_eps, lastq=OURS_LASTQ)}

# ---------- (2) term-spread probit, stored history, 4Q horizon, 2006+ ----------
lead = json.load(open(R+'geo/leading.json'))
p4 = lead['oos_probabilities']['4']   # keyed by forecast-MADE quarter t; Pr(rec in t+4)
probit = {}
for tag, C in CHRON.items():
    qi, lastq = C['q'], C['lastq']
    pos_pt, neg_pt, pos_cum, neg_cum = [], [], [], []
    for t, p in p4.items():
        if qorder(t) < qorder('2006Q1'): continue
        tgt = qadd(t, 4)
        if qorder(tgt) <= qorder(lastq):            # point: rec in exactly t+4
            (pos_pt if qi[tgt] else neg_pt).append(p)
            w = max(qi[qadd(t, n)] for n in range(1, 5))   # cum: any of t+1..t+4
            (pos_cum if w else neg_cum).append(p)
    per_ep = []
    for onset, end in C['eps']:
        oq, eq = q_of(onset), q_of(end)
        if qorder(oq) < qorder('2006Q1'): continue
        targets = [k for k in [qadd(oq, i) for i in range(qorder(eq)-qorder(oq)+1)]]
        probs = {t: p4.get(t) for t in (qadd(k, -4) for k in targets)}
        probs = {t: p for t, p in probs.items() if p is not None}
        p_on = p4.get(qadd(oq, -4))
        mx = max(probs.items(), key=lambda kv: kv[1]) if probs else (None, None)
        sig = sorted(t for t, p in probs.items() if p >= 0.30)
        per_ep.append(dict(onset=oq, end=eq, p_targeting_onset=p_on,
                           max_p=mx[1], max_p_made=mx[0],
                           first_made_ge_030=(sig[0] if sig else None),
                           lead_q_vs_onset=(qorder(oq)-qorder(sig[0]) if sig else None)))
    probit[tag] = dict(auc_point=auc_pairs(pos_pt, neg_pt), n_pos_point=len(pos_pt),
                       n_neg_point=len(neg_pt), auc_cum=auc_pairs(pos_cum, neg_cum),
                       n_pos_cum=len(pos_cum), n_neg_cum=len(neg_cum), episodes=per_ep)

# ---------- (3) Sahm rule as TRIGGER (SAHMREALTIME, first-Friday publication) ----------
sahm = {}
for r in csv.reader(open(R+'raw/SAHMREALTIME.csv')):
    if r and r[0][:1].isdigit() and r[1] not in ('', '.'): sahm[r[0][:7]] = float(r[1])
runs, cur, prevm = [], None, None
for m in sorted(sahm):
    if sahm[m] >= 0.50 and cur is None: cur = m
    if sahm[m] < 0.50 and cur is not None: runs.append((cur, prevm)); cur = None
    prevm = m
if cur is not None: runs.append((cur, prevm))
sahm_out = {}
for tag, C in CHRON.items():
    matched, rows = set(), []
    for onset, end in C['eps']:
        if end < '1959-12': continue          # before SAHMREALTIME history
        w0, w1 = madd(onset, -6), madd(end, 3)
        # every run OVERLAPPING the episode window belongs to the episode
        # (re-crossings inside a recession are not new triggers)
        hits = [rn for rn in runs if rn[0] <= w1 and rn[1] >= w0]
        for rn in hits: matched.add(rn)
        # the episode's own crossing = first run that STARTS in the window;
        # a prior episode's run merely ending inside it is a continuation, not a trigger
        fresh = [rn for rn in hits if rn[0] >= w0]
        if fresh:
            hit = fresh[0]
            rows.append(dict(onset=onset, end=end, cross_month=hit[0],
                             value=sahm[hit[0]], run_end=hit[1],
                             n_runs_in_window=len(hits),
                             left_censored=(hit[0] == min(sahm)),
                             pub_date=str(first_friday_next_month(hit[0])),
                             lag_months=mdiff(hit[0], onset),
                             pub_lag_days=(first_friday_next_month(hit[0])
                                           - date(int(onset[:4]), int(onset[5:7]), 1)).days))
        else:
            rows.append(dict(onset=onset, end=end, cross_month=None))
    false_tr = [dict(start=rn[0], end=rn[1],
                     peak=max(sahm[m] for m in sahm if rn[0] <= m <= rn[1]),
                     pub_date=str(first_friday_next_month(rn[0])))
                for rn in runs if rn not in matched]
    sahm_out[tag] = dict(episodes=rows, false_triggers=false_tr)
sahm_runs_all = [dict(start=a, end=b, peak=max(sahm[m] for m in sahm if a <= m <= b))
                 for a, b in runs]
sahm_2003 = {m: sahm.get(m) for m in ('2003-06', '2003-07', '2003-08', '2003-09')}
sahmc = {}
for r in csv.reader(open(R+'raw/SAHMCURRENT.csv')):
    if r and r[0][:1].isdigit() and r[1] not in ('', '.'): sahmc[r[0][:7]] = float(r[1])
sahmc_2003 = {m: sahmc.get(m) for m in ('2003-06', '2003-07', '2003-08', '2003-09')}

# ---------- (4) Anxious Index: AUC rec-within-2q (2006+), first >50 per episode ----------
anx = {}
for r in csv.reader(open(R+'raw/anxious_index.csv')):
    if r and r[0].isdigit(): anx[f"{r[0]}Q{r[1]}"] = float(r[2])
anx_out = {}
for tag, C in CHRON.items():
    qi, lastq = C['q'], C['lastq']
    pos, neg = [], []
    for t, v in anx.items():          # t = quarter being forecast (known mid t-1)
        if qorder(t) < qorder('2006Q1') or qorder(qadd(t, 1)) > qorder(lastq): continue
        y = max(qi[t], qi[qadd(t, 1)])           # recession in t or t+1
        (pos if y else neg).append(v)
    per_ep = []
    for onset, end in C['eps']:
        oq, eq = q_of(onset), q_of(end)
        win = [qadd(oq, i) for i in range(-2, qorder(eq)-qorder(oq)+2)]
        win = [k for k in win if k in anx]
        if not win: per_ep.append(dict(onset=oq, note='pre-history')); continue
        ex = [k for k in win if anx[k] > 50]
        mxk = max(win, key=lambda k: anx[k])
        per_ep.append(dict(onset=oq, end=eq,
                           first_gt50=(ex[0] if ex else None),
                           first_gt50_survey=(qadd(ex[0], -1) if ex else None),
                           max_val=anx[mxk], max_q=mxk))
    all50 = sorted(k for k, v in anx.items() if v > 50)
    anx_out[tag] = dict(auc_within2q=auc_pairs(pos, neg), n_pos=len(pos), n_neg=len(neg),
                        episodes=per_ep, all_gt50_forecast_quarters=all50)

# ---------- (5) STLFSI4: AUC rec-within-90-days (2006+) ----------
fsi = []
for r in csv.reader(open(R+'raw/STLFSI4.csv')):
    if r and r[0][:1].isdigit() and r[1] not in ('', '.'): fsi.append((r[0], float(r[1])))
fsi_out = {}
for tag, C in CHRON.items():
    mi = C['m']; known_end = date(2026, 6, 30)
    pos, neg = [], []
    for ds, v in fsi:
        d0 = date(int(ds[:4]), int(ds[5:7]), int(ds[8:10]))
        if d0 < date(2006, 1, 1) or d0 + timedelta(90) > known_end: continue
        months = set()
        dd = d0 + timedelta(1)
        while dd <= d0 + timedelta(90):
            months.add(f"{dd.year:04d}-{dd.month:02d}"); dd += timedelta(14)
        months.add(f"{(d0+timedelta(90)).year:04d}-{(d0+timedelta(90)).month:02d}")
        y = max(mi.get(m, 0) for m in months)
        (pos if y else neg).append(v)
    per_ep = []
    for onset, end in C['eps']:
        if end < '2006-01': continue
        o1 = date(int(onset[:4]), int(onset[5:7]), 1)
        pre = [x for x in fsi if date(int(x[0][:4]), int(x[0][5:7]), int(x[0][8:10])) < o1]
        w = [x for x in fsi if o1 - timedelta(90)
             <= date(int(x[0][:4]), int(x[0][5:7]), int(x[0][8:10]))
             and x[0][:7] <= end]
        mx = max(w, key=lambda x: x[1]) if w else (None, None)
        per_ep.append(dict(onset=onset, end=end,
                           last_pre_onset=(pre[-1] if pre else None),
                           peak=mx[1], peak_date=mx[0]))
    fsi_out[tag] = dict(auc_within90d=auc_pairs(pos, neg), n_pos=len(pos), n_neg=len(neg),
                        episodes=per_ep)

# ---------- (6) Chauvet-Piger smoothed (LOOKAHEAD caveat) ----------
cp = {}
for r in csv.reader(open(R+'raw/RECPROUSM156N.csv')):
    if r and r[0][:1].isdigit() and r[1] not in ('', '.'): cp[r[0][:7]] = float(r[1])
cp_out = {}
for tag, C in CHRON.items():
    mi = C['m']
    pos, neg = [], []
    for m, v in cp.items():           # coincident: same-month classification
        if m < '2006-01' or m not in mi: continue
        (pos if mi[m] else neg).append(v)
    per_ep = []
    for onset, end in C['eps']:
        if end < '1967-06': continue
        win = [m for m in sorted(cp) if madd(onset, -3) <= m <= madd(end, 3)]
        call = None
        for i in range(len(win)-2):
            if all(cp[win[i+j]] >= 80 for j in range(3)): call = win[i]; break
        mxm = max(win, key=lambda m: cp[m]) if win else None
        per_ep.append(dict(onset=onset, end=end, first_of_3mo_ge80=call,
                           lag_months=(mdiff(call, onset) if call else None),
                           max_val=(cp[mxm] if mxm else None), max_month=mxm))
    cp_out[tag] = dict(auc_coincident=auc_pairs(pos, neg), n_pos=len(pos), n_neg=len(neg),
                       episodes=per_ep)

# ---------- (1) incumbents: cite only ----------
lf = json.load(open(R+'geo/leading_final.json'))
incumbents = {h: dict(model=c['model'], confirmed_auc=c['tested_auc'], as_of=c['as_of'],
                      current_probability=c['probability'])
              for h, c in lf['current'].items()}

out = dict(
    generated='2026-07-18',
    chronologies=dict(
        nber=dict(source='raw/USRECD.csv (trough method: recession runs from the month AFTER the NBER peak through the trough month)',
                  episodes=[list(e) for e in nber_eps], last_known_month=NBER_LAST),
        ours=dict(source='geo/recpage.json rows io/ie (1980 + 1981-82 share io 1979-07 -> one double-dip episode)',
                  episodes=[list(e) for e in ours_eps], last_known_month=OURS_LAST)),
    incumbents=dict(source='geo/leading_final.json current.*.tested_auc (cited, not recomputed); '
                           'confirmation-era 2006Q1+ AUCs vs NBER per leading_final2.py line 193 and note_week',
                    values=incumbents,
                    targets={'1': 'point: recession in exactly t+1 (NBER quarterly)',
                             '4': 'cum: recession in any of t+1..t+4 (NBER quarterly)',
                             '0': 'weekly: NBER flag one week ahead'},
                    ours_chronology='UNRESOLVED - not scored against our chronology in leading_final.json; cite-only per protocol'),
    term_spread_probit_4q=dict(source='geo/leading.json oos_probabilities["4"] (stored walk-forward history, keyed by forecast-made quarter)',
                               era='forecasts made 2006Q1+, target quarter known', **probit),
    sahm_trigger=dict(source='raw/SAHMREALTIME.csv, trigger >= 0.50; publication = first Friday of month following the observation month',
                      sahm_realtime_2003=sahm_2003, sahm_current_2003=sahmc_2003,
                      all_runs_ge_050=sahm_runs_all,
                      notes=['2003 marginal case (site text, geo/site.html Section 4): on the honest real-time series the indicator NEVER reached 0.50 in 2003 (peak 0.47, Jul-Aug); only the revised-vintage SAHMCURRENT touches exactly 0.50 in Jul-Aug 2003 - a graze, never above threshold.',
                             '1976-11 single-month graze at exactly 0.50 (real-time) is the one pre-2024 standalone trigger on SAHMREALTIME; it does not appear on the revised-vintage series.',
                             '2024-07..09 run (peak 0.57, Jul reading pub 2024-08-02 by first-Friday convention): mechanically standalone under BOTH chronologies (starts 13 months after our 2022-23 ie); per site text it is the corroborated labor aftershock of the 2022-23 episode, so under our chronology it is a lagging confirmation, not a misfire.',
                             '1959-12 crossing is left-censored: SAHMREALTIME begins 1959-12 already above threshold (0.77); site text dates the (reconstructed) crossing to 1959-11.',
                             'First-Friday is a convention: actual BLS releases occasionally slip to the second Friday (e.g. the Apr-2020 report actually landed 2020-05-08, convention says 2020-05-01).'], **sahm_out),
    anxious_index=dict(source='raw/anxious_index.csv; value at forecast-quarter t is known mid-quarter t-1; outcome = recession in t or t+1',
                       **anx_out),
    stlfsi4=dict(source='raw/STLFSI4.csv weekly; outcome = any recession day in (d, d+90]; history starts 1993-12-31',
                 **fsi_out),
    chauvet_piger=dict(source='raw/RECPROUSM156N.csv SMOOTHED probabilities - NOT real-time (retrospective two-sided smoothing); '
                              'honest real-time comparison UNRESOLVED pending vintage data',
                       notes=['UNFAIR ADVANTAGE: smoothed probabilities are two-sided estimates revised with data unavailable in real time; the AUC of 1.0 vs NBER is hindsight, not forecasting skill. Publication lag is ~2.5 months on top.',
                              'Even WITH hindsight, the 3-consecutive-months>=80% calling rule (Piger FAQ) never fires for 1970 (peak 80.22, one month), 1990-91 (peak 60.44), 2001 (peak 28.54) or 2020 (100.0 in Mar-Apr but only 2 recession months, so a 3-month run is mechanically impossible) on the current-vintage series.',
                              'It is a COINCIDENT nowcast of four monthly indicators - scoring it at any horizon > 0 would be a category error; only same-month AUC is reported.',
                              'Honest real-time episode comparison: UNRESOLVED pending point-in-time vintages of the Chauvet-Piger probabilities.'], **cp_out))
json.dump(out, open(OUT, 'w'), indent=1)
print(json.dumps(out, indent=1)[:200])
print('written', OUT)
