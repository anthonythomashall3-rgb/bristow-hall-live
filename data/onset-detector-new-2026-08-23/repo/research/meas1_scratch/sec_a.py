"""B-MEAS-1 Section A (RQ-5): classify HTML masqueraders. Read-only.
Method: TSV is trusted for class/sha (never re-walk). Fingerprint = first 200
bytes of the file at first_path (targeted reads, not a tree walk)."""
import json, hashlib, os, re, sys

TSV = os.path.expanduser("~/Desktop/RMV2-Inventories/RMV2_TOTALITY_UNIQUE.tsv")
REPO = "/Users/anthonyhall/Desktop/RecessionMonitor 2/Recession Monitor V2"
QDIR = os.path.join(REPO, "data_archive/current_revised_and_spatial/quarantine")

def rows():
    with open(TSV, encoding="utf-8") as f:
        hdr = f.readline().rstrip("\n").split("\t")
        for line in f:
            parts = line.rstrip("\n").split("\t")
            yield dict(zip(hdr, parts))

html = [r for r in rows() if r["class"] == "HTML"]

def head200(path):
    try:
        with open(path, "rb") as fh:
            return fh.read(200)
    except OSError:
        return None

def cluster_of(b):
    if b is None:
        return "unreadable(first_path moved)"
    t = b.decode("latin-1", "replace").lower()
    if "<!doctype html" in t or "<html" in t:
        if "404" in t or "not found" in t or "error" in t:
            return "publisher error page"
        if "429" in t or "rate limit" in t or "too many requests" in t:
            return "rate-limit page"
        if "login" in t or "sign in" in t or "password" in t:
            return "login wall"
        return "html document (generic)"
    if t.startswith("<?php"):
        return "php source (non-html-tag)"
    if t.startswith("{") or t.startswith("["):
        return "json-ish body"
    if "<" in t[:5]:
        return "markup fragment"
    return "other/ambiguous"

# --- A.1/A.2: full HTML class ---
ext_re = re.compile(r"\.([^./]+)$")
clusters = {}
data_ext_masq = []
for r in html:
    m = ext_re.search(r["first_path"])
    ext = (m.group(1).lower() if m else "")
    b = head200(r["first_path"])
    cl = cluster_of(b)
    clusters.setdefault(cl, 0)
    clusters[cl] += 1
    if ext in ("csv", "json") or ext.startswith("xls"):
        data_ext_masq.append({"sha256": r["sha256"], "ext": ext, "bytes": r["bytes"],
                              "cluster": cl, "path": r["first_path"]})

# --- A.3: quarantine dir, per-file from bytes ---
def classify_file(path):
    with open(path, "rb") as fh:
        b = fh.read(200)
    # sha of whole file for the ledger
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    sha = h.hexdigest()
    t = b.decode("latin-1", "replace")
    tl = t.lower()
    is_html = ("<!doctype html" in tl or "<html" in tl or tl.startswith("<?php"))
    # real FRED-style CSV: header line with a date column name
    first_line = t.split("\n", 1)[0]
    looks_csv = ("," in first_line and not is_html and
                 re.match(r"^[\"']?(observation_date|DATE|date|realtime|[A-Za-z0-9_ ]+),", first_line) is not None)
    if is_html:
        if "404" in tl or "not found" in tl or "error" in tl:
            cl, verdict, rel = "publisher error page", "HTML masquerade (error page) — NOT data", False
        elif "429" in tl or "rate limit" in tl:
            cl, verdict, rel = "rate-limit page", "HTML masquerade (rate-limit) — NOT data", False
        elif "login" in tl or "sign in" in tl:
            cl, verdict, rel = "login wall", "HTML masquerade (login wall) — NOT data", False
        else:
            cl, verdict, rel = "html document", "HTML masquerade — NOT data", False
    elif looks_csv:
        cl, verdict, rel = "HTML-wrapped? no — real CSV table", "real data (CSV observations)", True
    else:
        cl, verdict, rel = "ambiguous", "ambiguous — needs manual look", False
    return {"file": os.path.basename(path), "sha256": sha, "bytes": os.path.getsize(path),
            "first_line": first_line[:120], "cluster": cl, "verdict": verdict,
            "release_eligible": rel}

qfiles = sorted(os.listdir(QDIR)) if os.path.isdir(QDIR) else []
qverdicts = [classify_file(os.path.join(QDIR, fn)) for fn in qfiles
             if os.path.isfile(os.path.join(QDIR, fn))]

ledger = {
    "batch": "B-MEAS-1", "section": "A", "rq": "RQ-5",
    "method": "TSV trusted for class; fingerprint=first 200 bytes of file at first_path",
    "html_class_total": len(html),
    "html_class_clusters": clusters,
    "html_with_data_extension_csv_json_xls": len(data_ext_masq),
    "data_extension_masqueraders": data_ext_masq,
    "quarantine_dir_file_count": len(qverdicts),
    "quarantine_verdicts": qverdicts,
    "release_eligible_count": sum(1 for q in qverdicts if q["release_eligible"]),
}
out = os.path.join(REPO, "data_vault/reports/html_masquerade_verdicts.v1.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w", encoding="utf-8") as f:
    json.dump(ledger, f, indent=2)

print("HTML_class_total", len(html))
print("clusters", json.dumps(clusters))
print("data_ext_masqueraders", len(data_ext_masq))
for d in data_ext_masq:
    print("  MASQ", d["ext"], d["sha256"][:12], d["path"].split("/")[-1])
print("quarantine_files", len(qverdicts))
for q in qverdicts:
    print(f"  Q {q['file']:32s} {q['cluster']:32s} rel={q['release_eligible']}")
print("release_eligible", ledger["release_eligible_count"])
print("LEDGER", out)
