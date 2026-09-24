"""B-SYNTH-BATTERY — synthetic planted-signal machinery battery (Window 3, no store write).

Validates the machinery test itself: the generator plants a factor-structured
recession-like signal with a strength dial straddling the CH-R126 MDES threshold
(~=0.85 SD), the placebo arm plants none, and the frozen pipeline (factor ->
Bai-Ng rank -> supervised ridge -> two-tier AMBER/RED detection) discriminates
signal from noise with the discrimination improving as strength rises.

These assertions test MACHINERY, not real-world recession detection (prereg v1.1 §8).
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research/method_v2/synth_battery"))

import synth_battery as sb  # noqa: E402


def test_binding_disclaimer_constant():
    # Prereg v1.1 §8 hard constraint: first line of every output.
    assert sb.DISCLAIMER == "validates machinery, NOT real-world recession detection."


def test_mdes_threshold_matches_chr126():
    # research/CH-R126.v1.json MDES_single_factor_SD.N11 = 0.845
    assert abs(sb.MDES_THRESHOLD_SD - 0.845) < 1e-9
    assert any(abs(s - 0.845) < 1e-9 for s in sb.DEFAULT_STRENGTHS)


def test_panel_shapes_and_placebo_flag():
    p = sb.make_panel(strength=1.0, seed=1, n_series=30, n_months=180)
    assert p["X"].shape == (180, 30)
    assert p["z"].shape == (180,)
    assert set(np.unique(p["z"])).issubset({0.0, 1.0})
    assert p["placebo"] is False
    assert sb.make_panel(strength=0.0, seed=1)["placebo"] is True


def test_signal_depresses_cycle_factor_during_episodes():
    # Machinery: at high strength the planted cycle-factor truth is lower in
    # episodes than out (the plant is real before the pipeline ever runs).
    p = sb.make_panel(strength=1.5, seed=7)
    z = p["z"].astype(bool)
    assert p["cycle_truth"][z].mean() < p["cycle_truth"][~z].mean()


def test_bai_ng_recovers_planted_rank_ballpark():
    # Clean panel (no real-time noise) with 3 factors -> Bai-Ng picks a small rank.
    p = sb.make_panel(strength=1.0, seed=3, n_series=60, n_months=240,
                      n_factors=3, real_time=False)
    r = sb.bai_ng_rank(p["X"])
    assert 1 <= r <= 6


def test_pipeline_runs_end_to_end():
    p = sb.make_panel(strength=1.0, seed=5)
    out = sb.run_pipeline(p)
    assert out["risk"].shape == (p["n_months"],)
    assert np.all(out["risk"] >= 0.0) and np.all(out["risk"] <= 1.0)
    assert out["r_hat"] >= 1


def test_two_tier_thresholds_derived_by_fixed_rule():
    p = sb.make_panel(strength=1.5, seed=11)
    pipe = sb.run_pipeline(p)
    thr = sb.derive_two_tier(pipe["risk"], p["z"])
    # AMBER derived (never-late leads every episode) => finite at strong signal.
    assert np.isfinite(thr["amber_thr"])
    # AMBER threshold is never higher than RED (amber is the earlier/looser tier).
    if np.isfinite(thr["red_thr"]):
        assert thr["amber_thr"] <= thr["red_thr"] + 1e-9


def test_placebo_red_never_fires_falsely():
    # RED rule = zero false alarms in replay. On a placebo (no planted signal),
    # the red firing rate on out-of-episode months must be 0 whenever the rule
    # is reported as met (never-false is a hard rule, not a target).
    p = sb.make_panel(strength=0.0, seed=21)
    pipe = sb.run_pipeline(p)
    thr = sb.derive_two_tier(pipe["risk"], p["z"])
    ev = sb.evaluate(pipe["risk"], p["z"], thr)
    if ev["red_rule_met"]:
        assert ev["false_alarm_rate_red"] == 0.0


def test_detection_improves_with_strength():
    # The core machinery claim, measured out-of-sample: crossing the MDES
    # threshold, held-out per-month detection (AUC) rises well above chance, while
    # the placebo arm sits at chance. AUC is the robust headline metric; the
    # amber/red tiers are the TRIPWIRE replay support reported alongside.
    rep = sb.run_battery(strengths=(0.0, 1.5), reps=8, seed0=20260809)
    placebo = rep["curves"][0]
    strong = rep["curves"][1]
    assert placebo["mean_test_auc"] < 0.65          # chance-ish, no planted signal
    assert strong["mean_test_auc"] >= 0.80          # strong signal recovered
    assert strong["mean_test_auc"] > placebo["mean_test_auc"] + 0.15


def test_test_auc_monotone_trend_across_grid():
    # Machinery recovery is monotone in strength in the mean: the strongest arm's
    # held-out AUC exceeds the sub-threshold arms'.
    rep = sb.run_battery(strengths=(0.0, 0.4, 0.845, 1.5), reps=8)
    aucs = [c["mean_test_auc"] for c in rep["curves"]]
    assert aucs[-1] > aucs[0]                        # 1.5 SD beats placebo
    assert aucs[2] > aucs[0]                          # at-MDES beats placebo
    assert aucs[-1] >= max(aucs[:2])                  # strongest is at the top


def test_battery_report_has_disclaimer_and_mdes_arm():
    rep = sb.run_battery(reps=4)
    assert rep["disclaimer"] == sb.DISCLAIMER
    assert any(c["straddles_mdes"] for c in rep["curves"])
    md = sb.to_markdown(rep)
    assert md.splitlines()[0] == sb.DISCLAIMER  # first line binding


def test_false_alarm_red_not_worse_than_amber():
    # RED is the stricter tier: its false-alarm rate must not exceed amber's
    # where both are finite (two-tier ordering, TRIPWIRE ruling).
    rep = sb.run_battery(strengths=(0.845, 1.1), reps=6)
    for c in rep["curves"]:
        faa = c["mean_false_alarm_rate_amber"]
        far = c["mean_false_alarm_rate_red"]
        if faa == faa and far == far:  # both non-nan
            assert far <= faa + 1e-9
