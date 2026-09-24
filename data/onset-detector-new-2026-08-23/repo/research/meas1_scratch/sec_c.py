"""B-MEAS-1 Section C (RQ-3): unique observation contribution of the big store
objects. Read-only. Streams each file once, uncapped, one record at a time via
raw_decode (no whole-record list in RAM). Dedupe key stated BEFORE counting:
  (series_id, observation_period, value, available_at)
information_set_mode is also emitted so the union can be reasoned mode-aware.
Writes keys to disk; dedupe via `sort -u` in the shell step, not in RAM."""
import json, os, sys

LIST = "research/meas1_scratch/big79.tsv"
KEYOUT = "research/meas1_scratch/big79_keys.tsv"
STATS = "research/meas1_scratch/rq3_stats.json"

dec = json.JSONDecoder()
raw_records = 0
files_done = 0
series = set()
modes = {}
malformed_files = []

with open(KEYOUT, "w", encoding="utf-8") as ko:
    for line in open(LIST):
        sha, nbytes, path = line.rstrip("\n").split("\t")
        try:
            data = open(path, encoding="utf-8").read()
        except OSError as e:
            malformed_files.append(f"{path}: read {e}")
            continue
        try:
            i = data.index('"records"')
            i = data.index("[", i) + 1
        except ValueError:
            malformed_files.append(f"{path}: no records array")
            continue
        n = len(data)
        while i < n:
            c = data[i]
            if c in " \t\r\n,":
                i += 1
                continue
            if c == "]":
                break
            try:
                obj, end = dec.raw_decode(data, i)
            except json.JSONDecodeError as e:
                malformed_files.append(f"{path}@{i}: {e}")
                break
            i = end
            raw_records += 1
            sid = obj.get("series_id", "")
            op = obj.get("observation_period", "")
            val = obj.get("value", "")
            av = obj.get("available_at", "")
            mode = obj.get("information_set_mode", "")
            series.add(sid)
            modes[mode] = modes.get(mode, 0) + 1
            ko.write(f"{sid}\t{op}\t{val}\t{av}\n")
        files_done += 1
        del data
        print(f"  done {files_done}/79 raw={raw_records} {os.path.basename(path)}", flush=True)

stats = {
    "batch": "B-MEAS-1", "section": "C", "rq": "RQ-3",
    "dedupe_key": "(series_id, observation_period, value, available_at)",
    "big_objects_measured": files_done,
    "raw_records_total": raw_records,
    "distinct_series": len(series),
    "series_ids": sorted(series),
    "records_by_information_set_mode": modes,
    "malformed": malformed_files,
    "keyfile": KEYOUT,
    "note": "unique-tuple count = `LC_ALL=C sort -u KEYOUT | wc -l` (next shell step)",
}
with open(STATS, "w", encoding="utf-8") as f:
    json.dump(stats, f, indent=2)
print("RAW_RECORDS", raw_records, "FILES", files_done, "SERIES", len(series))
print("MODES", modes)
print("STATS", STATS)
