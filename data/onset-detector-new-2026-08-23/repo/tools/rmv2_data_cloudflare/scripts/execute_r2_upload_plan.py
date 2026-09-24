#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rmv2_extension.publisher import execute_upload_plan  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute a pointer-last Cloudflare R2 upload plan")
    parser.add_argument("plan", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    value = json.loads(args.plan.read_text(encoding="utf-8"))
    receipt = execute_upload_plan(value, apply=args.apply, receipt_path=args.receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    if receipt["status"] == "FAILED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
