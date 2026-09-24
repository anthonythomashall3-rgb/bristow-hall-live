# Build FIRST-PRINT and CURRENT-VINTAGE industry panels from the BLS CES vintage files.
# Rows = vintages (year, month published). Columns = observation months.
# First print of obs month M = the value in the EARLIEST vintage that reports M.
import csv, os, json
D='ces_vint'
def colmonth(c):
    try:
        mon,yy=c.split('_'); yy=int(yy)
        y=1900+yy if yy>=39 else 2000+yy
        m=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'].index(mon)+1
        return y*12+m-1
    except: return None
FP={}; CV={}
files=sorted(f for f in os.listdir(D) if f.endswith('_SA.csv'))
for fn in files:
    code=fn.split('_')[1]
    if code in ('000000','050000','060000','070000','080000'): continue   # aggregates
    path=os.path.join(D,fn)
    with open(path) as fh:
        rd=csv.reader(fh); hdr=next(rd)
        cm=[colmonth(c) for c in hdr]
        idx=[(i,m) for i,m in enumerate(cm) if m is not None and m>=2000*12]
        first={}; last={}
        for row in rd:
            if len(row)<3: continue
            try: vy,vm=int(row[0]),int(row[1])
            except: continue
            vt=vy*12+vm-1
            for i,m in idx:
                if i>=len(row): continue
                v=row[i].strip()
                if v in ('','.','-'): continue
                try: x=float(v)
                except: continue
                if m>vt: continue                 # not yet observable at that vintage
                if m not in first: first[m]=x     # rows are in vintage order -> earliest wins
                last[m]=x
    if len(first)>150: FP[code]=first; CV[code]=last
print(json.dumps({'industries':len(FP),
  'span':[min(min(v) for v in FP.values()), max(max(v) for v in FP.values())]}))
json.dump({'fp':{k:{str(m):v for m,v in s.items()} for k,s in FP.items()},
           'cv':{k:{str(m):v for m,v in s.items()} for k,s in CV.items()}},
          open('ces_inhand_panel.json','w'))
print("wrote ces_inhand_panel.json")
