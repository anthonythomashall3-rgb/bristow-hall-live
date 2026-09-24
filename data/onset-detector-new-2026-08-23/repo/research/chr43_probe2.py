import sys,re,json,time
sys.path.insert(0,"live_data")
from pathlib import Path
from collections import defaultdict,Counter
from rmv2_live.config import load_config, load_env_file
from rmv2_live.store import LiveStore
PR=Path(".").resolve()
cfgp=PR/"live_data/config/sources.v1.json"
load_env_file(cfgp.parent/"local.env"); cfg=load_config(cfgp)
st=LiveStore(PR,cfg); st.initialize()
heads=st.all_source_heads()
VINT=re.compile(r"vintage|deep|asof|archive|_alfred|snapshot",re.I)
kept=[sid for sid in heads if not VINT.search(sid)]
out=open("research/chr43_probe2.txt","w")
def p(*a): print(*a,file=out,flush=True)
sids_seen=set(); modes=Counter(); member_hit={}
MEMB=set(["ICSA","IURSA","SAHMREALTIME","UNRATE","UNRATEv","INDPRO","CMRMTSPL","TCU","GACDFSA066MSFRBPHI","NASDAQCOM","BAA10Y","VIXCLS","NFCI","PERMIT","HOUST","UMCSENT","W875RX1","PAYEMS"])
recids=set()
t0=time.time()
for i,sid in enumerate(kept):
    try: norm=st.read_normalized(heads[sid]["normalized_sha256"])
    except Exception as e: continue
    for r in norm.get("records",[]):
        si=r.get("series_id"); m=r.get("information_set_mode")
        if si: sids_seen.add(si)
        if m: modes[m]+=1
        if si and re.search(r"USREC|recession|NBER|RECPROUSM",si,re.I): recids.add(si)
        if si in MEMB: member_hit.setdefault(si,sid)
p("elapsed",round(time.time()-t0),"distinct series_id",len(sids_seen))
p("modes",dict(modes))
p("member series_id -> source head:",json.dumps(member_hit,indent=0))
p("recession series_ids:",sorted(recids))
p("sample series_ids:",sorted(list(sids_seen))[:60])
out.close()
