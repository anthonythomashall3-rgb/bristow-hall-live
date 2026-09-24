"""Real-time candidate registry intake validator (B-INTAKE-RT-1).

Schema-checks entries from ``research/rt_expansion/registry.v1.json`` against the
CH-R74 / CH-R74-B cross-check verdicts, rejects the fenced duplicates, and
mechanically renders schema-conformant planned-source RESERVATION drafts
(``enabled: false``, ``parser_version: None``).

A reservation is not acquisition and not admission. A reservation whose
``coverage_source_family_ids`` is not yet a registered source family cannot be
written to ``live_data/config/planned_sources.v1.json`` without first admitting
that family into ``data_vault/catalog/external_source_registry.csv`` (the
registered-family-subset invariant, tests/test_rmv2_source_matrix.py). Rendering
a draft here does not admit anything; it only shows what a reservation would be.
"""

from __future__ import absolute_import

from collections import Counter

# Byte-for-byte the reservation schema enforced by
# tests/test_rmv2_source_matrix.py :: PLANNED_SOURCE_FIELDS.
PLANNED_SOURCE_FIELDS = (
    "source_id",
    "registry_status",
    "enabled",
    "publisher",
    "endpoint",
    "endpoint_status",
    "auth_env",
    "cadence",
    "release_timezone",
    "release_clock",
    "observation_period",
    "revision_policy",
    "rights",
    "parser_version",
    "role",
    "clock_notes",
    "split_or_bias_guard",
    "coverage_source_family_ids",
)

# Fields every registry entry must carry to be reservable. If a field the
# reservation binds is absent, the entry is rejected rather than defaulted.
RESERVATION_REQUIRED_ENTRY_FIELDS = (
    "name",
    "publisher",
    "url",
    "cadence",
    "publication_lag",
    "real_time_class",
    "rights_class",
    "rights_evidence",
    "alive_evidence",
    "information_set_modes",
    "access_method",
    "endpoint_hint",
    "revision_policy_claim",
    "domain",
    "candidate_id",
)

_DUPE_PREFIX = "DUPE"
_COMPARATOR_DOMAIN = "nowcasts_composites"

# Rights-class → the auth env var the reservation would bind, when keyed.
_RIGHTS_TO_AUTH_ENV = {
    "free_registration_key": None,  # key identity resolved at enable time.
}


class IntakeRejection(Exception):
    """Raised for structural intake faults (e.g. duplicate candidate ids)."""


class _Verdict(object):
    __slots__ = ("accepted", "reason_code", "detail", "dedup_verdict")

    def __init__(self, accepted, reason_code, detail, dedup_verdict):
        self.accepted = accepted
        self.reason_code = reason_code
        self.detail = detail
        self.dedup_verdict = dedup_verdict


class IntakeResult(object):
    def __init__(self, reservations, rejections, counts):
        self.reservations = reservations
        self.rejections = rejections
        self.counts = counts


def classify_entry(entry, dedup_by_candidate):
    """Accept or reject one entry against its cross-check dedup verdict.

    ``dedup_by_candidate`` maps candidate_id -> dedup verdict string.
    """
    candidate_id = entry.get("candidate_id")
    if candidate_id not in dedup_by_candidate:
        return _Verdict(False, "UNXCHECKED",
                        "candidate_id not in cross-check map", None)

    dedup = dedup_by_candidate[candidate_id]
    if dedup.startswith(_DUPE_PREFIX):
        return _Verdict(False, "DUPE", dedup, dedup)

    missing = [f for f in RESERVATION_REQUIRED_ENTRY_FIELDS
               if not entry.get(f)]
    if missing:
        return _Verdict(False, "MISSING_FIELD",
                        ", ".join(missing), dedup)

    return _Verdict(True, None, None, dedup)


def _role_and_guard(entry, eligible):
    domain = entry.get("domain")
    hypothesis = entry.get("value_hypothesis") or ""
    if domain == _COMPARATOR_DOMAIN:
        guard = (
            "External comparator only: never a construction input. Firewall "
            "note - target-trained/nowcast comparator values must never enter "
            "the Stress Unit, National Index, or any factor model as an input; "
            "publish only as an external yardstick with attribution."
        )
        return "external_comparator", guard
    guard = (
        "Reservation only; concept, publisher, design, and vintage boundaries "
        "must stay explicit at enable time. No silent splice, relabel, "
        "interpolation, or promotion. " + (hypothesis[:200] if hypothesis else "")
    ).strip()
    return "input_candidate", guard


def reservation_draft(entry, dedup_verdict, eligible, flagged_rights):
    """Render one schema-conformant planned-source reservation draft."""
    candidate_id = entry["candidate_id"]
    role, guard = _role_and_guard(entry, eligible)

    if flagged_rights:
        registry_status = "RESERVED_LOWER_PRIORITY_NOT_ENABLED"
    elif entry.get("rights_class") == "free_registration_key":
        registry_status = "RESERVED_CREDENTIAL_BOUND_NOT_ENABLED"
    else:
        registry_status = "RESERVED_NOT_ENABLED"

    draft = {
        "source_id": candidate_id,
        "registry_status": registry_status,
        "enabled": False,
        "publisher": entry.get("publisher", ""),
        "endpoint": entry.get("endpoint_hint") or entry.get("url", ""),
        "endpoint_status": "CANDIDATE_UNVERIFIED_ROUTE",
        "auth_env": _RIGHTS_TO_AUTH_ENV.get(entry.get("rights_class")),
        "cadence": entry.get("cadence", ""),
        "release_timezone": "UNKNOWN_TO_BE_RESOLVED_AT_ENABLE",
        "release_clock": entry.get("publication_lag", ""),
        "observation_period": entry.get("latest_observation_seen", ""),
        "revision_policy": entry.get("revision_policy_claim", ""),
        "rights": entry.get("rights_class", ""),
        "parser_version": None,
        "role": role,
        "clock_notes": (
            "preserve published timezone, available_at, and retrieved_at "
            "separately; release clock unverified until dry-run"
        ),
        "split_or_bias_guard": guard,
        "coverage_source_family_ids": [candidate_id],
    }
    # Guarantee field order matches the enforced schema exactly.
    return {field: draft[field] for field in PLANNED_SOURCE_FIELDS}


def run_intake(entries, verdict_map):
    """Partition entries into reservations vs rejections; return counts.

    ``verdict_map`` maps candidate_id -> {dedup, eligible, flagged}.
    """
    seen = Counter(e.get("candidate_id") for e in entries)
    dups = [cid for cid, n in seen.items() if n > 1]
    if dups:
        raise IntakeRejection("duplicate candidate_ids: %r" % (sorted(dups),))

    dedup_by_candidate = {
        cid: v["dedup"] for cid, v in verdict_map.items()
    }

    reservations = []
    rejections = []
    counts = Counter()
    for entry in entries:
        verdict = classify_entry(entry, dedup_by_candidate)
        if not verdict.accepted:
            rejections.append((entry.get("candidate_id"), verdict.reason_code,
                               verdict.detail))
            if verdict.reason_code == "DUPE":
                counts["rejected_dupe"] += 1
            elif verdict.reason_code == "MISSING_FIELD":
                counts["rejected_missing_field"] += 1
            else:
                counts["rejected_unxchecked"] += 1
            continue
        meta = verdict_map[entry["candidate_id"]]
        reservations.append(reservation_draft(
            entry,
            dedup_verdict=verdict.dedup_verdict,
            eligible=meta["eligible"],
            flagged_rights=meta["flagged"],
        ))
        counts["reserved"] += 1

    return IntakeResult(reservations, rejections, counts)
