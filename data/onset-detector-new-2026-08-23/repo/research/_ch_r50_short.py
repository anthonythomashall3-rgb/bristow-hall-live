import csv,re
rows=[r for r in csv.DictReader(open("research/nber_catalog_scan.csv"))]
def find(kw,ystart=None,units=None,extra=None):
    out=[]
    for r in rows:
        t=r["title"].upper()
        if all(k in t for k in kw):
            if extra and extra.upper() not in t: continue
            out.append(r)
    out.sort(key=lambda r:(abs(int(r["ymin"] or 0)-(ystart or int(r["ymin"] or 0))), -int(r["nobs"])))
    return out[:5]
def show(lbl,res):
    print(f"===== {lbl} =====")
    for r in res: print(f'  {r["id"]:10} {r["ymin"]}-{r["ymax"]} n={r["nobs"]:>4} u={r["units"][:16]:<16}| {r["title"][:56]}')
show("commercial-paper rate ~1857",find(["COMMERCIAL PAPER"],1857))
show("pig iron ~1877",find(["PIG IRON"],1877))
show("steel ingot ~1899",find(["STEEL INGOT"],1899))
show("carloadings ~1918",find(["CARLOADING"],1918))
show("call money",find(["CALL"],1857))
show("retail trade ~1914",find(["RETAIL"],1914))
show("department store sales",find(["DEPARTMENT STORE"],1919))
