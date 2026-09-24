import io, re, zipfile, openpyxl
def repair(b):
    zin=zipfile.ZipFile(io.BytesIO(b)); items={n:zin.read(n) for n in zin.namelist()}
    cx=items.get('docProps/core.xml')
    if cx: items['docProps/core.xml']=re.sub(rb'T\s?(\d):', rb'T0\1:', cx)
    out=io.BytesIO(); zo=zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED)
    for n,d in items.items(): zo.writestr(n,d)
    zo.close(); out.seek(0); return out
b=open("research/prefetch/forecasts/spf/individual_rgdp.xlsx",'rb').read()
wb=openpyxl.load_workbook(repair(b),read_only=True,data_only=True)
print("sheets",wb.sheetnames)
ws=wb[wb.sheetnames[0]]; rows=list(ws.iter_rows(values_only=True))
print("nrows",len(rows),"header",rows[0])
for r in rows[1:5]: print(r)
print("last",rows[-1])
# distinct IDs, industries
hdr=rows[0]
idi=hdr.index('ID') if 'ID' in hdr else None
print("ID col",idi)
ids=set(r[idi] for r in rows[1:] if r[idi] is not None)
print("distinct IDs",len(ids),"min",min(ids),"max",max(ids))
wb.close()
# also list mean vs median aggregate files count
import os
sp="research/prefetch/forecasts/spf"
fs=sorted(os.listdir(sp))
agg=[f for f in fs if f.startswith(('mean_','median_'))]
ind=[f for f in fs if f.startswith('individual_')]
print("agg files",len(agg),"ind files",len(ind))
print("agg sample",agg[:6])
