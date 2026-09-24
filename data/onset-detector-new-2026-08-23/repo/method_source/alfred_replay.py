#!/usr/bin/env python3
"""THE POINT-IN-TIME REPLAY (ALFRED vintages, keyless alfredgraph endpoint).

For each of the six same-day calls, rebuild the entire instrument exactly as it
could have been built THAT MORNING — every revising input fetched as the vintage
published at the time (where ALFRED archives reach), non-revising inputs
truncated at the date (markets, rates: point-in-time by nature), the Sahm series
real-time by construction — baselines re-estimated on data through that day only.
Then test: (a) did the same-day call stand on then-published data?
           (b) did verification (E12 >= 7.5) arrive on then-published data?

Honesty tiers per input: 'vintage' (exact ALFRED archive), 'non-revising'
(exact by nature), 'fallback' (archive doesn't reach that far; current data
truncated — disclosed)."""
import csv, json, os, bisect, datetime as dt, urllib.error
from alfred_contract import (
    ABSENT_SENTINEL,
    ensure_positive_control,
    request_payload,
)

from collections import deque

RAW = "raw/"; VIN = "raw/vintages/"
os.makedirs(VIN, exist_ok=True)

REVISING = ["ICSA","IURSA","UNRATE","INDPRO","CMRMTSPL","TCU","GACDFSA066MSFRBPHI",
            "NFCI","HOUST","PERMIT","UMCSENT","W875RX1"]
NONREV   = ["NASDAQCOM","VIXCLS","BAA","AAA","BAA10Y"]
REALTIME = ["SAHMREALTIME"]

def parse(path):
    o = {}
    for r in csv.reader(open(path)):
        if r and r[0][:1].isdigit() and len(r) > 1 and r[1] not in ("", "."):
            o[dt.date(int(r[0][:4]), int(r[0][5:7]), int(r[0][8:10]))] = float(r[1])
    return o

CUR = {s: parse(RAW+s+".csv") for s in REVISING+NONREV+REALTIME+["USRECD"]}

def vintage(sid, d):
    """exact ALFRED vintage, or None if this vintage genuinely does not exist.

    ARCH1 (2026-07-26) found a look-ahead mechanism hiding in this function's error
    handler. A bare `except Exception` wrote an EMPTY file, so a network timeout was
    cached permanently as "this vintage does not exist" -- and series_asof then falls
    back to the CURRENT series, i.e. today's fully revised data, in place of the
    vintage. 1,096 of 4,633 cached files were zero-byte. A transport failure must
    never be recorded as an absence.

    A genuine 404 IS an absence and is still cached, as a marked sentinel rather than
    an empty file, so it is distinguishable on sight and by the audit.
    """
    f = f"{VIN}{sid}_{d.isoformat()}.csv"
    if not os.path.exists(f) or os.path.getsize(f) == 0:
        # a pre-existing zero-byte file is an artefact of the old bug: retry it
        if os.path.exists(f):
            os.remove(f)
        try:
            # The control shares the target's URL builder, transport, and parser.
            # If that route is broken or mistyped, no target file can be written.
            ensure_positive_control()
            data, _rows = request_payload(sid, d)
            tmp = f + ".tmp"
            with open(tmp, "wb") as handle:
                handle.write(data)
            os.replace(tmp, f)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # A 404 is absence only after the known vintage reproduced.
                ensure_positive_control(force=True)
                with open(f, "w") as fh:
                    fh.write(ABSENT_SENTINEL)
            else:
                if os.path.exists(f):
                    os.remove(f)
                raise RuntimeError(
                    "ALFRED vintage fetch failed for %s @ %s (HTTP %s). Refusing to "
                    "cache a transport failure as an absence; a replay that silently "
                    "substitutes today's data is not a replay." % (sid, d, e.code))
        except Exception as e:
            if os.path.exists(f):
                os.remove(f)
            raise RuntimeError(
                "ALFRED vintage fetch failed for %s @ %s (%s). Refusing to cache a "
                "transport failure as an absence." % (sid, d, type(e).__name__))
    try:
        head = open(f).readline()
        if head == ABSENT_SENTINEL:
            return None            # genuine 404, recorded as such
        if not head.startswith("observation_date"):
            return None
        return parse(f)
    except Exception:
        return None

def series_asof(d):
    """(series dict, tier dict) exactly as knowable on date d"""
    S = {}; tier = {}
    for sid in REVISING:
        v = vintage(sid, d)
        if v is not None:
            S[sid] = v; tier[sid] = "vintage"
        else:
            S[sid] = {k: x for k, x in CUR[sid].items() if k <= d}; tier[sid] = "fallback"
    for sid in NONREV:
        S[sid] = {k: x for k, x in CUR[sid].items() if k <= d}; tier[sid] = "non-revising"
    for sid in REALTIME:
        S[sid] = {k: x for k, x in CUR[sid].items() if k <= d}; tier[sid] = "real-time"
    return S, tier

# ---- the index pipeline, parameterized by as-of series (mirrors index_v1) ----
def yoy(series):
    out = {}; ks = sorted(series)
    for k in ks:
        p = k - dt.timedelta(days=365); i = bisect.bisect_left(ks, p)
        c = [x for x in ks[max(0,i-1):i+2] if abs((x-p).days) <= 20]
        if c:
            q = min(c, key=lambda x: abs((x-p).days))
            if series[q] != 0: out[k] = (series[k]/series[q]-1)*100
    return out
def wext(series, look, ismax):
    out = {}; ks = sorted(series); vals = [series[k] for k in ks]; lo = 0; dq = deque()
    for i, k in enumerate(ks):
        while lo < i and (k-ks[lo]).days > look: lo += 1
        while dq and dq[0] < lo: dq.popleft()
        while dq and ((vals[dq[-1]] <= vals[i]) if ismax else (vals[dq[-1]] >= vals[i])): dq.pop()
        dq.append(i); out[k] = vals[dq[0]]
    return out, ks
def drawdown(series):
    mx, ks = wext(series, 370, True); return {k: (series[k]/mx[k]-1)*100 if mx[k] else 0 for k in ks}
def risef(series, look=370):
    mn, ks = wext(series, look, False); return {k: series[k]-mn[k] for k in ks}

recks = sorted(CUR["USRECD"])
def in_rec(d):
    i = bisect.bisect_right(recks, d)-1; return i >= 0 and CUR["USRECD"][recks[i]] == 1
EXCL = [(dt.date(2020,1,1), dt.date(2021,12,31)), (dt.date(2023,1,1), dt.date(2025,6,30))]
def isbase(d):
    if in_rec(d): return False
    return not any(a <= d <= b for a, b in EXCL)

CH = {"labor":(.30,["ICSA","IURSA","SAHM","UNRATEv"]),"realactivity":(.25,["INDPRO","CMRMT","TCU","PHILLY"]),
      "creditequity":(.20,["NASDAQ","BAAAAA","BAA10Y","VIX"]),"finconditions":(.10,["NFCI"]),
      "housingincome":(.15,["PERMIT","HOUST","UMCSENT","W875"])}
def compress(v, C=4.0):
    return v if v <= C else C + (v-C)**0.25

def replay(asof):
    S, tier = series_asof(asof)
    T = {}
    T["ICSA"]=yoy(S["ICSA"]); T["IURSA"]=risef(S["IURSA"]); T["SAHM"]=S["SAHMREALTIME"]
    T["UNRATEv"]=risef(S["UNRATE"],120)
    T["INDPRO"]={k:-v for k,v in yoy(S["INDPRO"]).items()}; T["CMRMT"]={k:-v for k,v in yoy(S["CMRMTSPL"]).items()}
    T["TCU"]={k:-v for k,v in yoy(S["TCU"]).items()}; T["PHILLY"]={k:-v for k,v in S["GACDFSA066MSFRBPHI"].items()}
    T["NASDAQ"]={k:-v for k,v in drawdown(S["NASDAQCOM"]).items()}
    T["BAAAAA"]={d:S["BAA"][d]-S["AAA"][d] for d in S["BAA"] if d in S["AAA"]}
    T["BAA10Y"]=S["BAA10Y"]; T["NFCI"]=S["NFCI"]; T["VIX"]=S["VIXCLS"]
    T["PERMIT"]={k:-v for k,v in yoy(S["PERMIT"]).items()}; T["HOUST"]={k:-v for k,v in yoy(S["HOUST"]).items()}
    T["UMCSENT"]={k:-v for k,v in drawdown(S["UMCSENT"]).items()}; T["W875"]={k:-v for k,v in yoy(S["W875RX1"]).items()}
    Z = {}
    for nm, ser in T.items():
        ser = {k: v for k, v in ser.items() if k <= asof}
        ks = sorted(ser); base = [ser[k] for k in ks if isbase(k)]
        if len(base) < 24: Z[nm] = None; continue
        m = sum(base)/len(base); sd2 = (sum((x-m)**2 for x in base)/len(base))**.5 or 1
        Z[nm] = ({k:(ser[k]-m)/sd2 for k in ks}, ks)
    def zval(nm, d):
        if Z[nm] is None: return None
        ser, keys = Z[nm]; i = bisect.bisect_right(keys, d)-1
        return ser[keys[i]] if i >= 0 else None
    START = dt.date(1976,6,1)
    days = []; d = START
    while d <= asof: days.append(d); d += dt.timedelta(days=1)
    line = {}
    for d in days:
        t = ws = 0.0
        for cn,(w,mem) in CH.items():
            vals = [zval(x,d) for x in mem]; vals = [v for v in vals if v is not None]
            if vals: t += w*sum(vals)/len(vals); ws += w
        if ws: line[d] = t/ws
    lds = sorted(line)
    base = [line[d] for d in lds if isbase(d)]
    mu = sum(base)/len(base); sd2 = (sum((x-mu)**2 for x in base)/len(base))**.5
    q = deque(); s = 0.0; sm = {}
    for d in lds:
        v = (line[d]-mu)/sd2
        q.append(v); s += v
        while len(q) > 21: s -= q.popleft()
        sm[d] = compress(s/len(q))
    E = {}; q2 = deque(); s2 = 0.0
    for d in lds:
        v = max(sm[d],0.0); q2.append((d,v)); s2 += v
        while (d-q2[0][0]).days > 365: s2 -= q2.popleft()[1]
        E[d] = s2/30.44
    return sm[lds[-1]], E[lds[-1]], tier

if __name__ == "__main__":
    EPISODES = [("1980","1979-07-08","1979-09-14"),("1990-91","1989-10-27","1990-02-11"),
                ("2001","2000-11-27","2001-02-13"),("2007-09","2007-11-27","2008-02-11"),
                ("2020","2020-03-09","2020-04-20"),("2022-23","2022-10-19","2023-02-24")]
    out = []
    for k, call, ver in EPISODES:
        cd, vd = dt.date.fromisoformat(call), dt.date.fromisoformat(ver)
        r_c, e_c, tier_c = replay(cd)
        r_v, e_v, tier_v = replay(vd)
        nvin = sum(1 for t in tier_c.values() if t == "vintage")
        nfall = sum(1 for t in tier_c.values() if t == "fallback")
        row = {"episode": k, "call": call, "verify": ver,
               "reading_at_call": round(r_c,2), "call_stands": bool(r_c >= 1.0),
               "e12_at_verify": round(e_v,2), "verified": bool(e_v >= 7.5),
               "vintage_inputs": nvin, "nonrev_inputs": len(NONREV)+len(REALTIME), "fallback_inputs": nfall,
               "fallback_list": sorted([s for s,t in tier_c.items() if t=="fallback"])}
        # Publish only the date actually evaluated above. A later threshold date
        # requires its own replay computation; narrative recollection is not data.
        row["rt_call"] = call if row["call_stands"] else None
        row["note"] = (
            "evaluated call date met the 1.0-sigma threshold"
            if row["call_stands"] else
            "evaluated call date did not meet the 1.0-sigma threshold; "
            "no later call date was computed"
        )
        out.append(row)
        print(f"{k:8} call {call}: reading {r_c:+.2f} -> {'STANDS' if row['call_stands'] else 'FAILS'} | "
              f"verify {ver}: E12 {e_v:.2f} -> {'VERIFIED' if row['verified'] else 'not yet'} | "
              f"vintage {nvin}/12 revising, fallback: {','.join(row['fallback_list']) or 'none'}")
    json.dump({"episodes": out,
               "note": "vintage = exact ALFRED archive as published that day; non-revising inputs (markets, rates, real-time Sahm) are point-in-time by nature; fallback = archive does not reach that date, current data truncated (disclosed). Baseline exclusions use the final NBER chronology."},
              open("geo/vintage.json","w"), separators=(",",":"))
    print("saved geo/vintage.json")
