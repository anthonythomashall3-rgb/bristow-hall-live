"""As-of daily observed information-state surface for Recession Monitor V2.

Generation binding: instrument.v2.g1 (owner keep-decision
model_authority/keep_decisions/owner_keep_decision.instrument_chain.g1.json).

This package builds the OPEN dependency named in that keep-decision:
`daily_observed_information_state_surface` — the release-aware, as-of input
stream the Onset Watch and Forecaster both require. It reconstructs the adopted
predecessor instrument's pressure line P and energy E12 on the `observed_only`
lane (SKILL.md "daily measurement layer"), using only publisher observations
actually available by each decision cutoff.

No scientific outputs (no Watch, no chronology, no admission) are produced here.
"""

from .surface import (
    ObsRecord,
    daily_observed_information_state,
    daily_carry,
    MemberSpec,
    reconstruct_P_asof,
    reconstruct_E_asof,
    e12_from_reading,
    TRANSFORMS,
    BAR_E,
    RESET,
)

__all__ = [
    "ObsRecord",
    "daily_observed_information_state",
    "daily_carry",
    "MemberSpec",
    "reconstruct_P_asof",
    "reconstruct_E_asof",
    "e12_from_reading",
    "TRANSFORMS",
    "BAR_E",
    "RESET",
]
