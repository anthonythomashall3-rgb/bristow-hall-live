import json
rows=[r for r in json.load(open('research/measuring_sticks/inline_literals_raw.json')) if 'error' not in r]
def key(r): return (r['file'].split('/')[-1], r['line'], r['value'], r['func'])

# TIER B — structural / unit / plumbing (NOT a parameter). explicit (file,line) or value rules.
STRUCT_LINES = {
 ('forecaster_site.py',254),('forecaster_site.py',135),  # daynum, sha chunk
 ('nowcast_live.py',126),('nowcast_live.py',133),('nowcast_live.py',152), # month/quarter date lag
 ('energy_build.py',126),('features.py',62),('features.py',58 ), # eom/month wrap; day=21 kept? -> keep genuine below
 ('build_realtime_coverage_manifest.py',396),('build_realtime_coverage_manifest.py',115),
 ('build_realtime_coverage_manifest.py',130),('build_realtime_coverage_manifest.py',100),
 ('alfred_replay.py',69),  # http 404
 ('nowcast_live.py',221),  # min-sample <5 days (structural min)
 ('forecaster_site.py',506),  # member-count !=5
 ('backtest.py',257),  # months_between *12
}
UNIT_VALS={365.25,30.44,404.0,404,12,20971520}  # days/yr, days/mo, http, 1<<20
def is_struct(r):
    f=r['file'].split('/')[-1]
    if (f,r['line']) in STRUCT_LINES: return True
    if r['value'] in UNIT_VALS: return True
    if r['cat']=='threshold' and r['value']==12: return True   # month wrap
    if f=='nowcast_live.py' and r['value']==12: return True
    if f=='build_realtime_coverage_manifest.py': return True   # all IO/date plumbing
    if r['src'].strip().startswith('#'): return True
    return False

# TIER C — hardcoded reported metrics (frozen OUTPUTS baked into page; guard-blind, not a control stick)
REPORTED = [r for r in rows if r['file'].endswith('forecaster_site.py') and 445<=r['line']<=473]
REPORTED_KEYS={key(r) for r in REPORTED}

tierB=[r for r in rows if is_struct(r) and key(r) not in REPORTED_KEYS]
tierBkeys={key(r) for r in tierB}
tierC=REPORTED
tierA=[r for r in rows if key(r) not in tierBkeys and key(r) not in REPORTED_KEYS]

# semantic re-entry test: retired MODULE constant reused inline with SAME role.
# retired module consts (name->value) that could plausibly re-enter:
# BAR/REC_BAR=7.5, watch BAR=5.0, H/LEAD_WINDOW=24, CAT_W=3.0, ECHO_DRAIN/DRAIN=1.5,
# FLOOR/DFLOOR/COOL_SIGMA=0.5, RESET=2.0, LEAD_PAD=365, TAIL_PAD=730, Z_CLIP=8.0
# check tierA for value==7.5 or 8.0 (the two clearest single-role bars/clip):
semantic_flags=[r for r in tierA if r['value'] in (7.5,8.0)]

# multi-home inline sticks (same value+role copied across files) -> the real §24.7 defect
from collections import defaultdict
byval=defaultdict(list)
for r in tierA: byval[(r['value'],r['func'])].append(r['file'].split('/')[-1])
multihome={f"{v}::{fn}":sorted(set(fs)) for (v,fn),fs in byval.items() if len(set(fs))>1}

out={
 "tierA_genuine_inline_sticks": sorted(tierA,key=lambda r:(r['file'],r['line'])),
 "tierB_structural_unit_plumbing_count": len(tierB),
 "tierC_hardcoded_reported_metrics": sorted(tierC,key=lambda r:r['line']),
 "counts":{
   "tierA_genuine": len(tierA),
   "tierB_structural": len(tierB),
   "tierC_reported_metrics": len(tierC),
   "raw_total": len(rows),
   "dup_retired_value_coincidence": sum(1 for r in rows if r.get('dup_retired')),
   "semantic_role_reentry_of_retired_bar_or_clip": len(semantic_flags),
 },
 "multihome_inline_sticks": multihome,
}
json.dump(out,open('research/measuring_sticks/curated.json','w'),indent=1)
print("tierA genuine inline sticks (guard-blind, in force):",len(tierA))
print("tierB structural/unit/plumbing:",len(tierB))
print("tierC hardcoded reported metrics:",len(tierC))
print("dup-retired VALUE coincidence:",out['counts']['dup_retired_value_coincidence'])
print("semantic role re-entry (7.5/8.0 bar/clip inline):",len(semantic_flags))
print("multi-home inline sticks:",json.dumps(multihome,indent=1))
