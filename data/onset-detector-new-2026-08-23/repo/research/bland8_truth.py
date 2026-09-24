import io,re,zipfile,openpyxl,os,json
def repair(b):
    zin=zipfile.ZipFile(io.BytesIO(b)); items={n:zin.read(n) for n in zin.namelist()}
    cx=items.get('docProps/core.xml')
    if cx: items['docProps/core.xml']=re.sub(rb'T\s?(\d):', rb'T0\1:', cx)
    out=io.BytesIO(); zo=zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED)
    for n,d in items.items(): zo.writestr(n,d)
    zo.close(); out.seek(0); return out
sp="research/prefetch/forecasts/spf"; ax="research/prefetch/forecasts/anxious_index"
# 1) repair unlocks ALL 86 spf + 2 anxious?
fails=[]
for d in (sp,ax):
    for f in sorted(os.listdir(d)):
        if not f.endswith('.xlsx'): continue
        b=open(os.path.join(d,f),'rb').read()
        try:
            openpyxl.load_workbook(repair(b),read_only=True,data_only=True).close()
        except Exception as e:
            fails.append((f,repr(e)[:80]))
        # does raw (unrepaired) fail? test a couple
print("REPAIR: files that STILL fail:",fails)
# raw-fails check on 3 files
for f in ['individual_rgdp.xlsx','mean_rgdp_growth.xlsx']:
    b=open(os.path.join(sp,f),'rb').read()
    try:
        openpyxl.load_workbook(io.BytesIO(b),read_only=True,data_only=True).close(); print("RAW OK (no repair needed):",f)
    except Exception as e: print("RAW FAILS (repair needed):",f, repr(e)[:70])
# 2) Anxious truth
b=open(os.path.join(ax,"anxious_index_chart.xlsx"),'rb').read()
wb=openpyxl.load_workbook(repair(b),read_only=True,data_only=True); ws=wb['Data']
rows=[r for r in ws.iter_rows(values_only=True)]
data=[r for r in rows[4:]]  # after header at idx3
vals=[(int(r[0]),int(r[1]),r[2]) for r in data if r[0] is not None]
present=[v for v in vals if v[2] is not None]
print("ANXIOUS total-rows",len(vals),"present",len(present),"first",present[0],"last",present[-1])
wb.close()
# 3) mean_rgdp_growth truth per column
b=open(os.path.join(sp,"mean_rgdp_growth.xlsx"),'rb').read()
wb=openpyxl.load_workbook(repair(b),read_only=True,data_only=True); ws=wb['Mean_Growth']
rows=[r for r in ws.iter_rows(values_only=True)]; hdr=rows[0]; body=rows[1:]
for ci,name in enumerate(hdr):
    if ci<2: continue
    col=[(int(r[0]),int(r[1]),r[ci]) for r in body if r[0] is not None]
    avail=[c for c in col if c[2] not in (None,'#N/A')]
    print("COL",name,"rows",len(col),"avail",len(avail),"first_avail",avail[0] if avail else None,"last_avail",avail[-1] if avail else None)
wb.close()
