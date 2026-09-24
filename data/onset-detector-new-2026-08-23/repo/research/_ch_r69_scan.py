"""CH-R69 inline-parameter census scanner (read-only).

Walks the science path (bh/params.py::SCIENCE_FILES). For every numeric literal
INSIDE a function/method body (module-level constants are already the registry's
job), record: file, line, enclosing function, value, the source line text, and a
mechanical parent-context tag used by the exclusion rule. Writes raw rows to
research/_ch_r69_raw.json. No classification here — that is done in review.
"""
import ast, json, io, tokenize
from pathlib import Path

ROOT = Path(".").resolve()
SCIENCE_FILES = (
    "method_source/index_v1.py",
    "method_source/forecaster_site.py",
    "method_source/nowcast_live.py",
    "method_source/alfred_replay.py",
    "method_source/energy_build.py",
    "method_source/watch_build.py",
    "method_source/census_build.py",
    "method_source/forecaster/features.py",
    "method_source/forecaster/models.py",
    "method_source/forecaster/backtest.py",
    "model_authority/temporal/build_realtime_coverage_manifest.py",
)

def is_num(node):
    return (isinstance(node, ast.Constant)
            and isinstance(node.value, (int, float))
            and not isinstance(node.value, bool))

rows = []
for rel in SCIENCE_FILES:
    p = ROOT / rel
    if not p.exists():
        rows.append({"file": rel, "error": "MISSING"})
        continue
    src = p.read_text()
    lines = src.splitlines()
    tree = ast.parse(src)

    # map each node to parent + enclosing function
    parents = {}
    func_stack_map = {}
    def visit(node, func, parent):
        for child in ast.iter_child_nodes(node):
            parents[child] = parent
            newfunc = func
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                newfunc = child.name
            func_stack_map[child] = func  # enclosing func of THIS node
            visit(child, newfunc, node)
    func_stack_map[tree] = None
    visit(tree, None, None)

    for node in ast.walk(tree):
        if not is_num(node):
            continue
        func = func_stack_map.get(node)
        if func is None:
            continue  # module-level -> registry's domain, skip
        parent = parents.get(node)
        # mechanical context tag
        ptag = type(parent).__name__ if parent is not None else "?"
        # is this literal a subscript index?  arr[0], x[-1]
        is_index = isinstance(parent, ast.Subscript) or (
            isinstance(parent, ast.Slice))
        # unary minus wrapper
        if isinstance(parent, ast.UnaryOp) and isinstance(parent.op, ast.USub):
            ptag = "USub->" + type(parents.get(parent)).__name__
        ln = node.lineno
        rows.append({
            "file": rel,
            "line": ln,
            "func": func,
            "value": node.value,
            "parent": ptag,
            "is_index": bool(is_index),
            "src": lines[ln-1].strip()[:160] if 0 < ln <= len(lines) else "",
        })

Path("research/_ch_r69_raw.json").write_text(json.dumps(rows, indent=0))
# summary counts
from collections import Counter
byfile = Counter(r["file"] for r in rows if "value" in r)
print("total inline numeric literals:", sum(byfile.values()))
for f, c in byfile.items():
    print(f"{c:4d}  {f}")
print("missing:", [r["file"] for r in rows if r.get("error")])
