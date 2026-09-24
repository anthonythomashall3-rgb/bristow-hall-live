"""B-MEAS-1 Section C, extractor #2: the 36 store/generations snapshot.json
blobs (schema recession-monitor-v2.live-snapshot.v1). Observations live at
series[sid].observations[]. Same dedupe key; APPENDS to the same keyfile."""
import json, os

LIST = "research/meas1_scratch/big79.tsv"
KEYOUT = "research/meas1_scratch/big79_keys.tsv"
STATS2 = "research/meas1_scratch/rq3_stats2.json"

raw = 0
files = 0
series = set()
modes = {}
errs = []

with open(KEYOUT, "a", encoding="utf-8") as ko:
    for line in open(LIST):
        sha, nbytes, path = line.rstrip("\n").split("\t")
        if "store/generations" not in path:
            continue
        try:
            d = json.load(open(path, encoding="utf-8"))
        except Exception as e:
            errs.append(f"{path}: {e}")
            continue
        ser = d.get("series", {})
        for sid, obj in ser.items():
            for o in obj.get("observations", []):
                raw += 1
                s = o.get("series_id", sid)
                op = o.get("observation_period", "")
                val = o.get("value", "")
                av = o.get("available_at", "")
                mode = o.get("information_set_mode", "")
                series.add(s)
                modes[mode] = modes.get(mode, 0) + 1
                ko.write(f"{s}\t{op}\t{val}\t{av}\n")
        files += 1
        del d
        print(f"  store {files}/36 raw={raw} {os.path.basename(os.path.dirname(path))[:12]}", flush=True)

stats = {"store_blobs_measured": files, "store_raw_records": raw,
         "store_distinct_series": len(series), "store_modes": modes, "errors": errs}
with open(STATS2, "w", encoding="utf-8") as f:
    json.dump(stats, f, indent=2)
print("STORE_RAW", raw, "FILES", files, "SERIES", len(series))
print("MODES", modes)
