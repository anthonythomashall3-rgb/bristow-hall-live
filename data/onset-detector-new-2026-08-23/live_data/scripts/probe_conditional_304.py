#!/usr/bin/env python3
"""Extend R1's live 304 probe to the remaining advertised-but-untested sources.

Body-free: sends the stored validator as If-None-Match / If-Modified-Since on a GET
and reads ONLY the status line -- a 304 has no body and a 200 is aborted before the
body is read, so this downloads no source data. GET only (POST adapters skipped).
Rate-limited per host, per-request timeout, auth/errors recorded not fatal.

Targets: sources that advertise a validator (etag/last-modified on the latest
receipt) and were NOT in R1's 15-source probe.
"""
from __future__ import annotations

import glob
import json
import sys
import time
import urllib.request
import warnings
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
R1 = ROOT / "tools/rmv2_data_cloudflare/generated_live/R1_RELEASE_CALENDAR_DEEPEN.v1.json"
OUT = ROOT / "tools/rmv2_data_cloudflare/generated_live/research/conditional_304_extended_probe.v1.json"
TIMEOUT = 8
PER_HOST_SLEEP = 0.4
UA = "RecessionMonitorV2-conditional-probe/1.0 (already-acquired source revalidation)"


def latest_receipts():
    latest = {}
    for rp in glob.glob(str(ROOT / "live_data/store/receipts/*/*.json")):
        try:
            d = json.load(open(rp))
        except Exception:
            continue
        sid = d.get("source_id")
        t = d.get("clocks", {}).get("retrieved_at") or ""
        if sid and (sid not in latest or t > latest[sid][0]):
            latest[sid] = (t, d)
    return {sid: d for sid, (t, d) in latest.items()}


def probe_one(url, method, etag, last_modified):
    if method != "GET":
        return {"status": None, "answers_304": False, "note": "method %s -- conditional GET not applicable" % method}
    headers = {"User-Agent": UA}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
        status = resp.status
        resp.close()  # body-free: never read on 200
        return {"status": status, "answers_304": status == 304, "note": None}
    except urllib.error.HTTPError as e:
        code = e.code
        try:
            e.close()
        except Exception as close_exc:
            warnings.warn(
                "HTTP error response cleanup failed: %s" % close_exc,
                RuntimeWarning,
            )
        return {"status": code, "answers_304": code == 304,
                "note": "auth/error" if code in (401, 403, 400, 405) else "http_error"}
    except Exception as e:  # noqa
        return {"status": None, "answers_304": False, "note": "%s" % type(e).__name__}


def main():
    tested_by_r1 = set(json.load(open(R1))["measurements"]["3c_1_conditional_http"]
                       ["live_probe"]["results"])
    receipts = latest_receipts()

    targets = []
    for sid, d in receipts.items():
        if sid in tested_by_r1:
            continue
        resp = d.get("response", {})
        et, lm = resp.get("etag"), resp.get("last_modified")
        if not (et or lm):
            continue  # advertises no validator
        req = d.get("request", {})
        targets.append((sid, req.get("url", ""), req.get("method", "GET"), et, lm,
                        d.get("adapter") or resp.get("adapter")))

    results = {}
    last_host_time = defaultdict(float)
    for sid, url, method, et, lm, adapter in sorted(targets):
        host = urlparse(url).netloc
        wait = PER_HOST_SLEEP - (time.time() - last_host_time[host])
        if wait > 0:
            time.sleep(wait)
        r = probe_one(url, method, et, lm)
        last_host_time[host] = time.time()
        r.update({"host": host, "method": method,
                  "advertised": ("etag" if et else "") + ("last_modified" if lm else "")})
        results[sid] = r
        print("%-45s %s 304=%s %s" % (sid, r["status"], r["answers_304"], r["note"] or ""),
              file=sys.stderr)

    honored = sorted(s for s, r in results.items() if r["answers_304"])
    untestable = sorted(s for s, r in results.items()
                        if r["status"] in (None, 400, 401, 403, 405))
    ignored = sorted(s for s, r in results.items()
                     if r["status"] == 200)
    summary = {
        "r1_tested": len(tested_by_r1),
        "r1_answered_304": 6,
        "extended_targets": len(targets),
        "extended_probed": len(results),
        "extended_answered_304": len(honored),
        "extended_ignored_200": len(ignored),
        "extended_untestable": len(untestable),
        "true_total_tested": len(tested_by_r1) + len(results),
        "true_total_answered_304": 6 + len(honored),
        "extended_honored_source_ids": honored,
        "extended_untestable_source_ids": untestable,
        "results": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump(summary, open(OUT, "w"), indent=2, sort_keys=True)
    print(json.dumps({k: summary[k] for k in
                      ("r1_tested", "r1_answered_304", "extended_targets",
                       "extended_probed", "extended_answered_304",
                       "extended_ignored_200", "extended_untestable",
                       "true_total_tested", "true_total_answered_304")}, indent=2))


if __name__ == "__main__":
    main()
