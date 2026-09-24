"""Strict one-shot queue runner for the Recession Monitor V2 data autopilot."""

from __future__ import absolute_import

import fcntl
import datetime
import os
import re
import stat
import subprocess
import sys
from collections import namedtuple
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

from live_data.rmv2_live.canonical import (
    CanonicalDataError,
    atomic_write,
    canonical_json_bytes,
    sha256_bytes,
    strict_json_loads,
    utc_now,
)
from live_data.rmv2_live.cli import _build_feed_factory_inventory


QUEUE_SCHEMA = "recession-monitor-v2.data-autopilot-queue.v1"
ATTEMPT_SCHEMA = "recession-monitor-v2.data-autopilot-attempt.v2"
STATUS_SCHEMA = "recession-monitor-v2.data-autopilot-status.v2"
LEGACY_STATUS_SCHEMA = "recession-monitor-v2.data-autopilot-status.v1"
INVENTORY_SCHEMA = "recession-monitor-v2.feed-factory-inventory.v1"
TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SECRET_KEY_RE = re.compile(
    r"(?:^|[_-])(?:api[_-]?key|password|secret|token)(?:$|[_-])",
    re.IGNORECASE,
)

SUPPORTED_ACTIONS = frozenset((
    "factory_apply_reviewed",
    "factory_prepare",
    "report_only",
    "targeted_refresh",
    "verify_live",
))
MUTATING_ACTIONS = frozenset((
    "factory_apply_reviewed",
    "factory_prepare",
    "targeted_refresh",
))
NETWORK_ACTIONS = frozenset((
    "factory_prepare",
    "targeted_refresh",
))
EXCEPTION_KINDS = frozenset((
    "credential_required",
    "new_parser_required",
    "publisher_access_blocked",
    "rights_blocked",
    "target_quarantined",
))
SUCCESS_STATES = frozenset(("SUCCESS",))
FAILURE_STATES = frozenset(("FAILED", "PRECONDITION_FAILED"))
WAITING_STATES = frozenset((
    "BLOCKED_DEPENDENCY",
    "DEFERRED_SERVICE_BUSY",
    "DRY_RUN",
    "PENDING_DISABLED",
    "WAITING_FOR_RECEIPT",
))
NONINVOKED_STATES = frozenset((
    "BLOCKED_DEPENDENCY",
    "DEFERRED_SERVICE_BUSY",
    "EXCEPTION_RECORDED",
    "PENDING_DISABLED",
    "WAITING_FOR_RECEIPT",
))
PERSISTED_TASK_STATES = (
    SUCCESS_STATES |
    FAILURE_STATES |
    NONINVOKED_STATES
)
PERSISTED_OVERALL_STATES = frozenset((
    "BLOCKED_EXCEPTIONS_ONLY",
    "DEGRADED",
    "READY_FOR_REVIEW",
    "SCOPED_WORK_COMPLETE",
    "WORKING",
))
INVENTORY_OVERALL_STATES = frozenset((
    "BLOCKED_EXCEPTIONS_ONLY",
    "DEGRADED",
    "READY_FOR_REVIEW",
    "SCOPED_WORK_COMPLETE",
    "WORKING",
))

LoadedQueue = namedtuple("LoadedQueue", ("path", "queue", "queue_sha256"))


class QueueContractError(CanonicalDataError):
    """The explicit autopilot queue failed a fail-closed contract check."""


class OperationError(RuntimeError):
    """An allowlisted delegated operation failed exactly once."""


class ServiceBusyError(RuntimeError):
    """The live-data publication barrier was held; nothing was invoked."""


def _require_keys(mapping, expected, context):
    if not isinstance(mapping, dict):
        raise QueueContractError("%s must be an object" % context)
    missing = sorted(set(expected) - set(mapping))
    extra = sorted(set(mapping) - set(expected))
    if missing or extra:
        raise QueueContractError(
            "%s key mismatch; missing=%r extra=%r" %
            (context, missing, extra)
        )


def _safe_project_relative(value):
    if (
        not isinstance(value, str) or
        not value or
        "\\" in value or
        "\x00" in value
    ):
        raise QueueContractError("unsafe project path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise QueueContractError("unsafe project path")
    return path


def _path_within_root(path, root):
    try:
        path.relative_to(root)
    except ValueError:
        raise QueueContractError("path escaped the project root")


def _reject_linked_ancestors(path, root):
    root = Path(root).resolve()
    path = Path(path)
    _path_within_root(path, root)
    relative = path.relative_to(root)
    cursor = root
    for part in relative.parts[:-1]:
        cursor = cursor / part
        try:
            info = cursor.lstat()
        except FileNotFoundError:
            raise
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise QueueContractError("project path ancestor is unsafe")


def _safe_regular_bytes(path, allowed_root, missing_ok=False):
    root = Path(allowed_root).resolve()
    input_path = Path(path)
    path = input_path.parent.resolve() / input_path.name
    _path_within_root(path, root)
    try:
        _reject_linked_ancestors(path, root)
        final_info = path.lstat()
        if (
            stat.S_ISLNK(final_info.st_mode) or
            not stat.S_ISREG(final_info.st_mode) or
            final_info.st_nlink != 1
        ):
            raise QueueContractError(
                "path must be one regular unlinked file: %s" % path
            )
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(str(path), flags)
    except FileNotFoundError:
        if missing_ok:
            return None
        raise QueueContractError("required file is missing: %s" % path)
    except OSError as exc:
        raise QueueContractError("file cannot be safely opened: %s" % path) from exc
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise QueueContractError(
                "path must be one regular unlinked file: %s" % path
            )
        chunks = []
        total = 0
        while True:
            chunk = os.read(descriptor, 65536)
            if not chunk:
                break
            total += len(chunk)
            if total > 64 * 1024 * 1024:
                raise QueueContractError("file exceeds autopilot read limit")
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _binding(value, context):
    if value is None:
        return None
    _require_keys(value, ("path", "sha256"), context)
    _safe_project_relative(value["path"])
    if (
        not isinstance(value["sha256"], str) or
        not SHA256_RE.match(value["sha256"])
    ):
        raise QueueContractError("%s sha256 is invalid" % context)
    return value


def _scan_for_secrets(value, path="$"):
    if isinstance(value, dict):
        for key, item in value.items():
            if SECRET_KEY_RE.search(key) and item not in (None, False, ""):
                raise QueueContractError(
                    "embedded secret-like field is prohibited at %s.%s" %
                    (path, key)
                )
            _scan_for_secrets(item, "%s.%s" % (path, key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _scan_for_secrets(item, "%s[%d]" % (path, index))
    elif (
        isinstance(value, str) and
        value.lower().startswith(("bearer ", "basic "))
    ):
        raise QueueContractError(
            "embedded secret-like value is prohibited at %s" % path
        )


def _validate_policy(policy):
    _require_keys(
        policy,
        (
            "allow_mutation",
            "allow_network",
            "allowed_actions",
            "completion_scope",
            "no_ai",
            "rights_bypass_authorized",
            "science_authorized",
            "secrets_embedded",
            "target_access_authorized",
        ),
        "policy",
    )
    for field in (
        "allow_mutation",
        "allow_network",
        "no_ai",
        "rights_bypass_authorized",
        "science_authorized",
        "secrets_embedded",
        "target_access_authorized",
    ):
        if not isinstance(policy[field], bool):
            raise QueueContractError("policy.%s must be boolean" % field)
    if not policy["no_ai"]:
        raise QueueContractError("policy no_ai must remain true")
    if policy["secrets_embedded"]:
        raise QueueContractError("policy secrets_embedded must remain false")
    if (
        policy["rights_bypass_authorized"] or
        policy["science_authorized"] or
        policy["target_access_authorized"]
    ):
        raise QueueContractError(
            "policy prohibits rights, target, and science authority"
        )
    if (
        policy["completion_scope"] !=
        "registered_and_reserved_project_scope"
    ):
        raise QueueContractError("unsupported completion_scope")
    actions = policy["allowed_actions"]
    if (
        not isinstance(actions, list) or
        not actions or
        len(actions) != len(set(actions)) or
        actions != sorted(actions)
    ):
        raise QueueContractError(
            "policy.allowed_actions must be a sorted unique list"
        )
    unsupported = sorted(set(actions) - SUPPORTED_ACTIONS)
    if unsupported:
        raise QueueContractError(
            "unsupported action: %s" % ",".join(unsupported)
        )


def _validate_parameters(action, parameters):
    expected = {
        "factory_apply_reviewed": ("bundle_path",),
        "factory_prepare": ("draft_path",),
        "report_only": (),
        "targeted_refresh": ("source_id",),
        "verify_live": (),
    }[action]
    _require_keys(parameters, expected, "%s parameters" % action)
    if "bundle_path" in parameters:
        _safe_project_relative(parameters["bundle_path"])
    if "draft_path" in parameters:
        _safe_project_relative(parameters["draft_path"])
    if "source_id" in parameters:
        source_id = parameters["source_id"]
        if (
            not isinstance(source_id, str) or
            not TOKEN_RE.match(source_id) or
            source_id in (".", "..")
        ):
            raise QueueContractError("targeted_refresh source_id is invalid")


def _validate_task(task, policy, earlier_ids, seen_ids, index):
    _require_keys(
        task,
        (
            "action",
            "artifact",
            "enabled",
            "exception_kind",
            "expected_predecessors",
            "parameters",
            "prerequisites",
            "required_receipt",
            "reviewed",
            "task_id",
        ),
        "task[%d]" % index,
    )
    task_id = task["task_id"]
    if (
        not isinstance(task_id, str) or
        not TOKEN_RE.match(task_id) or
        task_id in (".", "..")
    ):
        raise QueueContractError("task_id is invalid")
    if task_id in seen_ids:
        raise QueueContractError("duplicate task_id: %s" % task_id)
    seen_ids.add(task_id)
    action = task["action"]
    if action not in SUPPORTED_ACTIONS:
        raise QueueContractError("unsupported action: %s" % action)
    if action not in policy["allowed_actions"]:
        raise QueueContractError(
            "task action is absent from policy.allowed_actions"
        )
    if not isinstance(task["enabled"], bool):
        raise QueueContractError("task enabled must be boolean")
    if not isinstance(task["reviewed"], bool):
        raise QueueContractError("task reviewed must be boolean")
    exception_kind = task["exception_kind"]
    if exception_kind is not None and exception_kind not in EXCEPTION_KINDS:
        raise QueueContractError("task exception_kind is invalid")
    if exception_kind is not None and (
        task["enabled"] or action != "report_only"
    ):
        raise QueueContractError(
            "named exception tasks must be disabled report_only entries"
        )
    prerequisites = task["prerequisites"]
    if (
        not isinstance(prerequisites, list) or
        len(prerequisites) != len(set(prerequisites)) or
        any(not isinstance(item, str) for item in prerequisites)
    ):
        raise QueueContractError("task prerequisites are invalid")
    for prerequisite in prerequisites:
        if prerequisite not in earlier_ids:
            raise QueueContractError(
                "prerequisite must name an earlier task: %s" % prerequisite
            )
    _validate_parameters(action, task["parameters"])
    artifact = _binding(task["artifact"], "task artifact")
    receipt = _binding(task["required_receipt"], "task required_receipt")
    predecessors = task["expected_predecessors"]
    if not isinstance(predecessors, list):
        raise QueueContractError("task expected_predecessors must be a list")
    seen_paths = set()
    for number, predecessor in enumerate(predecessors):
        _binding(predecessor, "task predecessor[%d]" % number)
        if predecessor["path"] in seen_paths:
            raise QueueContractError("duplicate predecessor path")
        seen_paths.add(predecessor["path"])
    if action in NETWORK_ACTIONS and not policy["allow_network"]:
        raise QueueContractError(
            "%s requires policy.allow_network" % action
        )
    if action in MUTATING_ACTIONS:
        if not policy["allow_mutation"]:
            raise QueueContractError(
                "%s requires policy.allow_mutation" % action
            )
        if not task["reviewed"]:
            raise QueueContractError(
                "%s requires reviewed=true" % action
            )
        if not predecessors:
            raise QueueContractError(
                "%s requires an exact predecessor binding" % action
            )
        if artifact is None:
            raise QueueContractError(
                "%s requires an exact artifact binding" % action
            )
    if action == "factory_apply_reviewed" and not task["reviewed"]:
        raise QueueContractError(
            "factory_apply_reviewed requires reviewed=true"
        )
    if action == "factory_prepare" and artifact is not None:
        if artifact["path"] != task["parameters"]["draft_path"]:
            raise QueueContractError(
                "factory_prepare artifact must bind its draft_path"
            )
    if action == "factory_apply_reviewed" and artifact is not None:
        if artifact["path"] != task["parameters"]["bundle_path"]:
            raise QueueContractError(
                "factory_apply_reviewed artifact must bind its bundle_path"
            )
    earlier_ids.add(task_id)
    return receipt


def load_queue(project_root, queue_path=None):
    """Read and validate one exact queue without executing any operation."""
    project_root = Path(project_root).resolve()
    if queue_path is None:
        queue_path = (
            project_root / "live_data" / "config" /
            "autopilot_queue.v1.json"
        )
    queue_path = Path(queue_path)
    if not queue_path.is_absolute():
        queue_path = project_root / queue_path
    try:
        data = _safe_regular_bytes(queue_path, project_root)
        queue = strict_json_loads(data)
    except QueueContractError:
        raise
    except (CanonicalDataError, OSError, UnicodeError, ValueError) as exc:
        raise QueueContractError(str(exc)) from exc
    _require_keys(
        queue,
        ("policy", "queue_id", "schema_version", "tasks"),
        "queue",
    )
    if queue["schema_version"] != QUEUE_SCHEMA:
        raise QueueContractError("unsupported queue schema")
    if (
        not isinstance(queue["queue_id"], str) or
        not TOKEN_RE.match(queue["queue_id"])
    ):
        raise QueueContractError("queue_id is invalid")
    _scan_for_secrets(queue)
    _validate_policy(queue["policy"])
    tasks = queue["tasks"]
    if not isinstance(tasks, list) or not tasks:
        raise QueueContractError("queue tasks must be a nonempty list")
    earlier_ids = set()
    seen_ids = set()
    for index, task in enumerate(tasks):
        _validate_task(
            task,
            queue["policy"],
            earlier_ids,
            seen_ids,
            index,
        )
    canonical = canonical_json_bytes(queue)
    if data not in (canonical, canonical + b"\n"):
        raise QueueContractError("queue must use canonical JSON bytes")
    return LoadedQueue(
        queue_path,
        queue,
        sha256_bytes(data),
    )


def _bound_path(project_root, binding):
    relative = _safe_project_relative(binding["path"])
    return Path(project_root) / Path(*relative.parts)


def _check_binding(project_root, binding, missing_state=None):
    path = _bound_path(project_root, binding)
    data = _safe_regular_bytes(
        path,
        project_root,
        missing_ok=missing_state is not None,
    )
    if data is None:
        return missing_state
    if sha256_bytes(data) != binding["sha256"]:
        raise QueueContractError(
            "bound file hash is stale: %s" % binding["path"]
        )
    return "MATCH"


def _subprocess_json(project_root, arguments):
    command = [
        sys.executable,
        "-B",
        "-m",
        "live_data.rmv2_live",
        "--project-root",
        str(project_root),
    ] + list(arguments)
    environment = dict(os.environ)
    environment.update({
        "LANG": "C",
        "LC_ALL": "C",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "PYTHONIOENCODING": "utf-8",
        "TZ": "UTC",
    })
    completed = subprocess.run(
        command,
        cwd=str(project_root),
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=1800,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        if len(detail) > 2000:
            detail = detail[-2000:]
        raise OperationError(
            "delegated command failed (%d): %s" %
            (completed.returncode, detail)
        )
    try:
        value = strict_json_loads(completed.stdout)
    except (CanonicalDataError, ValueError, UnicodeError) as exc:
        raise OperationError(
            "delegated command did not return strict JSON"
        ) from exc
    if not isinstance(value, dict):
        raise OperationError("delegated command result must be an object")
    return value


@contextmanager
def _live_publication_barrier(project_root):
    """Serialize behind the one live-data refresh/publication barrier.

    The resident live-data service commits a source head before it switches
    the public generation pointer. Auditing runtime evidence inside that
    window observes a real, self-healing intermediate state, not a defect, so
    this cycle refuses to read it rather than reporting a false mismatch.
    """
    path = Path(project_root) / "live_data" / "runtime" / "refresh.lock"
    if not path.parent.is_dir():
        raise QueueContractError("live publication barrier is unavailable")
    descriptor = _open_lock(path)
    if descriptor is None:
        raise ServiceBusyError(
            "live-data refresh holds the publication barrier"
        )
    try:
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


class DefaultExecutor(object):
    """Delegate only the five allowlisted operations to existing owners."""

    def __init__(self, report_inventory=None):
        self.report_inventory = report_inventory

    def __call__(self, action, parameters, project_root):
        project_root = Path(project_root).resolve()
        if action == "report_only":
            if self.report_inventory is not None:
                return self.report_inventory
            return _build_feed_factory_inventory(project_root)
        if action == "verify_live":
            with _live_publication_barrier(project_root):
                return _subprocess_json(project_root, ["verify"])
        if action == "factory_prepare":
            return _subprocess_json(project_root, [
                "feed-factory",
                "prepare",
                "--draft",
                parameters["draft_path"],
            ])
        if action == "factory_apply_reviewed":
            return _subprocess_json(project_root, [
                "feed-factory",
                "apply",
                "--bundle",
                parameters["bundle_path"],
            ])
        if action == "targeted_refresh":
            return _subprocess_json(project_root, [
                "refresh",
                "--source",
                parameters["source_id"],
            ])
        raise QueueContractError("unsupported action: %s" % action)


def _result_summary(output):
    if not isinstance(output, dict):
        return {"output_type": type(output).__name__}
    keys = (
        "configured_sources",
        "overall_state",
        "schema_version",
        "source_id",
        "status",
    )
    summary = {
        key: output[key]
        for key in keys
        if key in output and isinstance(output[key], (bool, int, str))
    }
    summary["output_key_count"] = len(output)
    return summary


def _task_result(
    task,
    state,
    started_at,
    finished_at,
    invocation_count=0,
    output=None,
    error=None,
):
    error_value = str(error) if error is not None else None
    error_type = type(error).__name__ if error is not None else None
    output_summary = _result_summary(output) if output is not None else None
    receipt = None
    if invocation_count:
        receipt = sha256_bytes(canonical_json_bytes({
            "action": task["action"],
            "error": error_value,
            "error_type": error_type,
            "finished_at": finished_at,
            "output_summary": output_summary,
            "started_at": started_at,
            "state": state,
            "task_id": task["task_id"],
        }))
    return {
        "action": task["action"],
        "error": error_value,
        "error_type": error_type,
        "finished_at": finished_at,
        "invocation_count": invocation_count,
        "operation_receipt_sha256": receipt,
        "output_summary": output_summary,
        "started_at": started_at,
        "state": state,
        "task_id": task["task_id"],
    }


def _nonnegative_int(value, context):
    if (
        not isinstance(value, int) or
        isinstance(value, bool) or
        value < 0
    ):
        raise QueueContractError("%s must be a nonnegative integer" % context)
    return value


def _exact_string_list(value, context, tokens=False):
    if (
        not isinstance(value, list) or
        any(not isinstance(item, str) or not item for item in value)
    ):
        raise QueueContractError("%s must be a string list" % context)
    if tokens and any(not TOKEN_RE.match(item) for item in value):
        raise QueueContractError("%s contains an invalid identifier" % context)
    if value != sorted(set(value)):
        raise QueueContractError("%s must be sorted and unique" % context)
    return value


def _validate_counted_ids(value, context):
    _require_keys(value, ("count", "source_ids"), context)
    count = _nonnegative_int(value["count"], "%s.count" % context)
    source_ids = _exact_string_list(
        value["source_ids"],
        "%s.source_ids" % context,
        tokens=True,
    )
    if count != len(source_ids):
        raise QueueContractError("%s count/list mismatch" % context)
    return source_ids


def _validate_inventory_collection(value, context):
    _require_keys(
        value,
        ("artifact_count", "paths", "source_count", "source_ids"),
        context,
    )
    artifact_count = _nonnegative_int(
        value["artifact_count"],
        "%s.artifact_count" % context,
    )
    paths = _exact_string_list(value["paths"], "%s.paths" % context)
    for path in paths:
        _safe_project_relative(path)
    source_count = _nonnegative_int(
        value["source_count"],
        "%s.source_count" % context,
    )
    source_ids = _exact_string_list(
        value["source_ids"],
        "%s.source_ids" % context,
        tokens=True,
    )
    if artifact_count != len(paths) or source_count != len(source_ids):
        raise QueueContractError("%s count/list mismatch" % context)
    return source_ids


def _validate_inventory(inventory):
    """Validate the exact Feed Factory inventory used for state decisions."""
    top_keys = (
        "active_generation",
        "blocked_or_deferred",
        "candidate_lifecycle",
        "completion_blockers",
        "counts",
        "errors",
        "factory_artifacts",
        "factory_root",
        "overall_state",
        "overall_state_reason",
        "pending_candidates",
        "reservations",
        "schema_version",
        "scientific_effect",
        "scope_notice",
        "sources",
        "status",
    )
    _require_keys(inventory, top_keys, "inventory")
    if inventory["schema_version"] != INVENTORY_SCHEMA:
        raise QueueContractError("inventory schema_version is invalid")
    if inventory["scientific_effect"] != "none":
        raise QueueContractError("inventory scientific_effect is invalid")
    if (
        not isinstance(inventory["factory_root"], str) or
        not inventory["factory_root"] or
        not isinstance(inventory["scope_notice"], str) or
        not inventory["scope_notice"] or
        not isinstance(inventory["overall_state_reason"], str) or
        not inventory["overall_state_reason"]
    ):
        raise QueueContractError("inventory text field is invalid")
    if inventory["overall_state"] not in INVENTORY_OVERALL_STATES:
        raise QueueContractError("inventory overall_state is invalid")
    expected_status = (
        "FAIL" if inventory["overall_state"] == "DEGRADED" else "PASS"
    )
    if inventory["status"] != expected_status:
        raise QueueContractError("inventory status/state mismatch")
    errors = inventory["errors"]
    if (
        not isinstance(errors, list) or
        any(not isinstance(item, str) or not item for item in errors)
    ):
        raise QueueContractError("inventory errors must be a string list")

    generation = inventory["active_generation"]
    _require_keys(
        generation,
        ("generation_id", "recovery_required", "source_count", "source_ids"),
        "inventory.active_generation",
    )
    generation_id = generation["generation_id"]
    if (
        generation_id is not None and
        (
            not isinstance(generation_id, str) or
            not SHA256_RE.match(generation_id)
        )
    ):
        raise QueueContractError("inventory generation_id is invalid")
    if not isinstance(generation["recovery_required"], bool):
        raise QueueContractError("inventory recovery_required is invalid")
    generation_ids = _exact_string_list(
        generation["source_ids"],
        "inventory.active_generation.source_ids",
        tokens=True,
    )
    if (
        _nonnegative_int(
            generation["source_count"],
            "inventory.active_generation.source_count",
        ) != len(generation_ids)
    ):
        raise QueueContractError("inventory generation count/list mismatch")
    if generation_id is None and generation_ids:
        raise QueueContractError("inventory generation identity is missing")

    blocked = inventory["blocked_or_deferred"]
    _require_keys(
        blocked,
        ("rights_blocked", "target_quarantined"),
        "inventory.blocked_or_deferred",
    )
    rights_ids = _validate_counted_ids(
        blocked["rights_blocked"],
        "inventory.blocked_or_deferred.rights_blocked",
    )
    target_ids = _validate_counted_ids(
        blocked["target_quarantined"],
        "inventory.blocked_or_deferred.target_quarantined",
    )

    reservations = inventory["reservations"]
    _require_keys(
        reservations,
        (
            "configured_counts",
            "configured_source_ids",
            "counts",
            "fulfilled",
            "source_ids",
        ),
        "inventory.reservations",
    )
    reservation_counts = reservations["counts"]
    reservation_ids = reservations["source_ids"]
    configured_counts = reservations["configured_counts"]
    configured_ids = reservations["configured_source_ids"]
    reservation_groups = ("credential", "lower_priority", "normal")
    _require_keys(
        reservation_counts,
        reservation_groups + ("total",),
        "inventory.reservations.counts",
    )
    _require_keys(
        reservation_ids,
        reservation_groups,
        "inventory.reservations.source_ids",
    )
    _require_keys(
        configured_counts,
        reservation_groups + ("total",),
        "inventory.reservations.configured_counts",
    )
    _require_keys(
        configured_ids,
        reservation_groups,
        "inventory.reservations.configured_source_ids",
    )
    reservation_sets = {}
    configured_sets = {}
    for group in reservation_groups:
        source_ids = _exact_string_list(
            reservation_ids[group],
            "inventory.reservations.source_ids.%s" % group,
            tokens=True,
        )
        count = _nonnegative_int(
            reservation_counts[group],
            "inventory.reservations.counts.%s" % group,
        )
        if count != len(source_ids):
            raise QueueContractError(
                "inventory reservation count/list mismatch"
            )
        reservation_sets[group] = set(source_ids)
        configured_source_ids = _exact_string_list(
            configured_ids[group],
            "inventory.reservations.configured_source_ids.%s" % group,
            tokens=True,
        )
        configured_count = _nonnegative_int(
            configured_counts[group],
            "inventory.reservations.configured_counts.%s" % group,
        )
        if configured_count != len(configured_source_ids):
            raise QueueContractError(
                "inventory configured reservation count/list mismatch"
            )
        configured_sets[group] = set(configured_source_ids)
    if any(
        reservation_sets[left].intersection(reservation_sets[right])
        for left, right in (
            ("credential", "lower_priority"),
            ("credential", "normal"),
            ("lower_priority", "normal"),
        )
    ):
        raise QueueContractError("inventory reservation groups overlap")
    if _nonnegative_int(
        reservation_counts["total"],
        "inventory.reservations.counts.total",
    ) != sum(len(value) for value in reservation_sets.values()):
        raise QueueContractError("inventory reservation total mismatch")
    if any(
        configured_sets[left].intersection(configured_sets[right])
        for left, right in (
            ("credential", "lower_priority"),
            ("credential", "normal"),
            ("lower_priority", "normal"),
        )
    ):
        raise QueueContractError(
            "inventory configured reservation groups overlap"
        )
    if _nonnegative_int(
        configured_counts["total"],
        "inventory.reservations.configured_counts.total",
    ) != sum(len(value) for value in configured_sets.values()):
        raise QueueContractError(
            "inventory configured reservation total mismatch"
        )
    fulfilled_ids = set(_validate_counted_ids(
        reservations["fulfilled"],
        "inventory.reservations.fulfilled",
    ))
    if fulfilled_ids.intersection(set().union(*reservation_sets.values())):
        raise QueueContractError(
            "inventory fulfilled/outstanding reservations overlap"
        )
    for group in reservation_groups:
        if configured_sets[group] != (
            reservation_sets[group] |
            (fulfilled_ids & configured_sets[group])
        ):
            raise QueueContractError(
                "inventory configured/outstanding reservation mismatch"
            )
    if set().union(*configured_sets.values()) != (
        set().union(*reservation_sets.values()) | fulfilled_ids
    ):
        raise QueueContractError(
            "inventory configured/fulfilled reservation mismatch"
        )

    sources = inventory["sources"]
    source_groups = ("enabled", "failed", "healthy", "not_yet_refreshed")
    _require_keys(sources, source_groups, "inventory.sources")
    source_sets = {
        group: set(_validate_counted_ids(
            sources[group],
            "inventory.sources.%s" % group,
        ))
        for group in source_groups
    }
    if any(
        source_sets[left].intersection(source_sets[right])
        for left, right in (
            ("failed", "healthy"),
            ("failed", "not_yet_refreshed"),
            ("healthy", "not_yet_refreshed"),
        )
    ):
        raise QueueContractError("inventory source health groups overlap")
    if source_sets["enabled"] != (
        source_sets["failed"] |
        source_sets["healthy"] |
        source_sets["not_yet_refreshed"]
    ):
        raise QueueContractError("inventory enabled/source-health mismatch")
    if not set(generation_ids).issubset(source_sets["enabled"]):
        raise QueueContractError(
            "inventory generation/enabled source mismatch"
        )
    if (
        generation_id is not None and
        not generation["recovery_required"] and
        set(generation_ids) != source_sets["enabled"]
    ):
        raise QueueContractError(
            "inventory generation source set is incomplete"
        )
    # A fulfilled reservation is identified by its planned-reservation id, not
    # by an enabled source id. A reservation may be fulfilled by an exact
    # source-id match OR by endpoint identity, in which case the fulfilled id
    # is the planned id (e.g. "tsa_throughput") and the enabled source carries
    # a distinct suffixed id ("tsa_throughput_current"). The contract is that a
    # fulfilled id is a known configured reservation, not that it equals a
    # source id (asserting the latter forced a permanent DEGRADED loop).
    if not fulfilled_ids.issubset(
        set().union(*configured_sets.values())
    ):
        raise QueueContractError(
            "inventory fulfilled reservation is not a configured reservation"
        )

    artifact_groups = ("candidates", "drafts", "probes", "recipes")
    counts = inventory["counts"]
    artifacts = inventory["factory_artifacts"]
    _require_keys(counts, artifact_groups, "inventory.counts")
    _require_keys(
        artifacts,
        artifact_groups,
        "inventory.factory_artifacts",
    )
    factory_source_ids = set()
    for group in artifact_groups:
        artifact_count = _nonnegative_int(
            counts[group],
            "inventory.counts.%s" % group,
        )
        artifact = artifacts[group]
        factory_source_ids.update(_validate_inventory_collection(
            artifact,
            "inventory.factory_artifacts.%s" % group,
        ))
        if artifact_count != artifact["artifact_count"]:
            raise QueueContractError("inventory artifact count mismatch")

    lifecycle = inventory["candidate_lifecycle"]
    if not isinstance(lifecycle, list):
        raise QueueContractError("inventory candidate_lifecycle must be a list")
    lifecycle_keys = (
        "bundle_id",
        "config_applied",
        "live",
        "manifest_path",
        "predecessor_matches_active",
        "source_already_active",
        "source_id",
        "state",
    )
    lifecycle_states = frozenset((
        "CONFIGURED_AWAITING_REFRESH",
        "LIVE",
        "READY_FOR_REVIEW",
        "SUPERSEDED_OR_HISTORICAL",
    ))
    for index, item in enumerate(lifecycle):
        context = "inventory.candidate_lifecycle[%d]" % index
        _require_keys(item, lifecycle_keys, context)
        if (
            not isinstance(item["bundle_id"], str) or
            not item["bundle_id"] or
            not isinstance(item["source_id"], str) or
            not TOKEN_RE.match(item["source_id"]) or
            item["state"] not in lifecycle_states or
            any(
                not isinstance(item[key], bool)
                for key in (
                    "config_applied",
                    "live",
                    "predecessor_matches_active",
                    "source_already_active",
                )
            )
        ):
            raise QueueContractError("%s is invalid" % context)
        _safe_project_relative(item["manifest_path"])
        if (
            item["live"] and
            (
                not item["config_applied"] or
                not item["source_already_active"]
            )
        ):
            raise QueueContractError("%s live binding is invalid" % context)
    if lifecycle != sorted(
        lifecycle,
        key=lambda item: (item["source_id"], item["bundle_id"]),
    ):
        raise QueueContractError("inventory candidate_lifecycle is unordered")
    expected_pending = [
        item for item in lifecycle
        if item["state"] in (
            "CONFIGURED_AWAITING_REFRESH",
            "READY_FOR_REVIEW",
        )
    ]
    if inventory["pending_candidates"] != expected_pending:
        raise QueueContractError("inventory pending candidates mismatch")

    blockers = inventory["completion_blockers"]
    blocker_keys = (
        "credential_exceptions",
        "failed_sources",
        "lower_priority_exceptions",
        "normal_actionable_reservations",
        "not_yet_refreshed_sources",
        "ready_for_review_candidates",
        "rights_exceptions",
        "target_quarantine_exceptions",
        "unresolved_factory_sources",
    )
    _require_keys(blockers, blocker_keys, "inventory.completion_blockers")
    blocker_values = {
        key: _exact_string_list(
            blockers[key],
            "inventory.completion_blockers.%s" % key,
            tokens=True,
        )
        for key in blocker_keys
    }
    expected_blockers = {
        "credential_exceptions": sorted(reservation_sets["credential"]),
        "failed_sources": sorted(source_sets["failed"]),
        "lower_priority_exceptions": sorted(
            reservation_sets["lower_priority"]
        ),
        "normal_actionable_reservations": sorted(
            reservation_sets["normal"]
        ),
        "not_yet_refreshed_sources": sorted(
            source_sets["not_yet_refreshed"]
        ),
        "ready_for_review_candidates": sorted(set(
            item["source_id"]
            for item in lifecycle
            if item["state"] == "READY_FOR_REVIEW"
        )),
        "rights_exceptions": rights_ids,
        "target_quarantine_exceptions": target_ids,
        "unresolved_factory_sources": sorted(
            factory_source_ids - source_sets["healthy"]
        ),
    }
    if blocker_values != expected_blockers:
        raise QueueContractError("inventory blocker/list mismatch")
    return inventory


def _count(inventory, *path):
    value = inventory
    for key in path:
        if not isinstance(value, dict):
            return 0
        value = value.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def derive_overall_state(queue, task_results, inventory):
    """Derive an honest scoped status without treating exceptions as done."""
    try:
        _validate_inventory(inventory)
        if (
            not isinstance(queue, dict) or
            not isinstance(queue.get("tasks"), list) or
            not isinstance(task_results, list) or
            any(
                not isinstance(item, dict) or
                item.get("state") not in (
                    PERSISTED_TASK_STATES |
                    frozenset(("DRY_RUN",))
                )
                for item in task_results
            )
        ):
            return "DEGRADED"
    except (QueueContractError, TypeError, ValueError):
        return "DEGRADED"
    result_states = {item["state"] for item in task_results}
    if (
        result_states.intersection(FAILURE_STATES) or
        bool(inventory.get("errors")) or
        inventory.get("overall_state") == "DEGRADED" or
        inventory.get("active_generation", {}).get("recovery_required") is True or
        _count(inventory, "sources", "failed", "count") > 0
    ):
        return "DEGRADED"
    if (
        inventory.get("pending_candidates") or
        inventory.get("overall_state") == "READY_FOR_REVIEW"
    ):
        return "READY_FOR_REVIEW"
    queue_exceptions = any(
        item.get("exception_kind") in EXCEPTION_KINDS
        for item in queue.get("tasks", [])
    )
    exception_count = (
        _count(inventory, "reservations", "counts", "credential") +
        _count(inventory, "reservations", "counts", "lower_priority") +
        _count(inventory, "blocked_or_deferred", "rights_blocked", "count") +
        _count(inventory, "blocked_or_deferred", "target_quarantined", "count")
    )
    normal_work = (
        _count(inventory, "reservations", "counts", "normal") > 0 or
        _count(inventory, "sources", "not_yet_refreshed", "count") > 0 or
        bool(result_states.intersection(WAITING_STATES)) or
        any(
            not item.get("enabled") and item.get("exception_kind") is None
            for item in queue.get("tasks", [])
        )
    )
    if normal_work:
        return "WORKING"
    if exception_count or queue_exceptions:
        return "BLOCKED_EXCEPTIONS_ONLY"
    return "SCOPED_WORK_COMPLETE"


def _state_reason(state):
    return {
        "BLOCKED_EXCEPTIONS_ONLY": (
            "Only named credential, rights, target, publisher-access, "
            "new-parser, or intentionally deferred exceptions remain."
        ),
        "DEGRADED": (
            "A task, feed, binding, or verified generation requires repair."
        ),
        "LOCKED_OUT": (
            "Another one-shot autopilot cycle owns the nonblocking lock."
        ),
        "READY_FOR_REVIEW": (
            "At least one prepared candidate requires independent review."
        ),
        "SCOPED_WORK_COMPLETE": (
            "The explicit registered and reserved project scope has no "
            "remaining normal work or named exception."
        ),
        "WORKING": (
            "Normal reservations, receipts, refreshes, or explicit queue "
            "work remain."
        ),
    }[state]


def _safe_output_directory(project_root):
    project_root = Path(project_root).resolve()
    runtime = project_root / "live_data" / "runtime"
    autopilot = runtime / "autopilot"
    attempts = autopilot / "attempts"
    for path in (runtime, autopilot, attempts):
        if path.exists():
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                raise QueueContractError(
                    "autopilot output directory is unsafe"
                )
        else:
            path.mkdir(mode=0o755)
    return autopilot, attempts


def _open_lock(path):
    """Open an at-most-once coordinator lock, never a store writer lock."""
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(str(path), flags, 0o644)
    except OSError as exc:
        raise QueueContractError("autopilot lock cannot be opened") from exc
    info = os.fstat(descriptor)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        os.close(descriptor)
        raise QueueContractError("autopilot lock is unsafe")
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(descriptor)
        return None
    return descriptor


def _inventory_or_error(provider):
    try:
        value = provider()
        _validate_inventory(value)
        return value
    except Exception as exc:
        empty_collection = {
            "artifact_count": 0,
            "paths": [],
            "source_count": 0,
            "source_ids": [],
        }
        return {
            "active_generation": {
                "generation_id": None,
                "recovery_required": True,
                "source_count": 0,
                "source_ids": [],
            },
            "blocked_or_deferred": {
                "rights_blocked": {"count": 0, "source_ids": []},
                "target_quarantined": {"count": 0, "source_ids": []},
            },
            "candidate_lifecycle": [],
            "completion_blockers": {
                "credential_exceptions": [],
                "failed_sources": [],
                "lower_priority_exceptions": [],
                "normal_actionable_reservations": [],
                "not_yet_refreshed_sources": [],
                "ready_for_review_candidates": [],
                "rights_exceptions": [],
                "target_quarantine_exceptions": [],
                "unresolved_factory_sources": [],
            },
            "counts": {
                "candidates": 0,
                "drafts": 0,
                "probes": 0,
                "recipes": 0,
            },
            "errors": ["%s: %s" % (type(exc).__name__, exc)],
            "factory_artifacts": {
                "candidates": dict(empty_collection),
                "drafts": dict(empty_collection),
                "probes": dict(empty_collection),
                "recipes": dict(empty_collection),
            },
            "factory_root": "unavailable",
            "overall_state": "DEGRADED",
            "overall_state_reason": (
                "The Feed Factory inventory failed its exact contract."
            ),
            "pending_candidates": [],
            "reservations": {
                "configured_counts": {
                    "credential": 0,
                    "lower_priority": 0,
                    "normal": 0,
                    "total": 0,
                },
                "configured_source_ids": {
                    "credential": [],
                    "lower_priority": [],
                    "normal": [],
                },
                "counts": {
                    "credential": 0,
                    "lower_priority": 0,
                    "normal": 0,
                    "total": 0,
                },
                "fulfilled": {
                    "count": 0,
                    "source_ids": [],
                },
                "source_ids": {
                    "credential": [],
                    "lower_priority": [],
                    "normal": [],
                },
            },
            "schema_version": INVENTORY_SCHEMA,
            "scientific_effect": "none",
            "scope_notice": "Inventory unavailable; fail-closed state only.",
            "sources": {
                "enabled": {"count": 0, "source_ids": []},
                "failed": {"count": 0, "source_ids": []},
                "healthy": {"count": 0, "source_ids": []},
                "not_yet_refreshed": {"count": 0, "source_ids": []},
            },
            "status": "FAIL",
        }


def _inventory_summary(inventory):
    _validate_inventory(inventory)
    generation = inventory.get("active_generation", {})
    return {
        "active_generation_sha256": generation.get("generation_id"),
        "active_generation_recovery_required": generation[
            "recovery_required"
        ],
        "blocked_rights_count": _count(
            inventory, "blocked_or_deferred", "rights_blocked", "count"
        ),
        "credential_reservation_count": _count(
            inventory, "reservations", "counts", "credential"
        ),
        "error_count": len(inventory.get("errors", [])),
        "healthy_source_count": _count(
            inventory, "sources", "healthy", "count"
        ),
        "inventory_overall_state": inventory["overall_state"],
        "lower_priority_reservation_count": _count(
            inventory, "reservations", "counts", "lower_priority"
        ),
        "not_yet_refreshed_source_count": _count(
            inventory, "sources", "not_yet_refreshed", "count"
        ),
        "normal_reservation_count": _count(
            inventory, "reservations", "counts", "normal"
        ),
        "pending_candidate_count": len(
            inventory.get("pending_candidates", [])
        ),
        "target_quarantined_count": _count(
            inventory,
            "blocked_or_deferred",
            "target_quarantined",
            "count",
        ),
        "unhealthy_source_count": _count(
            inventory, "sources", "failed", "count"
        ),
    }


def _validate_timestamp(value, context):
    if not isinstance(value, str) or not UTC_RE.match(value):
        raise QueueContractError("%s timestamp is invalid" % context)
    try:
        parsed = datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise QueueContractError(
            "%s timestamp is invalid" % context
        ) from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise QueueContractError("%s timestamp is invalid" % context)
    return value


def _validate_inventory_summary(summary):
    keys = (
        "active_generation_recovery_required",
        "active_generation_sha256",
        "blocked_rights_count",
        "credential_reservation_count",
        "error_count",
        "healthy_source_count",
        "inventory_overall_state",
        "lower_priority_reservation_count",
        "normal_reservation_count",
        "not_yet_refreshed_source_count",
        "pending_candidate_count",
        "target_quarantined_count",
        "unhealthy_source_count",
    )
    _require_keys(summary, keys, "attempt.inventory_summary")
    generation = summary["active_generation_sha256"]
    if (
        generation is not None and
        (
            not isinstance(generation, str) or
            not SHA256_RE.match(generation)
        )
    ):
        raise QueueContractError("attempt generation is invalid")
    if not isinstance(
        summary["active_generation_recovery_required"],
        bool,
    ):
        raise QueueContractError("attempt recovery flag is invalid")
    if summary["inventory_overall_state"] not in INVENTORY_OVERALL_STATES:
        raise QueueContractError("attempt inventory state is invalid")
    for key in keys:
        if key in (
            "active_generation_recovery_required",
            "active_generation_sha256",
            "inventory_overall_state",
        ):
            continue
        _nonnegative_int(summary[key], "attempt.inventory_summary.%s" % key)
    return summary


def _validate_output_summary(value, context):
    allowed = frozenset((
        "configured_sources",
        "output_key_count",
        "overall_state",
        "schema_version",
        "source_id",
        "status",
    ))
    if (
        not isinstance(value, dict) or
        "output_key_count" not in value or
        not set(value).issubset(allowed)
    ):
        raise QueueContractError("%s output_summary is invalid" % context)
    output_key_count = _nonnegative_int(
        value["output_key_count"],
        "%s.output_key_count" % context,
    )
    if output_key_count < len(value) - 1:
        raise QueueContractError("%s output key count is invalid" % context)
    for key, item in value.items():
        if key == "output_key_count":
            continue
        if (
            not isinstance(item, (bool, int, str)) or
            isinstance(item, float)
        ):
            raise QueueContractError("%s output_summary is invalid" % context)


def _validate_task_result(
    value,
    index,
    attempt_started_at,
    attempt_finished_at,
    expected_task=None,
):
    context = "attempt.task_results[%d]" % index
    keys = (
        "action",
        "error",
        "error_type",
        "finished_at",
        "invocation_count",
        "operation_receipt_sha256",
        "output_summary",
        "started_at",
        "state",
        "task_id",
    )
    _require_keys(value, keys, context)
    if (
        not isinstance(value["action"], str) or
        value["action"] not in SUPPORTED_ACTIONS or
        not isinstance(value["task_id"], str) or
        not TOKEN_RE.match(value["task_id"]) or
        value["state"] not in PERSISTED_TASK_STATES
    ):
        raise QueueContractError("%s identity/state is invalid" % context)
    started_at = _validate_timestamp(
        value["started_at"],
        "%s.started_at" % context,
    )
    finished_at = _validate_timestamp(
        value["finished_at"],
        "%s.finished_at" % context,
    )
    if (
        started_at > finished_at or
        started_at < attempt_started_at or
        finished_at > attempt_finished_at
    ):
        raise QueueContractError("%s timestamp order is invalid" % context)
    invocation_count = _nonnegative_int(
        value["invocation_count"],
        "%s.invocation_count" % context,
    )
    if expected_task is not None:
        if (
            value["task_id"] != expected_task["task_id"] or
            value["action"] != expected_task["action"]
        ):
            raise QueueContractError("%s queue binding is invalid" % context)
        if expected_task["exception_kind"] is not None:
            permitted_states = frozenset(("EXCEPTION_RECORDED",))
        elif not expected_task["enabled"]:
            permitted_states = frozenset(("PENDING_DISABLED",))
        else:
            permitted_states = (
                SUCCESS_STATES |
                FAILURE_STATES |
                frozenset((
                    "BLOCKED_DEPENDENCY",
                    "DEFERRED_SERVICE_BUSY",
                    "WAITING_FOR_RECEIPT",
                ))
            )
        if value["state"] not in permitted_states:
            raise QueueContractError("%s task state is invalid" % context)

    if value["state"] == "SUCCESS":
        if (
            invocation_count != 1 or
            value["error"] is not None or
            value["error_type"] is not None or
            not isinstance(value["operation_receipt_sha256"], str) or
            not SHA256_RE.match(value["operation_receipt_sha256"])
        ):
            raise QueueContractError("%s success contract is invalid" % context)
        _validate_output_summary(value["output_summary"], context)
    elif value["state"] == "FAILED":
        if (
            invocation_count != 1 or
            not isinstance(value["error"], str) or
            not value["error"] or
            not isinstance(value["error_type"], str) or
            not TOKEN_RE.match(value["error_type"]) or
            not isinstance(value["operation_receipt_sha256"], str) or
            not SHA256_RE.match(value["operation_receipt_sha256"]) or
            value["output_summary"] is not None
        ):
            raise QueueContractError("%s failure contract is invalid" % context)
    elif value["state"] == "PRECONDITION_FAILED":
        if (
            invocation_count != 0 or
            not isinstance(value["error"], str) or
            not value["error"] or
            not isinstance(value["error_type"], str) or
            not TOKEN_RE.match(value["error_type"]) or
            value["operation_receipt_sha256"] is not None or
            value["output_summary"] is not None
        ):
            raise QueueContractError(
                "%s precondition contract is invalid" % context
            )
    elif value["state"] == "DEFERRED_SERVICE_BUSY":
        if (
            invocation_count != 0 or
            not isinstance(value["error"], str) or
            not value["error"] or
            not isinstance(value["error_type"], str) or
            not TOKEN_RE.match(value["error_type"]) or
            value["operation_receipt_sha256"] is not None or
            value["output_summary"] is not None
        ):
            raise QueueContractError(
                "%s deferred contract is invalid" % context
            )
    elif (
        invocation_count != 0 or
        value["error"] is not None or
        value["error_type"] is not None or
        value["operation_receipt_sha256"] is not None or
        value["output_summary"] is not None
    ):
        raise QueueContractError("%s noninvoked contract is invalid" % context)
    if invocation_count:
        expected_receipt = sha256_bytes(canonical_json_bytes({
            "action": value["action"],
            "error": value["error"],
            "error_type": value["error_type"],
            "finished_at": value["finished_at"],
            "output_summary": value["output_summary"],
            "started_at": value["started_at"],
            "state": value["state"],
            "task_id": value["task_id"],
        }))
        if value["operation_receipt_sha256"] != expected_receipt:
            raise QueueContractError(
                "%s operation receipt mismatch" % context
            )
    return value


def _state_from_attempt_summary(task_results, summary):
    result_states = {item["state"] for item in task_results}
    if (
        result_states.intersection(FAILURE_STATES) or
        summary["error_count"] > 0 or
        summary["unhealthy_source_count"] > 0 or
        summary["active_generation_recovery_required"] or
        summary["inventory_overall_state"] == "DEGRADED"
    ):
        return "DEGRADED"
    if (
        summary["pending_candidate_count"] > 0 or
        summary["inventory_overall_state"] == "READY_FOR_REVIEW"
    ):
        return "READY_FOR_REVIEW"
    if (
        summary["normal_reservation_count"] > 0 or
        summary["not_yet_refreshed_source_count"] > 0 or
        summary["inventory_overall_state"] == "WORKING" or
        result_states.intersection(WAITING_STATES)
    ):
        return "WORKING"
    if (
        summary["credential_reservation_count"] > 0 or
        summary["lower_priority_reservation_count"] > 0 or
        summary["blocked_rights_count"] > 0 or
        summary["target_quarantined_count"] > 0 or
        "EXCEPTION_RECORDED" in result_states or
        summary["inventory_overall_state"] == "BLOCKED_EXCEPTIONS_ONLY"
    ):
        return "BLOCKED_EXCEPTIONS_ONLY"
    return "SCOPED_WORK_COMPLETE"


def _validate_attempt(
    value,
    raw_bytes,
    attempt_path,
    attempts_root,
    loaded=None,
):
    keys = (
        "cycle_id",
        "dry_run",
        "finished_at",
        "inventory_summary",
        "overall_state",
        "overall_state_reason",
        "process_id",
        "queue_id",
        "queue_sha256",
        "replayed_existing_attempt",
        "schema_version",
        "started_at",
        "task_results",
    )
    _require_keys(value, keys, "attempt")
    if raw_bytes != canonical_json_bytes(value):
        raise QueueContractError("attempt bytes are not canonical")
    if value["schema_version"] != ATTEMPT_SCHEMA:
        raise QueueContractError("attempt schema_version is invalid")
    if value["dry_run"] is not False:
        raise QueueContractError("persisted attempt cannot be a dry run")
    if value["replayed_existing_attempt"] is not False:
        raise QueueContractError("persisted attempt replay flag is invalid")
    if (
        not isinstance(value["process_id"], int) or
        isinstance(value["process_id"], bool) or
        value["process_id"] < 1
    ):
        raise QueueContractError("attempt process_id is invalid")
    if (
        not isinstance(value["queue_id"], str) or
        not TOKEN_RE.match(value["queue_id"]) or
        not isinstance(value["queue_sha256"], str) or
        not SHA256_RE.match(value["queue_sha256"])
    ):
        raise QueueContractError("attempt queue identity is invalid")
    started_at = _validate_timestamp(
        value["started_at"],
        "attempt.started_at",
    )
    finished_at = _validate_timestamp(
        value["finished_at"],
        "attempt.finished_at",
    )
    if finished_at < started_at:
        raise QueueContractError("attempt timestamp order is invalid")
    expected_cycle_id = sha256_bytes(canonical_json_bytes({
        "process_id": value["process_id"],
        "queue_sha256": value["queue_sha256"],
        "started_at": started_at,
    }))
    if (
        value["cycle_id"] != expected_cycle_id or
        not isinstance(value["cycle_id"], str) or
        not SHA256_RE.match(value["cycle_id"])
    ):
        raise QueueContractError("attempt cycle identity is invalid")
    attempts_root = Path(attempts_root).resolve()
    attempt_path = Path(attempt_path)
    if (
        attempt_path.parent.resolve() != attempts_root or
        attempt_path.name != "%s.json" % value["cycle_id"]
    ):
        raise QueueContractError("attempt filename/cycle relationship is invalid")
    if loaded is not None and (
        value["queue_id"] != loaded.queue["queue_id"] or
        value["queue_sha256"] != loaded.queue_sha256
    ):
        raise QueueContractError("attempt queue binding is invalid")
    if value["overall_state"] not in PERSISTED_OVERALL_STATES:
        raise QueueContractError("attempt overall_state is invalid")
    if value["overall_state_reason"] != _state_reason(
        value["overall_state"]
    ):
        raise QueueContractError("attempt state reason is invalid")
    summary = _validate_inventory_summary(value["inventory_summary"])
    task_results = value["task_results"]
    if not isinstance(task_results, list) or not task_results:
        raise QueueContractError(
            "attempt task_results must be a nonempty list"
        )
    expected_tasks = loaded.queue["tasks"] if loaded is not None else None
    if expected_tasks is not None and len(task_results) != len(expected_tasks):
        raise QueueContractError("attempt task result count is invalid")
    seen = set()
    for index, result in enumerate(task_results):
        expected_task = (
            expected_tasks[index] if expected_tasks is not None else None
        )
        _validate_task_result(
            result,
            index,
            started_at,
            finished_at,
            expected_task=expected_task,
        )
        if result["task_id"] in seen:
            raise QueueContractError("attempt task result IDs are duplicated")
        seen.add(result["task_id"])
    if value["overall_state"] != _state_from_attempt_summary(
        task_results,
        summary,
    ):
        raise QueueContractError("attempt state/summary mismatch")
    return value


def _validate_status(value, raw_bytes, project_root, loaded=None):
    keys = (
        "active_generation_sha256",
        "attempt_path",
        "attempt_sha256",
        "cycle_id",
        "overall_state",
        "overall_state_reason",
        "queue_id",
        "queue_sha256",
        "schema_version",
        "task_state_counts",
        "updated_at",
    )
    _require_keys(value, keys, "latest status")
    if raw_bytes != canonical_json_bytes(value):
        raise QueueContractError("latest status bytes are not canonical")
    if value["schema_version"] != STATUS_SCHEMA:
        raise QueueContractError("latest status schema_version is invalid")
    if (
        not isinstance(value["cycle_id"], str) or
        not SHA256_RE.match(value["cycle_id"]) or
        not isinstance(value["queue_id"], str) or
        not TOKEN_RE.match(value["queue_id"]) or
        not isinstance(value["queue_sha256"], str) or
        not SHA256_RE.match(value["queue_sha256"]) or
        not isinstance(value["attempt_sha256"], str) or
        not SHA256_RE.match(value["attempt_sha256"])
    ):
        raise QueueContractError("latest status identity is invalid")
    if value["overall_state"] not in PERSISTED_OVERALL_STATES:
        raise QueueContractError("latest status state is invalid")
    if value["overall_state_reason"] != _state_reason(
        value["overall_state"]
    ):
        raise QueueContractError("latest status state reason is invalid")
    generation = value["active_generation_sha256"]
    if (
        generation is not None and
        (
            not isinstance(generation, str) or
            not SHA256_RE.match(generation)
        )
    ):
        raise QueueContractError("latest status generation is invalid")
    _validate_timestamp(value["updated_at"], "latest status.updated_at")

    relative = _safe_project_relative(value["attempt_path"])
    expected_relative = PurePosixPath(
        "live_data/runtime/autopilot/attempts"
    ) / ("%s.json" % value["cycle_id"])
    if relative != expected_relative:
        raise QueueContractError("latest status attempt path is invalid")
    project_root = Path(project_root).resolve()
    attempts_root = (
        project_root / "live_data" / "runtime" / "autopilot" / "attempts"
    ).resolve()
    attempt_path = project_root.joinpath(*relative.parts)
    attempt_bytes = _safe_regular_bytes(attempt_path, attempts_root)
    if sha256_bytes(attempt_bytes) != value["attempt_sha256"]:
        raise QueueContractError("latest status attempt hash mismatch")
    try:
        attempt = strict_json_loads(attempt_bytes)
    except (CanonicalDataError, TypeError, UnicodeError, ValueError) as exc:
        raise QueueContractError("latest status attempt is invalid") from exc
    _validate_attempt(
        attempt,
        attempt_bytes,
        attempt_path,
        attempts_root,
        loaded=loaded,
    )

    expected_counts = {
        state: sum(
            1 for item in attempt["task_results"]
            if item["state"] == state
        )
        for state in sorted({
            item["state"] for item in attempt["task_results"]
        })
    }
    counts = value["task_state_counts"]
    if not isinstance(counts, dict):
        raise QueueContractError("latest status task counts are invalid")
    for state, count in counts.items():
        if state not in PERSISTED_TASK_STATES:
            raise QueueContractError("latest status task state is invalid")
        _nonnegative_int(count, "latest status.task_state_counts.%s" % state)
        if count == 0:
            raise QueueContractError("latest status zero task count is invalid")
    if counts != expected_counts:
        raise QueueContractError("latest status task counts mismatch")
    if (
        value["cycle_id"] != attempt["cycle_id"] or
        value["queue_id"] != attempt["queue_id"] or
        value["queue_sha256"] != attempt["queue_sha256"] or
        value["overall_state"] != attempt["overall_state"] or
        value["overall_state_reason"] != attempt["overall_state_reason"] or
        value["updated_at"] != attempt["finished_at"] or
        generation != attempt["inventory_summary"][
            "active_generation_sha256"
        ]
    ):
        raise QueueContractError(
            "latest status attempt/state/generation binding mismatch"
        )
    return value


def _execute_tasks(
    loaded,
    project_root,
    executor,
    dry_run,
    clock,
):
    results = []
    results_by_id = {}
    for task in loaded.queue["tasks"]:
        now = clock()
        if task["exception_kind"] is not None:
            result = _task_result(
                task,
                "EXCEPTION_RECORDED",
                now,
                now,
            )
        elif not task["enabled"]:
            result = _task_result(
                task,
                "PENDING_DISABLED",
                now,
                now,
            )
        elif any(
            results_by_id[prerequisite]["state"] not in (
                SUCCESS_STATES |
                (frozenset(("DRY_RUN",)) if dry_run else frozenset())
            )
            for prerequisite in task["prerequisites"]
        ):
            result = _task_result(
                task,
                "BLOCKED_DEPENDENCY",
                now,
                now,
            )
        else:
            invoked = False
            try:
                if task["required_receipt"] is not None:
                    receipt_state = _check_binding(
                        project_root,
                        task["required_receipt"],
                        missing_state="MISSING",
                    )
                    if receipt_state == "MISSING":
                        result = _task_result(
                            task,
                            "WAITING_FOR_RECEIPT",
                            now,
                            now,
                        )
                        results.append(result)
                        results_by_id[task["task_id"]] = result
                        continue
                if task["artifact"] is not None:
                    _check_binding(project_root, task["artifact"])
                for predecessor in task["expected_predecessors"]:
                    _check_binding(project_root, predecessor)
                if dry_run:
                    result = _task_result(
                        task,
                        "DRY_RUN",
                        now,
                        now,
                    )
                else:
                    invoked = True
                    output = executor(
                        task["action"],
                        dict(task["parameters"]),
                        project_root,
                    )
                    if not isinstance(output, dict):
                        raise OperationError(
                            "operation result must be an object"
                        )
                    finished_at = clock()
                    result = _task_result(
                        task,
                        "SUCCESS",
                        now,
                        finished_at,
                        invocation_count=1,
                        output=output,
                    )
            except Exception as exc:
                finished_at = clock()
                if isinstance(exc, ServiceBusyError):
                    state = "DEFERRED_SERVICE_BUSY"
                    invoked = False
                elif isinstance(exc, QueueContractError):
                    state = "PRECONDITION_FAILED"
                else:
                    state = "FAILED"
                result = _task_result(
                    task,
                    state,
                    now,
                    finished_at,
                    invocation_count=1 if invoked else 0,
                    error=exc,
                )
        results.append(result)
        results_by_id[task["task_id"]] = result
    return results


def run_cycle(
    project_root,
    queue_path=None,
    dry_run=False,
    executor=None,
    inventory_provider=None,
    clock=None,
    process_id=None,
):
    """Run one deterministic at-most-once cycle; never retry internally."""
    project_root = Path(project_root).resolve()
    loaded = load_queue(project_root, queue_path)
    clock = clock or utc_now
    process_id = os.getpid() if process_id is None else process_id
    if (
        not isinstance(process_id, int) or
        isinstance(process_id, bool) or
        process_id < 1
    ):
        raise QueueContractError("process_id is invalid")
    started_at = clock()
    cycle_id = sha256_bytes(canonical_json_bytes({
        "process_id": process_id,
        "queue_sha256": loaded.queue_sha256,
        "started_at": started_at,
    }))
    provider = inventory_provider or (
        lambda: _build_feed_factory_inventory(project_root)
    )
    default_executor_requested = executor is None
    reusable_inventory = None
    if (
        default_executor_requested and
        not any(
            task["action"] in MUTATING_ACTIONS
            for task in loaded.queue["tasks"]
            if task["enabled"]
        )
    ):
        reusable_inventory = _inventory_or_error(provider)
    executor = executor or DefaultExecutor(reusable_inventory)
    if dry_run:
        task_results = _execute_tasks(
            loaded,
            project_root,
            executor,
            True,
            clock,
        )
        inventory = (
            reusable_inventory
            if reusable_inventory is not None
            else _inventory_or_error(provider)
        )
        overall_state = derive_overall_state(
            loaded.queue,
            task_results,
            inventory,
        )
        return {
            "cycle_id": cycle_id,
            "dry_run": True,
            "finished_at": clock(),
            "inventory_summary": _inventory_summary(inventory),
            "overall_state": overall_state,
            "overall_state_reason": _state_reason(overall_state),
            "process_id": process_id,
            "queue_id": loaded.queue["queue_id"],
            "queue_sha256": loaded.queue_sha256,
            "replayed_existing_attempt": False,
            "schema_version": ATTEMPT_SCHEMA,
            "started_at": started_at,
            "task_results": task_results,
        }

    autopilot_root, attempts_root = _safe_output_directory(project_root)
    descriptor = _open_lock(autopilot_root / "cycle.lock")
    if descriptor is None:
        return {
            "cycle_id": cycle_id,
            "dry_run": False,
            "finished_at": clock(),
            "inventory_summary": None,
            "overall_state": "LOCKED_OUT",
            "overall_state_reason": _state_reason("LOCKED_OUT"),
            "process_id": process_id,
            "queue_id": loaded.queue["queue_id"],
            "queue_sha256": loaded.queue_sha256,
            "replayed_existing_attempt": False,
            "schema_version": ATTEMPT_SCHEMA,
            "started_at": started_at,
            "task_results": [],
        }
    try:
        attempt_path = attempts_root / ("%s.json" % cycle_id)
        if attempt_path.exists():
            prior_bytes = _safe_regular_bytes(attempt_path, attempts_root)
            try:
                prior = strict_json_loads(prior_bytes)
            except (
                CanonicalDataError,
                TypeError,
                UnicodeError,
                ValueError,
            ) as exc:
                raise QueueContractError(
                    "persisted attempt is invalid"
                ) from exc
            _validate_attempt(
                prior,
                prior_bytes,
                attempt_path,
                attempts_root,
                loaded=loaded,
            )
            replay = dict(prior)
            replay["replayed_existing_attempt"] = True
            return replay
        task_results = _execute_tasks(
            loaded,
            project_root,
            executor,
            False,
            clock,
        )
        inventory = (
            reusable_inventory
            if reusable_inventory is not None
            else _inventory_or_error(provider)
        )
        overall_state = derive_overall_state(
            loaded.queue,
            task_results,
            inventory,
        )
        attempt = {
            "cycle_id": cycle_id,
            "dry_run": False,
            "finished_at": clock(),
            "inventory_summary": _inventory_summary(inventory),
            "overall_state": overall_state,
            "overall_state_reason": _state_reason(overall_state),
            "process_id": process_id,
            "queue_id": loaded.queue["queue_id"],
            "queue_sha256": loaded.queue_sha256,
            "replayed_existing_attempt": False,
            "schema_version": ATTEMPT_SCHEMA,
            "started_at": started_at,
            "task_results": task_results,
        }
        attempt_bytes = canonical_json_bytes(attempt)
        _validate_attempt(
            attempt,
            attempt_bytes,
            attempt_path,
            attempts_root,
            loaded=loaded,
        )
        atomic_write(attempt_path, attempt_bytes)
        latest = {
            "active_generation_sha256": attempt[
                "inventory_summary"
            ]["active_generation_sha256"],
            "attempt_path": str(attempt_path.relative_to(project_root)),
            "attempt_sha256": sha256_bytes(attempt_bytes),
            "cycle_id": cycle_id,
            "overall_state": overall_state,
            "overall_state_reason": attempt["overall_state_reason"],
            "queue_id": loaded.queue["queue_id"],
            "queue_sha256": loaded.queue_sha256,
            "schema_version": STATUS_SCHEMA,
            "task_state_counts": {
                state: sum(
                    1
                    for item in task_results
                    if item["state"] == state
                )
                for state in sorted({
                    item["state"] for item in task_results
                })
            },
            "updated_at": attempt["finished_at"],
        }
        latest_bytes = canonical_json_bytes(latest)
        _validate_status(
            latest,
            latest_bytes,
            project_root,
            loaded=loaded,
        )
        atomic_write(autopilot_root / "latest_status.json", latest_bytes)
        return attempt
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def read_latest_status(project_root, queue_path=None):
    project_root = Path(project_root).resolve()
    autopilot_root = (
        project_root / "live_data" / "runtime" / "autopilot"
    )
    path = autopilot_root / "latest_status.json"
    data = _safe_regular_bytes(
        path,
        autopilot_root,
        missing_ok=True,
    )
    if data is None:
        return {
            "overall_state": "NOT_RUN",
            "schema_version": STATUS_SCHEMA,
        }
    try:
        value = strict_json_loads(data)
    except (
        CanonicalDataError,
        TypeError,
        UnicodeError,
        ValueError,
    ) as exc:
        raise QueueContractError("latest autopilot status is invalid") from exc
    if (
        isinstance(value, dict) and
        value.get("schema_version") == LEGACY_STATUS_SCHEMA
    ):
        return {
            "overall_state": "NOT_RUN",
            "schema_version": STATUS_SCHEMA,
            "superseded_status_schema": LEGACY_STATUS_SCHEMA,
        }
    loaded = load_queue(project_root, queue_path)
    return _validate_status(
        value,
        data,
        project_root,
        loaded=loaded,
    )
