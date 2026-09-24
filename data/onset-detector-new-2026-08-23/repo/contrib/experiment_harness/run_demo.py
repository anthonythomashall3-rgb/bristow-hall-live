"""End-to-end smoke run of the B-EXP-0 harness against the real (read-only) store.

Proves the machinery wires together; adopts NOTHING. Writes a small artifact to
research/BEXP0_harness_demo.json. Run:  python3 -m contrib.experiment_harness.run_demo
"""
import datetime as dt
import json
import os
import random

from contrib.experiment_harness.asof_replay import AsOfReplayEngine, build_store_loader
from contrib.experiment_harness import replay_ci

OUT = "research/BEXP0_harness_demo.json"
# a landed deep vintage lane (source head stem) — read-only demonstration input
DEMO_SOURCE = "fred_w875rx1_fredmd_panel_vintages_deep"


def main():
    loader = build_store_loader()
    engine = AsOfReplayEngine(loader)

    rng = random.Random(20260806)
    asof = replay_ci.select_replay_date(rng, dt.date(2005, 1, 1), dt.date(2026, 8, 5))

    result = engine.reconstruct([DEMO_SOURCE], asof)
    report = {
        "note": "B-EXP-0 harness E2E smoke; adopts nothing; read-only store access",
        "demo_source": DEMO_SOURCE,
        "asof": str(asof),
        "fallback_class": result.fallback_class,
        "frontier": str(result.frontier),
        "n_obs_knowable": result.n_obs,
    }
    os.makedirs("research", exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(report, fh, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
