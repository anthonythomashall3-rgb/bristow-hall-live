"""bh — the Bristow-Hall operations CLI (Batch A2 spine).

This package is the deterministic-automation layer over Recession Monitor V2.
It is imported as a top-level package from the repository root (the same root
on which the test suite runs). Nothing here mutates the data store directly;
store mutation remains the province of the rulebook's two writers
(paste-block sessions and promoted runbooks, rulebook Part I).

Section references (e.g. "A2 §35") point at BATCH A2 items; rulebook
references (e.g. "rulebook §1.5") point at BRISTOW_HALL_RULEBOOK.md.
"""

__all__ = ["cli"]

# Kept deliberately tiny: importing bh must never trigger I/O or resolution.
GENERATION_BINDING = "instrument.v2.g1"  # rulebook §2.1
