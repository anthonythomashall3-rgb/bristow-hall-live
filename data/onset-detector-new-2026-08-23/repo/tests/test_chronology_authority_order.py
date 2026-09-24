"""B-CHRONOLOGY-RECONCILE — sentinel: >1 recession chronology is reachable from the
science path with NO declared authority order.

The instrument holds THREE recession chronologies (measured, director AST sweep 2026-08-09;
full evidence research/chronology_reconcile/three_way_table.v1.json):

  1. USRECD           — NBER daily indicator; defines the z-standardisation baseline
                        (method_source/index_v1.py:114 in_recession / :118 is_baseline).
  2. RECS             — 7 hand-typed episodes (method_source/index_v1.py:207); drives the
                        published sigma-above-expansion output.
  3. ledger onset_T_star — 13 frozen episodes
                        (model_authority/target_ledger/instrument_onset_target_ledger.v1.json);
                        the grading target, explicitly NOT the NBER peak.

Standardised against one, graded against another, reported against a third, and NOTHING
declares which governs. This test asserts the HEALTHY state (one governing chronology declared,
or an explicit authority order). It is RED today by design:

  * Making it green means DECLARING the governing chronology — that is deriving an instrument
    parameter, forbidden by rulebook §22.4 while the universe is open (DR-CHRON-1 is a Phase-3
    item; see research/chronology_reconcile/DERIVATION_REQUIREMENTS.v1.md and CH-R124).
  * So it is marked xfail(strict=True): it fails now (the defect), it does NOT break suite-green
    (sanctioned open defect), and the moment a batch DECLARES the order and wires it, this test
    xpasses -> strict flips it to a hard failure, forcing that batch to remove the xfail and
    convert it into a live regression guard. The defect therefore cannot silently return.
"""
import ast
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
INDEX = REPO / "method_source" / "index_v1.py"
LEDGER = REPO / "model_authority" / "target_ledger" / "instrument_onset_target_ledger.v1.json"
REGISTRY = REPO / "model_authority" / "parameters" / "parameter_registry.v1.json"


def _reachable_chronologies():
    """Distinct recession chronologies referenced from the science path (measured, not asserted)."""
    found = set()
    src = INDEX.read_text()
    tree = ast.parse(src)
    # chronology 1: USRECD used to define the baseline (in_recession -> S["USRECD"])
    if "USRECD" in src and "is_baseline" in src:
        found.add("USRECD_baseline")
    # chronology 2: RECS module-level assignment
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "RECS":
                    found.add("RECS_output")
    # chronology 3: frozen ledger onset_T_star episodes
    if LEDGER.exists():
        led = json.loads(LEDGER.read_text())
        if led.get("recession_targets"):
            found.add("ledger_onset_T_star")
    return found


def _authority_order_declared():
    """True iff a governing-chronology authority order has been DECLARED.

    Contract (what a Phase-3 declaration must produce): either a dedicated artifact
    model_authority/chronology/governing_chronology.v1.json, or a science_declarations entry
    in the parameter registry carrying an explicit `governing_chronology_authority` key.
    Neither exists today, by §22.4.
    """
    artifact = REPO / "model_authority" / "chronology" / "governing_chronology.v1.json"
    if artifact.exists():
        return True
    reg = json.loads(REGISTRY.read_text())
    decls = reg.get("science_declarations", {}).get("declarations", {})
    for d in decls.values():
        if isinstance(d, dict) and d.get("governing_chronology_authority"):
            return True
    return False


@pytest.mark.xfail(
    strict=True,
    reason="B-CHRONOLOGY-RECONCILE: 3 recession chronologies reachable, no declared authority "
    "order. DR-CHRON-1 is a Phase-3 derivation (rulebook §22.4) — cannot be answered while the "
    "universe is open. Remove this xfail only in the batch that declares the governing chronology.",
)
def test_single_governing_chronology_or_declared_authority_order():
    chronologies = _reachable_chronologies()
    # The premise must be real for the sentinel to mean anything: prove >1 chronology reachable.
    assert len(chronologies) > 1, (
        "premise broke: expected multiple reachable chronologies, found %s" % sorted(chronologies)
    )
    # HEALTHY state: with multiple chronologies reachable, an authority order MUST be declared.
    assert _authority_order_declared(), (
        "multiple recession chronologies (%s) are reachable from the science path with NO "
        "declared authority order governing z-standardisation" % sorted(chronologies)
    )
