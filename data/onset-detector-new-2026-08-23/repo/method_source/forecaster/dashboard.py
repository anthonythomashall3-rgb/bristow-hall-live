"""Generate a dependency-free local dashboard from immutable evidence."""

import html
import json
from pathlib import Path

from .prospective import ForecastLedger


def _percent(value):
    return "n/a" if value is None else f"{100.0 * float(value):.1f}%"


def render_dashboard(ledger_path: Path, artifact_root: Path) -> str:
    entries = ForecastLedger(ledger_path).read()
    valid, bad = ForecastLedger.verify(entries)
    latest = entries[-1]["payload"] if entries and valid else None
    scorecard = json.loads(
        (Path(artifact_root) / "scorecard_approximate.json").read_text(
            encoding="utf-8"
        )
    )
    rows = []
    for horizon in sorted(scorecard["selection"], key=int):
        family = scorecard["selection"][horizon]
        score = scorecard["horizons"][horizon][family] if family else None
        episode = score["episode_metrics"] if score else None
        probability = (
            latest.get("horizon_probabilities", {}).get(horizon)
            if latest else None
        )
        state = (
            latest.get("policy_states", {}).get(horizon, {}).get("state")
            if latest else "unavailable"
        )
        rows.append(
            "<tr>"
            f"<td>{html.escape(horizon)} months</td>"
            f"<td>{html.escape(str(family or 'none'))}</td>"
            f"<td>{_percent(probability)}</td>"
            f"<td>{html.escape(str(state))}</td>"
            f"<td>{_percent(episode['episode_recall']) if episode else 'n/a'}</td>"
            f"<td>{_percent(episode['episode_precision']) if episode else 'n/a'}</td>"
            f"<td>{'PASS' if score and score['joint_gate_pass'] else 'FAIL'}</td>"
            "</tr>"
        )
    issue = latest.get("issued_at") if latest else "No forecast issued"
    integrity = "verified" if valid else f"FAILED at sequence {bad}"
    status = latest.get("status") if latest else "unavailable"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Recession Forecaster V2 — Shadow Evidence</title>
<style>
:root {{ color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui; }}
body {{ margin: 0; background: #07111f; color: #e7edf5; }}
main {{ max-width: 1100px; margin: auto; padding: 40px 24px 64px; }}
.banner {{ border: 1px solid #fb7185; background: #3f1220; padding: 18px; border-radius: 12px; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(220px,1fr)); gap: 14px; margin: 20px 0; }}
.card {{ background: #0f2035; padding: 18px; border: 1px solid #29425f; border-radius: 12px; }}
.label {{ color: #9fb1c6; font-size: .8rem; text-transform: uppercase; letter-spacing: .08em; }}
.value {{ font-size: 1.2rem; margin-top: 8px; overflow-wrap: anywhere; }}
table {{ width: 100%; border-collapse: collapse; background: #0f2035; }}
th,td {{ text-align: left; padding: 12px; border-bottom: 1px solid #29425f; }}
th {{ color: #9fb1c6; }}
small {{ color: #9fb1c6; }}
</style>
</head>
<body><main>
<h1>Recession Forecaster V2</h1>
<div class="banner"><strong>NO ADOPTION — EXPERIMENTAL SHADOW ONLY.</strong>
Historical performance failed the registered joint gate. This page is not the
production recession website and does not replace its detector.</div>
<div class="cards">
<div class="card"><div class="label">Shadow status</div><div class="value">{html.escape(str(status))}</div></div>
<div class="card"><div class="label">Issued at</div><div class="value">{html.escape(str(issue))}</div></div>
<div class="card"><div class="label">Ledger integrity</div><div class="value">{html.escape(integrity)}</div></div>
<div class="card"><div class="label">Deployment eligible</div><div class="value">NO</div></div>
</div>
<h2>Current shadow probabilities and historical evidence</h2>
<table><thead><tr><th>Horizon</th><th>Selected family</th><th>Current probability</th>
<th>Policy state</th><th>Historical recall</th><th>Historical precision</th><th>Joint gate</th>
</tr></thead><tbody>{''.join(rows)}</tbody></table>
<p><small>Historical figures are contaminated nested walk-forward sensitivity
evidence using revised macro data. Strict-vintage performance is unestablished.
Fewer than eight independent eligible recessions exist, so the registered
episode-bootstrap interval is refused. Prospective reliability is unknown.</small></p>
</main></body></html>
"""


def generate_dashboard(
    ledger_path: Path, artifact_root: Path, output_path: Path
) -> Path:
    text = render_dashboard(ledger_path, artifact_root)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(output_path)
    return output_path
