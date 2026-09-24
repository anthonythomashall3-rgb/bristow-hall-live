"""B-ACQ-5 fetch — probe + prefetch FRED bytes for four absent/unused mechanisms:
term structure (term spread), funding spreads, money & credit, retail control.
All candidates are the PROVEN fred_json_api shape (JSON series + observations
endpoints). Zero new parser shapes (section 6.1 caps shapes not sources; 6.2
unlimited instances of a proven shape). Key read via engine (never shell env,
never written to disk). manifest.jsonl mirrors research/prefetch/bacq3 format:
url stores <KEY> redaction, body bytes are the source object (key-free).
"""
import hashlib
import json
import sys
import time
sys.path.insert(0, ".")
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

from tools.rmv2_data_cloudflare.rmv2_connectors import engine

KEY = engine._read_credential("FRED_API_KEY")
if not KEY:
    raise SystemExit("FRED_API_KEY did not resolve")

OUT = Path("research/prefetch/bacq5")
OUT.mkdir(parents=True, exist_ok=True)

# category -> [(series_id, human_reason)]
CANDS = {
    "a_term_structure": [
        ("T10Y2Y", "10Y minus 2Y Treasury spread (classic recession predictor)"),
        ("T10Y3M", "10Y minus 3M Treasury spread (Estrella-Mishkin best predictor)"),
        ("T10YFF", "10Y minus federal funds rate spread"),
        ("DGS2", "2Y Treasury constant maturity yield (daily)"),
        ("DGS3MO", "3M Treasury constant maturity yield (daily)"),
        ("DGS1", "1Y Treasury constant maturity yield (daily)"),
        ("DGS5", "5Y Treasury constant maturity yield (daily)"),
        ("DGS10", "10Y Treasury constant maturity yield (daily)"),
        ("GS2", "2Y Treasury constant maturity yield (monthly)"),
    ],
    "b_funding_spreads": [
        ("TEDRATE", "TED spread 3M LIBOR minus 3M T-bill (funding stress; disc 2022)"),
        ("DCPF3M", "3M AA financial commercial paper rate"),
        ("DCPN3M", "3M AA nonfinancial commercial paper rate"),
        ("SOFR", "Secured Overnight Financing Rate (2018+)"),
        ("DPRIME", "bank prime loan rate"),
    ],
    "c_money_credit": [
        ("M2SL", "M2 money stock SA (money growth)"),
        ("M1SL", "M1 money stock SA"),
        ("M2REAL", "real M2 money stock"),
        ("BOGMBASE", "monetary base total"),
        ("TOTRESNS", "total reserves of depository institutions NSA"),
        ("NONBORRES", "nonborrowed reserves of depository institutions"),
    ],
    "d_retail_control": [
        ("RSXFS", "advance retail sales retail trade excl food services"),
        ("RRSFS", "real retail and food services sales"),
        ("RSAFS", "advance retail and food services sales total"),
        ("MARTSSM44X72USS", "advance retail excl food services (Census control base)"),
        ("PCEC96", "real personal consumption expenditures"),
    ],
}


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "rmv2-bacq5/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.getcode(), r.read()


def _redact(url):
    return url.replace(KEY, "<KEY>")


def main():
    man = open(OUT / "manifest.jsonl", "w")
    ok, skipped = 0, []
    for cat, series in CANDS.items():
        for sid, reason in series:
            meta_url = ("https://api.stlouisfed.org/fred/series?series_id=%s"
                        "&api_key=%s&file_type=json" % (sid, KEY))
            obs_url = ("https://api.stlouisfed.org/fred/series/observations?"
                       "series_id=%s&api_key=%s&file_type=json" % (sid, KEY))
            rec = {"candidate": reason, "fred_id": sid, "category": cat,
                   "kind": "fred_current_obs", "url": _redact(obs_url),
                   "fetch_utc": _now()}
            try:
                mc, mb = _get(meta_url)
                if mc != 200:
                    raise RuntimeError("meta http %d" % mc)
                mj = json.loads(mb)
                if not mj.get("seriess"):
                    raise RuntimeError("no seriess in meta")
                oc, ob = _get(obs_url)
                if oc != 200:
                    raise RuntimeError("obs http %d" % oc)
                oj = json.loads(ob)
                if "observations" not in oj:
                    raise RuntimeError("no observations in obs")
            except (urllib.error.HTTPError, urllib.error.URLError,
                    RuntimeError, ValueError) as exc:
                rec.update({"status": "skip", "error": str(exc)})
                man.write(json.dumps(rec, sort_keys=True) + "\n")
                skipped.append((sid, str(exc)))
                print("SKIP", sid, exc)
                time.sleep(0.4)
                continue
            (OUT / ("%s.meta.json" % sid)).write_bytes(mb)
            (OUT / ("%s.obs.json" % sid)).write_bytes(ob)
            sha = hashlib.sha256(ob).hexdigest()
            s = mj["seriess"][0]
            rec.update({"status": "ok", "http": 200, "bytes": len(ob),
                        "sha256": sha, "note": cat,
                        "title": s.get("title"),
                        "frequency": s.get("frequency"),
                        "seasonal_adjustment": s.get("seasonal_adjustment_short"),
                        "units": s.get("units"),
                        "observation_start": s.get("observation_start"),
                        "observation_end": s.get("observation_end"),
                        "last_updated": s.get("last_updated")})
            man.write(json.dumps(rec, sort_keys=True) + "\n")
            ok += 1
            print("OK  ", sid, len(ob), "B", s.get("frequency"),
                  s.get("observation_start"), "->", s.get("observation_end"))
            time.sleep(0.4)
    man.close()
    print("\nFETCH DONE ok=%d skip=%d" % (ok, len(skipped)))
    if skipped:
        print("SKIPPED:", skipped)


main()
