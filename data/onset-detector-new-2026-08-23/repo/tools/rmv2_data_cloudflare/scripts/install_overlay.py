#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rmv2_extension.installer import install_overlay  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    package_root = Path(__file__).resolve().parents[1]
    receipt = install_overlay(package_root, args.project_root, apply=args.apply)
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
