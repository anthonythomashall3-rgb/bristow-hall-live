"""Canonical serialization, strict JSON loading, hashing, and atomic files."""

from __future__ import absolute_import

import hashlib
import json
import os
import secrets
import warnings
from datetime import datetime, timezone
from pathlib import Path


class CanonicalDataError(ValueError):
    """Raised when input cannot be represented by the canonical contract."""


def utc_now():
    """Return an RFC 3339 UTC timestamp without fractional seconds."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(data):
    if not isinstance(data, bytes):
        raise TypeError("sha256_bytes requires bytes")
    return hashlib.sha256(data).hexdigest()


def _validate_tree(value, path="$"):
    if value is None or isinstance(value, (bool, int, str)):
        return
    if isinstance(value, float):
        raise CanonicalDataError("%s contains a floating-point value" % path)
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_tree(item, "%s[%d]" % (path, index))
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalDataError("%s contains a non-string key" % path)
            _validate_tree(item, "%s.%s" % (path, key))
        return
    raise CanonicalDataError("%s contains unsupported type %s" % (path, type(value).__name__))


def canonical_json_bytes(value):
    """Serialize the strict JSON subset used by receipts and pointers."""
    _validate_tree(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def pretty_json_bytes(value):
    _validate_tree(value)
    return (json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        indent=2,
    ) + "\n").encode("utf-8")


def strict_json_loads(data):
    """Decode UTF-8 JSON while rejecting duplicates and non-finite numbers."""
    if isinstance(data, bytes):
        text = data.decode("utf-8", errors="strict")
    elif isinstance(data, str):
        text = data
    else:
        raise TypeError("strict_json_loads requires bytes or str")

    def pairs_hook(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise CanonicalDataError("duplicate JSON key: %s" % key)
            result[key] = value
        return result

    def reject_constant(token):
        raise CanonicalDataError("non-finite JSON number: %s" % token)

    value = json.loads(text, object_pairs_hook=pairs_hook, parse_constant=reject_constant)
    _validate_tree(value)
    return value


def read_json(path):
    return strict_json_loads(Path(path).read_bytes())


def atomic_write(path, data, mode=0o644):
    """Durably replace a file using a same-directory temporary file."""
    path = Path(path)
    if not isinstance(data, bytes):
        raise TypeError("atomic_write requires bytes")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.parent / (".%s.%s.tmp" % (path.name, secrets.token_hex(8)))
    descriptor = None
    try:
        descriptor = os.open(str(temp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            descriptor = None
            # os.open applies the ambient umask, so a restrictive umask would
            # silently produce a mode the immutability contract rejects.
            # fchmod is not umask-filtered, so the requested mode is exact
            # regardless of who launched this process.
            os.fchmod(handle.fileno(), mode)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(temp), str(path))
        try:
            directory_fd = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError as exc:
            # Some filesystems do not permit directory fsync. The file itself
            # was still fsynced before the atomic replace.
            warnings.warn(
                "directory fsync unavailable after atomic write: %s" % exc,
                RuntimeWarning,
            )
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            temp.unlink()
        except FileNotFoundError:
            temp = None


def atomic_write_group(items, mode=0o644):
    """Publish several files as a crash-consistent group.

    Each file is written to a fsync'd same-directory temp, then ALL temps are
    committed with back-to-back ``os.replace`` calls. This shrinks any
    cross-file inconsistency window (e.g. a JSON that records the byte count of
    a sibling CSV) from a full serialize-and-write gap down to two adjacent
    syscalls, so a killed writer cannot leave a JSON that disagrees with its
    CSV for any meaningful duration. On any error before commit, every staged
    temp is removed and no live file is touched (last-known-good preserved).
    ``items`` is an iterable of ``(path, bytes)`` pairs.
    """
    staged = []
    try:
        for path, data in items:
            path = Path(path)
            if not isinstance(data, bytes):
                raise TypeError("atomic_write_group requires bytes")
            path.parent.mkdir(parents=True, exist_ok=True)
            temp = path.parent / (".%s.%s.tmp" % (path.name, secrets.token_hex(8)))
            descriptor = os.open(str(temp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
            with os.fdopen(descriptor, "wb", closefd=True) as handle:
                os.fchmod(handle.fileno(), mode)
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            staged.append((temp, path))
        # Commit: adjacent renames only. Nothing between them can serialize,
        # allocate, or block, so an observer cannot catch a half-committed group.
        committed = list(staged)
        for temp, path in staged:
            os.replace(str(temp), str(path))
        staged = []
        for _temp, path in committed:
            try:
                directory_fd = os.open(str(path.parent), os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            except OSError as exc:
                warnings.warn(
                    "directory fsync unavailable after grouped write: %s" % exc,
                    RuntimeWarning,
                )
    finally:
        for temp, _ in staged:
            try:
                temp.unlink()
            except OSError as exc:
                warnings.warn(
                    "staged atomic-write cleanup failed for %s: %s" %
                    (temp, exc),
                    RuntimeWarning,
                )


def atomic_write_json(path, value, pretty=True):
    data = pretty_json_bytes(value) if pretty else canonical_json_bytes(value)
    atomic_write(path, data)
    return sha256_bytes(data)
