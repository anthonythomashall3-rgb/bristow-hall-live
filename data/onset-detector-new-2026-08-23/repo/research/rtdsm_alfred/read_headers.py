"""CH-R103 stdlib xlsx header/colA reader (no openpyxl in this env).

Reads ONLY row 1 (vintage column names) and column A (obs periods) of each
RTDSM workbook -> first/last vintage stamp + obs-period span. Values are NOT
read; the identity test is decided on the vintage-date GRID, which the column
headers fully determine. Pure stdlib: zipfile + xml.
"""
import json, re, zipfile, io, sys
import xml.etree.ElementTree as ET

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_VCOL = re.compile(r"^(?P<var>[A-Za-z0-9]+?)(?P<yy>\d{2})(?P<kind>[QM])(?P<n>\d{1,2})$")
_QMID = {"1":"02","2":"05","3":"08","4":"11"}
_QF = {"1":"01","2":"04","3":"07","4":"10"}

def yy4(yy):
    n=int(yy); return 2000+n if n<50 else 1900+n

def vstamp(name, var):
    m=_VCOL.match(name)
    if not m or m.group("var").upper()!=var.upper(): return None
    y=yy4(m.group("yy")); k=m.group("kind"); n=m.group("n")
    if k=="Q":
        mo=_QMID.get(n)
        if not mo: return None
    else:
        mi=int(n)
        if not 1<=mi<=12: return None
        mo="%02d"%mi
    return "%04d%s01"%(y,mo)

def colref_to_idx(ref):
    c=re.match(r"^([A-Z]+)",ref).group(1); n=0
    for ch in c: n=n*26+(ord(ch)-64)
    return n-1

def read(path, var):
    z=zipfile.ZipFile(path)
    shared=[]
    if "xl/sharedStrings.xml" in z.namelist():
        r=ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in r.findall(NS+"si"):
            shared.append("".join(t.text or "" for t in si.iter(NS+"t")))
    # find first worksheet
    wbook=ET.fromstring(z.read("xl/workbook.xml"))
    # sheet1 default
    sheetpath="xl/worksheets/sheet1.xml"
    for n in z.namelist():
        if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"):
            sheetpath=n; break
    def cellval(c):
        t=c.get("t"); v=c.find(NS+"v"); isx=c.find(NS+"is")
        if isx is not None:
            return "".join(x.text or "" for x in isx.iter(NS+"t"))
        if v is None or v.text is None: return None
        if t=="s": return shared[int(v.text)]
        return v.text
    header=[]; colA=[]
    root=ET.fromstring(z.read(sheetpath))
    sd=root.find(NS+"sheetData")
    for row in sd.findall(NS+"row"):
        rn=row.get("r")
        cells={colref_to_idx(c.get("r")):cellval(c) for c in row.findall(NS+"c")}
        if rn=="1":
            mx=max(cells) if cells else -1
            header=[cells.get(i) for i in range(mx+1)]
        else:
            colA.append(cells.get(0))
    z.close()
    stamps=[]
    for name in header[1:]:
        if not name: continue
        s=vstamp(str(name).strip(), var)
        if s: stamps.append(s)
    periods=[str(p).strip() for p in colA if p not in (None,"")]
    kind="M" if header[1] and _VCOL.match(str(header[1]).strip()) and _VCOL.match(str(header[1]).strip()).group("kind")=="M" else "Q"
    return {
        "var":var,"file":path.split("/")[-1],"n_vintage_cols":len(stamps),
        "first_vintage":min(stamps) if stamps else None,
        "last_vintage":max(stamps) if stamps else None,
        "kind":kind,"n_obs_rows":len(periods),
        "first_period":periods[1] if len(periods)>1 else (periods[0] if periods else None),
        "last_period":periods[-1] if periods else None,
    }

if __name__=="__main__":
    import os
    base="research/prefetch/rtdsm"
    man=[json.loads(l) for l in open(base+"/_manifest.jsonl")]
    # one representative QvMd/MvMd file per var (the vintage matrix)
    picks={}
    for e in man:
        f=e["file"]
        if re.search(r"v[Md]d?\.xlsx$",f) or f.endswith("QvMd.xlsx") or f.endswith("MvMd.xlsx"):
            picks.setdefault(e["var"],e)
    # fallback: first file per var
    for e in man:
        picks.setdefault(e["var"],e)
    out=[]
    for var in sorted(picks):
        e=picks[var]; p=base+"/"+e["path"].split("rtdsm/")[-1] if "rtdsm/" in e["path"] else base+"/"+e["path"]
        p=os.path.join(base, e["path"].replace("rtdsm/",""))
        try:
            out.append(read(p,var))
        except Exception as ex:
            out.append({"var":var,"file":e["file"],"error":repr(ex)})
    json.dump(out, open("research/rtdsm_alfred/rtdsm_headers.json","w"), indent=0)
    ok=[o for o in out if "error" not in o]
    print("parsed",len(ok),"/",len(out),"errors",len(out)-len(ok))
