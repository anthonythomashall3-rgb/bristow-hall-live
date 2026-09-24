"""BATCH RTDSM-1 tests.

Covers:
- §1.2 credential leak guard: the resolution/report path must never emit the
  32-char FRED key (or any 32-char alphanumeric token) to any captured output.
- §6 RED test for the RTDSM xlsx parser shape (added once the measured shape is
  known; written failing-first before the parser exists).
"""
from __future__ import annotations

import io
import re
import contextlib

import pytest

from rmv2_connectors import engine

# A FRED key is 32 lowercase alphanumerics. Guard on any 32+ run of [A-Za-z0-9].
TOKEN_RE = re.compile(r"[A-Za-z0-9]{32,}")


# ---------------------------------------------------------------- §1.2 leak guard

def test_credential_source_never_returns_value():
    """_credential_source reports only a source label, never the secret."""
    via = engine._credential_source("FRED_API_KEY")
    assert via in {"env", "local_env", "keychain", "none"}
    assert not TOKEN_RE.search(via)


def test_credential_report_emits_no_token():
    """Capturing all stdout/stderr of the report path yields no 32-char token."""
    buf_out, buf_err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
        via = engine._credential_source("FRED_API_KEY")
        resolved = bool(engine._read_credential("FRED_API_KEY"))
        # what the batch is permitted to print:
        print({"resolved": resolved, "via": via})
    captured = buf_out.getvalue() + buf_err.getvalue()
    leaks = TOKEN_RE.findall(captured)
    assert not leaks, f"credential material leaked to output: {leaks!r}"


def test_read_credential_value_not_in_repr_paths():
    """The resolved value, if present, must not equal its own source label and
    must not be emitted by the reporting helpers."""
    val = engine._read_credential("FRED_API_KEY")
    if val:  # only meaningful when a key is configured
        assert engine._credential_source("FRED_API_KEY") != val
        assert val not in repr({"via": engine._credential_source("FRED_API_KEY")})
