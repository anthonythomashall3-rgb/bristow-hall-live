import ast, re, os, json
ROOT="method_source"
MODULES=["alfred_replay.py","census_build.py","energy_build.py","forecaster_site.py",
"index_v1.py","nowcast_harness.py","nowcast_live.py","production_sources.py",
"recpage_build.py","watch_build.py"]
# add research_artifacts py
ra=[os.path.join("research_artifacts",f) for f in os.listdir(os.path.join(ROOT,"research_artifacts")) if f.endswith(".py")]
files=MODULES+ra

# FRED-style series id: uppercase alnum, 3-20 chars, has a letter. Also known lowercase dataset names via URL.
SID=re.compile(r'^[A-Z][A-Z0-9]{2,19}$')
URL=re.compile(r'https?://[^\s"\'<>)]+')
# heuristics for dataset/path tokens
def toks_from_str(s):
    out=set()
    for u in URL.findall(s): out.add(("url",u))
    # split on non-idchars to find embedded ids
    for part in re.split(r'[^A-Za-z0-9_./-]+', s):
        if not part: continue
        if SID.match(part): out.add(("sid",part))
        if "/" in part and ("." in part or part.startswith("data") or "vault" in part): out.add(("path",part))
    return out

results={}
allstr={}
for rel in files:
    p=os.path.join(ROOT,rel)
    if not os.path.exists(p): continue
    src=open(p,encoding="utf-8",errors="replace").read()
    found=set()
    try:
        tree=ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value,str):
                found|=toks_from_str(node.value)
            # f-strings: JoinedStr -> constant parts only (dynamic parts flagged separately)
            if isinstance(node, ast.JoinedStr):
                for v in node.values:
                    if isinstance(v, ast.Constant) and isinstance(v.value,str):
                        found|=toks_from_str(v.value)
    except SyntaxError:
        for m in re.findall(r'["\']([^"\']+)["\']', src):
            found|=toks_from_str(m)
    results[rel]=sorted(found)

# aggregate
sids=set(); urls=set(); paths=set()
for rel,items in results.items():
    for k,v in items:
        if k=="sid": sids.add(v)
        elif k=="url": urls.add(v)
        elif k=="path": paths.add(v)
json.dump({"per_module":{k:[list(x) for x in v] for k,v in results.items()},
           "series_ids":sorted(sids),"urls":sorted(urls),"paths":sorted(paths)},
          open("research/oldsrc_census/raw_harvest.json","w"),indent=1)
print("modules_scanned",len([f for f in files if os.path.exists(os.path.join(ROOT,f))]))
print("candidate_series_ids",len(sids))
print("urls",len(urls))
print("paths",len(paths))
