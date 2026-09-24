import json, os, re, datetime as dt, bisect
ROOT="live_data"
HEADS=f"{ROOT}/runtime/source_heads"
NORM=f"{ROOT}/store/normalized/sha256"
def norm_path(sha): return f"{NORM}/{sha[:2]}/{sha}.json"
def load_source(source_id):
    h=json.load(open(f"{HEADS}/{source_id}.json"))
    sha=h["normalized_sha256"]
    d=json.load(open(norm_path(sha)))
    return h,d["records"]
ASOF_RE=re.compile(r"\.(?:DEEP)?ASOF(\d{8})$")
def asof_date(series_id):
    m=ASOF_RE.search(series_id or "")
    if not m: return None
    s=m.group(1); return dt.date(int(s[:4]),int(s[4:6]),int(s[6:8]))
def members():
    d=json.load(open("model_authority/temporal/realtime_coverage_manifest.v1.json"))
    return d["members"], d["channels"]
