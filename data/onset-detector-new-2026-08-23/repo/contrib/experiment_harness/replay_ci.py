"""Replay-CI prototype (B-EXP-0 deliverable 4 / improvement 49).

Picks a random past date, replays the pipeline as-of that date, and asserts the replayed
artifact is BYTE-IDENTICAL to the published one. This is a prototype: it is wired to
NOTHING yet. ``replay_fn`` and ``publish_fn`` are injected; their defaults raise
NotImplementedError so an unwired run fails loudly instead of silently "passing" a
comparison against nothing. Adopting this into the nightly is a later owner-approved batch.

Byte-identity uses canonical JSON (sorted keys, compact separators) so the check is stable
across dict ordering — matching how the vault's own byte-identical assertions are framed
(A2 items 25.1 / 48: same payload + same template => byte-identical).
"""
import datetime as dt
import hashlib
import json


def select_replay_date(rng, min_date, today):
    """Pick a random past date in ``[min_date, today)`` using the supplied ``random.Random``
    (seedable for reproducibility — no import-time RNG)."""
    span = (today - min_date).days
    if span <= 0:
        raise ValueError("min_date must be before today")
    return min_date + dt.timedelta(days=rng.randrange(span))


def canonicalize(obj):
    """Canonical JSON bytes: sorted keys, compact separators, UTF-8."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def compare_replay(replayed, published):
    """Compare two artifacts for byte-identity via canonical JSON hashing."""
    rb, pb = canonicalize(replayed), canonicalize(published)
    return {
        "byte_identical": rb == pb,
        "replay_sha256": _sha(rb),
        "published_sha256": _sha(pb),
    }


def _unwired(_date):
    raise NotImplementedError(
        "replay_ci is a prototype wired to NOTHING; supply replay_fn and publish_fn "
        "explicitly. Nightly adoption is a later owner-approved batch."
    )


def run_replay_ci(asof, replay_fn=_unwired, publish_fn=_unwired):
    """Replay as-of ``asof`` and compare to the published artifact for the same date.

    Both hooks are injected; the defaults raise so nothing is asserted against a missing
    pipeline. Returns the comparison report augmented with the as-of date.
    """
    replayed = replay_fn(asof)
    published = publish_fn(asof)
    report = compare_replay(replayed, published)
    report["asof"] = str(asof)
    return report
