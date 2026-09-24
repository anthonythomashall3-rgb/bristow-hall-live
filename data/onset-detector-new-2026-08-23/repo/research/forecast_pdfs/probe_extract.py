"""B-REG-FORECAST-PDFS-R2 probe: prove text-layer extractability across the two
SEP projection-table formats + Livingston. Pure stdlib (zlib FlateDecode + BT/ET
Tj/TJ string scan). Writes ONE compact JSON summary; never dumps raw text to stdout.
"""
import json, re, sys, zlib
from pathlib import Path

def extract_text(pdf_bytes):
    """Return concatenated text-layer strings from all FlateDecode content streams."""
    out = []
    # find all stream...endstream, try zlib-inflate, scan for (..)Tj and [..]TJ
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", pdf_bytes, re.DOTALL):
        raw = m.group(1)
        try:
            data = zlib.decompress(raw)
        except Exception:
            continue
        # collect strings inside ( ) accounting for escapes; and TJ arrays
        buf = []
        i = 0
        n = len(data)
        while i < n:
            c = data[i:i+1]
            if c == b"(":
                j = i + 1
                depth = 1
                s = bytearray()
                while j < n and depth > 0:
                    ch = data[j:j+1]
                    if ch == b"\\":
                        nxt = data[j+1:j+2]
                        s += nxt
                        j += 2
                        continue
                    if ch == b"(":
                        depth += 1; s += ch
                    elif ch == b")":
                        depth -= 1
                        if depth > 0:
                            s += ch
                    else:
                        s += ch
                    j += 1
                buf.append(s.decode("latin-1", "replace"))
                i = j
            else:
                i += 1
        if buf:
            out.append("".join(buf))
    return "\n".join(out)

INDEX = json.load(open("research/forecast_pdfs/pdf_dated_index.v1.json"))

def pick(patts):
    res = []
    for r in INDEX:
        b = r["base"]
        for p in patts:
            if p(b):
                res.append(r); break
    return res

sep_comp = pick([lambda b: b.endswith("SEPcompilation.pdf")])
sep_tabl = pick([lambda b: b.startswith("fomcprojtabl")])
liv = [r for r in INDEX if r["cls"] == "forecast_livingston"
       and re.match(r"liv(dec|jun)\d\d\.pdf$", r["base"])]

ANCHORS = ["Real GDP", "Unemployment", "PCE inflation", "Change in real GDP",
           "Central tendency", "Range", "GDP"]

def probe(rows, label, k=4):
    rows = sorted(rows, key=lambda r: r.get("meeting_or_doc_date") or r["base"])
    picks = rows[:2] + rows[-2:] if len(rows) > 4 else rows
    recs = []
    for r in picks:
        p = Path(r["path"])
        try:
            txt = extract_text(p.read_bytes())
        except Exception as e:
            recs.append({"base": r["base"], "err": repr(e)}); continue
        low = txt.lower()
        anch = {a: (a.lower() in low) for a in ANCHORS}
        # count numeric range pairs "X.X to Y.Y"
        pairs = len(re.findall(r"\d\.\d\s*to\s*\d\.\d", txt))
        recs.append({"base": r["base"], "date": r.get("meeting_or_doc_date"),
                     "text_len": len(txt), "range_pairs": pairs,
                     "anchors_hit": sum(anch.values()),
                     "anchors": {a: v for a, v in anch.items() if v}})
    return {"label": label, "n_total": len(rows), "probed": recs}

summary = {
    "sep_compilation": probe(sep_comp, "SEPcompilation"),
    "sep_projtabl": probe(sep_tabl, "fomcprojtabl"),
    "livingston": probe(liv, "livingston"),
}
Path("research/forecast_pdfs/probe_summary.json").write_text(
    json.dumps(summary, indent=1))
print(json.dumps(summary, indent=1))
