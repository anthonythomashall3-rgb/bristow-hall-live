"""Deterministic execution and evidence-package generation for a registered run."""

import datetime as dt
import hashlib
import json
import os
from pathlib import Path
from typing import Dict, Mapping

from . import catalog
from .audit import run_audit
from .backtest import run_nested_backtest
from .evaluate import evaluate_backtest
from .features import FeatureBuilder, FeatureDataset
from .protocol import ROOT
from .targets import episodes_from_usrecd


def registered_run_spec_path() -> Path:
    candidates = sorted((ROOT / "forecaster").glob("run_spec_v2_*.json"))
    if not candidates:
        raise RuntimeError("no registered v2 run specification found")
    return candidates[-1]


def _canonical(value: object) -> str:
    return json.dumps(
        value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False
    ) + "\n"


def _write_once(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"immutable artifact differs: {path}")
        return
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dataset_summary(dataset: FeatureDataset) -> Dict[str, object]:
    quality = {}
    for row in dataset.rows:
        for value in row.data_quality.values():
            quality[value] = quality.get(value, 0) + 1
    return {
        "schema": "bh.forecaster.dataset-summary.v1",
        "mode": dataset.mode,
        "feature_names": dataset.feature_names,
        "row_count": len(dataset.rows),
        "skipped_issue_count": len(dataset.skipped),
        "first_issue": dataset.rows[0].issue_at.isoformat() if dataset.rows else None,
        "last_issue": dataset.rows[-1].issue_at.isoformat() if dataset.rows else None,
        "data_quality_feature_counts": quality,
        "last_row_source_checksums": dataset.rows[-1].source_checksums
        if dataset.rows else {},
        "skipped": dataset.skipped,
    }


def _normalize_audit(audit: Dict[str, object]) -> Dict[str, object]:
    result = json.loads(json.dumps(audit))
    result.pop("audited_at", None)
    for source in result.get("source_status", {}).values():
        source.pop("age_days", None)
    return result


def _fmt(value: object, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def render_report(
    run_spec: Mapping[str, object],
    strict: Mapping[str, object],
    approximate: Mapping[str, object],
    strict_dataset: Mapping[str, object],
    approximate_dataset: Mapping[str, object],
) -> str:
    lines = [
        "# Recession Forecaster V2 Evidence Report",
        "",
        f"Run: `{run_spec['run_id']}`",
        "",
        "**Decision: NO ADOPTION.** The registered deployment gate requires both "
        "the complete historical joint scorecard and at least 12 months of "
        "prospective confirmation. Prospective confirmation does not yet exist.",
        "",
        "All historical scores below are contaminated nested walk-forward evidence: "
        "the eras were previously inspected. The approximate tier also uses current "
        "revised macro values at conservative historical lags and is not a "
        "vintage-correct performance estimate.",
        "",
        "## Data coverage",
        "",
        "| Tier | Rows | First issue | Last issue | Skipped issues |",
        "|---|---:|---|---|---:|",
        f"| Strict vintage | {strict_dataset['row_count']} | "
        f"{strict_dataset['first_issue'] or 'n/a'} | "
        f"{strict_dataset['last_issue'] or 'n/a'} | "
        f"{strict_dataset['skipped_issue_count']} |",
        f"| Approximate current-vintage | {approximate_dataset['row_count']} | "
        f"{approximate_dataset['first_issue'] or 'n/a'} | "
        f"{approximate_dataset['last_issue'] or 'n/a'} | "
        f"{approximate_dataset['skipped_issue_count']} |",
        "",
        "The strict tier has too little exact-vintage episode history to satisfy "
        "the 15-year/three-prior-recession training floor. It therefore reports "
        "unestablished performance rather than silently substituting revised data.",
        "",
        "## Selected approximate-tier scorecard",
        "",
        "| Horizon | Selected family | Episodes caught/eligible | Recall | Precision | "
        "False alerts/decade | Warning time | Median lead days | Brier skill | "
        "Calibration gate | Joint gate |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for horizon in sorted(approximate["selection"], key=int):
        family = approximate["selection"][horizon]
        if family is None:
            lines.append(f"| {horizon}m | none | 0/0 | n/a | n/a | n/a | n/a | n/a | n/a | fail | fail |")
            continue
        score = approximate["horizons"][horizon][family]
        episode = score["episode_metrics"]
        row = score["row_metrics"]
        lines.append(
            f"| {horizon}m | {family} | "
            f"{episode['caught_episode_count']}/{episode['eligible_episode_count']} | "
            f"{_fmt(episode['episode_recall'])} | {_fmt(episode['episode_precision'])} | "
            f"{_fmt(episode['false_alarm_episodes_per_decade'])} | "
            f"{_fmt(episode['time_under_warning_fraction'])} | "
            f"{_fmt(episode['median_lead_days'], 1)} | {_fmt(row['brier_skill'])} | "
            f"{'pass' if score['calibration_gate_pass'] else 'fail'} | "
            f"{'pass' if score['joint_gate_pass'] else 'fail'} |"
        )
    lines.extend(
        [
            "",
            "Model selection is the lowest registered expected loss at each horizon; "
            "the term-spread family wins ties on the pre-registered simplicity rule. "
            "No family or threshold was changed after results.",
            "",
            "## Every eligible recession for selected policies",
            "",
            "| Horizon | Episode | Status | First alert | Lead days | First-alert probability | "
            "Maximum pre-onset probability |",
            "|---:|---|---|---|---:|---:|---:|",
        ]
    )
    for horizon in sorted(approximate["selection"], key=int):
        family = approximate["selection"][horizon]
        if family is None:
            continue
        for episode in approximate["horizons"][horizon][family]["episodes"]:
            lines.append(
                f"| {horizon}m | {episode['episode_id']} | {episode['status']} | "
                f"{episode['first_valid_alert'] or 'none'} | "
                f"{_fmt(episode['lead_days'], 0)} | "
                f"{_fmt(episode['probability_at_first_alert'])} | "
                f"{_fmt(episode['maximum_pre_onset_probability'])} |"
            )
    lines.extend(
        [
            "",
            "## False-alert accounting for selected policies",
            "",
            "| Horizon | Start | End | Days | Peak probability | Late nowcast/detection |",
            "|---:|---|---|---:|---:|---|",
        ]
    )
    false_count = 0
    for horizon in sorted(approximate["selection"], key=int):
        family = approximate["selection"][horizon]
        if family is None:
            continue
        for alert in approximate["horizons"][horizon][family]["false_alarms"]:
            false_count += 1
            lines.append(
                f"| {horizon}m | {alert['start']} | {alert['end']} | "
                f"{alert['duration_days']} | {_fmt(alert['peak_probability'])} | "
                f"{alert['late_nowcast_or_detection']} |"
            )
    if not false_count:
        lines.append("| — | none | — | — | — | — |")
    lines.extend(
        [
            "",
            "## Uncertainty and falsification",
            "",
            "The selected historical evaluation contains fewer than eight independent "
            "eligible recession episodes. Per the registration, percentile intervals "
            "are refused rather than treating adjacent months as independent. Each "
            "candidate artifact includes shuffled-outcome, shifted-placebo-onset, "
            "pandemic-exclusion, era-partition, and leave-one-episode diagnostics.",
            "",
            "## What can and cannot be claimed",
            "",
            "- The software enforces release-aware features, purged nested temporal "
            "validation, training-only calibration/thresholds, one-to-one alert "
            "matching, and complete false-alert accounting.",
            "- Strict historical performance is unestablished because exact vintages "
            "do not cover enough prior recession episodes.",
            "- Approximate-tier numbers are timing sensitivity only, not real-time "
            "historical performance and not prospective reliability.",
            "- No 95% reliability claim, perfect-forecaster claim, incumbent "
            "replacement, paper change, or production deployment is supported.",
            "- The highest-value next evidence is uninterrupted append-only shadow "
            "forecasting for at least 12 months, broader exact-vintage acquisition, "
            "and an independent audit before any adoption decision.",
            "",
        ]
    )
    return "\n".join(lines)


def _registered_hash(run_id: str) -> str:
    ledger = ROOT / "research" / "experiments" / "master_forecaster_v2.jsonl"
    records = [
        json.loads(line)
        for line in ledger.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    matches = [
        record for record in records
        if record.get("run_id") == run_id
        and record.get("status") == "registered_before_results"
    ]
    if len(matches) != 1:
        raise RuntimeError(f"run {run_id} lacks one pre-result registration")
    return str(matches[0]["run_spec_sha256"])


def run_evidence(raw_root: Path, spec_path: Path = None) -> Path:
    spec_path = Path(spec_path or registered_run_spec_path())
    run_spec = json.loads(spec_path.read_text(encoding="utf-8"))
    expected_spec_hash = _registered_hash(str(run_spec["run_id"]))
    if _sha(spec_path) != expected_spec_hash:
        raise RuntimeError("registered run specification hash mismatch")
    raw_root = Path(raw_root)
    episodes = episodes_from_usrecd(raw_root / "USRECD.csv")
    builder = FeatureBuilder(raw_root)
    cutoff = dt.date.fromisoformat(run_spec["data_cutoff"])
    feature_end = dt.date.fromisoformat(run_spec["feature_issue_end"])
    datasets = {}
    backtests = {}
    scorecards = {}
    for mode, settings in run_spec["modes"].items():
        start = dt.date.fromisoformat(settings["issue_start"])
        dataset = builder.build_dataset(start, feature_end, mode)
        datasets[mode] = dataset
        backtest = run_nested_backtest(
            dataset,
            episodes,
            cutoff,
            run_spec["horizons_months"],
            run_spec["families"],
            minimum_training_years=run_spec["minimum_training_years"],
            minimum_training_episodes=run_spec[
                "minimum_training_recession_episodes"
            ],
            refit_months=run_spec["outer_refit_months"],
        )
        backtests[mode] = backtest
        scorecards[mode] = evaluate_backtest(
            backtest, episodes, cutoff, seed=run_spec["bootstrap_seed"]
        )
    artifact_root = (
        ROOT / "forecaster" / "artifacts" / f"run-{run_spec['run_id']}"
    )
    files = {
        "run_spec.json": run_spec,
        "dataset_strict.json": _dataset_summary(datasets["strict_vintage"]),
        "dataset_approximate.json": _dataset_summary(
            datasets["approximate_current_vintage"]
        ),
        "backtest_strict.json": backtests["strict_vintage"],
        "backtest_approximate.json": backtests["approximate_current_vintage"],
        "scorecard_strict.json": scorecards["strict_vintage"],
        "scorecard_approximate.json": scorecards["approximate_current_vintage"],
        "audit.json": _normalize_audit(run_audit(raw_root)),
    }
    for name, value in files.items():
        _write_once(artifact_root / name, _canonical(value))
    report = render_report(
        run_spec,
        scorecards["strict_vintage"],
        scorecards["approximate_current_vintage"],
        files["dataset_strict.json"],
        files["dataset_approximate.json"],
    )
    _write_once(artifact_root / "REPORT.md", report)
    manifest_files = {
        path.name: _sha(path)
        for path in sorted(artifact_root.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    manifest = {
        "schema": "bh.forecaster.artifact-manifest.v1",
        "run_id": run_spec["run_id"],
        "registered_run_spec_sha256": expected_spec_hash,
        "registered_model_code_commit": run_spec["code_commit"],
        "evidence_generator_sha256": _sha(Path(__file__)),
        "files": manifest_files,
        "immutable": True,
    }
    _write_once(artifact_root / "manifest.json", _canonical(manifest))
    return artifact_root


def raw_root_from_environment() -> Path:
    value = os.environ.get("FORECASTER_RAW_ROOT")
    if value:
        return Path(value)
    # Env unset: resolve the DECLARED read-root (external_read_roots.v1.json),
    # the authoritative in-repo name for this mandatory external input. One home
    # for the resolution (§24.7); catalog.raw_root() is the single resolver.
    declared = catalog.declared_forecaster_raw_root()
    if declared is not None:
        return declared
    raise RuntimeError("FORECASTER_RAW_ROOT is required")
