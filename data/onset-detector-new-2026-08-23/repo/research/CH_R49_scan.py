#!/usr/bin/env python3
"""CH-R49 SPF identity preflight scanner. Read-only. No network, no store writes."""
import os, re, json, zipfile, glob
from xml.etree import ElementTree as ET

SPFDIR = "research/prefetch/forecasts/spf"
OUT = "research/CH_R49_scan_raw.json"

# name-ish heuristics: a value that looks like a human name (letters + space) not a code
NAME_HEADER_HINTS = re.compile(r"(name|creator|author|analyst|respondent|firm|company|institution|contact|last.?modified)", re.I)
# SPF anonymous ids are small integers. A human name = alphabetic tokens.
ALPHA_NAME = re.compile(r"^[A-Za-z][A-Za-z.\-']+(?:\s+[A-Za-z.\-']+){1,3}$")

def shared_strings(z):
    try:
        data = z.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ET.fromstring(data)
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    out = []
    for si in root.iter(ns+"si"):
        # concatenate all t nodes
        txt = "".join(t.text or "" for t in si.iter(ns+"t"))
        out.append(txt)
    return out

def core_xml(z):
    try:
        data = z.read("docProps/core.xml")
    except KeyError:
        return None, {}
    txt = data.decode("utf-8", "replace")
    fields = {}
    for tag in ("creator","lastModifiedBy","title","subject","description","keywords","category"):
        m = re.search(rf"<(?:dc:|cp:)?{tag}>(.*?)</(?:dc:|cp:)?{tag}>", txt, re.S|re.I)
        if m:
            fields[tag] = m.group(1).strip()
    return txt, fields

def sheet_names(z):
    try:
        wb = z.read("xl/workbook.xml").decode("utf-8","replace")
    except KeyError:
        return []
    return re.findall(r'<sheet[^>]*name="([^"]*)"', wb)

def scan_file(path):
    rec = {"file": os.path.basename(path), "sheets": [], "core": {}, "core_defect": False,
           "name_hits": [], "id_column_values_sample": {}, "headers_by_sheet": {}}
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        ss = shared_strings(z)
        # scan shared strings for human names & name-ish headers
        for i, s in enumerate(ss):
            s2 = s.strip()
            if not s2:
                continue
            if NAME_HEADER_HINTS.search(s2):
                rec["name_hits"].append({"where":"sharedStrings","value":s2,"reason":"header-hint"})
            elif ALPHA_NAME.match(s2) and len(s2) > 4 and not s2.isupper():
                # candidate human name (mixed-case multi-token alpha). SPF codes are UPPER.
                rec["name_hits"].append({"where":"sharedStrings","value":s2,"reason":"looks-like-name"})
        rec["sheets"] = sheet_names(z)
        # core.xml
        raw, fields = core_xml(z)
        rec["core"] = fields
        # openpyxl core defect: core.xml present but malformed/empty dcterms — check well-formed
        if raw is not None:
            try:
                ET.fromstring(raw.encode() if isinstance(raw,str) else raw)
            except Exception as e:
                rec["core_defect"] = True
                rec["core_defect_msg"] = str(e)
        else:
            rec["core_defect"] = True
            rec["core_defect_msg"] = "no docProps/core.xml"
        # flag human names in core fields
        for k,v in fields.items():
            if v and k in ("creator","lastModifiedBy") and ALPHA_NAME.match(v) and not v.isupper():
                rec["name_hits"].append({"where":f"core.xml/{k}","value":v,"reason":"name-in-metadata"})
        # per-sheet header row: read first sheet's row 1 to get column headers.
        # Build sheet id -> path map
        sheet_files = sorted([n for n in names if re.match(r"xl/worksheets/sheet\d+\.xml$", n)])
        for sf in sheet_files[:60]:
            try:
                data = z.read(sf).decode("utf-8","replace")
            except Exception:
                continue
            # first row cells
            first_row = re.search(r"<row[^>]*r=\"1\"[^>]*>(.*?)</row>", data, re.S)
            hdrs = []
            if first_row:
                for c in re.finditer(r'<c[^>]*?(?:t="(?P<t>[^"]*)")?[^>]*?><v>(?P<v>[^<]*)</v></c>', first_row.group(1)):
                    val = c.group("v")
                    if c.group("t") == "s":
                        try: val = ss[int(val)]
                        except: pass
                    hdrs.append(val)
            rec["headers_by_sheet"][sf] = hdrs
    return rec

def main():
    files = sorted(glob.glob(os.path.join(SPFDIR,"individual_*.xlsx")))
    allrecs = [scan_file(p) for p in files]
    # also scan the micro master + a couple aggregates for completeness
    for extra in ["spfmicrodata.xlsx"]:
        p = os.path.join(SPFDIR, extra)
        if os.path.exists(p):
            allrecs.append(scan_file(p))
    json.dump({"records": allrecs}, open(OUT,"w"), indent=1)
    # summary
    names_present = False
    files_with_names = []
    for r in allrecs:
        if r["name_hits"]:
            names_present = True
            files_with_names.append(r["file"])
    print("FILES SCANNED:", len(allrecs))
    print("NAMES_PRESENT:", names_present)
    print("FILES_WITH_NAMES:", files_with_names)
    print("CORE_DEFECT files:", [r["file"] for r in allrecs if r["core_defect"]])
    print("--- name_hits detail ---")
    for r in allrecs:
        if r["name_hits"]:
            print(r["file"])
            for h in r["name_hits"][:20]:
                print("   ", h)
    print("--- core.xml fields (first 3 files) ---")
    for r in allrecs[:3]:
        print(r["file"], r["core"])

if __name__ == "__main__":
    main()
