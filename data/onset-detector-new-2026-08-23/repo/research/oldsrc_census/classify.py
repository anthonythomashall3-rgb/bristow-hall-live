import json,csv,re
raw=json.load(open("research/oldsrc_census/raw_harvest.json"))
cands=set(raw["series_ids"])

# --- reference sets ---
cat_sid={}; prov_sid={}
with open("data_vault/catalog/metric_catalog.csv") as f:
    for r in csv.DictReader(f):
        cat_sid[r["series_id"]]=r
        if r.get("provider_series_id"): prov_sid[r["provider_series_id"]]=r

reg_ids=set()
with open("data_vault/catalog/external_source_registry.csv") as f:
    for r in csv.DictReader(f):
        for k in ("source_id","family"): 
            if r.get(k): reg_ids.add(r[k])

# live source_matrix rows: collect any series-ish tokens + enabled flag
sm=json.load(open("live_data/catalog/source_matrix.v1.json"))
sm_rows = sm.get("rows") or sm.get("matrix") or []
sm_ids={}
if isinstance(sm_rows,list):
    for row in sm_rows:
        if not isinstance(row,dict): continue
        sid=row.get("series_id") or row.get("metric") or row.get("provider_series_id")
        en=row.get("enabled")
        if sid: sm_ids[sid]=en

# common code words to drop as false positives (not external series)
CODEWORDS=set("""TRUE FALSE NONE NULL JSON HTML HTTP HTTPS CSV XML API URL UTC GET POST
ID IDS KEY KEYS VAL SHA SHA256 MD5 UTF ASCII NAN INF OK ERROR WARN INFO DEBUG
NBER FRED ALFRED BLS BEA DOL CENSUS OECD USD GDP CPI PDF PNG SVG JS CSS EOF TODO
FIXME XXX ISO RGBA RGB DIV SPAN BODY HEAD META NA SA NSA YOY QOQ MOM SAAR
LEFT RIGHT TOP BOTTOM MODE READ WRITE PATH ROOT MAIN SELF INIT ARGS KWARGS
MEAN STD MIN MAX SUM ABS LOG EXP AND OR NOT XOR ADD SUB MUL DIV""".split())

def lanes_of(r):
    try: L=json.loads(r.get("local_lanes_json") or "[]")
    except Exception: L=[]
    if isinstance(L,dict): L=list(L.keys())
    return [str(x) for x in L]

def datatime(r):
    rev = (r.get("named_vintage_local_status","") ,)
    lanes=lanes_of(r)
    ljoin=" ".join(lanes).lower()
    has_revised = r.get("local_current_file_count","0") not in ("","0") or "current" in ljoin or "revised" in ljoin
    has_asof = r.get("local_vintage_file_count","0") not in ("","0") or "asof" in ljoin or "vintage" in ljoin or r.get("named_vintage_local_status","")=="present"
    tags=[]
    if has_revised: tags.append("current_revised")
    if has_asof: tags.append("archive_snapshot_asof")
    return ",".join(tags) if tags else "unknown"

landed=[]; reg_not_enabled=[]; absent=[]; dropped=[]
for c in sorted(cands):
    if c in CODEWORDS: dropped.append(c); continue
    r = cat_sid.get(c) or prov_sid.get(c)
    if r:
        landed.append({"id":c,"catalog_series_id":r["series_id"],"data_time":datatime(r),
                       "rights":r.get("rights_status",""),"asof":r.get("named_vintage_local_status","")})
    elif c in reg_ids or c in sm_ids:
        reg_not_enabled.append({"id":c,"enabled":sm_ids.get(c)})
    else:
        absent.append(c)

out={"counts":{"candidates":len(cands),"dropped_codewords":len(dropped),
      "LANDED":len(landed),"REGISTERED_NOT_ENABLED":len(reg_not_enabled),"ABSENT":len(absent)},
     "LANDED":landed,"REGISTERED_NOT_ENABLED":reg_not_enabled,"ABSENT":sorted(absent),"dropped":sorted(dropped)}
json.dump(out,open("research/oldsrc_census/classified.json","w"),indent=1)
print(json.dumps(out["counts"],indent=1))
print("ABSENT sample:",sorted(absent)[:60])
