import io,re,zipfile,openpyxl,os,json
def repair(b):
    zin=zipfile.ZipFile(io.BytesIO(b)); items={n:zin.read(n) for n in zin.namelist()}
    cx=items.get('docProps/core.xml')
    if cx: items['docProps/core.xml']=re.sub(rb'T\s?(\d):', rb'T0\1:', cx)
    out=io.BytesIO(); zo=zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED)
    for n,d in items.items(): zo.writestr(n,d)
    zo.close(); out.seek(0); return out
sp="research/prefetch/forecasts/spf"
agg=sorted(f for f in os.listdir(sp) if f.startswith(('mean_','median_')))
rep={}
for f in agg:
    b=open(os.path.join(sp,f),'rb').read()
    wb=openpyxl.load_workbook(repair(b),read_only=True,data_only=True)
    sn=wb.sheetnames
    ws=wb[sn[0]]; it=ws.iter_rows(values_only=True)
    hdr=next(it)
    rep[f]={"sheets":sn,"header":[str(x) for x in hdr]}
    wb.close()
json.dump(rep,open("research/bland8_aggsurvey.json","w"),indent=0)
# summarize: unique sheet-name set, header patterns
sheets=set(tuple(v["sheets"]) for v in rep.values())
print("distinct sheet tuples:")
for s in sorted(sheets): print("  ",s)
print("n agg files",len(agg))
# column-name first-token check: YEAR,QUARTER then value cols
for f in list(rep)[:4]+list(rep)[-4:]:
    print(f, rep[f]["sheets"], rep[f]["header"])
