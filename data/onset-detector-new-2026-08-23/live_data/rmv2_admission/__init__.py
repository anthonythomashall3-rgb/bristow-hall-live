"""Deterministic, AI-free admission runner for Recession Monitor V2.

This package drains an immutable, reviewed approved-draft queue through the
mandatory admission cadence (quiesce agents -> per-draft prepare/apply/targeted
refresh in batches of at most five -> verify -> public bundle regeneration ->
key-leak scan -> relaunch agents), with a hard stop to a green store on any
failed check, an append-only journal, and a dedicated single-writer lock. It
never binds any scientific model, never reads a secret value, and only quiesces
the launchd agents when the live-data publication barrier is provably free.
"""

from __future__ import absolute_import
