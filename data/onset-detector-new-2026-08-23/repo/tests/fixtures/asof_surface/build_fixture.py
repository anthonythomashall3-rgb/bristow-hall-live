#!/usr/bin/env python3
"""Deterministically build the as-of surface synthetic revision-flip fixture.

SYNTHETIC / target-free (SKILL.md equation-derivation protocol step 8:
"sign-reversing revision" mechanism). One INDPRO-like monthly member, neg_yoy
transform, one channel. A single reference period (2022-01) carries a weak value
in the vintage available by the decision cutoff and a revised-up value that only
becomes available AFTER the cutoff. Flipping the vintage value must move the
as-of E12 path; the current_revised (final) path never sees the vintage and must
not move.

Run: python3 tests/fixtures/asof_surface/build_fixture.py
"""
import datetime as dt
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "revision_flip.v1.json"

FLIP_PERIOD = "2022-01-01"           # reference period whose vintage is revised
CUTOFF = "2022-03-01"               # decision cutoff (before the revision is public)
ASOF_VALUE = 95.0                    # weak first release available 2022-02-15
REVISED_VALUE = 107.4               # revised-up value, available 2022-04-15 (> cutoff)


def months(start_ym, n):
    y, m = start_ym
    out = []
    for _ in range(n):
        out.append(dt.date(y, m, 1))
        m += 1
        if m == 13:
            y += 1
            m = 1
    return out


def build():
    grid_months = months((2019, 1), 42)   # 2019-01 .. 2022-06
    # current_revised (final) monthly INDPRO-like index: gentle expansion ramp,
    # NO dip at the flip period (the weakness was revised away).
    final = {}
    for k, d in enumerate(grid_months):
        final[d.isoformat()] = round(100.0 + 0.6 * k, 3)
    # the as-of vintage stream: for every period a first release available ~15d
    # into the following month equal to the final value, EXCEPT the flip period,
    # which is released weak (ASOF_VALUE) and only revised to the final value on
    # a later date (after the cutoff).
    asof_records = []
    for d in grid_months:
        rel = (d.replace(day=15) + dt.timedelta(days=31)).replace(day=15)  # ~mid next month
        val = final[d.isoformat()]
        if d.isoformat() == FLIP_PERIOD:
            # weak first release (available before cutoff)
            asof_records.append({
                "reference_period_end": d.isoformat(),
                "value": ASOF_VALUE,
                "available_at": "2022-02-15",
                "vintage_label": "ASOF20220215",
            })
            # revised-up value (available AFTER cutoff -> invisible at cutoff)
            asof_records.append({
                "reference_period_end": d.isoformat(),
                "value": REVISED_VALUE,
                "available_at": "2022-04-15",
                "vintage_label": "ASOF20220415",
            })
        else:
            asof_records.append({
                "reference_period_end": d.isoformat(),
                "value": val,
                "available_at": rel.isoformat(),
                "vintage_label": "ASOF" + rel.strftime("%Y%m%d"),
            })
    payload = {
        "schema_version": "recession-monitor-v2.asof-surface-synthetic-fixture.v1",
        "fixture_id": "revision_flip.v1",
        "synthetic": True,
        "target_free": True,
        "mechanism": "sign_reversing_revision",
        "generation_binding": "instrument.v2.g1",
        "member": {"series_id": "INDPRO", "channel": "realactivity", "transform": "neg_yoy"},
        "decision_cutoff": CUTOFF,
        "flip_reference_period": FLIP_PERIOD,
        "asof_value_before_cutoff": ASOF_VALUE,
        "revised_value_after_cutoff": REVISED_VALUE,
        "daily_grid": {"start": "2021-06-01", "end": CUTOFF},
        "baseline_exclusion_window": {"start": "2021-10-01", "end": "2022-06-01"},
        "current_revised_final": final,
        "asof_vintage_records": asof_records,
        "expected_property": (
            "E_asof at the cutoff (uses ASOF_VALUE=95.0 for 2022-01) is STRICTLY GREATER "
            "than E_final (uses REVISED_VALUE=107.4): the weak first release raises as-of "
            "recession stress. Flipping ASOF_VALUE moves E_asof; E_final never sees the "
            "vintage and is invariant."
        ),
    }
    body = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    OUT.write_text(body, encoding="utf-8")
    print("WROTE", OUT.name, "sha256", hashlib.sha256(body.encode()).hexdigest())


if __name__ == "__main__":
    build()
