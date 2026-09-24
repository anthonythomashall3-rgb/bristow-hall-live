#!/usr/bin/env python3
"""Assemble CH1_CHANNEL_STRUCTURE_PROBE.v1.json from ch1_results.json. Pure read of the
scratch results + interpretation; no vault write, no module import."""
import json
B = "/Users/anthonyhall/Desktop/RecessionMonitor 2/Recession Monitor V2/research/channel_structure_ch1/"
r = json.load(open(B + "scratch/ch1_results.json"))

VAULT_SHA = "4567dbefed8393ed55f236db6358e035f8ab6a3a2c640937a1ee8824faa9eb0e"

receipt = {
 "schema": "recession-monitor-v2.ch1-channel-structure-probe.v1",
 "probe": "PROBE CH1 — channel structure on transformed values",
 "writes_vault": False, "decides": False, "admits": False,
 "measured_on": "transformed signed-deterioration z (Z[name]) exactly as channel_score/zval "
                "receives them; index_v1 imported with NOWCAST_DISABLE=1 (pure carry-forward, "
                "no live-edge substituted-diagnostic fills)",
 "information_set_mode": "current_revised (raw/ -> data_archive/current_revised_and_spatial)",
 "members_measured": 17,

 "s0_transformed_span_and_window": {
    "per_member": r["s0_span"],
    "nn_daily_over_window": r["s0_nn_daily"],
    "sample_window": r["s0_window"],
    "note": "one window used throughout all correlations; pairwise-complete deletion. "
            "VIX non-null only from 1990-01-02 (nn_daily 13357), BAA10Y from 1986-01-02 "
            "(nn_daily 14818); all other members carry across the full 18320-day grid."
 },

 "s1_correlation": {
    "pearson_matrix_transformed": r["s1_pearson_matrix"],
    "named_pairs_raw_vs_transformed": r["s1_named_pairs"],
    "spearman_named": r["s1_spearman_named"],
    "collinear_ge_0p80_transformed": r["s1_collinear_ge_0p80"],
    "findings": [
      "INDPRO~CMRMT raw 0.966 -> transformed 0.875 (falls 0.091): partial trend inflation, "
      "but still a real structural duplicate at >=0.80.",
      "PERMIT~HOUST raw 0.953 -> 0.911 (falls 0.042): holds, real duplicate.",
      "BAA10Y~BAAAAA raw 0.816 -> 0.816 (unchanged): both already spreads; real duplicate. "
      "Spearman only 0.668, so the linear tie is looser by rank.",
      "SAHM~UNRATEv raw 0.505 -> 0.534 (rises): NOT collinear.",
      "IURSA~UNRATEv raw 0.789 -> transformed 0.724 (falls): moderate, below flag; but "
      "IURSA~SAHM is 0.857 (flagged).",
      "Six transformed pairs at |r|>=0.80: PERMIT~HOUST 0.911, INDPRO~TCU 0.900, "
      "INDPRO~CMRMT 0.875, IURSA~SAHM 0.857, CMRMT~TCU 0.816, BAAAAA~BAA10Y 0.816. "
      "realactivity has three mutually-collinear members (INDPRO,TCU,CMRMT); labor has "
      "IURSA~SAHM.",
      "Flags are labels for the report only; no weight/member decision is derived here."
    ]
 },

 "s2_effective_independent_members": {
    "formula": "participation ratio PR = (sum eig)^2 / sum(eig^2) on the member "
               "pairwise-complete Pearson correlation matrix",
    "per_channel": r["s2_effective_n"],
    "nfci_first_nonnull": r["s2_nfci_first_nonnull"],
    "findings": [
      "labor eff-N 1.65 of nominal 4; realactivity eff-N 1.55 of nominal 4 — realactivity "
      "carries ~1.5 independent signals at full 0.25 weight.",
      "creditequity 1.93, housingincome 2.44, finconditions 1.0.",
      "s2.3 CONTRADICTS the brief's '2011 per V1': under current-vintage the NFCI byte "
      "series is non-null from 1971-01-08, not 2011. Confirmed from raw/NFCI.csv."
    ]
 },

 "s3_variance_contribution": {
    "method": "contribution_c = Cov(w_c*cs_c, headline)/Var(headline) on full-coverage days "
              "(all 5 channels present; wsum=1.0)",
    "overall": r["s3_var_decomp"]["all"],
    "recession_only": r["s3_var_decomp"]["recession"],
    "expansion_only": r["s3_var_decomp"]["expansion"],
    "nominal_weight": r["s3_var_decomp"]["nominal_weight"],
    "gap_realized_minus_nominal": r["s3_var_decomp"]["gap_realized_minus_nominal"],
    "equal_contribution_weights_ERC_measurement_only": r["s3_var_decomp"]["equal_contribution_weights_ERC"],
    "findings": [
      "labor drives 0.751 of headline variance at nominal weight 0.30 (gap +0.451); "
      "recession-only 0.901. Every other channel is under-realized vs nominal: "
      "realactivity 0.106 vs 0.25 (-0.144), creditequity 0.066 vs 0.20 (-0.134), "
      "housingincome 0.045 vs 0.15 (-0.105), finconditions 0.032 vs 0.10 (-0.068).",
      "CAVEAT: labor's dominance is heavily leveraged by the 2020 ICSA-yoy spike "
      "(headline hits 22.8 in 2020 vs <5 elsewhere); the variance decomposition is "
      "outlier-sensitive and should not be read as a stable steady-state contribution.",
      "Equal-variance-contribution (ERC) weights would be labor 0.069, realactivity 0.223, "
      "creditequity 0.241, finconditions 0.197, housingincome 0.270 — reported as a "
      "measurement, NOT adopted."
    ]
 },

 "s4_lead_lag": {
    "evidence_kind": r["s4_lead_lag"]["evidence_kind"],
    "chronology_reference": r["s4_lead_lag"]["chronology"],
    "crossing_rule": r["s4_lead_lag"]["rule"],
    "channel_thresholds_pct80": r["s4_lead_lag"]["channel_thresholds_pct80"],
    "per_episode_lead_days_plus_is_lead": r["s4_lead_lag"]["per_episode_lead_days"],
    "per_channel_stats": r["s4_lead_lag"]["per_channel_stats"],
    "reachable_onsets": r["s4_lead_lag"]["reachable_onsets"],
    "n_reachable": r["s4_lead_lag"]["n_reachable"],
    "unreachable": r["s4_lead_lag"]["unreachable"],
    "GATE": "external_comparator — this section may NOT set any weight without this label "
            "following the weight into the receipt. Chronology is NBER onsets via USRECD, "
            "an external comparator, not a construction input.",
    "findings": [
      "6 of 8 ledger-style episodes reachable in the 1976-06+ window. 1973-75 pre-window; "
      "2022-24* has no NBER recession day (USRECD never 1) so no onset to reference.",
      "median leads: labor 191d, realactivity 168d, creditequity 173d, housingincome 153d, "
      "finconditions 658d (NFCI crosses very early and noisily). Dispersion is large "
      "(IQR 214-607d); realactivity and creditequity LAG at some episodes (2008, 1980)."
    ]
 },

 "s5_baseline_swap": {
    **r["s5_baseline_swap"],
    "findings": [
      "SEVERITY ORDERING IS IDENTICAL under current, statistical-mean, and "
      "statistical-median/MAD baselines: 2020 > 2007-09 > 1980 > 1981-82 > 2001 > 1990-91 "
      "> 2022-24*. Ordering — the product's first requirement — is robust to the "
      "NBER-free baseline swap.",
      "Magnitudes move: headline corr current vs stat-mean 0.918 (max div 18.56 at "
      "2020-04-04, the COVID spike), current vs stat-median 0.988 (max div 7.62 at "
      "2020-05-01). stat-mean compresses (full-distribution sd inflated by recession mass); "
      "stat-median/MAD amplifies.",
      "s5.5 2022-24*: when NO LONGER excluded from the baseline its own observations enter "
      "mu/sd and pull its peak toward zero (peak 0.33 current -> 0.011 stat-mean, 0.518 "
      "stat-median). It remains the mildest episode and does not reorder. Reported as a "
      "measurement; nothing tuned to preserve or destroy any 2022 result.",
      "s5.6 two robust estimators run because the choice is otherwise arbitrary: "
      "full-distribution mean/std and median/(1.4826*MAD). Both preserve the ordering."
    ]
 },

 "s6_missing_channel": {
    **r["s6_missing_channel"],
    "HEADLINE": "IMMATERIAL IN THIS BUILD. Under current-vintage NFCI is non-null from "
                "1971, so all five channels are present every day in 1976-06..END: the true "
                "achieved weight sum is exactly 1.00 on all 18320 days. Renormalized and "
                "zero-contribution headlines are therefore byte-identical (corr 1.0, max "
                "divergence 0.0) and the severity ordering is identical under both. The "
                "brief's premise that four channels rescale 0.90->1.00 before 2011 does NOT "
                "hold for current-vintage; it would only bind in a vintage/first-release "
                "mode where NFCI starts 2011."
 },

 "s8_gates": {
    "vault_sha_start_DATA_SHA256SUMS": VAULT_SHA,
    "vault_sha_end_DATA_SHA256SUMS": VAULT_SHA,
    "vault_byte_identical": True,
    "verify_start": "PASS mode=catalog files=27270 bytes=842485829 series=270",
    "verify_end": "PASS mode=catalog files=27270 bytes=842485829 series=270",
    "side_effects_cleaned": "import of index_v1 created method_source/__pycache__/"
        "index_v1.cpython-38.pyc (a payload root); removed before final verify — verify "
        "PASS restored and payload sha unchanged throughout.",
    "steps_skipped": "none out-of-scope; no writer lock taken; target ledger 8b204ccd, "
        "operational_status.json, and tests untouched.",
    "stop": "clean end; measurement only; nothing admitted/promoted/frozen."
 }
}
json.dump(receipt, open(B + "CH1_CHANNEL_STRUCTURE_PROBE.v1.json", "w"), indent=1, default=str)
print("receipt written:", B + "CH1_CHANNEL_STRUCTURE_PROBE.v1.json")
