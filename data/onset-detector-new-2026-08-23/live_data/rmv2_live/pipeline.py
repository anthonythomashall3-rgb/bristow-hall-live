"""End-to-end publisher acquisition, normalization, and atomic publication."""

from __future__ import absolute_import

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .adapters import PublisherHttpClient, SourceBlocked, SourceUnavailable, normalize
from .canonical import (
    CanonicalDataError,
    atomic_write_json,
    canonical_json_bytes,
    read_json,
    sha256_bytes,
    utc_now,
)
from .matrix import build_source_matrix, write_source_matrix
from .store import (
    SHA256_RE,
    LiveStore,
    generation_storage_fingerprint,
    read_verified_generation,
    safe_regular_file,
    source_binding_from_head,
    validate_source_binding,
)


SNAPSHOT_MATERIALIZER_VERSION = "source_policy.v2"


def _project_source_snapshot(
    source_id, binding, records, projection_policy="latest_only.v1"
):
    """Project one source's snapshot contribution — pure and deterministic.

    Returns ``{"binding", "record_count", "series"}`` where ``series`` maps each
    series_id to the ``latest_admissible_observation_only`` entry.  This is the
    exact per-source reduction the full rebuild performs inline; factoring it out
    lets the content-addressed projection cache reuse it byte-for-byte.  Cross-
    source series-id collision is enforced by the caller at assembly (a series_id
    is owned by exactly one source); this function only reduces within one source.
    """
    if projection_policy == "archival_panel.v1":
        seen = set()
        units = {}
        for record in records:
            forecaster_id = record.get("spf_forecaster_id")
            industry = record.get("spf_industry")
            horizon = record.get("spf_horizon")
            if (
                not isinstance(forecaster_id, int) or
                isinstance(forecaster_id, bool) or
                (industry is not None and (
                    not isinstance(industry, int) or
                    isinstance(industry, bool)
                )) or
                not isinstance(horizon, str) or
                not horizon or
                record.get("observation_period") is None
            ):
                raise CanonicalDataError(
                    "archival panel record dimensions are invalid"
                )
            series_id = record["series_id"]
            prior_unit = units.setdefault(series_id, record["unit"])
            if prior_unit != record["unit"]:
                raise CanonicalDataError(
                    "snapshot series unit changed within one source"
                )
            key = (
                series_id,
                record["observation_period"],
                forecaster_id,
                industry,
            )
            if key in seen:
                raise CanonicalDataError(
                    "archival panel has duplicate dimension keys"
                )
            seen.add(key)
        return {
            "binding": binding,
            "record_count": len(records),
            "series": {},
        }
    if projection_policy == "greenbook_vintage_panel.v1":
        # Greenbook Row Format is inherently multi-vintage: each observation_period
        # recurs across many GBdate meeting vintages (and, for the projection half,
        # many forecast horizons). Keep it as archival multi-key EVIDENCE excluded
        # from the flat latest-per-(series,period) snapshot (B-ACQ-GREENBOOK; the
        # archival_panel.v1 pattern from B-LAND-8-R3, keyed on greenbook_vintage
        # instead of the SPF forecaster dimensions).
        seen = set()
        units = {}
        for record in records:
            vintage = record.get("greenbook_vintage")
            horizon = record.get("forecast_horizon")
            if (
                not isinstance(vintage, str) or
                not vintage or
                record.get("observation_period") is None or
                (horizon is not None and (
                    not isinstance(horizon, int) or
                    isinstance(horizon, bool)
                ))
            ):
                raise CanonicalDataError(
                    "greenbook vintage panel record dimensions are invalid"
                )
            series_id = record["series_id"]
            prior_unit = units.setdefault(series_id, record["unit"])
            if prior_unit != record["unit"]:
                raise CanonicalDataError(
                    "snapshot series unit changed within one source"
                )
            key = (
                series_id,
                record["observation_period"],
                vintage,
                horizon,
            )
            if key in seen:
                raise CanonicalDataError(
                    "greenbook vintage panel has duplicate dimension keys"
                )
            seen.add(key)
        return {
            "binding": binding,
            "record_count": len(records),
            "series": {},
        }
    if projection_policy != "latest_only.v1":
        raise CanonicalDataError("snapshot projection policy is invalid")

    series = {}
    for record in records:
        series_id = record["series_id"]
        item = series.get(series_id)
        if item is None:
            series[series_id] = {
                "latest": record,
                "observations": [],
                "series_id": series_id,
                "source_id": source_id,
                "unit": record["unit"],
            }
            continue
        if item["unit"] != record["unit"]:
            raise CanonicalDataError(
                "snapshot series unit changed within one source"
            )
        current = item["latest"]
        current_key = (
            current["observation_period"] is not None,
            current["observation_period"] or "",
        )
        candidate_key = (
            record["observation_period"] is not None,
            record["observation_period"] or "",
        )
        if candidate_key == current_key:
            raise CanonicalDataError(
                "snapshot series has duplicate observation periods"
            )
        if candidate_key > current_key:
            item["latest"] = record
    for item in series.values():
        item["observations"] = [item["latest"]]
    return {
        "binding": binding,
        "record_count": len(records),
        "series": series,
    }


def _atomic_bundle_groups(config):
    source_ids = {source["source_id"] for source in config["sources"]}
    groups = {}
    for source in config["sources"]:
        series = source.get("series")
        if not isinstance(series, dict) or "atomic_bundle_id" not in series:
            continue
        bundle_id = series["atomic_bundle_id"]
        members = series.get("atomic_bundle_members")
        if (
            not isinstance(bundle_id, str) or
            not bundle_id or
            not isinstance(members, list) or
            len(members) < 2 or
            any(not isinstance(member, str) or not member for member in members) or
            len(members) != len(set(members)) or
            source["source_id"] not in members or
            not set(members).issubset(source_ids)
        ):
            raise CanonicalDataError("atomic source-bundle metadata was invalid")
        prior = groups.setdefault(bundle_id, tuple(members))
        if prior != tuple(members):
            raise CanonicalDataError("atomic source-bundle members differed")
    for bundle_id, members in groups.items():
        declared = {
            source["source_id"]
            for source in config["sources"]
            if (
                isinstance(source.get("series"), dict) and
                source["series"].get("atomic_bundle_id") == bundle_id
            )
        }
        if declared != set(members):
            raise CanonicalDataError("atomic source-bundle exact set differed")
    return groups


def _validate_selected_atomic_bundles(config, selected):
    """Reject commands that request only part of an atomic publisher bundle."""
    if not selected:
        return
    for bundle_id, members in _atomic_bundle_groups(config).items():
        overlap = set(members).intersection(selected)
        if overlap and overlap != set(members):
            raise ValueError(
                "atomic source bundle %s requires exact members %r" %
                (bundle_id, list(members))
            )


def _parse_timestamp(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


RELEASE_CALENDAR_SCHEMA = "recession-monitor-v2.release-calendar.v1"


def load_release_calendar(project_root):
    """Load release_calendar.v1.json's per-source map, or ``{}`` if absent.

    The calendar is advisory scheduling metadata, never a scientific input. When
    it is missing (tests, fresh checkouts) the scheduler degrades to the pre-
    existing fixed-interval poll_seconds gating — identical behaviour.
    """
    path = Path(project_root) / "live_data" / "config" / "release_calendar.v1.json"
    if not path.exists():
        return {}
    try:
        doc = read_json(path)
    except Exception:
        return {}
    if not isinstance(doc, dict) or doc.get("schema_version") != RELEASE_CALENDAR_SCHEMA:
        return {}
    sources = doc.get("sources")
    return sources if isinstance(sources, dict) else {}


CONDITIONAL_HTTP_SCHEMA = "recession-monitor-v2.conditional-http.v1"


def load_conditional_http_policy(project_root):
    """Load conditional_http.v1.json, or ``None`` if absent (R1A section 4).

    When present it gates If-Modified-Since / If-None-Match to sources MEASURED to
    honor HTTP 304 (positive allowlist). When absent the pipeline keeps its prior
    behaviour -- send a conditional header whenever a validator is stored -- so
    tests and fresh checkouts are unaffected.
    """
    path = Path(project_root) / "live_data" / "config" / "conditional_http.v1.json"
    if not path.exists():
        return None
    try:
        doc = read_json(path)
    except Exception:
        return None
    if not isinstance(doc, dict) or doc.get("schema_version") != CONDITIONAL_HTTP_SCHEMA:
        return None
    honors = doc.get("honors_304", {})
    return {
        "adapters": set(honors.get("adapters", [])),
        "source_ids": set(honors.get("source_ids", [])),
    }


def _release_boundary(entry, now):
    """Most recent expected-release instant at or before ``now`` (or ``None``).

    Rolls the calendar's ``next_expected_release_utc`` forward/backward by the
    modal ``cadence_gap_days`` so the boundary tracks real time without the
    static file having to be regenerated. Returns ``None`` when the source has no
    derivable release schedule (confidence "unknown") — the caller then falls
    back to the fixed interval. No schedule is invented here; if the calendar did
    not derive a next release, this yields nothing.
    """
    iso = entry.get("next_expected_release_utc")
    gap = entry.get("cadence_gap_days")
    base = _parse_timestamp(iso) if iso else None
    if base is None or not gap:
        return None
    step = timedelta(days=gap)
    boundary = base
    while boundary + step <= now:
        boundary += step
    while boundary > now:
        boundary -= step
    return boundary


class RefreshPipeline(object):
    def __init__(self, project_root, config, http_client=None, clock=None):
        self.project_root = Path(project_root).resolve()
        self.config = config
        self.store = LiveStore(self.project_root, config)
        self.http_client = http_client or PublisherHttpClient()
        self.clock = clock or utc_now
        self._generation_binding_cache = None
        self.release_calendar = load_release_calendar(self.project_root)
        self.conditional_http_policy = load_conditional_http_policy(self.project_root)

    def _send_conditional(self, source):
        """Whether to send If-Modified-Since / If-None-Match for this source.

        No policy loaded -> prior behaviour (send when a validator is stored).
        Policy loaded -> only sources measured to honor HTTP 304 (R1A section 4)."""
        policy = self.conditional_http_policy
        if policy is None:
            return True
        return (source["adapter"] in policy["adapters"]
                or source["source_id"] in policy["source_ids"])

    def _is_due(self, source, status, now):
        if not status or not status.get("attempted_at"):
            return True
        attempted = _parse_timestamp(status["attempted_at"])
        if attempted is None:
            return True
        # A failed/blocked poll always earns a fast fixed retry, independent of
        # the release calendar — a transient publisher flake near a release must
        # not be pinned "not due" until the next release boundary.
        if status.get("outcome") in ("blocked", "failed"):
            return (now - attempted).total_seconds() >= min(source["poll_seconds"], 300)
        # Release-calendar gating: for a source with a derived next release, poll
        # only once that release boundary has passed and we have not yet polled
        # for it. Idle windows before the next release poll nothing.
        entry = self.release_calendar.get(source["source_id"])
        if entry is not None:
            boundary = _release_boundary(entry, now)
            if boundary is not None:
                return attempted < boundary
        # Fallback (confidence "unknown", no calendar, or no derived release):
        # the pre-existing fixed-interval poll_seconds gate.
        return (now - attempted).total_seconds() >= source["poll_seconds"]

    def _source_by_id(self):
        return {source["source_id"]: source for source in self.config["sources"]}

    def _current_generation_binding(self):
        pointer_path = self.store.public / "latest.pointer.json"
        if not pointer_path.exists():
            self._generation_binding_cache = None
            return None, None, {}
        pointer_bytes = safe_regular_file(pointer_path, self.store.public)
        if (
            self._generation_binding_cache is not None and
            self._generation_binding_cache["pointer_bytes"] == pointer_bytes
        ):
            current_fingerprint = generation_storage_fingerprint(
                self.store.public,
                self.store.root / "generations",
                self._generation_binding_cache["pointer"],
                self._generation_binding_cache["source_bindings"],
            )
            if (
                current_fingerprint ==
                self._generation_binding_cache["storage_fingerprint"]
            ):
                return self._generation_binding_cache["binding"]
        generation = read_verified_generation(
            self.store.public,
            self.store.root / "generations",
            materialize_members=("snapshot.json", "status.json"),
            attest_bindings=True,
        )
        status = generation["members"]["status.json"]
        if status.get("schema_version") != "recession-monitor-v2.live-status.v1":
            raise CanonicalDataError("public generation status schema is invalid")
        snapshot = generation["members"]["snapshot.json"]
        source_bindings = {
            source["source_id"]: validate_source_binding(source)
            for source in snapshot["sources"]
        }
        binding = (
            generation["pointer"],
            status,
            source_bindings,
        )
        self._generation_binding_cache = {
            "binding": binding,
            "pointer": generation["pointer"],
            "pointer_bytes": pointer_bytes,
            "source_bindings": generation["source_bindings"],
            "storage_fingerprint": generation["storage_fingerprint"],
        }
        return binding

    @staticmethod
    def _latest_attempt_counts(outcomes):
        state_counts = {}
        for outcome in outcomes:
            key = outcome["outcome"]
            state_counts[key] = state_counts.get(key, 0) + 1
        return state_counts

    def _runtime_head_receipt_map(self, heads=None):
        heads = heads if heads is not None else self.store.all_source_heads()
        result = {}
        for source_id, head in sorted(heads.items()):
            if not isinstance(head, dict) or head.get("source_id") != source_id:
                raise CanonicalDataError("runtime source head identity is invalid")
            receipt_sha256 = head.get("receipt_sha256")
            if (
                not isinstance(receipt_sha256, str) or
                not SHA256_RE.match(receipt_sha256)
            ):
                raise CanonicalDataError(
                    "runtime source head receipt identity is invalid"
                )
            result[source_id] = receipt_sha256
        return result

    def _runtime_head_binding_map(self, heads=None):
        heads = heads if heads is not None else self.store.all_source_heads()
        return {
            source_id: source_binding_from_head(source_id, head)
            for source_id, head in sorted(heads.items())
        }

    def _active_generation_light(self):
        """Read the active generation's pointer, status, and bound head-receipt
        map from the committed files WITHOUT re-verifying store content.

        Cheap: three small JSON reads and no O(store) hashing — unlike
        ``_current_generation_binding`` which re-authenticates the whole closure
        (``read_verified_generation`` / ``generation_storage_fingerprint``). This
        is exactly the incremental signal the idle-tick fast-exit needs: has any
        source head's receipt moved off what the active generation bound? Full
        closure re-verification stays in ``verify --full``. Returns
        ``(pointer, status, head_receipt_map)`` or ``(None, None, None)``.
        """
        pointer_path = self.store.public / "latest.pointer.json"
        if not pointer_path.exists():
            return None, None, None
        try:
            pointer = read_json(pointer_path)
            gen_dir = (
                self.store.root / "generations" / pointer["generation_sha256"]
            )
            manifest = read_json(gen_dir / "manifest.json")
            status = read_json(gen_dir / "status.json")
        except (FileNotFoundError, KeyError, CanonicalDataError):
            return None, None, None
        return pointer, status, manifest.get("source_head_receipt_sha256")

    def _current_source_health(self):
        statuses = self.store.all_source_statuses()
        heads = self.store.all_source_heads()
        health = {}
        for source in sorted(
            self.config["sources"],
            key=lambda item: item["source_id"],
        ):
            source_id = source["source_id"]
            if source.get("archival"):
                # Frozen-admission deep-vintage rows: bound = archival_static
                # (healthy, never refreshed); unbound (no head) is still a defect.
                head = heads.get(source_id)
                health[source_id] = (
                    "archival_static" if head is not None else "archival_unbound"
                )
                continue
            if not source["enabled"]:
                health[source_id] = "disabled"
                continue
            status = statuses.get(source_id)
            head = heads.get(source_id)
            outcome = status.get("outcome") if isinstance(status, dict) else None
            if outcome in ("blocked", "failed"):
                health[source_id] = outcome
            elif head is None:
                health[source_id] = "awaiting_first_success"
            elif outcome in ("success", "unchanged"):
                health[source_id] = "healthy"
            else:
                health[source_id] = "recovery_pending"
        counts = {}
        for state in health.values():
            counts[state] = counts.get(state, 0) + 1
        return health, counts

    @staticmethod
    def _service_state(
        active_generation_available,
        current_source_health,
        generation_recovery_required,
    ):
        if not active_generation_available:
            return "awaiting_first_success"
        unhealthy = {
            state
            for state in current_source_health.values()
            if state not in ("disabled", "healthy", "archival_static")
        }
        if generation_recovery_required or unhealthy:
            return "degraded"
        return "ready"

    def _operational_status(
        self,
        status,
        pointer,
        generated_at,
        outcomes,
        generation_recovery_required=False,
    ):
        latest_attempt_counts = self._latest_attempt_counts(outcomes)
        current_source_health, current_source_health_counts = (
            self._current_source_health()
        )
        operational = dict(status)
        operational["active_generation_sha256"] = (
            pointer["generation_sha256"] if pointer is not None else None
        )
        operational["current_source_health"] = current_source_health
        operational[
            "current_source_health_counts"
        ] = current_source_health_counts
        operational["generated_at"] = generated_at
        operational["generation_advanced"] = False
        operational["generation_advance_reasons"] = []
        operational[
            "generation_recovery_required"
        ] = generation_recovery_required
        operational["latest_attempt_counts"] = latest_attempt_counts
        operational["last_refresh_outcomes"] = outcomes
        operational[
            "last_refresh_state_counts"
        ] = latest_attempt_counts
        operational["service_state"] = self._service_state(
            pointer is not None,
            current_source_health,
            generation_recovery_required,
        )
        operational[
            "schema_version"
        ] = "recession-monitor-v2.live-operational-status.v1"
        return operational

    def _validate_generation_recovery_heads(
        self,
        runtime_heads,
    ):
        # Enabled live collectors PLUS archival (frozen-admission) rows: an
        # archival deep-vintage head is config-known to the runtime even though
        # the resident service never fetches it (archival ⇒ enabled:false).
        expected_ids = {
            source["source_id"]
            for source in self.config["sources"]
            if source["enabled"] or source.get("archival")
        }
        if set(runtime_heads) != expected_ids:
            raise CanonicalDataError(
                "runtime source heads do not match enabled source exact set"
            )
        source_map = self._source_by_id()
        for source_id, head in sorted(runtime_heads.items()):
            if (
                head.get("adapter") != source_map[source_id]["adapter"] or
                head.get("method_version") !=
                source_map[source_id]["method_version"]
            ):
                raise CanonicalDataError(
                    "recovery source head parser identity is stale"
                )
            # Recovery runs on the hot divergence path (including first-tick
            # rebind of transient-diverged heads); attest against the content-
            # addressed evidence instead of re-reading multi-GB normalized blobs.
            self.store.attest_source_head(source_id, head)

    def refresh(self, source_ids=None, due_only=False):
        selected = set(source_ids or [])
        source_map = self._source_by_id()
        unknown = sorted(selected - set(source_map))
        if unknown:
            raise ValueError("unknown source ids: %r" % unknown)
        _validate_selected_atomic_bundles(self.config, selected)
        self.store.initialize()
        with self.store.refresh_lock():
            attempted_at = self.clock()
            now = _parse_timestamp(attempted_at) or datetime.now(timezone.utc)
            bundle_groups = _atomic_bundle_groups(self.config)
            bundle_membership = {
                source_id: bundle_id
                for bundle_id, members in bundle_groups.items()
                for source_id in members
            }
            due_bundle_members = set()
            if due_only:
                for members in bundle_groups.values():
                    if selected and not set(members).intersection(selected):
                        continue
                    if any(
                        self._is_due(
                            source_map[source_id],
                            self.store.read_source_status(source_id),
                            now,
                        )
                        for source_id in members
                    ):
                        due_bundle_members.update(members)
            outcomes = []
            for source in self.config["sources"]:
                source_id = source["source_id"]
                if selected and source_id not in selected:
                    continue
                if not source["enabled"]:
                    outcomes.append({
                        "outcome": "disabled",
                        "source_id": source_id,
                    })
                    continue
                prior_status = self.store.read_source_status(source_id)
                if (
                    due_only and
                    source_id in bundle_membership and
                    source_id not in due_bundle_members
                ):
                    outcomes.append({
                        "outcome": "not_due",
                        "source_id": source_id,
                    })
                    continue
                if (
                    due_only and
                    source_id not in bundle_membership and
                    not self._is_due(source, prior_status, now)
                ):
                    outcomes.append({
                        "outcome": "not_due",
                        "source_id": source_id,
                    })
                    continue
                outcomes.append(self._refresh_source(source, attempted_at))

            # Idle-tick fast exit (guarded). Under due_only, if the release
            # calendar / poll gate left EVERY source not-due, nothing was
            # acquired, so nothing can have changed. We may then skip the
            # O(sources) coverage + source-matrix rebuild (minutes at this store
            # size) that otherwise runs on every tick — BUT only when the full
            # path would not publish anyway: the active generation must already
            # exist, be v2, carry the current materializer, and bind the current
            # runtime source heads (no crash-stranded divergence). When any of
            # those fail we fall through to the full path so a stranded head is
            # still recovered/republished on this not-due tick (see
            # test_stranded_source_head_is_published_on_the_next_not_due_tick).
            # This produces exactly the same operational_status and return as the
            # no-change fast path below, only without the rebuild. (A source-matrix
            # DEFINITION change ships with a code/config deploy -> service restart,
            # after which the first due tick republishes; it is never silently
            # lost, only deferred past a run of purely idle ticks.)
            if due_only and all(
                outcome["outcome"] in ("not_due", "disabled") for outcome in outcomes
            ):
                (
                    idle_pointer,
                    idle_status,
                    idle_active_receipts,
                ) = self._active_generation_light()
                idle_is_v2 = bool(
                    idle_pointer and
                    idle_pointer.get("schema_version") ==
                    "recession-monitor-v2.live-pointer.v2"
                )
                idle_materializer_ok = (
                    (idle_status or {}).get("snapshot_materializer_version") ==
                    SNAPSHOT_MATERIALIZER_VERSION
                )
                idle_diverged = (
                    idle_active_receipts is None or
                    self._runtime_head_receipt_map() != idle_active_receipts
                )
                if (
                    idle_status is not None and
                    idle_is_v2 and
                    idle_materializer_ok and
                    not idle_diverged
                ):
                    status = dict(idle_status)
                    status["generated_at"] = attempted_at
                    status["last_refresh_outcomes"] = outcomes
                    status["last_refresh_state_counts"] = {}
                    for outcome in outcomes:
                        key = outcome["outcome"]
                        status["last_refresh_state_counts"][key] = (
                            status["last_refresh_state_counts"].get(key, 0) + 1
                        )
                    operational_status = self._operational_status(
                        status,
                        idle_pointer,
                        attempted_at,
                        outcomes,
                        generation_recovery_required=False,
                    )
                    atomic_write_json(
                        self.store.public / "operational_status.json",
                        operational_status,
                    )
                    matrix_receipt = dict(idle_status["source_matrix"])
                    matrix_receipt["json_path"] = str(
                        self.project_root /
                        "live_data" /
                        "catalog" /
                        "source_matrix.v1.json"
                    )
                    return {
                        "idle": True,
                        "matrix": matrix_receipt,
                        "outcomes": outcomes,
                        "pointer": None,
                        "snapshot_source_count": idle_status["snapshot_source_count"],
                        "status": status,
                    }

            coverage = self.build_coverage(attempted_at)
            matrix = build_source_matrix(
                self.project_root,
                self.config,
                self.store,
                coverage,
                attempted_at,
            )
            source_evidence_changed = any(
                outcome["outcome"] == "success" for outcome in outcomes
            )
            (
                current_pointer,
                current_status,
                active_source_bindings,
            ) = (
                self._current_generation_binding()
            )
            runtime_heads = self.store.all_source_heads()
            runtime_source_bindings = self._runtime_head_binding_map(
                runtime_heads
            )
            source_head_generation_diverged = bool(
                current_pointer is not None and
                runtime_source_bindings != active_source_bindings
            )
            if source_head_generation_diverged:
                recovery_status = self._operational_status(
                    current_status,
                    current_pointer,
                    attempted_at,
                    outcomes,
                    generation_recovery_required=True,
                )
                atomic_write_json(
                    self.store.public / "operational_status.json",
                    recovery_status,
                )
            bundle_errors, bundle_candidates = self._atomic_bundle_state(
                outcomes
            )
            if bundle_errors:
                outcomes.extend(
                    {
                        "error": message,
                        "outcome": "failed",
                        "source_id": bundle_id,
                    }
                    for bundle_id, message in sorted(bundle_errors.items())
                )
                if current_pointer is None or current_status is None:
                    raise CanonicalDataError(
                        "atomic source bundle is incomplete: %r" %
                        bundle_errors
                    )
                operational_status = self._operational_status(
                    current_status,
                    current_pointer,
                    attempted_at,
                    outcomes,
                    generation_recovery_required=(
                        source_head_generation_diverged
                    ),
                )
                atomic_write_json(
                    self.store.public / "operational_status.json",
                    operational_status,
                )
                matrix_receipt = dict(current_status["source_matrix"])
                matrix_receipt["json_path"] = str(
                    self.project_root /
                    "live_data" /
                    "catalog" /
                    "source_matrix.v1.json"
                )
                return {
                    "matrix": matrix_receipt,
                    "outcomes": outcomes,
                    "pointer": None,
                    "snapshot_source_count": current_status[
                        "snapshot_source_count"
                    ],
                    "status": current_status,
                }
            atomic_bundle_evidence_changed = False
            for bundle_id, candidate in sorted(bundle_candidates.items()):
                prior = self.store.read_atomic_bundle(bundle_id)
                if prior != candidate:
                    atomic_bundle_evidence_changed = True
                    self.store.write_atomic_bundle(bundle_id, candidate)
            current_generation_is_v2 = bool(
                current_pointer and
                current_pointer.get("schema_version") ==
                "recession-monitor-v2.live-pointer.v2"
            )
            current_matrix_definition = (
                (current_status or {})
                .get("source_matrix", {})
                .get("definition_sha256")
            )
            matrix_definition_changed = (
                current_matrix_definition !=
                matrix["definition_sha256"]
            )
            snapshot_materializer_changed = (
                (current_status or {}).get("snapshot_materializer_version") !=
                SNAPSHOT_MATERIALIZER_VERSION
            )
            if (
                not source_evidence_changed and
                not atomic_bundle_evidence_changed and
                not matrix_definition_changed and
                not snapshot_materializer_changed and
                not source_head_generation_diverged and
                current_generation_is_v2 and
                current_status is not None
            ):
                status = dict(current_status)
                status["coverage_counts"] = coverage["counts"]
                status["generated_at"] = attempted_at
                status["last_refresh_outcomes"] = outcomes
                status["last_refresh_state_counts"] = {}
                for outcome in outcomes:
                    key = outcome["outcome"]
                    status["last_refresh_state_counts"][key] = (
                        status["last_refresh_state_counts"].get(key, 0) + 1
                    )
                operational_status = self._operational_status(
                    status,
                    current_pointer,
                    attempted_at,
                    outcomes,
                    generation_recovery_required=False,
                )
                atomic_write_json(
                    self.store.public / "operational_status.json",
                    operational_status,
                )
                matrix_receipt = dict(current_status["source_matrix"])
                matrix_receipt["json_path"] = str(
                    self.project_root /
                    "live_data" /
                    "catalog" /
                    "source_matrix.v1.json"
                )
                return {
                    "matrix": matrix_receipt,
                    "outcomes": outcomes,
                    "pointer": None,
                    "snapshot_source_count": current_status[
                        "snapshot_source_count"
                    ],
                    "status": status,
                }

            if source_head_generation_diverged:
                self._validate_generation_recovery_heads(
                    runtime_heads,
                )
            snapshot = self.build_snapshot(attempted_at)
            matrix_receipt = write_source_matrix(self.project_root, matrix)
            status = self.build_status(attempted_at, outcomes, snapshot, coverage)
            status["source_matrix"] = {
                "csv_bytes": matrix_receipt["csv_bytes"],
                "csv_sha256": matrix_receipt["csv_sha256"],
                "definition_sha256": matrix_receipt["definition_sha256"],
                "json_bytes": matrix_receipt["json_bytes"],
                "json_sha256": matrix_receipt["json_sha256"],
                "row_count": matrix_receipt["row_count"],
            }
            pointer = None
            if snapshot["sources"] and (
                source_evidence_changed or
                atomic_bundle_evidence_changed or
                matrix_definition_changed or
                snapshot_materializer_changed or
                source_head_generation_diverged or
                not current_generation_is_v2
            ):
                pointer = self.store.publish_generation(snapshot, status, coverage)
            if pointer is not None:
                current_pointer = pointer
                committed = read_verified_generation(
                    self.store.public,
                    self.store.root / "generations",
                    materialize_members=("snapshot.json",),
                    attest_bindings=True,
                )
                if (
                    committed["manifest"]["source_head_receipt_sha256"] !=
                    self._runtime_head_receipt_map()
                ):
                    raise CanonicalDataError(
                        "published generation does not bind current source heads"
                    )
                committed_bindings = {
                    source["source_id"]: validate_source_binding(source)
                    for source in committed["members"]["snapshot.json"]["sources"]
                }
                if committed_bindings != self._runtime_head_binding_map():
                    raise CanonicalDataError(
                        "published generation does not bind source evidence"
                    )
            operational_status = self._operational_status(
                status,
                current_pointer,
                attempted_at,
                outcomes,
                generation_recovery_required=False,
            )
            operational_status["generation_advanced"] = pointer is not None
            operational_status["generation_advance_reasons"] = [
                reason
                for reason, active in (
                    ("source_evidence_changed", source_evidence_changed),
                    (
                        "atomic_bundle_evidence_changed",
                        atomic_bundle_evidence_changed,
                    ),
                    ("source_matrix_definition_changed", matrix_definition_changed),
                    (
                        "snapshot_materializer_changed",
                        snapshot_materializer_changed,
                    ),
                    (
                        "source_head_generation_diverged",
                        source_head_generation_diverged,
                    ),
                    ("pointer_schema_upgrade", not current_generation_is_v2),
                )
                if active
            ]
            atomic_write_json(
                self.store.public / "operational_status.json",
                operational_status,
            )
            return {
                "matrix": matrix_receipt,
                "outcomes": outcomes,
                "pointer": pointer,
                "snapshot_source_count": len(snapshot["sources"]),
                "status": status,
            }

    def _atomic_bundle_errors(self, outcomes):
        errors, _ = self._atomic_bundle_state(outcomes)
        return errors

    def _atomic_bundle_state(self, outcomes):
        outcome_by_source = {
            outcome["source_id"]: outcome
            for outcome in outcomes
        }
        failures = {
            outcome["source_id"]: outcome.get("error", outcome["outcome"])
            for outcome in outcomes
            if outcome["outcome"] in ("blocked", "failed")
        }
        errors = {}
        candidates = {}
        for bundle_id, members in _atomic_bundle_groups(self.config).items():
            member_failures = {
                member: failures[member]
                for member in members
                if member in failures
            }
            if member_failures:
                errors[bundle_id] = "member acquisition failed: %r" % (
                    member_failures,
                )
                continue
            data_through = set()
            member_bindings = []
            for member in members:
                head = self.store.read_source_head(member)
                if head is None:
                    errors[bundle_id] = "member source head is absent"
                    break
                configured = self._source_by_id()[member]
                if (
                    head.get("adapter") != configured["adapter"] or
                    head.get("method_version") != configured["method_version"]
                ):
                    errors[bundle_id] = "member source head parser identity differed"
                    break
                try:
                    normalized = self.store.verify_source_head(
                        member,
                        head,
                    )["normalized"]
                except CanonicalDataError as exc:
                    errors[bundle_id] = str(exc)
                    break
                records = normalized.get("records")
                if not isinstance(records, list) or not records:
                    errors[bundle_id] = "member normalized records are absent"
                    break
                bundle_values = {
                    record.get("atomic_bundle_id") for record in records
                }
                through_values = {
                    record.get("data_through") for record in records
                }
                if bundle_values != {bundle_id} or len(through_values) != 1:
                    errors[bundle_id] = "member bundle identity differed"
                    break
                data_through.update(through_values)
                member_bindings.append({
                    "adapter": head["adapter"],
                    "method_version": head["method_version"],
                    "normalized_sha256": head["normalized_sha256"],
                    "receipt_sha256": head["receipt_sha256"],
                    "record_count": head["record_count"],
                    "source_bytes_sha256": head["source_bytes_sha256"],
                    "source_id": member,
                })
            if bundle_id not in errors and len(data_through) != 1:
                errors[bundle_id] = "member data-through editions differed"
            if bundle_id in errors:
                continue
            through = next(iter(data_through))
            if not isinstance(through, str) or not through:
                errors[bundle_id] = "member data-through edition was invalid"
                continue
            candidate = {
                "atomic_bundle_id": bundle_id,
                "data_through": through,
                "members": sorted(
                    member_bindings,
                    key=lambda item: item["source_id"],
                ),
                "schema_version": (
                    "recession-monitor-v2.atomic-source-bundle.v1"
                ),
            }
            complete_attempt = all(
                member in outcome_by_source and
                outcome_by_source[member]["outcome"]
                in ("success", "unchanged")
                for member in members
            )
            if complete_attempt:
                candidates[bundle_id] = candidate
                continue
            committed = self.store.read_atomic_bundle(bundle_id)
            if committed != candidate:
                errors[bundle_id] = (
                    "member heads differ from committed bundle"
                )
        return errors, candidates

    def _refresh_source(self, source, attempted_at):
        source_id = source["source_id"]
        prior_head = self.store.read_source_head(source_id)
        prior_parser_matches = bool(
            prior_head and
            prior_head.get("adapter") == source["adapter"] and
            prior_head.get("method_version") == source["method_version"]
        )
        source_digest = None
        failure_stage = "request"
        conditional_headers = {}
        if prior_parser_matches and self._send_conditional(source):
            if prior_head.get("etag"):
                conditional_headers["If-None-Match"] = prior_head["etag"]
            if prior_head.get("last_modified"):
                conditional_headers["If-Modified-Since"] = prior_head[
                    "last_modified"
                ]
        try:
            response = self.http_client.fetch(
                source,
                now=_parse_timestamp(attempted_at),
                conditional_headers=conditional_headers,
            )
            if response.status == 304:
                if not prior_parser_matches:
                    raise SourceUnavailable(
                        "publisher returned HTTP 304 without a compatible prior source head"
                    )
                source_digest = prior_head["source_bytes_sha256"]
                return self._record_unchanged(
                    source,
                    prior_head,
                    response,
                    attempted_at,
                    source_digest,
                    "http_304_not_modified",
                )
            source_digest, _ = self.store.store_source_object(response.body)
            if (
                prior_head is not None and
                source_digest == prior_head["source_bytes_sha256"] and
                prior_parser_matches
            ):
                return self._record_unchanged(
                    source,
                    prior_head,
                    response,
                    attempted_at,
                    source_digest,
                    "publisher_bytes_identical",
                )
            failure_stage = "normalization"
            records = normalize(source, response.body, attempted_at)
            for record in records:
                record["provenance_url"] = response.url
                record["retrieved_at"] = attempted_at
                record["source_bytes_sha256"] = source_digest
                record["validated_at"] = attempted_at
                record["vintage_id"] = source_digest
            normalized = {
                "parser_id": "rmv2-live/%s" % source["adapter"],
                "records": records,
                "retrieved_at": attempted_at,
                "schema_version": "recession-monitor-v2.normalized-source.v1",
                "source_bytes_sha256": source_digest,
                "source_id": source_id,
            }
            normalized_digest, _ = self.store.store_normalized(normalized)
            failure_stage = "receipt"
            receipt = {
                "clocks": {
                    "provider_available_at": attempted_at,
                    "publisher_released_at": None,
                    "retrieved_at": attempted_at,
                    "validated_at": attempted_at,
                },
                "information_set_mode": source["information_set_mode"],
                "normalized_sha256": normalized_digest,
                "outcome": "retrieved_and_validated",
                "predecessor_receipt_sha256": (
                    prior_head.get("receipt_sha256") if prior_head else None
                ),
                "publisher": source["publisher"],
                "request": {
                    "body_sha256": response.request_body_sha256,
                    "conditional_headers": response.request_headers,
                    "method": response.request_method,
                    "parameters": response.request_parameters,
                    "url": response.url,
                },
                "response": {
                    "content_length": len(response.body),
                    "content_type": response.headers.get("content-type"),
                    "etag": response.headers.get("etag"),
                    "last_modified": response.headers.get("last-modified"),
                    "status": response.status,
                },
                "rights_status": source["rights_status"],
                "schema_version": "recession-monitor-v2.acquisition-receipt.v1",
                "source_bytes_sha256": source_digest,
                "source_id": source_id,
            }
            receipt_digest, _ = self.store.store_receipt(source_id, receipt)
            head = {
                "adapter": source["adapter"],
                "etag": response.headers.get("etag"),
                "latest_observation_period": max(
                    (
                        record["observation_period"]
                        for record in records
                        if record["observation_period"] is not None
                    ),
                    default=None,
                ),
                "last_modified": response.headers.get("last-modified"),
                "method_version": source["method_version"],
                "normalized_sha256": normalized_digest,
                "record_count": len(records),
                "receipt_sha256": receipt_digest,
                "retrieved_at": attempted_at,
                "schema_version": "recession-monitor-v2.source-head.v1",
                "source_bytes_sha256": source_digest,
                "source_id": source_id,
            }
            self.store.write_source_head(source_id, head)
            state = {
                "attempted_at": attempted_at,
                "error": None,
                "last_success_at": attempted_at,
                "outcome": "success",
                "receipt_sha256": receipt_digest,
                "schema_version": "recession-monitor-v2.source-status.v1",
                "source_id": source_id,
            }
            self.store.write_source_status(source_id, state)
            return {
                "outcome": "success",
                "record_count": len(records),
                "source_id": source_id,
            }
        except (SourceBlocked, SourceUnavailable, OSError, ValueError) as exc:
            outcome = "blocked" if isinstance(exc, SourceBlocked) else "failed"
            attempt = {
                "attempted_at": attempted_at,
                "error_type": type(exc).__name__,
                "failure_stage": failure_stage,
                "message": str(exc),
                "outcome": outcome,
                "source_bytes_sha256": source_digest,
                "schema_version": "recession-monitor-v2.acquisition-attempt.v1",
                "source_id": source_id,
            }
            attempt_digest, _ = self.store.store_attempt(source_id, attempt)
            state = {
                "attempt_receipt_sha256": attempt_digest,
                "attempted_at": attempted_at,
                "error": {
                    "message": str(exc),
                    "type": type(exc).__name__,
                },
                "last_success_at": (
                    prior_head.get("retrieved_at") if prior_head else None
                ),
                "outcome": outcome,
                "schema_version": "recession-monitor-v2.source-status.v1",
                "source_id": source_id,
            }
            self.store.write_source_status(source_id, state)
            return {
                "error": str(exc),
                "outcome": outcome,
                "source_id": source_id,
            }

    def _record_unchanged(
        self,
        source,
        prior_head,
        response,
        attempted_at,
        source_digest,
        reason,
    ):
        source_id = source["source_id"]
        attempt = {
            "attempted_at": attempted_at,
            "error_type": None,
            "failure_stage": None,
            "message": None,
            "outcome": "unchanged",
            "predecessor_receipt_sha256": prior_head["receipt_sha256"],
            "reason": reason,
            "request": {
                "body_sha256": response.request_body_sha256,
                "conditional_headers": response.request_headers,
                "method": response.request_method,
                "parameters": response.request_parameters,
                "url": response.url,
            },
            "response": {
                "content_length": len(response.body),
                "content_type": response.headers.get("content-type"),
                "etag": response.headers.get("etag"),
                "last_modified": response.headers.get("last-modified"),
                "status": response.status,
            },
            "schema_version": "recession-monitor-v2.acquisition-attempt.v1",
            "source_bytes_sha256": source_digest,
            "source_id": source_id,
        }
        attempt_digest, _ = self.store.store_attempt(source_id, attempt)
        state = {
            "attempt_receipt_sha256": attempt_digest,
            "attempted_at": attempted_at,
            "error": None,
            "last_success_at": prior_head["retrieved_at"],
            "outcome": "unchanged",
            "receipt_sha256": prior_head["receipt_sha256"],
            "schema_version": "recession-monitor-v2.source-status.v1",
            "source_id": source_id,
        }
        self.store.write_source_status(source_id, state)
        return {
            "attempt_receipt_sha256": attempt_digest,
            "outcome": "unchanged",
            "reason": reason,
            "record_count": prior_head["record_count"],
            "source_id": source_id,
        }

    def build_snapshot(self, generated_at, use_projection_cache=True):
        """Materialize the snapshot preimage from the runtime source heads.

        Incremental: each source's contribution (its immutable binding + its
        latest-admissible-observation-per-series projection + record count) is a
        pure function of its content-addressed normalized object, so it is
        memoized in a content-addressed projection cache keyed by
        ``normalized_sha256`` under the materializer version.  A per-source
        admission then re-projects ONLY the source(s) whose evidence head
        changed; unchanged sources are reused from the cache.  ``use_projection_
        cache=False`` forces the full rebuild (the reference path) and is the
        byte-for-byte equality oracle in the tests.  The complete raw ->
        normalized -> receipt -> binding closure re-verification stays in
        ``verify --full`` and is never weakened here.
        """
        sources = []
        series = {}
        full_history_record_count = 0
        archival_panel_sources = []
        archival_panel_record_count = 0
        source_map = self._source_by_id()
        for source_id, head in sorted(self.store.all_source_heads().items()):
            configured = source_map.get(source_id)
            if (
                configured is None or
                head.get("adapter") != configured["adapter"] or
                head.get("method_version") != configured["method_version"]
            ):
                raise CanonicalDataError(
                    "snapshot source head parser identity is stale"
                )
            projection_policy = configured.get(
                "snapshot_projection", "latest_only.v1"
            )
            cache_version = "%s.%s" % (
                SNAPSHOT_MATERIALIZER_VERSION,
                projection_policy,
            )
            projection = None
            if use_projection_cache:
                projection = self.store.read_snapshot_projection(
                    source_id, head, cache_version
                )
            if projection is None:
                evidence = self.store.verify_source_head(source_id, head)
                projection = _project_source_snapshot(
                    source_id,
                    evidence["binding"],
                    evidence["normalized"]["records"],
                    projection_policy,
                )
                if use_projection_cache:
                    self.store.write_snapshot_projection(
                        source_id,
                        head,
                        cache_version,
                        projection,
                    )
            full_history_record_count += projection["record_count"]
            if projection_policy in (
                "archival_panel.v1", "greenbook_vintage_panel.v1"
            ):
                archival_panel_sources.append(source_id)
                archival_panel_record_count += projection["record_count"]
            for series_id, item in projection["series"].items():
                if series_id in series:
                    raise CanonicalDataError(
                        "snapshot series id is emitted by multiple sources"
                    )
                series[series_id] = item
            sources.append(projection["binding"])
        snapshot_projection = {
            "full_history_location": (
                "content_addressed_normalized_source_objects"
            ),
            "observations_per_series": 1,
            "projection": "latest_admissible_observation_only",
        }
        if archival_panel_sources:
            snapshot_projection.update({
                "archival_panel_record_count": archival_panel_record_count,
                "archival_panel_sources": sorted(archival_panel_sources),
                "archival_panel_storage": (
                    "content_addressed_normalized_source_objects"
                ),
                "archival_panel_projection": "excluded_from_flat_series",
            })
        preimage = {
            "data_policy": {
                "ai_dependency": "none",
                "browser_scientific_calculation": "prohibited",
                "current_revised_is_not_strict_first_release": True,
                "scientific_model_binding": "not_authorized",
            },
            "full_history_record_count": full_history_record_count,
            "generated_at": generated_at,
            "information_set_modes": [
                "archive_snapshot_asof",
                "current_revised",
                "stitched_strict_first_release",
                "substituted_diagnostic",
            ],
            "projected_record_count": len(series),
            "schema_version": "recession-monitor-v2.live-snapshot.v1",
            "series": {key: series[key] for key in sorted(series)},
            "snapshot_projection": snapshot_projection,
            "sources": sources,
        }
        preimage["generation_content_sha256"] = sha256_bytes(canonical_json_bytes(preimage))
        return preimage

    def build_coverage(self, generated_at):
        registry_path = (self.project_root / self.config["catalog_registry"]).resolve()
        configured = {}
        for source in self.config["sources"]:
            for catalog_id in source["coverage_source_ids"]:
                configured.setdefault(catalog_id, []).append(source)
        statuses = self.store.all_source_statuses()
        heads = self.store.all_source_heads()
        rows = []
        with registry_path.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                catalog_id = row["source_id"]
                adapters = configured.get(catalog_id, [])
                enabled = [item for item in adapters if item["enabled"]]
                successful = [
                    item for item in enabled
                    if (
                        (statuses.get(item["source_id"]) or {}).get("outcome")
                        in ("success", "unchanged")
                        and item["source_id"] in heads
                    )
                ]
                if row["access_class"] == "C":
                    state = "blocked_rights"
                elif row["access_class"] == "D":
                    state = "quarantined_target_bearing"
                elif successful and all(
                    item["adapter"] == "raw_capture" for item in successful
                ):
                    state = "captured_unparsed_not_admissible"
                elif successful:
                    state = "live_current_revised"
                elif enabled:
                    state = "configured_awaiting_success"
                elif adapters and any(item.get("secret_env") for item in adapters):
                    state = "blocked_missing_secret_or_enablement"
                else:
                    state = "planned_publisher_adapter"
                rows.append({
                    "access_class": row["access_class"],
                    "coverage": row["coverage"],
                    "frequency": row["frequency"],
                    "live_state": state,
                    "primary_url": row["primary_url"],
                    "publisher": row["publisher"],
                    "rights_status": row["rights_status"],
                    "source_id": catalog_id,
                    "typical_release_or_availability": row["typical_release_or_availability"],
                })
        counts = {}
        for row in rows:
            counts[row["live_state"]] = counts.get(row["live_state"], 0) + 1
        return {
            "counts": counts,
            "generated_at": generated_at,
            "rows": rows,
            "schema_version": "recession-monitor-v2.source-coverage.v1",
            "total_source_families": len(rows),
        }

    def build_status(self, generated_at, outcomes, snapshot, coverage):
        latest_attempt_counts = self._latest_attempt_counts(outcomes)
        current_source_health, current_source_health_counts = (
            self._current_source_health()
        )
        return {
            "api": {
                "host": self.config["api"]["host"],
                "port": self.config["api"]["port"],
            },
            "coverage_counts": coverage["counts"],
            "current_source_health": current_source_health,
            "current_source_health_counts": current_source_health_counts,
            "data_policy": {
                "ai_dependency": "none",
                "browser_scientific_calculation": "prohibited",
                "scientific_model_binding": "not_authorized",
            },
            "generated_at": generated_at,
            "generation_recovery_required": False,
            "latest_attempt_counts": latest_attempt_counts,
            "last_refresh_outcomes": outcomes,
            "last_refresh_state_counts": latest_attempt_counts,
            "no_ai": True,
            "schema_version": "recession-monitor-v2.live-status.v1",
            "scientific_outputs_updated": False,
            "service_state": self._service_state(
                bool(snapshot["sources"]),
                current_source_health,
                False,
            ),
            "snapshot_materializer_version": SNAPSHOT_MATERIALIZER_VERSION,
            "snapshot_source_count": len(snapshot["sources"]),
            "snapshot_series_count": len(snapshot["series"]),
        }
