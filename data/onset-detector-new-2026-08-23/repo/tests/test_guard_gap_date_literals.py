"""B-GUARD-GAP-EXCL — the numeric guard silently excluded EXCL (a dt.date list)
as a 'derived expression'. The date-literal class must be guarded on ANY RHS
form, retired where it controls model output, and tracked transitively.

RED-before-fix: bh.params exposes no date-literal guard yet, so every reference
below raises AttributeError until the widening lands.
"""

import json
from pathlib import Path

import bh.params as params

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "model_authority/parameters/date_literal_registry.v1.json"


def test_excl_is_now_accounted_for_and_retired():
    # The original defect: EXCL at index_v1.py:116 was invisible to the guard.
    doc = json.loads(REGISTRY.read_text(encoding="utf-8"))
    excl = [
        r for r in doc["records"]
        if r["file"] == "method_source/index_v1.py" and r["line"] == 116
    ]
    assert excl, "EXCL date boundary must be registered"
    assert all(r["provenance"] == "retired" for r in excl)
    assert all(r["controls_model_output"] for r in excl)


def test_date_literal_guard_enforces_registry_on_any_rhs_form():
    g = params.date_literal_guard()
    # Registry matches code exactly: no unregistered/moved literal, no drift.
    assert g["unregistered"] == []
    assert g["missing_from_registry"] == []
    # Both RHS forms are covered: iso_text AND date_constructor.
    assert g["literal_kinds"] == {"date_constructor", "iso_text"}


def test_retired_and_documentary_provenance_counts():
    g = params.date_literal_guard()
    assert g["retired_count"] == 73
    assert g["documentary_count"] == 19


def test_a_new_or_moved_date_literal_would_fail_the_build():
    # Widening proof: drop EXCL from a copy of the registry and the guard must
    # flag it as an unregistered code literal — i.e. a moved/new date fails.
    doc = json.loads(REGISTRY.read_text(encoding="utf-8"))
    doctored = dict(doc)
    doctored["records"] = [
        r for r in doc["records"]
        if not (r["file"] == "method_source/index_v1.py" and r["line"] == 116)
    ]
    g = params.date_literal_guard(registry_override=doctored)
    assert any(
        "method_source/index_v1.py::116" in k for k in g["unregistered"]
    ), "a code date literal absent from the registry must be flagged"


def test_transitive_retirement_is_tracked():
    doc = json.loads(REGISTRY.read_text(encoding="utf-8"))
    tr = {e["key"]: e for e in doc["transitive_retirement"]}
    excl_keys = [k for k in tr if k.startswith("method_source/index_v1.py::116::")]
    assert excl_keys, "EXCL must appear in transitive_retirement tracking"
    dependents = tr[excl_keys[0]]["transitively_retires"]
    assert any("z-score" in d or "MU/SD/Z" in d for d in dependents)
    assert any("channel score" in d for d in dependents)
