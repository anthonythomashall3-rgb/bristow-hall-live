#!/usr/bin/env python3
"""Verify, rebuild, and atomically sync the public live bundle to the site."""
from __future__ import absolute_import, print_function

import hashlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.publish_public_bundle import BUNDLE_SCHEMA, build
from live_data.rmv2_live.canonical import atomic_write


FILES = (
    "coverage.json",
    "manifest.json",
    "series_latest.json",
    "status.json",
    "summary.json",
    "pointer.json",
)
TARGET_REL = Path("live_data/public_deploy/site_target.path")


class PublishError(RuntimeError):
    pass


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _resolve_target(project_root, target):
    if target is None:
        config = project_root / TARGET_REL
        try:
            lines = [
                line.strip()
                for line in config.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            ]
        except OSError as exc:
            raise PublishError("site target file is unavailable") from exc
        if len(lines) != 1:
            raise PublishError("site target file must contain exactly one path")
        target = Path(lines[0]).expanduser()
        if not target.is_absolute():
            target = project_root / target
    # The anti-symlink guards below must be evaluated on the DECLARED path, not a
    # resolved one: Path.resolve() dereferences every component, so
    # `resolved.is_symlink()` is unconditionally False and the guard was dead
    # code. With it dead, replacing `<site>/data` with a symlink to anywhere
    # writable silently redirected the entire publish — every name check still
    # passed (name=="live", parent.name=="data", index.html found through the
    # link) and publish() reported success while the real site kept serving the
    # previous generation forever.
    declared = Path(target)
    for probe in (declared, declared.parent, declared.parent.parent):
        if probe.is_symlink():
            raise PublishError(
                "site target path contains a symlink (%s); refusing to publish" % probe
            )
    target = declared.resolve()
    if target.name != "live" or target.parent.name != "data":
        raise PublishError("site target must be an explicit data/live directory")
    if not target.is_dir() or target.is_symlink():
        raise PublishError("site data/live target must already exist and not be a symlink")
    site_root = target.parent.parent
    index = site_root / "index.html"
    if not index.is_file() or index.is_symlink():
        raise PublishError("site target has no regular index.html")
    return target


def _verified_bundle(source):
    source = Path(source).resolve()
    if not source.is_dir() or source.is_symlink():
        raise PublishError("public bundle source is unavailable")
    receipt_path = source.parents[1] / "publish_receipt.json"
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PublishError("public bundle receipt is unreadable") from exc
    if (
        receipt.get("schema_version") != BUNDLE_SCHEMA or
        receipt.get("scientific_effect") != "none" or
        set(receipt.get("files") or {}) != set(FILES)
    ):
        raise PublishError("public bundle receipt schema is invalid")

    payloads = {}
    for name in FILES:
        path = source / name
        if not path.is_file() or path.is_symlink():
            raise PublishError("public bundle receipt member is unavailable")
        data = path.read_bytes()
        declared = receipt["files"][name]
        if (
            declared.get("bytes") != len(data) or
            declared.get("sha256") != _sha256(data)
        ):
            raise PublishError("public bundle receipt does not match %s" % name)
        payloads[name] = data
    return receipt, payloads


def publish(project_root, target=None, source=None, rebuild=True):
    """Publish only a fully verified bundle into an already-identified site.

    All source members are verified before the first target write. Each target
    member is replaced atomically, and the generation pointer is written last.
    Unrelated site files are preserved.
    """
    project_root = Path(project_root).resolve()
    if rebuild:
        build(project_root)
    source = Path(
        source or (project_root / "live_data/public_deploy/data/live")
    ).resolve()
    target = _resolve_target(project_root, target)
    if source == target:
        raise PublishError("site target must differ from the bundle source")
    receipt, payloads = _verified_bundle(source)

    for name in FILES:
        atomic_write(target / name, payloads[name], mode=0o644)

    for name in FILES:
        if (target / name).read_bytes() != payloads[name]:
            raise PublishError("post-publish verification failed for %s" % name)
    return {
        "file_count": len(FILES),
        "generation_sha256": receipt["generation_sha256"],
        "published": True,
        "schema_version": "recession-monitor-v2.site-publish-receipt.v1",
        "source": str(source),
        "target": str(target),
    }


def main(argv=None):
    argv = list(argv or sys.argv[1:])
    project_root = Path(argv[0]) if argv else Path(__file__).resolve().parents[1]
    try:
        result = publish(project_root)
    except (OSError, PublishError, ValueError, KeyError) as exc:
        print("SITE PUBLISH FAILED: %s" % exc, file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
