"""B-ACQ-PUBLISHER-DIRECT — DOL ETA-539 raw state report landed as a deep
offline-current frozen snapshot on the PROVEN dol_eta539_csv shape.

The staged bytes (research/_staging/publisher_direct/dol_eta539/csv/ar539.csv,
fetched by B-FETCH-PUBLISHER-DIRECT) are the publisher's CURRENT operational
database — the raw ar539 report carries current/revised state values, NOT
first-release vintages and NOT as-of snapshots. It therefore lands
current_revised and is BARRED from any as-of / real-time claim (owner CLOCK
ruling 2026-08-08). The already-enabled dol_eta539_live lane keeps only the last
160 rows per state; this frozen deep lane preserves the full 1984-06 .. 2026-07
span for the ~600 state-episode cross-section. §6.1 caps SHAPES not sources; the
dol_eta539_csv adapter is already proven (dol_eta539_live). §3.1 each state
series is its own id, never aliased onto ICSA / ICNSA.

G.17 (Federal Reserve, xml) and Census NRC (starts/permits xlsx) are staged but
NOT landed here: each needs a NEW parser shape (§6.1) and both target the
CH-R122-measured real-time-redundant labor/output cluster — deferred to a parser
batch, recorded in the receipt (§19.4 no silent drop).
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "live_data/config/sources.v1.json"
STAGED = ROOT / "research/_staging/publisher_direct/dol_eta539/csv/ar539.csv"

sys.path.insert(0, str(ROOT / "live_data"))

DEEP_ID = "dol_eta539_deep_offline"


def _sources():
    return {s["source_id"]: s for s in json.load(open(CFG))["sources"]}


def test_dol_deep_source_registered_and_shaped():
    s = _sources().get(DEEP_ID)
    assert s is not None, "missing landed source %s" % DEEP_ID
    assert s["adapter"] == "dol_eta539_csv"
    assert s["enabled"] is False
    assert s["archival"] is True
    assert s["information_set_mode"] == "current_revised"
    assert s["coverage_source_ids"] == ["dol_ui_claims"]
    # full-span retention: max measured rows per state is 2132; must not truncate.
    assert int(s["series"]["retention_rows_per_state"]) >= 2132
    assert "BARRED from as-of" in s["label"]


def test_dol_deep_parses_full_state_cross_section():
    from rmv2_live.adapters import normalize
    s = _sources()[DEEP_ID]  # RED pre-land: KeyError until the source is registered
    body = STAGED.read_bytes()
    recs = normalize(s, body, "2026-08-08T00:00:00Z")
    states = {r["state"] for r in recs}
    periods = [r["observation_period"] for r in recs if r["observation_period"]]
    assert len(states) >= 53, len(states)
    assert min(periods) <= "1984-06-30", min(periods)
    assert max(periods) >= "2026-07-01", max(periods)
    # initial_claims + continued + 5 diagnostic measures, all own-id under the
    # deep source, never the live source or a member id.
    ids = {r["series_id"] for r in recs}
    assert all(i.startswith(DEEP_ID + ".") for i in ids)
    assert any(i.endswith(".initial_claims") for i in ids)
