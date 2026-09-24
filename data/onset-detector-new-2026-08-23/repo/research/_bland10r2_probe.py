import sys, json
sys.path.insert(0,"live_data")
from rmv2_live import rtdsm_xlsx as rx
out={}
for var,f in [("CPI","research/prefetch/rtdsm/cpi/cpiQvMd.xlsx"),
              ("M1","research/prefetch/rtdsm/m1/m1QvMd.xlsx"),
              ("M2","research/prefetch/rtdsm/m2/m2QvMd.xlsx")]:
    b=open(f,"rb").read()
    ws,wb=rx.load_worksheet(b)
    rows=ws.iter_rows(values_only=True)
    header=[None if c is None else str(c).strip() for c in next(rows)]
    hdr_nonempty=[h for h in header if h]
    wb.close()
    # try parse with var
    try:
        cells,sha,meta=rx.parse_matrix(b,var)
        out[var]={"ok":True,"header0":header[0],"first3cols":hdr_nonempty[1:4],
                  "lastcol":hdr_nonempty[-1],"n_header":len(hdr_nonempty),
                  "meta":meta,"sha":sha}
    except Exception as e:
        out[var]={"ok":False,"header0":header[0],"first3cols":hdr_nonempty[1:4],
                  "lastcol":hdr_nonempty[-1],"n_header":len(hdr_nonempty),"err":str(e)}
json.dump(out,open("research/_bland10r2_probe.json","w"),indent=1)
print(json.dumps(out,indent=1)[:1600])
