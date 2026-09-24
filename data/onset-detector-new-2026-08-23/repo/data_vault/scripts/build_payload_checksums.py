#!/usr/bin/env python3
"""Rebuild the exact SHA-256 manifest for every governed payload byte."""

from __future__ import annotations

import argparse
import hashlib
import os
import stat
import tempfile
from pathlib import Path
from typing import Iterable, List


PAYLOAD_ROOTS = ("data", "data_archive", "method_source")
EXCLUSIONS = frozenset(("data_archive/README.md",))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def payload_paths(root: Path) -> List[Path]:
    result = []
    for directory in PAYLOAD_ROOTS:
        base = root / directory
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            if relative in EXCLUSIONS:
                continue
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or path.is_symlink():
                raise ValueError("payload is not a regular non-symlink file: %s" % relative)
            result.append(path)
    return sorted(result, key=lambda item: item.relative_to(root).as_posix())


def manifest_bytes(root: Path, paths: Iterable[Path]) -> bytes:
    rows = [
        "%s  %s\n" % (
            sha256_file(path),
            path.relative_to(root).as_posix(),
        )
        for path in paths
    ]
    return "".join(rows).encode("utf-8")


def atomic_write(path: Path, payload: bytes) -> None:
    descriptor, temporary = tempfile.mkstemp(
        prefix=path.name + ".",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    args = parser.parse_args()
    root = args.root.resolve()
    paths = payload_paths(root)
    payload = manifest_bytes(root, paths)
    output = root / "DATA_SHA256SUMS"
    atomic_write(output, payload)
    print(
        "WROTE DATA_SHA256SUMS records=%d bytes=%d sha256=%s" % (
            len(paths),
            len(payload),
            hashlib.sha256(payload).hexdigest(),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
