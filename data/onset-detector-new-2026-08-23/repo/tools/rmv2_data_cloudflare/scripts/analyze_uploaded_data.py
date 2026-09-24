#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rmv2_extension.evidence_analysis import analyze_evidence, write_artifacts  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze mounted Recession Monitor V2 data evidence")
    parser.add_argument("input_root", type=Path)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--generated-at")
    parser.add_argument("--omit-strict-realtime", action="store_true")
    args = parser.parse_args()
    report = analyze_evidence(args.input_root, generated_at=args.generated_at, include_strict_realtime=not args.omit_strict_realtime)
    outputs = write_artifacts(report, args.output_root)
    print(json.dumps({"gap_summary": report["gap_summary"], "outputs": outputs}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
