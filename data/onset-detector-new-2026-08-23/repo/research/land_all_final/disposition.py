#!/usr/bin/env python3
"""B-LAND-ALL-FINAL: assign a receipted disposition to EVERY unique-by-sha data-class
candidate (not matched to a store payload sha). Rule-based by path prefix. §19.4: zero
silent caps — every row lands in exactly one bucket; residual 'UNCLASSIFIED' is reported
in full for manual inspection. Read-only."""
import os, json, collections

BH = os.path.expanduser("~/Projects/bristow-hall")
REPO = os.path.join(BH, "repo")
OUT = os.path.join(REPO, "research/land_all_final")

store = set()
for line in open(os.path.join(REPO, "DATA_SHA256SUMS")):
    line = line.strip()
    if line: store.add(line.split()[0])

idx = json.load(open(os.path.join(REPO, "data_universe_index.v2.json")))
rec_by_sha = {}
for r in idx["files"]:
    rec_by_sha.setdefault(r["sha256"], r)
cand = [r for r in rec_by_sha.values()
        if r["klass"] == "data" and r["sha256"] not in store]

# ordered (prefix_substring, disposition_bucket, reason)
RULES = [
    ("repo/live_data/store/",            "STORE_INTERNAL",   "live_data acquisition-spine store internal artifact (IS the store; distinct manifest from data_vault DATA_SHA256SUMS)"),
    ("repo/live_data/feed_factory/",     "OPERATIONAL",      "feed_factory candidate/probe/draft — acquisition machinery output, not external raw data"),
    ("repo/live_data/runtime/",          "OPERATIONAL",      "live_data runtime status/heads/autopilot — operational state, not data"),
    ("repo/live_data/",                  "OPERATIONAL",      "live_data spine internal (non-store path)"),
    ("repo/research/prefetch/nber_macrohistory", "HELD_BLOCKED", "NBER macrohistory raw .dat — OPEN blocker DEFECT__nber_macrohist_parser_scinotation_gap; landing gated on parser fix"),
    ("repo/research/prefetch/",          "STAGING",          "prefetched raw source bytes staged by a prior/in-flight acquisition batch; landed series live in store under their own sha"),
    ("repo/research/_staging/bea_histdata", "STAGING",       "BEA histdata staging — feeds B-FETCH-BEA-HISTDATA (W2, in-flight)"),
    ("repo/research/_staging/fraser",    "STAGING",          "FRASER staging — feeds B-ACQ-FRASER family"),
    ("repo/research/_staging/",          "STAGING",          "in-flight acquisition staging bytes"),
    ("repo/research/land_all_final/",    "THIS_BATCH",       "this batch's own artifacts"),
    ("repo/research/",                   "DERIVED_OUTPUT",   "research derived output (arrays/results/scratch) — not acquirable raw data"),
    ("repo/tools/",                      "DERIVED_OUTPUT",   "tool-generated output"),
    ("repo/data_archive/",              "REDUNDANT",        "in-repo data archive; superseded copies of landed series"),
    ("repo/site/",                       "DERIVED_OUTPUT",   "site payload display aggregate (derived_output per B-XVERSION census)"),
    ("repo/artifact_build/",             "DERIVED_OUTPUT",   "artifact build output"),
    ("repo/",                            "REPO_OTHER",       "other in-repo data-class file not in payload manifest"),
    ("archive/rmv2-archive/",            "BACKUP_DUPE",      "predecessor backup snapshot (owner: old versions inadequate, DATA-only; swept by B-XV-LAND-OLDRAW / B-XVERSION-DATA-CENSUS)"),
    ("archive/vault-backups/",           "BACKUP_DUPE",      "vault backup snapshot — byte copies of store vintages"),
    ("archive/saved/",                   "PREDECESSOR",      "read-only preserved predecessor (Codex BHI2 Complex) — fidelity-pinned, DATA lessons in B-LESSONS-AUDIT"),
    ("archive/",                         "ARCHIVE_OTHER",    "archived misc data-class file"),
    ("projects-old/",                    "PREDECESSOR_DERIVED", "predecessor Codex research derived output (npz/npy/jsonl arrays) — not raw data (owner: methods excluded, lessons in B-LESSONS-AUDIT)"),
    ("inbox/",                           "INBOX",            "inbox drop — transient"),
    ("inventories/",                     "DERIVED_OUTPUT",   "inventory ledger (derived accounting, not source data)"),
    ("queue/",                           "QUEUE_META",       "queue/mailbox metadata json — not data"),
    ("ops/",                             "OPERATIONAL",      "ops logs/state"),
    ("papers/",                          "DOC",              "paper asset"),
    ("Codex", "PREDECESSOR",             "read-only Codex outputs (~/Documents/Codex) — DATA lessons in B-LESSONS-AUDIT"),
]

buckets = collections.defaultdict(lambda: {"n": 0, "bytes": 0, "reason": "", "sample": []})
unclassified = []
for r in cand:
    rel = os.path.relpath(r["path"], BH)
    placed = False
    for pref, bucket, reason in RULES:
        if rel.startswith(pref) or pref in rel:
            b = buckets[bucket]
            b["n"] += 1; b["bytes"] += r["size"]; b["reason"] = reason
            if len(b["sample"]) < 3: b["sample"].append(rel)
            placed = True; break
    if not placed:
        unclassified.append(rel)

report = {
    "candidates_total": len(cand),
    "buckets": {k: {"n": v["n"], "bytes": v["bytes"], "reason": v["reason"], "sample": v["sample"]}
                for k, v in sorted(buckets.items(), key=lambda kv: -kv[1]["n"])},
    "unclassified_n": len(unclassified),
    "unclassified": unclassified[:200],
}
with open(os.path.join(OUT, "disposition_report.json"), "w") as f:
    json.dump(report, f, indent=2)

print("candidates_total", len(cand), "unclassified", len(unclassified))
for k, v in report["buckets"].items():
    print(f"  {v['n']:6d}  {v['bytes']:>13d}  {k:22} :: {v['reason'][:70]}")
