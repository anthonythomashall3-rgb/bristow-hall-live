"""Read-only standard-library API for local shadow forecasts and evidence."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, Sequence, Tuple

from .prospective import ForecastLedger


def api_resource(
    route: str, ledger_path: Path, artifact_root: Path
) -> Tuple[int, Dict[str, object]]:
    ledger = ForecastLedger(ledger_path)
    entries = ledger.read()
    valid, bad = ledger.verify(entries)
    if route == "/health":
        return (
            200 if valid else 503,
            {
                "schema": "bh.forecaster.api-health.v1",
                "ok": valid,
                "ledger_entries": len(entries),
                "first_bad_sequence": bad,
            },
        )
    if route == "/forecast":
        if not valid:
            return 503, {"error": "prospective ledger integrity failure"}
        if not entries:
            return 404, {"error": "no prospective shadow forecast"}
        return 200, {
            "schema": "bh.forecaster.api-forecast.v1",
            "forecast": entries[-1],
        }
    if route == "/evidence":
        artifact_root = Path(artifact_root)
        scorecard = json.loads(
            (artifact_root / "scorecard_approximate.json").read_text(
                encoding="utf-8"
            )
        )
        manifest = json.loads(
            (artifact_root / "manifest.json").read_text(encoding="utf-8")
        )
        selected = {}
        for horizon, family in scorecard["selection"].items():
            score = scorecard["horizons"][horizon][family] if family else None
            selected[horizon] = {
                "family": family,
                "joint_gate_pass": score["joint_gate_pass"] if score else False,
                "episode_metrics": score["episode_metrics"] if score else None,
            }
        return 200, {
            "schema": "bh.forecaster.api-evidence.v1",
            "run_id": manifest["run_id"],
            "historical_joint_gate_pass": scorecard[
                "historical_joint_gate_pass"
            ],
            "prospective_confirmation_complete": scorecard[
                "prospective_confirmation_complete"
            ],
            "deployment_eligible": scorecard["deployment_eligible"],
            "selected": selected,
        }
    return 404, {"error": "not found"}


def handler_factory(ledger_path: Path, artifact_root: Path):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            status, payload = api_resource(
                self.path.split("?", 1)[0], ledger_path, artifact_root
            )
            body = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            return

    return Handler


def main(argv: Sequence[str] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    server = ThreadingHTTPServer(
        (args.host, args.port), handler_factory(args.ledger, args.artifacts)
    )
    print(f"http://{args.host}:{args.port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
