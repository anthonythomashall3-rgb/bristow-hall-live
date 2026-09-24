"""Command-line entry point for registered forecaster workflows."""

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Sequence

from .audit import run_audit
from .catalog import audit_catalog
from .dashboard import generate_dashboard
from .protocol import ROOT, load_protocol, validate_protocol
from .prospective import ForecastLedger, issue_shadow_forecast
from .runner import raw_root_from_environment, run_evidence


def validate_registration() -> None:
    protocol = load_protocol()
    validate_protocol(protocol)
    manifest_path = ROOT / "forecaster" / "artifacts" / "registration_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures = []
    for relative, expected in manifest["pinned_files"].items():
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        if actual != expected:
            failures.append(f"{relative}: expected {expected}, got {actual}")
    if failures:
        raise SystemExit("REGISTRATION INVALID\n" + "\n".join(failures))
    print(
        "PROTOCOL REGISTERED: "
        f"{protocol['schema']}; historical={protocol['historical_evidence_status']}; "
        f"untouched={protocol['untouched_evidence']}"
    )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "command",
        choices=[
            "validate-protocol",
            "audit-data",
            "audit",
            "backtest",
            "report",
            "shadow",
            "dashboard",
        ],
    )
    result.add_argument(
        "--artifacts",
        type=Path,
        default=ROOT / "forecaster" / "artifacts" / "run-p3-20260722-v3",
    )
    result.add_argument(
        "--ledger",
        type=Path,
        default=ROOT / "forecaster" / "prospective" / "ledger.jsonl",
    )
    result.add_argument(
        "--dashboard-output",
        type=Path,
        default=ROOT / "forecaster" / "static" / "index.html",
    )
    return result


def main(argv: Sequence[str] = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "validate-protocol":
        validate_registration()
    elif args.command == "audit-data":
        result = audit_catalog()
        print(json.dumps(result, indent=2, sort_keys=True))
        if not result["ok"]:
            return 1
    elif args.command == "audit":
        result = run_audit()
        print(json.dumps(result, indent=2, sort_keys=True))
        if not result["ok"]:
            return 1
    elif args.command in {"backtest", "report"}:
        artifact_root = run_evidence(raw_root_from_environment())
        print(artifact_root)
    elif args.command == "shadow":
        issued_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
        entry = issue_shadow_forecast(
            raw_root_from_environment(),
            args.artifacts,
            args.ledger,
            issued_at,
        )
        generate_dashboard(args.ledger, args.artifacts, args.dashboard_output)
        print(json.dumps(entry, indent=2, sort_keys=True))
    elif args.command == "dashboard":
        valid, bad = ForecastLedger.verify(ForecastLedger(args.ledger).read())
        if not valid:
            raise SystemExit(f"prospective ledger invalid at sequence {bad}")
        print(generate_dashboard(args.ledger, args.artifacts, args.dashboard_output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
