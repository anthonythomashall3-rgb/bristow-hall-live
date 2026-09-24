"""Non-destructive overlay installer for the V2 data/Cloudflare extension."""
from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

_MAPPINGS = (
    ("rmv2_extension", "tools/rmv2_data_cloudflare/rmv2_extension"),
    ("scripts", "tools/rmv2_data_cloudflare/scripts"),
    ("config", "tools/rmv2_data_cloudflare/config"),
    ("tests", "tools/rmv2_data_cloudflare/tests"),
    ("generated", "tools/rmv2_data_cloudflare/generated"),
    ("cloudflare", "cloudflare/recession-monitor-v2-data"),
    ("docs", "docs/rmv2_data_cloudflare"),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("overlay package may not contain symlinks: %s" % path)
        if path.is_file() and "__pycache__" not in path.parts and ".pytest_cache" not in path.parts:
            yield path


def _plan(package_root: Path, project_root: Path) -> List[Tuple[Path, Path]]:
    actions: List[Tuple[Path, Path]] = []
    for source_name, destination_name in _MAPPINGS:
        source_dir = package_root / source_name
        if not source_dir.exists(): continue
        for source in _files(source_dir):
            actions.append((source, project_root / destination_name / source.relative_to(source_dir)))
    return actions


def _copy_atomic(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".%s." % destination.name, suffix=".tmp", dir=str(destination.parent)); os.close(fd)
    try:
        shutil.copy2(str(source), tmp_name); os.replace(tmp_name, str(destination))
    except Exception:
        try: os.unlink(tmp_name)
        except OSError: pass
        raise


def install_overlay(package_root: Path, project_root: Path, apply: bool = False) -> Dict[str, Any]:
    package_root = Path(package_root).resolve(); project_root = Path(project_root).resolve()
    if not package_root.is_dir() or not project_root.is_dir():
        raise ValueError("package and project roots must exist")
    planned: List[str] = []; skipped: List[str] = []; to_copy: List[Tuple[Path, Path]] = []
    for source, destination in _plan(package_root, project_root):
        relative = str(destination.relative_to(project_root))
        if destination.exists():
            if destination.is_symlink() or not destination.is_file():
                raise FileExistsError("conflicting destination: %s" % destination)
            if _sha256(source) != _sha256(destination):
                raise FileExistsError("conflicting existing file: %s" % destination)
            skipped.append(relative)
        else:
            planned.append(relative); to_copy.append((source, destination))
    copied: List[str] = []
    if apply:
        for source, destination in to_copy:
            _copy_atomic(source, destination); copied.append(str(destination.relative_to(project_root)))
    return {"schema_version": "recession-monitor-v2.overlay-install.v1", "apply": bool(apply), "planned": planned, "copied": copied, "skipped_identical": skipped}
