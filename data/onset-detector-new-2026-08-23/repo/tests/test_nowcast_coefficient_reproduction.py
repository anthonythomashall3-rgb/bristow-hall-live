"""Offline proof that the frozen nowcast constants are reproducible.

Owner ruling 2026-08-08
(_mailbox/answers/20260808T041632Z_B-BLOCKER-SWEEP__nowcast_reproduction_contract.md)
splits the contract into two assertions that are NOT alternatives:

1. BIT-EXACT, HOST-GATED. On the pinned reproduction stack
   (CPython 3.8.10 + numpy 1.24.4 -- the stack that produced the frozen literals in
   method_source/nowcast_live.py) the fresh fit equals the frozen literals with exact
   Python numeric equality. That IS the reproduction contract and it is NOT weakened here.
   Off that stack the exact assertion is SKIPPED with an explicit reason naming the stack
   mismatch -- never a silent skip.

2. ALWAYS-ON DERIVED DRIFT ALARM. On every stack, the maximum relative divergence between
   the fresh fit and the frozen literals must stay under a tolerance DERIVED from the
   measured cross-stack ULP spread (never a round number, per rulebook 18.2). Real
   coefficient drift is orders of magnitude larger, so this catches a genuine regression on
   any machine -- including the ones that cannot run the bit-exact assertion.

MEASUREMENT of record (B-NOWCAST-REPRO-GATE, research/B-NOWCAST-REPRO-GATE.v1.json):
  pinned  CPython 3.8.10 / numpy 1.24.4 (arm64 Darwin, accelerate) -> exact_match, rel_div 0
  off-pin CPython 3.14.5 / numpy 2.5.1  (arm64 Darwin, accelerate) -> rel_div 1.422314e-11 (B_HOUST[0])
  off-pin aarch64 Linux (answer file, B_CMRMT[0])                  -> rel_div 1.985449e-15
"""

from __future__ import annotations

import functools
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

import numpy
import pytest


ROOT = Path(__file__).resolve().parents[1]
REPRO = ROOT / "method_source" / "nowcast_reproduction"
SCRIPT = REPRO / "reproduce.py"
MANIFEST = REPRO / "reproduction_manifest.v1.json"

# ---- pinned reproduction stack (measured: the ONLY stack that reproduces bit-exact) ----
PINNED_PYTHON = "3.8.10"
PINNED_NUMPY = "1.24.4"

# ---- derived drift tolerance (rulebook 18.2), watch_build.py:72 shape -- NOT a round number ----
# Completed measurement: max cross-stack relative divergence of the frozen coefficients.
#   pinned  3.8.10 / numpy 1.24.4  -> 0.0            (defines the pin)
#   off-pin 3.14.5 / numpy 2.5.1   -> 1.422314e-11   (B_HOUST[0], near-zero intercept, worst case)
#   off-pin aarch64 Linux          -> 1.985449e-15   (B_CMRMT[0], answer file)
# Spread ceiling = max observed off-pin = 1.422314e-11. Stated headroom = 100x: two decades
# above the measured jitter, still ~8 decades below any real refit drift (smallest frozen
# coefficient is 2.185610e-04, and a genuine constant change moves a coefficient by O(1e-3)+).
MEASURED_MAX_REL_DIV = 1.422314e-11
DRIFT_HEADROOM = 100
DRIFT_TOL = MEASURED_MAX_REL_DIV * DRIFT_HEADROOM  # = 1.422314e-09


def _stack_id() -> str:
    return "CPython %s / numpy %s (%s %s)" % (
        platform.python_version(),
        numpy.__version__,
        platform.system(),
        platform.machine(),
    )


def _on_pinned_stack() -> bool:
    return (
        platform.python_version() == PINNED_PYTHON
        and numpy.__version__ == PINNED_NUMPY
    )


@functools.lru_cache(maxsize=1)
def _report():
    run = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert run.stdout, run.stderr
    return run.returncode, json.loads(run.stdout)


def _flatten(mapping, prefix=""):
    flat = {}
    for key, value in mapping.items():
        if isinstance(value, dict):
            flat.update(_flatten(value, prefix + key + "."))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                flat["%s%s[%d]" % (prefix, key, index)] = item
        else:
            flat[prefix + key] = value
    return flat


def _max_relative_divergence(report):
    expected = _flatten(report["expected"])
    actual = _flatten(report["actual"])
    worst = 0.0
    for key, exp in expected.items():
        act = actual[key]
        denom = max(abs(exp), abs(act))
        rel = 0.0 if denom == 0.0 else abs(act - exp) / denom
        worst = max(worst, rel)
    return worst


def test_reproduction_inputs_are_pinned():
    """Host-independent: the frozen information set and input pins still hold."""
    manifest = json.loads(MANIFEST.read_text())
    snapshot = REPRO / manifest["inputs"]["nfci_final_vintage"]["path"]
    assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == (
        manifest["inputs"]["nfci_final_vintage"]["sha256"]
    )
    _, report = _report()
    assert report["input_pins_match"] is True
    assert all(report["input_pin_checks"].values())
    assert report["information_set_end"] == "2026-07-18"
    assert report["fit_end"] == "2011-12-31"


def test_nowcast_constants_reproduce_bit_exact_on_pinned_stack():
    """Bit-exact, HOST-GATED. Skipped off-pin with an explicit reason (never silently)."""
    if not _on_pinned_stack():
        pytest.skip(
            "bit-exact reproduction is pinned to CPython %s / numpy %s; running on %s "
            "(off-pin runs are informational -- covered by the always-on drift alarm)"
            % (PINNED_PYTHON, PINNED_NUMPY, _stack_id())
        )
    returncode, report = _report()
    assert returncode == 0, report
    assert report["status"] == "exact_match"
    assert report["actual"] == report["expected"]


def test_nowcast_constants_drift_alarm_under_derived_tolerance():
    """Always-on. Relative divergence must sit under the derived tolerance on ANY stack."""
    _, report = _report()
    worst = _max_relative_divergence(report)
    assert worst <= DRIFT_TOL, (
        "coefficient drift %.6e exceeds derived tolerance %.6e on %s "
        "-- real drift, not ULP jitter" % (worst, DRIFT_TOL, _stack_id())
    )
