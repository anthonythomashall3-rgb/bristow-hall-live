"""B-ACQ-LEI-CEI fetch — probe + prefetch FRED bytes for the Conference Board
LEI (10) / CEI (4) benchmark component sets. All free candidates are the PROVEN
fred_json_api shape (JSON series + observations endpoints). Zero new parser
shapes (section 6.1 caps shapes not sources; 6.2 unlimited instances). Licensed
components (ISM New Orders, Leading Credit Index) are probed for rights posture
and NOT landed as raw bytes. Key read via engine (never shell env, never disk).
manifest.jsonl mirrors research/prefetch/bacq5 format: url stores <KEY>
redaction; body bytes are the key-free source object.
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

OUT = Path("research/prefetch/bacq_leicei")
OUT.mkdir(parents=True, exist_ok=True)

# category -> [(series_id, human_reason)]
CANDS = {
    "cei_components": [
        ("PAYEMS", "CEI: payroll employment (Chauvet-Piger DFMS input); MEMBER-ABSENT gap"),
        ("W875RX1", "CEI: personal income less transfer payments"),
        ("CMRMTSPL", "CEI: manufacturing and trade sales"),
        ("INDPRO", "CEI: industrial production"),
    ],
    "lei_free": [
        ("AWHMAN", "LEI: avg weekly hours mfg (production/nonsupervisory) - classic series"),
        ("AWHAEMAN", "LEI: avg weekly hours mfg (all employees) - modern all-employee basis"),
        ("ACOGNO", "LEI: manufacturers' new orders consumer goods (closest free proxy for consumer goods & materials)"),
        ("NEWORDER", "LEI: manufacturers' new orders nondefense capital goods ex aircraft"),
        ("SP500", "LEI: S&P 500 index of stock prices (section 3.1: NOT NASDAQ); FRED free is rights-limited ~10yr"),
        ("UMCSENT", "LEI proxy: UMich consumer sentiment (NEAR consumer expectations component)"),
    ],
    "lei_licensed": [
        ("NAPMNOI", "LEI: ISM Manufacturing New Orders Index (ISM-proprietary/licensed; expected discontinued on FRED)"),
    ],
}


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "rmv2-bacq-leicei/1.0"})
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
