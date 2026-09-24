import json, os
P = "/Users/anthonyhall/Desktop/RecessionMonitor 2"
def load(f): return json.load(open(os.path.join(P,f)))

# NBER recession peak months (monthly-datable), 1975->present
NBER = ["1980-01/1980-07","1981-07/1982-11","1990-07/1991-03","2001-03/2001-11","2007-12/2009-06","2020-02/2020-04"]
def rec_covered(start_year, end_year):
    # count NBER recessions whose peak-year falls within [start_year,end_year]
    yrs=[1980,1981,1990,2001,2007,2020]
    return sum(1 for y in yrs if start_year<=y<=end_year)

R={}

# state_econ: per-metric m0 + len (monthly or annual)
d=load("state_econ.json")["states"]
al=d["AL"]
se={}
for m,rec in al.items():
    if isinstance(rec,dict) and "v" in rec:
        se[m]={"m0":rec.get("m0"),"y0":rec.get("y0"),"q0":rec.get("q0"),"n":len(rec["v"])}
    else:
        se[m]={"raw":str(rec)[:40]}
R["state_econ"]={"n_units":len(d),"metrics_AL":se}

# state_metrics: months + states->metric structure
d=load("state_metrics.json")
months=d.get("months")
R["state_metrics"]={"n_months":len(months) if isinstance(months,list) else None,
    "month_first":months[0] if months else None,"month_last":months[-1] if months else None,
    "meta":d.get("meta"),"n_states":len(d["states"])}
st0=list(d["states"].keys())[0]
sv=d["states"][st0]
R["state_metrics"]["state0"]=st0
if isinstance(sv,dict):
    R["state_metrics"]["metric_keys"]=list(sv.keys())
    mk0=list(sv.keys())[0]
    vv=sv[mk0]
    R["state_metrics"]["sample_metric"]=mk0
    R["state_metrics"]["sample_val_type"]=type(vv).__name__
    R["state_metrics"]["sample_val_len"]=len(vv) if isinstance(vv,list) else None

# county_econ: per-field annual coverage. records are per-fips dict of metric->{y0,v}
d=load("county_econ.json")["data"]
fips0="01001"
ce={}
present={}
for f,rec in d.items():
    for m in rec:
        present[m]=present.get(m,0)+1
r0=d[fips0]
for m,v in r0.items():
    if isinstance(v,dict):
        ce[m]={"keys":list(v.keys()),"y0":v.get("y0"),"n":len(v.get("v",[])) if isinstance(v.get("v"),list) else None}
    else:
        ce[m]=str(v)[:30]
R["county_econ"]={"n_units":len(d),"fields_present_count":present,"sample_fields":ce}

# county_hist: years list, annual per fips = list aligned to years; monthly mkeys
d=load("county_hist.json")
R["county_hist"]={"n_units":len(d["annual"]),"years":[d["years"][0],d["years"][-1]],
    "n_years":len(d["years"]),"mkeys":[d["monthly"] and None], }
R["county_hist"]["mkeys_span"]=[d["mkeys"][0],d["mkeys"][-1]] if d.get("mkeys") else None
# annual sample length
a0=d["annual"][list(d["annual"].keys())[0]]
R["county_hist"]["annual_sample_len"]=len(a0) if isinstance(a0,list) else None

# county_industry: years, sectors, data per fips
d=load("county_industry.json")
R["county_industry"]={"n_units":len(d["data"]),"years":[d["years"][0],d["years"][-1]],
    "n_sectors":len(d["sectors"])}
di0=d["data"][list(d["data"].keys())[0]]
sec0=list(di0.keys())[0]
R["county_industry"]["sample_sector_rec"]={sec0: di0[sec0]}

# county_qcew
d=load("county_qcew.json")
R["county_qcew"]={"n_units":len(d["data"]),"qtrs":d["qtrs"]}

# metros
d=load("metros.json")
m0=d["metros"][list(d["metros"].keys())[0]]
R["metros"]={"n_metros":len(d["metros"]),"n_missing":len(d.get("missing",[])),
    "hv_h0":m0.get("h0"),"hv_n":len(m0.get("hv",[])),"pv_p0":m0.get("p0"),"pv_n":len(m0.get("pv",[]))}

# metro_econ
d=load("metro_econ.json")["metros"]
me=d["AL"]
R["metro_econ"]={"n":len(d),"hpi_q0":me["hpi"]["q0"],"hpi_n":len(me["hpi"]["v"]),
    "gdp_y0":me["gdp"]["y0"],"gdp_n":len(me["gdp"]["v"]),"has_cbsa":"cbsa" in me}

# industry_geo
d=load("industry_geo.json")
ig_states=len(d["states"]); ig_metros=len(d["metros"])
st0=d["states"][list(d["states"].keys())[0]]
R["industry_geo"]={"m0":d["m0"],"n_sectors":len(d["sectors"]),
    "n_states":ig_states,"n_metros":ig_metros,
    "sector_sufs":[s["suf"] for s in d["sectors"]]}
# one series length
if isinstance(st0,dict):
    sfx=list(st0.keys())[0]
    R["industry_geo"]["series_sample_len"]=len(st0[sfx]) if isinstance(st0[sfx],list) else None

json.dump(R, open("/Users/anthonyhall/Desktop/RecessionMonitor 2/Recession Monitor V2/research/geo_probe/spans.json","w"),indent=1,default=str)
print("OK")
