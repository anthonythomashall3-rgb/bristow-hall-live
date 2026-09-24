#!/usr/bin/env python3
"""B-LAND-ALL-FINAL steps 1-2: cross every unique-by-sha DATA file from the v2
universe walk against the store sha manifest. Partition:
  already_in_store  -> sha present in DATA_SHA256SUMS (landed, no action)
  candidate         -> data-class, sha NOT in store -> needs landing OR receipted disposition
Group candidates by tree + directory + ext so dispositions apply in bulk (§19.4 no silent cap:
every candidate row is accounted). Read-only; zero store writes."""
import os, json, collections

BH = os.path.expanduser("~/Projects/bristow-hall")
REPO = os.path.join(BH, "repo")
OUT = os.path.join(REPO, "research/land_all_final")

# store sha set (col1 of DATA_SHA256SUMS)
store = set()
with open(os.path.join(REPO, "DATA_SHA256SUMS")) as f:
    for line in f:
        line = line.strip()
        if not line: continue
        store.add(line.split()[0])

idx = json.load(open(os.path.join(REPO, "data_universe_index.v2.json")))
files = idx["files"]

# unique by sha (first occurrence), keep all paths per sha for reporting copies
paths_by_sha = collections.defaultdict(list)
rec_by_sha = {}
for r in files:
    paths_by_sha[r["sha256"]].append(r["path"])
    rec_by_sha.setdefault(r["sha256"], r)

uniq = list(rec_by_sha.values())
in_store = [r for r in uniq if r["sha256"] in store]
not_store = [r for r in uniq if r["sha256"] not in store]

data_cand = [r for r in not_store if r["klass"] == "data"]

# directory grouping for data candidates
def topdir(p):
    rel = os.path.relpath(p, BH)
    parts = rel.split(os.sep)
    return os.sep.join(parts[:4])  # coarse dir bucket

grp = collections.defaultdict(lambda: {"n": 0, "bytes": 0, "exts": collections.Counter()})
for r in data_cand:
    g = grp[topdir(r["path"])]
    g["n"] += 1; g["bytes"] += r["size"]; g["exts"][r["ext"]] += 1

groups = sorted(grp.items(), key=lambda kv: -kv[1]["n"])
summary = {
    "unique_by_sha": len(uniq),
    "already_in_store": len(in_store),
    "not_in_store": len(not_store),
    "not_in_store_data_class": len(data_cand),
    "not_in_store_by_class": dict(collections.Counter(r["klass"] for r in not_store)),
    "data_candidate_groups": [
        {"dir": k, "n": v["n"], "bytes": v["bytes"], "exts": dict(v["exts"])}
        for k, v in groups
    ],
}
with open(os.path.join(OUT, "crosscheck_summary.json"), "w") as f:
    json.dump(summary, f, indent=2)

# full candidate rows (path,sha,size,ext,tree) for disposition
with open(os.path.join(OUT, "data_candidates.tsv"), "w") as f:
    f.write("tree\tsize\text\tsha256\tpath\tn_copies\n")
    for r in sorted(data_cand, key=lambda r: (r["tree"], r["path"])):
        f.write(f'{r["tree"]}\t{r["size"]}\t{r["ext"]}\t{r["sha256"]}\t{r["path"]}\t{len(paths_by_sha[r["sha256"]])}\n')

print(json.dumps(summary)[:1200])
