"""B-MEAS-1 Section B (RQ-2): repair the corrupt observation-span ceiling.
Read-only. Method: scan every UNIQUE class==CSV file (TSV first_path). A 'date
column' = header cell whose lowercased name contains 'date'/'period'/'time' OR
the first column. Value is a VALID date iff it matches ^YYYY-MM-DD$ and parses
as a real calendar date with 1700<=year<=2099. Anything date-column-shaped that
fails is a REJECT (collected with sha+path+row+value). No silent exclusions."""
import csv, os, re, json, datetime

TSV = os.path.expanduser("~/Desktop/RMV2-Inventories/RMV2_TOTALITY_UNIQUE.tsv")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LOOSE_RE = re.compile(r"^\d{3,4}-\d{1,2}-\d{1,2}$")

def is_date_col(name):
    n = (name or "").lower()
    return ("date" in n or "period" in n or n in ("time", "observation_date"))

def valid(v):
    if not DATE_RE.match(v):
        return None
    try:
        d = datetime.date.fromisoformat(v)
    except ValueError:
        return None
    if 1700 <= d.year <= 2099:
        return d
    return None

rows = []
with open(TSV, encoding="utf-8") as f:
    hdr = f.readline().rstrip("\n").split("\t")
    for line in f:
        p = line.rstrip("\n").split("\t")
        r = dict(zip(hdr, p))
        if r["class"] == "CSV":
            rows.append(r)

max_valid = None
max_ctx = None
rejects = []          # date-column-shaped but not a valid calendar date in range
special = {"2028-01-01": [], "2036-10-01": []}
loose_max = None
loose_ctx = None
scanned = errors = 0

for r in rows:
    path = r["first_path"]
    try:
        with open(path, "r", encoding="utf-8", errors="replace", newline="") as fh:
            reader = csv.reader(fh)
            header = next(reader, None)
            if not header:
                continue
            date_idx = [i for i, c in enumerate(header) if is_date_col(c)]
            if not date_idx:
                date_idx = [0]  # fall back to first column
            scanned += 1
            for rownum, row in enumerate(reader, start=2):
                for i in date_idx:
                    if i >= len(row):
                        continue
                    v = row[i].strip().strip('"')
                    if not v:
                        continue
                    d = valid(v)
                    if d is not None:
                        if max_valid is None or d > max_valid:
                            max_valid = d
                            max_ctx = (r["sha256"], path, rownum, v)
                        if v in special and len(special[v]) < 5:
                            special[v].append({"sha256": r["sha256"], "path": path, "row": rownum})
                    else:
                        # only flag things that look like they were meant to be dates
                        if LOOSE_RE.match(v) or (len(v) >= 7 and v[:4].isdigit() and "-" in v):
                            if len(rejects) < 200:
                                rejects.append({"sha256": r["sha256"], "path": path,
                                                "row": rownum, "col": header[i], "value": v})
                            # track the loose max to reveal what corrupted the ceiling
                            if loose_max is None or v > loose_max:
                                loose_max = v
                                loose_ctx = (r["sha256"], path, rownum, header[i], v)
    except (OSError, StopIteration):
        errors += 1
    except Exception:
        errors += 1

out = {
    "batch": "B-MEAS-1", "section": "B", "rq": "RQ-2",
    "method": "unique class==CSV; date cols by name-contains date/period/time else col0; "
              "valid=^YYYY-MM-DD$ & real calendar date & 1700<=yr<=2099",
    "csv_files_total": len(rows),
    "csv_files_scanned": scanned,
    "read_errors": errors,
    "true_ceiling_valid": max_valid.isoformat() if max_valid else None,
    "true_ceiling_ctx": {"sha256": max_ctx[0], "path": max_ctx[1], "row": max_ctx[2],
                         "value": max_ctx[3]} if max_ctx else None,
    "corrupt_loose_max_value": loose_max,
    "corrupt_loose_max_ctx": ({"sha256": loose_ctx[0], "path": loose_ctx[1], "row": loose_ctx[2],
                               "col": loose_ctx[3], "value": loose_ctx[4]} if loose_ctx else None),
    "reject_count": len(rejects),
    "rejects_sample": rejects[:50],
    "special_2028_01_01": special["2028-01-01"],
    "special_2036_10_01": special["2036-10-01"],
}
outp = "research/meas1_scratch/rq2_ceiling.json"
with open(outp, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)

print("csv_total", len(rows), "scanned", scanned, "read_errors", errors)
print("TRUE_CEILING(valid)", out["true_ceiling_valid"], "ctx", out["true_ceiling_ctx"])
print("CORRUPT loose_max", loose_max, "ctx", out["corrupt_loose_max_ctx"])
print("reject_count", len(rejects))
print("2028-01-01 seen in", len(special["2028-01-01"]), "->", special["2028-01-01"][:2])
print("2036-10-01 seen in", len(special["2036-10-01"]), "->", special["2036-10-01"][:3])
print("OUT", outp)
