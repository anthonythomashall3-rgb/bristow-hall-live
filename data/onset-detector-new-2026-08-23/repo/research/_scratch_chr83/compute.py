import json,csv,os
from datetime import date
def load(sid):
    h=json.load(open(f"live_data/runtime/source_heads/{sid}.json"))
    sha=h["normalized_sha256"]
    return json.load(open(f"live_data/store/normalized/sha256/{sha[:2]}/{sha}.json"))["records"]

def q(period):  # 'YYYY-MM-DD' start-of-quarter -> quarter index (year*4+q0)
    y,m,_=period.split("-"); y=int(y); m=int(m)
    return y*4+(m-1)//3  # q in 0..3
def qlabel(qi):
    y=qi//4; qq=qi%4+1; return f"{y}Q{qq}"

# NBER quarterly recession spans (peak quarter .. trough quarter), inclusive
NBER=[("1969Q4","1969Q4","1970Q4"),("1973Q4","1973Q4","1975Q1"),
      ("1980Q1","1980Q1","1980Q3"),("1981Q3","1981Q3","1982Q4"),
      ("1990Q3","1990Q3","1991Q1"),("2001Q1","2001Q1","2001Q4"),
      ("2007Q4","2007Q4","2009Q2"),("2020Q1","2020Q1","2020Q2")]
def lbl2qi(s):
    y=int(s[:4]); qq=int(s[-1]); return y*4+(qq-1)
EP=[(o,lbl2qi(o),lbl2qi(pk),lbl2qi(tr)) for o,pk,tr in NBER]
recset=set()
for _,o,pk,tr in EP:
    for qi in range(pk,tr+1): recset.add(qi)

# ---- SPF point growth forecast: build (survey_q, horizon)->value ; DRGDP2=h0 ... DRGDP6=h4
def spf_signal(sid):
    recs=load(sid)
    code_h={"DRGDP2":0,"DRGDP3":1,"DRGDP4":2,"DRGDP5":3,"DRGDP6":4}
    fc={}  # (survey_qi,h)->val
    surveys=set()
    for r in recs:
        if r.get("value_status")!="actual": continue
        c=r.get("spf_target_code")
        if c not in code_h: continue
        sq=lbl2qi(qlabel(q(r["observation_period"])))
        try: v=float(r["value"])
        except: continue
        fc[(sq,code_h[c])]=v; surveys.add(sq)
    return fc,sorted(surveys)

def score_pointfc(fc,surveys,name,thr=0.0):
    # target-quarter negative call = fc(survey, target-survey) with horizon = target-survey in 0..4
    # earliest survey giving a <thr forecast for a target quarter within [peak,trough]
    rows=[]
    # false alarms: negative calls for NON-recession target quarters
    neg_targets=set()
    for (sq,h),v in fc.items():
        if v<thr:
            neg_targets.add(sq+h)
    fa=sorted(t for t in neg_targets if t not in recset)
    # cluster consecutive
    clusters=[]; 
    for t in fa:
        if clusters and t-clusters[-1][-1]<=1: clusters[-1].append(t)
        else: clusters.append([t])
    for o,onq,pk,tr in EP:
        best=None  # (lead, survey, target, val)
        for (sq,h),v in fc.items():
            tq=sq+h
            if v<thr and pk<=tq<=tr:
                lead=onq-sq  # quarters survey precedes onset
                if best is None or lead>best[0]:
                    best=(lead,sq,tq,v)
        if best is None:
            verdict="MISS"; detail=""
        else:
            lead,sq,tq,v=best
            if lead>0: verdict=f"LEAD +{lead}"
            elif lead==0: verdict="coincident"
            else: verdict=f"LATE {lead}"
            detail=f"survey {qlabel(sq)} fc {qlabel(tq)}={v:.2f}"
        rows.append((name,o,verdict,detail))
    return rows,clusters,fa

# ---- GDPNow: current-quarter nowcast; signal = nowcast<0
def score_gdpnow():
    recs=load("gdpnow_atlanta_fred_forecast_current_offline")
    vals={}  # qi->val
    for r in recs:
        if r.get("value_status")!="actual": continue
        try: v=float(r["value"])
        except: continue
        vals[lbl2qi(qlabel(q(r["observation_period"])))]=v
    span=(min(vals),max(vals))
    neg=sorted(qi for qi,v in vals.items() if v<0)
    fa=[t for t in neg if t not in recset]
    rows=[]
    for o,onq,pk,tr in EP:
        in_range = span[0]<=pk<=span[1] or span[0]<=tr<=span[1]
        if not in_range:
            rows.append(("gdpnow",o,"NO COVERAGE","")); continue
        hits=[(qi,vals[qi]) for qi in range(pk,tr+1) if qi in vals and vals[qi]<0]
        if hits:
            qi,v=hits[0]; lead=onq-qi
            verd = f"LEAD +{lead}" if lead>0 else ("coincident" if lead==0 else f"LATE {lead}")
            rows.append(("gdpnow",o,verd,f"nowcast {qlabel(qi)}={v:.2f}"))
        else:
            rows.append(("gdpnow",o,"MISS(in-range)",""))
    return rows,vals,fa,span

out=[]
med_fc,med_s=spf_signal("philadelphia_spf_median_rgdp_growth")
mean_fc,mean_s=spf_signal("philadelphia_spf_mean_rgdp_growth")
rmed,cmed,famed=score_pointfc(med_fc,med_s,"spf_median_rgdp")
rmean,cmean,famean=score_pointfc(mean_fc,mean_s,"spf_mean_rgdp")
rgn,gnvals,fagn,gnspan=score_gdpnow()

print("=== SPF MEDIAN rgdp point-forecast (thr<0) ===")
for _,o,v,d in rmed: print(f"  {o}: {v}  {d}")
negcount=sum(1 for (sq,h),val in med_fc.items() if val<0)
print(f"  total negative point-forecasts (any survey×horizon): {negcount}")
print(f"  false-alarm non-recession target quarters: {len(famed)} -> {[qlabel(t) for t in famed]}")
print("=== SPF MEAN rgdp point-forecast (thr<0) ===")
for _,o,v,d in rmean: print(f"  {o}: {v}  {d}")
print(f"  false-alarm non-recession target quarters: {len(famean)} -> {[qlabel(t) for t in famean]}")
print("=== GDPNOW (thr<0) span",qlabel(gnspan[0]),qlabel(gnspan[1]),"===")
for _,o,v,d in rgn: print(f"  {o}: {v}  {d}")
print("  gdpnow negative nowcast quarters:",[qlabel(qi) for qi in sorted(gnvals) if gnvals[qi]<0], "FA:",[qlabel(t) for t in fagn])

# write CSV
os.makedirs("research/forecast_detection",exist_ok=True)
with open("research/forecast_detection/detection_records.v1.csv","w",newline="") as f:
    w=csv.writer(f)
    w.writerow(["source","signal_def","nber_onset_qtr","verdict","lead_or_lag_q","detail","threshold"])
    def emit(rows,sig,thr):
        for _,o,v,d in rows:
            lead=""
            if v.startswith("LEAD"): lead=v.split("+")[1]
            elif v=="coincident": lead="0"
            elif v.startswith("LATE"): lead=v.split()[1]
            w.writerow([_,sig,o,v.split()[0] if " " in v else v,lead,d,thr])
    emit(rmed,"SPF median 1-4Q-ahead real GDP growth fc < 0","0.0")
    emit(rmean,"SPF mean 1-4Q-ahead real GDP growth fc < 0","0.0")
    emit(rgn,"Atlanta GDPNow current-Q nowcast < 0","0.0")
    # anxious row reused from CH-R36 (authoritative)
    anx=[("1969Q4","coincident","0","peak AI 45.9@1970Q2; p75 cross coincident"),
         ("1973Q4","LATE","-1","p75 cross LATE -1; peak 74.1@1975Q1"),
         ("1980Q1","LEAD","2","p75 lead +2; peak 70.1@1980Q1"),
         ("1981Q3","ARTIFACT","","+6 carryover from 1980, not independent"),
         ("1990Q3","LEAD","2","p75 lead +2; peak 70.0@1991Q1"),
         ("2001Q1","LATE","-1","p75 cross LATE -1"),
         ("2007Q4","LATE","-2","p75 cross LATE -2; AI only 17.0 at onset"),
         ("2020Q1","MISS","","never reached p75; peak 18.1 (CH-R36 keyed 2019Q4)")]
    for o,v,l,d in anx:
        w.writerow(["anxious_index","SPF Anxious Index P(decline) own-p75 cross (CH-R36)",o,v,l,d,"own p75=23.9"])
print("\nWROTE research/forecast_detection/detection_records.v1.csv")
