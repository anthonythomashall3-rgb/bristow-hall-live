"""Parameter registry + undeclared-constant guard — A2 §56 / rulebook §18.

One registry declares every module-level scientific constant once
(`model_authority/parameters/parameter_registry.v1.json`). The guard scans the
science path and fails the suite on any module-level numeric constant that is
not in the registry — a new magic number is a red build, not a lint warning
(A2 §56.3).

Scope, stated (A2 §56 gate / rulebook §19.4 no silent caps): the guard covers
MODULE-LEVEL named numeric constants — the class the owner's audit is about
(the two recession bars, the four-copy channel weights, the five-copy baseline
exclusions, the frozen OLS vectors). It deliberately does NOT try to classify
every inline function-body literal (array indices, `**0.25`, `> 0.5`
comparisons) — those are ~2000 tokens the AST cannot separate from plumbing
without judgment, so they are out of scope and reported as the coverage gap.

Seeding is mechanical (A2 §56.7): every constant enters as `inherited` unless a
receipt already proves otherwise. Nothing is upgraded to `derived` here —
upgrading needs the measurement, and the measurement is a science batch.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from . import paths

# A declared constant name: ALL-CAPS (digits/underscore allowed). This is what
# separates `BAR`, `REC_BAR`, `B_CMRMT`, `CHANNELS` from the lowercase computed
# intermediates these script-style modules also assign at module scope.
_CONST_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")

REGISTRY_REL = Path("model_authority") / "parameters" / "parameter_registry.v1.json"

# The science path: the modules that compute model output (from the audit map).
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

PROVENANCE_CLASSES = ("derived", "calibrated", "chosen", "inherited", "retired")

# Date-literal registry (B-GUARD-GAP-EXCL). The numeric scanner above treats any
# `dt.date(...)` / round(...) RHS as a "derived expression" and drops it into
# excluded_derived — so EXCL (index_v1.py:116), a list of date tuples that decides
# the whole expansion z-baseline, passed the build undeclared. The fix is NOT to
# make the numeric guard flag every non-numeric module constant: measured, that is
# 192 mostly-computed intermediates (S/T/Z/MU/SD comprehensions) — a false-positive
# storm the owner's STOP clause told us to reject, not ship. Instead the date class
# gets its own registry, enforced here on ANY RHS form (iso text AND date
# constructor), with retirement + transitive tracking.
DATE_REGISTRY_REL = (
    Path("model_authority") / "parameters" / "date_literal_registry.v1.json"
)
_ISO_DATE = re.compile(r"(?<!\d)(?:19|20)\d{2}-\d{2}-\d{2}(?!\d)")


def _rhs_has_number(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, (int, float)) and not isinstance(
            child.value, bool
        ):
            return True
    return False


def _safe(v):
    if isinstance(v, (int, float, str, bool)) or v is None:
        return v
    if isinstance(v, (list, tuple)):
        return [_safe(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _safe(x) for k, x in v.items()}
    return repr(v)


def _literal_value(node: ast.AST):
    """(value, is_pure_literal). is_pure_literal is False for any expression
    (dt.date(...), round(...), name references) — those are derived, not magic
    numbers, and are out of the guard's scope."""
    try:
        val = ast.literal_eval(node)
    except (ValueError, SyntaxError, TypeError):
        return None, False
    return _safe(val), True


def _has_number(value) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, list):
        return any(_has_number(x) for x in value)
    if isinstance(value, dict):
        return any(_has_number(x) for x in value.values())
    return False


def _target_names(target: ast.AST):
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        return [t.id for t in target.elts if isinstance(t, ast.Name)]
    return []


def _pairs(targets, rhs):
    """Yield (name, value_node) pairs, unpacking `A, B = 1, 2` elementwise."""
    if (
        len(targets) == 1
        and isinstance(targets[0], (ast.Tuple, ast.List))
        and isinstance(rhs, (ast.Tuple, ast.List))
        and len(targets[0].elts) == len(rhs.elts)
    ):
        for tgt, val in zip(targets[0].elts, rhs.elts):
            if isinstance(tgt, ast.Name):
                yield tgt.id, val
        return
    names = [n for t in targets for n in _target_names(t)]
    for name in names:
        yield name, rhs  # chained `A = B = <rhs>` shares the same RHS


def scan_science(repo: Path | None = None) -> dict:
    """Parse the science path once (A2 §56.3).

    Returns {"constants": {"relpath::NAME": {...}}, "excluded_derived": [...]}.
    A constant is: module scope, ALL-CAPS name, PURE numeric literal RHS.
    Expressions (`G30 = round(...)`, `START = dt.date(...)`) and lowercase
    computed intermediates are excluded — reported as the coverage gap, never
    silently (rulebook §19.4).
    """
    root = paths.resolve_repo(str(repo) if repo else None)
    constants: dict = {}
    excluded: list = []
    for rel in SCIENCE_FILES:
        path = root / rel
        if not path.is_file():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:  # module scope only
            if isinstance(node, ast.Assign):
                targets, rhs0 = node.targets, node.value
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                targets, rhs0 = [node.target], node.value
            else:
                continue
            for name, valnode in _pairs(targets, rhs0):
                if not _CONST_NAME.match(name):
                    continue  # lowercase computed intermediate — not a constant
                value, is_literal = _literal_value(valnode)
                if not (is_literal and _has_number(value)):
                    if _rhs_has_number(valnode):
                        excluded.append(f"{rel}::{name}")  # derived/expression
                    continue
                constants[f"{rel}::{name}"] = {
                    "module": rel,
                    "name": name,
                    "line": node.lineno,
                    "value": value,
                }
    return {"constants": constants, "excluded_derived": sorted(set(excluded))}


def extract_module_constants(repo: Path | None = None) -> dict:
    """Just the declared numeric constants (A2 §56.3)."""
    return scan_science(repo)["constants"]


def registry_path(repo: Path | None = None) -> Path:
    return paths.resolve_repo(str(repo) if repo else None) / REGISTRY_REL


def load_registry(repo: Path | None = None) -> dict:
    path = registry_path(repo)
    if not path.is_file():
        return {"schema_version": "recession-monitor-v2.parameter-registry.v1", "parameters": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def guard(repo: Path | None = None) -> dict:
    """Compare code constants against the registry (A2 §56.3)."""
    scan = scan_science(repo)
    code = scan["constants"]
    excluded = scan["excluded_derived"]
    registry = load_registry(repo)
    declared = set(registry.get("parameters", {}).keys())
    in_code = set(code.keys())
    unregistered = sorted(in_code - declared)  # new magic numbers -> FAIL
    missing_from_code = sorted(declared - in_code)  # registered but gone -> drift
    # Value drift: a constant changed in code without updating its registry
    # entry (and its provenance). Read-only pin — no science-code edit (A2 §56.2
    # refactor is out of A2 scope; this gives the registry teeth without it).
    reg_params = registry.get("parameters", {})
    value_drift = []
    for key in sorted(in_code & declared):
        if reg_params[key].get("value") != code[key]["value"]:
            value_drift.append(key)
    covered = len(in_code & declared)
    total = len(in_code) if in_code else 1
    # Retirement guard (B-RETIRE-INHERITED / owner ruling EFFN_ONLY): a RETIRED
    # parameter keeps its value+file:line so the old instrument stays
    # reproducible, but loses authority. Existing citations (constants still in
    # code, frozen as the grandfather baseline) are WARNED. Any retired-provenance
    # constant appearing in code beyond that baseline is a NEW citation of a
    # retired stick and FAILS the build — retirement removes authority, not
    # reproducibility, and nothing new may lean on it.
    retired = retired_citation_report(in_code, registry)
    retired_citations = retired["retired_citations"]
    new_retired_citations = retired["new_retired_citations"]
    return {
        "unregistered": unregistered,
        "missing_from_code": missing_from_code,
        "value_drift": value_drift,
        "code_constant_count": len(in_code),
        "declared_count": len(declared),
        "excluded_derived": excluded,
        "excluded_derived_count": len(excluded),
        "coverage_fraction": round(covered / total, 4),
        "duplicates": detect_duplicates(registry),
        "retired_citations": retired_citations,
        "new_retired_citations": new_retired_citations,
    }


def retired_citation_report(in_code_keys, registry: dict) -> dict:
    """Retirement guard (B-RETIRE-INHERITED / owner ruling EFFN_ONLY).

    A RETIRED parameter keeps its value and file:line so the old instrument
    stays reproducible, but loses all authority. ``retired_citation_baseline``
    freezes the set of retired constants allowed to remain in code. Any retired
    constant found in code beyond that baseline is a NEW citation of a retired
    stick — a red build, not a warning. Existing citations are warned only.
    """
    reg_params = registry.get("parameters", {})
    in_code = set(in_code_keys)
    retired_keys = {
        k for k, e in reg_params.items() if e.get("provenance") == "retired"
    }
    baseline = set(registry.get("retired_citation_baseline", []))
    return {
        "retired_citations": sorted(in_code & retired_keys),
        "new_retired_citations": sorted((in_code & retired_keys) - baseline),
    }


def detect_duplicates(registry: dict) -> list:
    """Two entries sharing `controls` without `alias_of` (A2 §56.5)."""
    by_controls: dict = {}
    for key, entry in registry.get("parameters", {}).items():
        controls = (entry.get("controls") or "").strip().lower()
        if not controls:
            continue
        by_controls.setdefault(controls, []).append((key, entry))
    offenders = []
    for controls, entries in by_controls.items():
        if len(entries) < 2:
            continue
        # allowed if every-but-one links to another via alias_of
        keys = {k for k, _ in entries}
        unlinked = [k for k, e in entries if not (e.get("alias_of") in keys)]
        if len(unlinked) > 1:
            offenders.append({"controls": controls, "keys": sorted(keys)})
    return offenders


def date_registry_path(repo: Path | None = None) -> Path:
    return paths.resolve_repo(str(repo) if repo else None) / DATE_REGISTRY_REL


def load_date_registry(repo: Path | None = None) -> dict:
    path = date_registry_path(repo)
    if not path.is_file():
        return {"records": [], "transitive_retirement": []}
    return json.loads(path.read_text(encoding="utf-8"))


def current_date_literals(repo: Path | None = None) -> set:
    """Every date literal on the science path, on ANY RHS form (B-GUARD-GAP-EXCL).

    Returns {(relpath, line, literal_kind, value)}. Mirrors
    build_date_literal_registry: ISO-text matches by regex, ``dt.date(...)``
    constructors by AST walk — the two forms the numeric scanner could not see.
    """
    root = paths.resolve_repo(str(repo) if repo else None)
    keys = set()
    for rel in SCIENCE_FILES:
        path = root / rel
        if not path.is_file():
            continue
        source = path.read_text(encoding="utf-8")
        for lineno, text in enumerate(source.splitlines(), 1):
            for match in _ISO_DATE.finditer(text):
                keys.add((rel, lineno, "iso_text", match.group(0)))
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Attribute) and func.attr == "date"):
                continue
            try:
                y, m, d = [ast.literal_eval(a) for a in node.args[:3]]
            except (ValueError, TypeError, SyntaxError):
                continue
            if all(isinstance(v, int) for v in (y, m, d)):
                keys.add((rel, node.lineno, "date_constructor", f"{y:04d}-{m:02d}-{d:02d}"))
    return keys


def date_literal_guard(repo: Path | None = None, registry_override: dict | None = None) -> dict:
    """Enforce the date-literal registry (B-GUARD-GAP-EXCL).

    A date literal in code but absent from the registry is a NEW or MOVED
    boundary — a red build, not a warning (the gap that let EXCL through). A
    registry row absent from code is drift. Controlling boundaries are retired;
    the transitive closure travels with them.
    """
    doc = registry_override if registry_override is not None else load_date_registry(repo)
    records = doc.get("records", [])
    registered = {
        (r["file"], r["line"], r["literal_kind"], r["value"]) for r in records
    }
    in_code = current_date_literals(repo)
    unregistered = sorted(
        f"{f}::{ln}::{kind}::{val}" for (f, ln, kind, val) in (in_code - registered)
    )
    missing = sorted(
        f"{f}::{ln}::{kind}::{val}" for (f, ln, kind, val) in (registered - in_code)
    )
    retired = [r for r in records if r.get("provenance") == "retired"]
    documentary = [r for r in records if r.get("provenance") == "documentary"]
    return {
        "unregistered": unregistered,
        "missing_from_registry": missing,
        "retired_count": len(retired),
        "documentary_count": len(documentary),
        "literal_kinds": {r["literal_kind"] for r in records},
        "transitive_retirement": doc.get("transitive_retirement", []),
    }


def provenance_counts(registry: dict) -> dict:
    counts = {c: 0 for c in PROVENANCE_CLASSES}
    for entry in registry.get("parameters", {}).values():
        prov = entry.get("provenance")
        if prov in counts:
            counts[prov] += 1
    return counts


def cli(args) -> int:
    registry = load_registry()
    counts = provenance_counts(registry)
    g = guard()
    dg = date_literal_guard()
    if getattr(args, "json", False):
        print(json.dumps(
            {"provenance_counts": counts, "guard": g, "date_literal_guard": dg},
            indent=2,
        ))
        return 0
    print("parameter registry provenance (A2 §56.4):")
    for cls in PROVENANCE_CLASSES:
        print(f"  {cls}: {counts[cls]}")
    print(f"  inherited is a DEFECT count and must trend to zero.")
    print(f"guard: {g['declared_count']} declared / {g['code_constant_count']} in code, "
          f"coverage {g['coverage_fraction']:.2%}")
    if g["unregistered"]:
        print(f"  UNREGISTERED (would fail build): {len(g['unregistered'])}")
        for k in g["unregistered"][:20]:
            print(f"    {k}")
    if g["duplicates"]:
        print(f"  DUPLICATE controls without alias_of: {len(g['duplicates'])}")
    if g.get("retired_citations"):
        print(f"  retired constants still in code (reproducibility, WARNED): "
              f"{len(g['retired_citations'])}")
    if g.get("new_retired_citations"):
        print(f"  NEW citation(s) of a retired parameter (would fail build): "
              f"{len(g['new_retired_citations'])}")
        for k in g["new_retired_citations"][:20]:
            print(f"    {k}")
    print(f"date-literal guard (B-GUARD-GAP-EXCL): "
          f"{dg['retired_count']} retired / {dg['documentary_count']} documentary")
    if dg["unregistered"]:
        print(f"  UNREGISTERED date literal(s) (would fail build): {len(dg['unregistered'])}")
        for k in dg["unregistered"][:20]:
            print(f"    {k}")
    if dg["missing_from_registry"]:
        print(f"  date registry drift (in registry, gone from code): "
              f"{len(dg['missing_from_registry'])}")
    return 0
