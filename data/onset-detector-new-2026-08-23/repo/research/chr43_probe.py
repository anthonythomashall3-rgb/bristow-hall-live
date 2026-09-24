import sys,re,json,time
sys.path.insert(0,"live_data")
from pathlib import Path
from rmv2_live.config import load_config, load_env_file
from rmv2_live.store import LiveStore
PR=Path(".").resolve()
cfgp=PR/"live_data/config/sources.v1.json"
load_env_file(cfgp.parent/"local.env"); cfg=load_config(cfgp)
st=LiveStore(PR,cfg); st.initialize()
heads=st.all_source_heads()
VINT=re.compile(r"vintage|deep|asof|archive|_alfred|snapshot",re.I)
kept=[sid for sid in heads if not VINT.search(sid)]
out=open("research/chr43_probe.txt","w")
def p(*a): print(*a,file=out)
p("total heads",len(heads),"non-vintage",len(kept))
# recession indicator?
rec=[sid for sid in heads if re.search(r"USREC|recession|NBER",sid,re.I)]
p("recession-like heads:",rec[:20])
# member sources present?
MEMBER_SRC=["ICSA","IURSA","SAHMREALTIME","UNRATE","INDPRO","CMRMTSPL","TCU","GACDFSA066MSFRBPHI","NASDAQCOM","BAA10Y","VIXCLS","NFCI","PERMIT","HOUST","UMCSENT","W875RX1","PAYEMS"]
present=[m for m in MEMBER_SRC if m in heads]
p("members present:",len(present),present)
p("members missing:",[m for m in MEMBER_SRC if m not in heads])
out.close()
