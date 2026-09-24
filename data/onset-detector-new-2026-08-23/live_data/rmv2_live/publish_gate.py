"""Publish-side rights firewall (B-LAND-11-R2 Step 1).

The mirror of ``feed_factory._validate_family_bindings`` at the EMIT boundary.
``_validate_family_bindings`` decides whether bytes may ENTER the store; this
module decides whether stored bytes may be PUBLISHED. Internal scientific use of
licensed data is unrestricted under the owner ruling; only publication to a
public artifact (site bundle, HTTP API, content-addressed CDN bundle) is gated.

Authority:
  - ``_mailbox/answers/20260806T131145Z_B-LAND-11_FINCONDITIONS_INPUTS.md``
  - ``OWNER_RULING_20260806_RIGHTS_ALL_CHANNELS.md``

Rights class resolution is registry-derived (never a caller-supplied free-text
string — CH-R72 named that the primary bypass). A family's ``publish_class`` is
read from ``external_source_registry.csv``. Fail-closed default: an UNSET
``publish_class`` on a LICENSED family (``access_class`` C/D) resolves to
``internal_only``; a non-licensed family defaults to ``public`` so nothing
already landed changes behaviour.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

INTERNAL_ONLY = "internal_only"
PUBLIC = "public"
# B-RIGHTS-1 — OWNER_RULING_20260808_PUBLISH_ALL_GOOD_DATA.md. An explicit
# publishable class for raw licensed bytes the owner cleared for publication.
# Publishability is `!= internal_only`; this class publishes like `public`.
PUBLISH_ALL_GOOD_DATA = "publish_all_good_data"

KNOWN_PUBLISH_CLASSES = frozenset((PUBLIC, INTERNAL_ONLY, PUBLISH_ALL_GOOD_DATA))

# The 7 class-C families the ruling migrated. The ruling made the three-leg
# "good data" determination (rights-clear AND identity-certified AND
# clock-resolved-or-barred) for EXACTLY these families; the gate is fail-closed
# to this set so `publish_all_good_data` cannot silently extend to an unvetted
# family without a new owner ruling.
RULING_20260808_GOOD_DATA_FAMILIES = frozenset((
    "moody_corporate_yields", "ice_bofa_spreads", "sp_equity",
    "nasdaq_equity", "cboe_vix", "freddie_pmms", "michigan_consumers",
))

# access_class values that denote licensed / restricted families. Kept in sync
# with feed_factory._validate_family_bindings' admission block.
LICENSED_ACCESS_CLASSES = ("C", "D")


class PublishGateError(Exception):
    """Raised when a public emission would carry an internal_only series."""


def resolve_publish_class(registry_row):
    """The publication class of one registry family.

    Explicit ``publish_class`` wins. Absent, a licensed family (access_class
    C/D) fails closed to ``internal_only``; everything else is ``public``.
    """
    value = (registry_row.get("publish_class") or "").strip()
    if value:
        return value
    access_class = (registry_row.get("access_class") or "").strip()
    if access_class in LICENSED_ACCESS_CLASSES:
        return INTERNAL_ONLY
    return PUBLIC


def is_publishable_class(publish_class):
    """A class may publish iff it is not ``internal_only``.

    ``public`` and ``publish_all_good_data`` both publish (B-RIGHTS-1).
    """
    return publish_class != INTERNAL_ONLY


def assert_registry_publish_classes(registry_rows):
    """Fail-closed gate over registry publish_class values (B-RIGHTS-1).

    Every row must carry an explicit KNOWN class (no fallback resolution after
    the migration). ``publish_all_good_data`` is restricted to the ruling's
    certified 7 — the ruling made the three-leg "good data" determination for
    exactly those families, so an unlisted family carrying the class is a
    contract violation, not a publish. Raises naming the offender (§19.3).
    """
    for row in registry_rows:
        sid = row.get("source_id")
        pc = (row.get("publish_class") or "").strip()
        if not pc:
            raise PublishGateError(
                "publish_class blank on %s (B-RIGHTS-1 forbids fallback resolution)" % sid)
        if pc not in KNOWN_PUBLISH_CLASSES:
            raise PublishGateError("unknown publish_class %r on %s" % (pc, sid))
        if pc == PUBLISH_ALL_GOOD_DATA and sid not in RULING_20260808_GOOD_DATA_FAMILIES:
            raise PublishGateError(
                "family %s carries publish_all_good_data but is not in the "
                "ruling-certified set %s" % (sid, sorted(RULING_20260808_GOOD_DATA_FAMILIES)))


def _worst_class(classes):
    """The most restrictive class in an iterable. ``internal_only`` dominates;
    ``publish_all_good_data`` is preserved over ``public`` for audit fidelity.
    Both non-internal classes are publishable."""
    s = set(classes)
    if INTERNAL_ONLY in s:
        return INTERNAL_ONLY
    if PUBLISH_ALL_GOOD_DATA in s:
        return PUBLISH_ALL_GOOD_DATA
    return PUBLIC


def build_source_publish_class_map(sources, registry_by_id):
    """Map each ``source_id`` to the worst publish_class over its families.

    ``sources`` is the ``sources`` list from ``sources.v1.json``; each carries
    ``coverage_source_ids`` (registry family ids). ``registry_by_id`` maps family
    id to its registry row.
    """
    result = {}
    for source in sources:
        source_id = source.get("source_id")
        if not source_id:
            continue
        families = source.get("coverage_source_ids") or []
        classes = []
        for family_id in families:
            row = registry_by_id.get(family_id)
            if row is None:
                # An unknown family reference is a data-integrity issue, not a
                # licensing signal; treat as public (no regression) — admission
                # already refuses sources whose families are absent.
                classes.append(PUBLIC)
            else:
                classes.append(resolve_publish_class(row))
        result[source_id] = _worst_class(classes) if classes else PUBLIC
    return result


_REGISTRY_RELPATH = ("data_vault", "catalog", "external_source_registry.csv")
_SOURCES_RELPATH = ("live_data", "config", "sources.v1.json")


def discover_project_root(start):
    """Walk up from ``start`` to the directory holding the production registry.

    Returns the project root ``Path`` or ``None`` if no ancestor carries
    ``data_vault/catalog/external_source_registry.csv`` (e.g. a synthetic test
    tree). Lets the publish gate locate the registry regardless of whether the
    public root is ``<root>/public`` or ``<root>/live_data/public``.
    """
    current = Path(start).resolve()
    for candidate in (current, *current.parents):
        if (candidate.joinpath(*_REGISTRY_RELPATH)).is_file():
            return candidate
    return None


def load_source_publish_class_map(project_root):
    """Read registry + sources config and build the class map.

    Fail-safe for the P2 defense-in-depth layer: if the production registry or
    sources config is absent (a synthetic tree that never lands licensed data),
    return an empty map so no filtering occurs. The AUTHORITATIVE gates —
    admission (feed_factory) and the P1 bundle writer, which always run from the
    real project root — are unaffected by this fallback.
    """
    project_root = Path(project_root)
    registry_path = project_root.joinpath(*_REGISTRY_RELPATH)
    sources_path = project_root.joinpath(*_SOURCES_RELPATH)
    if not registry_path.is_file() or not sources_path.is_file():
        return {}
    with io.StringIO(
        registry_path.read_text(encoding="utf-8"), newline=""
    ) as handle:
        registry_by_id = {
            row["source_id"]: row for row in csv.DictReader(handle)
        }
    sources = json.loads(sources_path.read_text(encoding="utf-8")).get("sources", [])
    return build_source_publish_class_map(sources, registry_by_id)


def assert_series_publishable(series, source_publish_class_map):
    """Refuse to publish if any series belongs to an internal_only source.

    ``series`` is an iterable of dicts each carrying ``series_id`` and
    ``source_id``. Raises ``PublishGateError`` naming every offending series.
    """
    offenders = []
    for item in series:
        source_id = item.get("source_id")
        publish_class = source_publish_class_map.get(source_id, PUBLIC)
        if publish_class == INTERNAL_ONLY:
            offenders.append((item.get("series_id"), source_id))
    if offenders:
        listed = ", ".join(
            "%s(%s)" % (series_id, source_id) for series_id, source_id in offenders
        )
        raise PublishGateError(
            "refusing to publish internal_only series: %s" % listed
        )


def series_item_is_publishable(item, source_publish_class_map):
    """Whether one snapshot series item may be served on a public route."""
    source_id = (item or {}).get("source_id")
    return source_publish_class_map.get(source_id, PUBLIC) != INTERNAL_ONLY


def filter_snapshot_series(snapshot, source_publish_class_map):
    """Return a copy of a snapshot with internal_only series removed.

    Used by the public HTTP API (P2) so ``/snapshot``, ``/latest`` and
    ``/series/<id>`` never serve raw values or observation histories of a
    licensed family. The input snapshot is not mutated.
    """
    series = snapshot.get("series") or {}
    kept = {
        series_id: item
        for series_id, item in series.items()
        if series_item_is_publishable(item, source_publish_class_map)
    }
    filtered = dict(snapshot)
    filtered["series"] = kept
    return filtered


def aggregate_is_publishable(member_publish_classes):
    """Whether a derived aggregate over the given members may be published.

    Per the owner ruling and CH-R72's recoverability rule: an aggregate that
    contains a licensed (internal_only) member is publishable only when at least
    two distinct non-licensed members co-populate the aggregation cell, so the
    licensed leg is not algebraically recoverable from the published value.
    """
    classes = list(member_publish_classes)
    if INTERNAL_ONLY not in classes:
        return True
    non_licensed = [c for c in classes if c != INTERNAL_ONLY]
    return len(non_licensed) >= 2
