"""B-REFETCH-HTML17 fetch — refetch the 17 html_masquerading_as_csv poisoned
series via the PROVEN fred_json_api shape (zero new parser shapes). The original
poison came from the fredgraph.csv GRAPH endpoint returning a St. Louis Fed 404
error page (still 404s today for these ids); the JSON observations API is the
correct publisher route. Key read via engine (never shell env, never disk).
Writes clean bytes as `observation_date,<id>` CSV (the current_revised store
format) plus a key-redacted manifest. NO STORE WRITE here — probe/prefetch only.
"""
import csv
import hashlib
import io
import json
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, ".")
from tools.rmv2_data_cloudflare.rmv2_connectors import engine

KEY = engine._read_credential("FRED_API_KEY")
if not KEY:
    raise SystemExit("FRED_API_KEY did not resolve")

SERIES = [
    "A466RX1Q020SBEA", "AUTOSTOTALSA", "CES0500000008", "CMRMTSPLM",
    "CORPPROFIT", "GACDISA066MSFRBPHI", "IPN3361T3S", "LNS12000000",
    "LNS13008396", "NAPM", "PHIL", "SP500PR", "USALOLITONOSTSAMEI",
    "WILL5000IND", "WILL5000INDFC", "WILL5000PR", "WILL5000PRFC",
]

OUT = Path("research/prefetch/html17")
OUT.mkdir(parents=True, exist_ok=True)
OBS = "https://api.stlouisfed.org/fred/series/observations?series_id=%s&file_type=json&api_key=%s"
META = "https://api.stlouisfed.org/fred/series?series_id=%s&file_type=json&api_key=%s"


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "rmv2-html17-refetch/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.getcode(), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def _redact(url):
    return url.replace(KEY, "<FRED_API_KEY>")


manifest = []
summary = []
for sid in SERIES:
    mcode, mbody = _get(META % (sid, KEY))
    title = units = freq = None
    if mcode == 200:
        try:
            j = json.loads(mbody)
            s = j["seriess"][0]
            title, units, freq = s.get("title"), s.get("units"), s.get("frequency_short")
        except Exception:
            pass
    time.sleep(0.4)
    code, body = _get(OBS % (sid, KEY))
    nobs = 0
    csv_bytes = b""
    ok = False
    if code == 200:
        try:
            j = json.loads(body)
            obs = j.get("observations", [])
            buf = io.StringIO()
            w = csv.writer(buf, lineterminator="\n")
            w.writerow(["observation_date", sid])
            for o in obs:
                v = o.get("value", ".")
                if v == ".":
                    continue  # FRED missing marker; drop (matches graph-csv blanking)
                w.writerow([o["date"], v])
            csv_bytes = buf.getvalue().encode("utf-8")
            nobs = csv_bytes.count(b"\n") - 1
            ok = nobs > 0
        except Exception as e:
            summary.append((sid, code, "JSON_PARSE_ERR:%s" % e, 0))
    sha = hashlib.sha256(csv_bytes).hexdigest() if csv_bytes else None
    if ok:
        (OUT / ("%s.csv" % sid)).write_bytes(csv_bytes)
    manifest.append({
        "series_id": sid, "obs_http": code, "meta_http": mcode,
        "title": title, "units": units, "frequency_short": freq,
        "n_obs": nobs, "sha256": sha, "ok": ok,
        "obs_url": _redact(OBS % (sid, KEY)), "fetched_at": _now(),
    })
    summary.append((sid, code, "OK" if ok else "EMPTY/FAIL", nobs))
    time.sleep(0.4)

(OUT / "manifest.jsonl").write_text(
    "\n".join(json.dumps(m) for m in manifest) + "\n"
)
print("SERIES_ID                         HTTP  STATUS      NOBS")
for sid, code, st, n in summary:
    print("%-32s  %-4s  %-10s  %6d" % (sid, code, st, n))
ok_n = sum(1 for m in manifest if m["ok"])
print("\nOK=%d / %d" % (ok_n, len(SERIES)))
