import glob,os,re,csv
D="research/prefetch/nber_macrohistory"
# find files with any non-42 line
anom=[]
for dp in sorted(glob.glob(f"{D}/data/*/*.dat")):
    with open(dp,encoding="latin-1") as f:
        for i,ln in enumerate(f,1):
            raw=ln.rstrip("\n")
            if len(raw)!=42:
                anom.append((os.path.relpath(dp),i,len(raw),repr(raw[:56])))
print("=== non-42 lines ===")
for a in anom: print(a)
# period_max==0 and blank-missing files from catalog
print("=== catalog rows period_max=0 or nblank>0 ===")
for r in csv.DictReader(open("research/nber_catalog_scan.csv")):
    if r["period_max"]=="0" or int(r["nblank"])>0:
        print(r["id"],r["chapter"],"pmax",r["period_max"],"nblank",r["nblank"],"nobs",r["nobs"],r["title"][:40])
