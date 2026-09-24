import csv
rows=[r for r in csv.DictReader(open("research/nber_catalog_scan.csv"))]
print("=== any CARLOAD starting <=1918 ===")
for r in rows:
    if "CARLOAD" in r["title"].upper() and int(r["ymin"] or 9999)<=1918:
        print(" ",r["id"],r["ymin"],r["ymax"],r["nobs"],r["title"][:55])
print("=== all RETAIL TRADE titles ===")
for r in rows:
    if "RETAIL" in r["title"].upper() and "TRADE" in r["title"].upper():
        print(" ",r["id"],r["ymin"],r["ymax"],r["nobs"],r["title"][:55])
print("=== dept store SALES dupes m06002* ===")
for r in rows:
    if r["id"].startswith("m06002"):
        print(" ",r["id"],r["ymin"],r["ymax"],r["nobs"],r["sa"],"|",r["title"][:50])
# the 70 title-less: which chapters, sample doc
miss=[r for r in rows if not r["title"]]
from collections import Counter
print("=== 70 title-less by chapter ===",Counter(r["chapter"] for r in miss))
print("sample ids:",[r["id"] for r in miss[:8]])
