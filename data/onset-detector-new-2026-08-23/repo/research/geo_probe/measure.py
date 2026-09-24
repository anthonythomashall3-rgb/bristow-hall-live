import json, os

P = "/Users/anthonyhall/Desktop/RecessionMonitor 2"
FILES = ["state_econ.json","state_metrics.json","county_econ.json","county_hist.json",
         "county_industry.json","county_qcew.json","metros.json","metro_econ.json","industry_geo.json"]

def load(f): return json.load(open(os.path.join(P,f)))

def note(d):
    return d.get("note","") if isinstance(d,dict) else ""

out = {}
for f in FILES:
    d = load(f)
    out[f] = {"note": note(d), "top_keys": list(d.keys()) if isinstance(d,dict) else None}

# --- state_econ: states -> AL -> ? ---
d = load("state_econ.json")
al = d["states"]["AL"]
out["state_econ.json"]["sample_AL_type"] = type(al).__name__
out["state_econ.json"]["sample_AL"] = al if not isinstance(al,(dict,list)) else (list(al.keys()) if isinstance(al,dict) else al[:3])
out["state_econ.json"]["n_states"] = len(d["states"])
if isinstance(al,dict):
    k0=list(al.keys())[0]
    out["state_econ.json"]["AL_"+k0] = al[k0]

# --- state_metrics ---
d = load("state_metrics.json")
print("STATE_METRICS top:", list(d.keys()))
sk = [k for k in d.keys()]
out["state_metrics.json"]["top_keys"]=sk
for k in sk[:2]:
    v=d[k]
    if isinstance(v,dict):
        kk=list(v.keys())
        out["state_metrics.json"][k+"_keys"]=kk[:8]
        # drill one
        v2=v[kk[0]]
        out["state_metrics.json"][k+"_"+str(kk[0])+"_type"]=type(v2).__name__
        if isinstance(v2,dict):
            out["state_metrics.json"][k+"_"+str(kk[0])+"_subkeys"]=list(v2.keys())[:12]

# --- county_econ ---
d = load("county_econ.json")
ck=list(d.keys())
out["county_econ.json"]["top_keys"]=ck
# find the data dict
for k in ck:
    if isinstance(d[k],dict) and len(d[k])>100:
        fips=list(d[k].keys())[0]
        rec=d[k][fips]
        out["county_econ.json"]["data_key"]=k
        out["county_econ.json"]["n_units"]=len(d[k])
        out["county_econ.json"]["sample_fips"]=fips
        out["county_econ.json"]["sample_rec_type"]=type(rec).__name__
        out["county_econ.json"]["sample_rec"]=(list(rec.keys()) if isinstance(rec,dict) else rec)
        break

# --- county_hist ---
d = load("county_hist.json")
ck=list(d.keys())
out["county_hist.json"]["top_keys"]=ck
for k in ck:
    if isinstance(d[k],dict) and len(d[k])>100:
        fips=list(d[k].keys())[0]
        rec=d[k][fips]
        out["county_hist.json"]["data_key"]=k
        out["county_hist.json"]["n_units"]=len(d[k])
        out["county_hist.json"]["sample_fips"]=fips
        out["county_hist.json"]["sample_rec"]=(list(rec.keys())[:10] if isinstance(rec,dict) else (rec[:5] if isinstance(rec,list) else rec))
        break
for k in ck:
    if isinstance(d[k],list) and len(d[k])<50:
        out["county_hist.json"]["listkey_"+k]=d[k][:12]

# --- county_industry ---
d = load("county_industry.json")
ck=list(d.keys())
out["county_industry.json"]["top_keys"]=ck
for k in ck:
    if isinstance(d[k],dict) and len(d[k])>100:
        fips=list(d[k].keys())[0]
        rec=d[k][fips]
        out["county_industry.json"]["data_key"]=k
        out["county_industry.json"]["n_units"]=len(d[k])
        out["county_industry.json"]["sample_fips"]=fips
        out["county_industry.json"]["sample_rec"]=(list(rec.keys())[:12] if isinstance(rec,dict) else rec)
        break
for k in ck:
    if isinstance(d[k],list) and len(d[k])<80:
        out["county_industry.json"]["listkey_"+k]=d[k][:15]

# --- county_qcew ---
d = load("county_qcew.json")
out["county_qcew.json"]["qtrs"]=d["qtrs"]
fips=list(d["data"].keys())[0]
rec=d["data"][fips]
out["county_qcew.json"]["n_units"]=len(d["data"])
out["county_qcew.json"]["sample_fips"]=fips
out["county_qcew.json"]["sample_rec_type"]=type(rec).__name__
out["county_qcew.json"]["sample_rec"]=(list(rec.keys())[:12] if isinstance(rec,dict) else rec)
if isinstance(rec,dict):
    kk=list(rec.keys())[0]; out["county_qcew.json"]["rec_"+str(kk)]=rec[kk]

# --- metros ---
d = load("metros.json")
mid=list(d["metros"].keys())[0]
out["metros.json"]["n_metros"]=len(d["metros"])
out["metros.json"]["sample_cbsa"]=mid
out["metros.json"]["sample_metro"]=d["metros"][mid]

# --- metro_econ ---
d = load("metro_econ.json")
mk=list(d["metros"].keys())[0]
out["metro_econ.json"]["n"]=len(d["metros"])
out["metro_econ.json"]["sample_key"]=mk
out["metro_econ.json"]["sample"]=d["metros"][mk]

# --- industry_geo ---
d = load("industry_geo.json")
out["industry_geo.json"]["m0"]=d.get("m0")
out["industry_geo.json"]["n_sectors"]=len(d["sectors"])
out["industry_geo.json"]["sector0"]=d["sectors"][0]
st=list(d["states"].keys())[0]
out["industry_geo.json"]["state_sample_key"]=st
out["industry_geo.json"]["state_sample"]=d["states"][st] if not isinstance(d["states"][st],(list,dict)) else (list(d["states"][st].keys())[:8] if isinstance(d["states"][st],dict) else d["states"][st][:8])

json.dump(out, open("/Users/anthonyhall/Desktop/RecessionMonitor 2/Recession Monitor V2/research/geo_probe/raw_measure.json","w"), indent=1, default=str)
print("WROTE raw_measure.json")
