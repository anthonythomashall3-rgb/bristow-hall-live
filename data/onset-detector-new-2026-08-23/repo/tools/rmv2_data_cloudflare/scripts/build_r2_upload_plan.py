#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rmv2_extension.upload_plan import build_upload_plan  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle_root", type=Path)
    parser.add_argument("bucket")
    parser.add_argument("output", type=Path)
    parser.add_argument("--tool", choices=("rclone", "wrangler"), default="rclone")
    args = parser.parse_args()
    plan = build_upload_plan(args.bundle_root, args.bucket, tool=args.tool)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("wrote %d pointer-last upload steps" % len(plan["steps"]))


if __name__ == "__main__":
    main()
