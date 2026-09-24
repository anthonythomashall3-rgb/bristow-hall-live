import io, re, zipfile, openpyxl
from openpyxl.worksheet._read_only import ReadOnlyWorksheet
def repair(b):
    zin=zipfile.ZipFile(io.BytesIO(b)); items={n:zin.read(n) for n in zin.namelist()}
    cx=items.get('docProps/core.xml')
    if cx: items['docProps/core.xml']=re.sub(rb'T\s?(\d):', rb'T0\1:', cx)
    out=io.BytesIO(); zo=zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED)
    for n,d in items.items(): zo.writestr(n,d)
    zo.close(); out.seek(0); return out
b=open("research/prefetch/forecasts/anxious_index/anxious_index_chart.xlsx",'rb').read()
wb=openpyxl.load_workbook(repair(b),read_only=True,data_only=True)
ws=wb['Data']; rows=list(ws.iter_rows(values_only=True))
for ci in range(5):
    vals=[r[ci] for r in rows if len(r)>ci and r[ci] is not None]
    print("col",ci,"nonnull",len(vals),"sample",vals[:3],"...",vals[-3:])
# show rows 4..10 and around a recession
for r in rows[3:12]: print("R",r)
print("--- rows with AnxiousIndex nonnull ---")
cnt=0
for r in rows:
    if len(r)>2 and r[2] is not None:
        print(r); cnt+=1
        if cnt>4: break
wb.close()
