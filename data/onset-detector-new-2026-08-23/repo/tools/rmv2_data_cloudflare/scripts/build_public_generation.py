#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rmv2_extension.public_generation import build_generation, verify_generation  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    parser.add_argument("config", type=Path)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--generated-at")
    args = parser.parse_args()
    doc = json.loads(args.config.read_text(encoding="utf-8"))
    entries = doc if isinstance(doc, list) else doc.get("entries", [])
    pointer = build_generation(args.source_root, args.output_root, entries, generated_at=args.generated_at)
    check = verify_generation(args.output_root, pointer["generation_sha256"])
    if not check["ok"]:
        raise SystemExit("generation verification failed: %s" % check["errors"])
    print(json.dumps({"pointer": pointer, "verification": check}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
