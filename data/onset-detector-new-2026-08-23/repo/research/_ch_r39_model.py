import json,re
out=json.load(open("research/_ch_r39_vars.json"))
lbl=json.load(open("research/_ch_r39_labels.json"))
# calibration from B-LAND-4-R2: RUC 217 landable vints -> +180MB ; deep window MAX 2019-11
MB_PER_VINT=180.0/217.0   # 0.829
CAP=1139
NBER_PEAKS=[(1948,11),(1953,7),(1957,8),(1960,4),(1969,12),(1973,11),
            (1980,1),(1981,7),(1990,7),(2001,3),(2007,12),(2020,2)]
def decode(code,var):
    m=re.match(r'^[A-Za-z0-9]+?(\d{2})(Q|M)(\d{1,2})$',code) if code else None
    if not m: return None
    yy=int(m.group(1)); yr=2000+yy if yy<40 else 1900+yy
    per=int(m.group(3)); f=m.group(2)
    return (yr,per,f)
def to_month(yr,per,f):
    return yr*12+(per*3-2 if f=='Q' else per)-1  # rough month index; Q->first month of quarter
MAXY,MAXM=2019,11
maxidx=MAXY*12+MAXM-1
def span_count(first,last,f):
    fi=to_month(*first); li=to_month(*last)
    step=3 if f=='Q' else 1
    return max(0,(li-fi)//step+1)
MEMBER=set("ruc employ ipt ipm cut cum hstarts cpi m1 m2".split())
rows=[]
for o in out:
    fv=decode(o["first_vintage"],o["var"]); lv=decode(o["last_vintage"],o["var"])
    if not fv or not lv:
        o.update(dict(skip="undecodable vintage code")); rows.append(o); continue
    f=fv[2]
    total=span_count(fv,lv,f)
    landmax=(MAXY,4,f) if f=='Q' else (MAXY,11,f)
    land=min(span_count(fv,landmax,f), total) if to_month(*fv)<=maxidx else 0
    land=min(land,CAP)
    tail=total-min(land,total)  # 2020+ not deep-landable
    fy=fv[0]
    # pre-2000 recessions covered: peak year >= first vintage year, peak <2000
    covered=[p for p in NBER_PEAKS if p[0]<2000 and (p[0]>fy or (p[0]==fy))]
    # more precisely peak month index >= first vintage index
    fvi=to_month(*fv)
    covered=[p for p in NBER_PEAKS if p[0]<2000 and (p[0]*12+p[1]-1)>=fvi]
    all_cov=[p for p in NBER_PEAKS if (p[0]*12+p[1]-1)>=fvi]
    cost_mb=round(land*MB_PER_VINT,1)
    rows.append(dict(var=o["var"],label=lbl.get(o["var"],o["label"]),freq=f,
        first_vintage=o["first_vintage"],first_v_year=fy,
        cache_vints=o["vintages"],landable_vints=land,tail_2020plus=tail,
        cache_records=o["records"],obs_first=o["obs_first"],obs_last=o["obs_last"],
        bytes_all=o["bytes_all"],cost_store_mb=cost_mb,
        pre2000_recessions=len(covered),total_recessions_cov=len(all_cov),
        member_mapped=o["var"] in MEMBER))
json.dump(rows,open("research/_ch_r39_model.json","w"),indent=0)
dec=[r for r in rows if "skip" not in r]
print("decoded:",len(dec),"skipped:",len(rows)-len(dec))
print("RUC check:",[r for r in dec if r['var']=='ruc'][0]['landable_vints'],"(expect 217)")
tot=sum(r['cost_store_mb'] for r in dec)
mm=[r for r in dec if r['member_mapped'] and r['var']!='ruc']
print("full corpus landable store GB:",round(tot/1024,2))
print("9 remaining member-mapped store MB:",round(sum(r['cost_store_mb'] for r in mm),0),"vints:",sum(r['landable_vints'] for r in mm))
print("skipped vars:",[r['var'] for r in rows if 'skip' in r])
