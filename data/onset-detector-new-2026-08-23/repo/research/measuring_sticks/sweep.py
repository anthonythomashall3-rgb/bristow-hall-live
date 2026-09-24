import ast, json, os, glob

RETIRED = {5.0,8.0,11.0,14.0,3.0,1.5,0.5,15.0,2.38,7.5,365.0,2.0,730.0,0.02,24.0,
           8.0,5.0,90.0,45.0,180.0,1.0,0.3,0.25,0.2,0.1,0.15}
SCIENCE = [
 "method_source/index_v1.py","method_source/forecaster_site.py","method_source/nowcast_live.py",
 "method_source/alfred_replay.py","method_source/energy_build.py","method_source/watch_build.py",
 "method_source/census_build.py","method_source/forecaster/features.py",
 "method_source/forecaster/models.py","method_source/forecaster/backtest.py",
 "model_authority/temporal/build_realtime_coverage_manifest.py",
]

def enclosing(tree):
    # map node -> nearest enclosing FunctionDef name, and set of module-level const names
    parent={}
    for p in ast.walk(tree):
        for c in ast.iter_child_nodes(p):
            parent[c]=p
    modconsts=set()
    for n in tree.body:
        if isinstance(n,ast.Assign):
            for t in n.targets:
                if isinstance(t,ast.Name) and t.id.isupper():
                    modconsts.add(t.id)
    def infunc(node):
        cur=node
        while cur in parent:
            cur=parent[cur]
            if isinstance(cur,(ast.FunctionDef,ast.AsyncFunctionDef)):
                return cur.name
        return None
    return parent,infunc,modconsts

SKIP_VALS={0,1,-1,0.0,1.0,2,100,1000,60,1e-9,1e-8,1e-6,1e-12}  # identity/pct/ms/eps/unit
def classify(node,parent,src_lines):
    p=parent.get(node)
    # subscript index -> plumbing
    gp=parent.get(p) if p else None
    if isinstance(p,ast.Index): return "index"
    if isinstance(p,ast.Subscript): return "index"
    if isinstance(p,ast.Slice): return "slice"
    if isinstance(p,(ast.UnaryOp,)):
        p=parent.get(p) or p
    if isinstance(p,ast.Compare): return "threshold"
    if isinstance(p,ast.BinOp):
        if isinstance(p.op,(ast.Mult,ast.Div)): return "weight_scale"
        if isinstance(p.op,ast.Pow): return "power_norm"
        if isinstance(p.op,(ast.Add,ast.Sub)): return "offset"
        if isinstance(p.op,ast.Mod): return "modulo"
    if isinstance(p,ast.Call):
        fn=p.func
        nm=""
        if isinstance(fn,ast.Attribute): nm=fn.attr
        elif isinstance(fn,ast.Name): nm=fn.id
        low=nm.lower()
        if low in ("clip","clamp","minimum","maximum"): return "clip"
        if low in ("min","max"): return "clip"
        if low in ("round",): return "round"
        if low in ("rolling","ewm","shift","resample","window"): return "window_smooth"
        if "clip" in low: return "clip"
        return "call_arg:"+low
    if isinstance(p,ast.keyword):
        k=(p.arg or "").lower()
        if k in ("window","span","halflife","alpha","min_periods","periods","days","com"): return "window_smooth"
        if k in ("axis","ddof","n"): return "plumbing_kw"
        return "kwarg:"+k
    return "other"

rows=[]
for rel in SCIENCE:
    if not os.path.exists(rel): 
        rows.append({"file":rel,"error":"MISSING"}); continue
    src=open(rel).read(); lines=src.splitlines()
    tree=ast.parse(src)
    parent,infunc,modconsts=enclosing(tree)
    for node in ast.walk(tree):
        if isinstance(node,ast.Constant) and isinstance(node.value,(int,float)) and not isinstance(node.value,bool):
            fn=infunc(node)
            if fn is None: continue   # module-level -> guard-covered, skip
            v=node.value
            if v in SKIP_VALS: continue
            cat=classify(node,parent,lines)
            if cat in ("index","slice","plumbing_kw","modulo","round"): continue
            ln=node.lineno
            rows.append({"file":rel,"line":ln,"func":fn,"value":v,"cat":cat,
                         "dup_retired": float(v) in RETIRED,
                         "src":lines[ln-1].strip()[:120]})

os.makedirs("research/measuring_sticks",exist_ok=True)
json.dump(rows,open("research/measuring_sticks/inline_literals_raw.json","w"),indent=1)
# summary
from collections import Counter
real=[r for r in rows if "error" not in r]
print("total inline candidate literals:",len(real))
print("by cat:",dict(Counter(r["cat"] for r in real)))
print("dup_retired count:",sum(1 for r in real if r.get("dup_retired")))
print("by file:",dict(Counter(r["file"] for r in real)))
