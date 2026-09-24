#!/usr/bin/env python3
"""FRASER prose-headline extraction adapter — PROTOTYPE, proven on staged anchors.

Scope (measured, not assumed):
  INDPRO  index-level  from G.12/G.12.3/G.17 prose  "at X.X percent of the YYYY [annual] average"
  UNRATE  rate-level   from Employment Situation prose (3 level idioms, CHANGE idioms excluded)

The prior single-pass regex (B-ACQ-FRASER-RELEASES STOP) misfired BOTH ways:
  - MISSED  G.17 1990 108.8 (level phrased "at 108.8 percent of the 1987 annual average")
  - READ CHANGE AS LEVEL  unemployment "declined 0.4 point" style captured as a level
This adapter fixes both by (a) requiring the index-base anchor for INDPRO levels and
(b) matching only the three LEVEL idioms for UNRATE and taking the post-"to" value in a
from/to sentence. Every emitted value carries the source sentence for digit audit.

NOT a full-run tool. Emits null (not a guess) where prose carries no digit-verifiable level.
§6.3: no value is invented; a missing level is reported missing.
"""
import re, sys, json, subprocess, pathlib

WS = re.compile(r"\s+")

def text_of(pdf):
    # -layout preserves the prose line; collapse to single-space stream for multi-line idioms
    raw = subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                         capture_output=True, text=True).stdout
    return WS.sub(" ", raw)

# --- INDPRO: index LEVEL only (must carry the base-year anchor) ---
#   idiom A "at X.X percent of the YYYY average"   idiom B "to X.X percent of its YYYY annual average"
INDPRO_LEVEL = re.compile(
    r"\b(?:at|to)\s+(\d{2,3}[.,]\d)\s*percent\s+of\s+(?:the|its)\s+((?:19|20)\d{2})\s*(?:annual\s+)?average",
    re.IGNORECASE)

# --- UNRATE: LEVEL idioms only, CHANGE idioms excluded by construction ---
UNRATE_HELD = re.compile(
    r"unemployment rate\s*(?:held at|was little changed at|was|,)\s*(\d[.,]\d)\s*percent",
    re.IGNORECASE)
UNRATE_PAREN = re.compile(
    r"unemployment rate\s*\((\d\.\d)\s*percent\)", re.IGNORECASE)
UNRATE_FROMTO = re.compile(          # "rose/declined from A to B percent" -> level is B
    r"unemployment rate\s+(?:rose|declined|fell|increased|dropped|edged (?:up|down))\s+from\s+"
    r"\d\.\d\s*(?:to\s*)?percent?\s*(?:in \w+ )?to\s*(\d\.\d)\s*percent", re.IGNORECASE)
UNRATE_FROMTO2 = re.compile(         # "rose from A to B percent" simple
    r"unemployment rate\s+(?:rose|declined|fell|increased|dropped)\s+from\s+\d\.\d\s+to\s+(\d\.\d)\s*percent",
    re.IGNORECASE)

def sent_around(text, m, pad=90):
    a = max(0, m.start()-pad); b = min(len(text), m.end()+pad)
    return text[a:b].strip()

def _num(raw):
    # OCR sometimes writes comma-for-period (e.g. "109,7"). Flag it; DO NOT silently coerce
    # to a clean value — a corrupted decimal is a review item, not a digit-verified number.
    corrupt = "," in raw
    return float(raw.replace(",", ".")), corrupt

def extract_indpro(text):
    m = INDPRO_LEVEL.search(text)
    if not m: return None
    val, corrupt = _num(m.group(1))
    return {"metric":"INDPRO","value":val,"index_base":int(m.group(2)),
            "idiom":"of_the_YYYY_average","ocr_decimal_corrupt":corrupt,
            "digit_verified": not corrupt,"sentence":sent_around(text,m)}

def extract_unrate(text):
    for idiom, rx in (("held_at",UNRATE_HELD),("parenthetical",UNRATE_PAREN),
                      ("from_to",UNRATE_FROMTO2),("from_to_split",UNRATE_FROMTO)):
        m = rx.search(text)
        if m:
            val, corrupt = _num(m.group(1))
            return {"metric":"UNRATE","value":val,"index_base":None,
                    "idiom":idiom,"ocr_decimal_corrupt":corrupt,
                    "digit_verified": not corrupt,"sentence":sent_around(text,m)}
    return None

def classify(name):
    if "employnews" in name: return extract_unrate
    if name.startswith(("g17","g12")) or "_g17_" in name or "_g12" in name: return extract_indpro
    return None

if __name__ == "__main__":
    stage = pathlib.Path(sys.argv[1])
    out = []
    for pdf in sorted(stage.rglob("*.pdf")):
        n = pdf.stem
        fn = classify(n)
        if fn is None: continue
        rec = fn(text_of(pdf))
        out.append({"file":n,"printed":n.split("_")[-1],
                    "extracted": rec})
    json.dump(out, open(sys.argv[2],"w"), indent=1)
    print(json.dumps(out, indent=1))
