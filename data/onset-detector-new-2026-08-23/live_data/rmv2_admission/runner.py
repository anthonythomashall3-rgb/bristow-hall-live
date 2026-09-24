"""Strict batch admission runner for the Recession Monitor V2 live-data store.

The runner drains a reviewed, immutable approved-draft queue through the exact
admission cadence proven in prior sessions:

    (barrier must be free) -> bootout live-data + watchdog + data-autopilot
    -> for each draft in the batch (<= 5), sequentially:
           feed-factory prepare --draft
           feed-factory apply    --bundle <manifest.json>
           refresh --source <source_id>
    -> verify (status PASS + config-generation closure PASS + head count)
    -> regenerate the public bundle
    -> keyless structural key-leak scan
    -> bootstrap live-data + watchdog + data-autopilot

Design invariants (all fail-closed):

* Single coordinator. A dedicated ``admission/runner.lock`` flock serialises cycles;
  a second concurrent cycle returns ``LOCKED_OUT`` and touches nothing.
* Never fight the publication barrier. The runner refuses to bootout the
  scheduler while the project-wide writer barrier ``runtime/refresh.lock`` is
  held by a live refresh; it defers
  instead (``DEFERRED_BARRIER_HELD``). It never SIGTERM/SIGKILLs a refresh.
* Hard stop to green. On any failed per-draft or post-batch check the runner
  stops the queue, runs one clean full refresh to deterministically rebuild the
  matrix + generation (self-heal), re-verifies, and reports HALTED_GREEN or
  HALTED_DEGRADED. It never proceeds to a further batch after a failure.
* Batch-refresh is unsupported by the store (proven prior session): the runner
  always refreshes per admission with ``--source``.
* No AI, no secret value ever read. Only the ``secret_env`` NAME is referenced;
  the key-leak scan is structural (looks for ``api_key=`` / bearer tokens), it
  never reads ``local.env``.
* Scientific outputs are never bound; ``scientific_binding`` must stay false.

Every external effect is injected (``run_cli``, ``stop_agents``,
``start_agents``, ``barrier_free``, ``read_state``, ``publish_bundle``,
``key_scan``, ``now``) so a cycle is fully hermetic under test. The defaults in
:class:`DefaultOperations` wire the real subprocess CLI, launchd, and bundle
publisher.
"""

from __future__ import absolute_import

import fcntl
import os
import plistlib
import re
import stat
import subprocess
import sys
import time
from pathlib import Path, PurePosixPath

from live_data.rmv2_live.canonical import (
    CanonicalDataError,
    atomic_write,
    canonical_json_bytes,
    sha256_bytes,
    strict_json_loads,
    utc_now,
)


QUEUE_SCHEMA = "recession-monitor-v2.admission-queue.v1"
JOURNAL_SCHEMA = "recession-monitor-v2.admission-journal-entry.v1"
STATUS_SCHEMA = "recession-monitor-v2.admission-latest-status.v1"
DISCOVERY_SCHEMA = "recession-monitor-v2.feed-discovery-spec.v1"

TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
# B-FAST-1 §3 (rulebook conformance, NOT a raised pin). The rulebook caps *new
# parser shapes* at 5 per cycle (§6.1) while allowing *unlimited instances of a
# proven shape* (§6.2). The prior constant ``MAX_BATCH_CEILING`` was applied to
# the *total* batch size, conflating the two and throttling proven-shape drain
# to 5/cycle. This limit now constrains new shapes only; a proven shape is
# unbounded per cycle. The numeric 5 is unchanged — this is a scope correction,
# not a loosened threshold.
MAX_NEW_SHAPES_PER_BATCH = 5

# Structural, keyless leak signatures. These never require reading a secret
# value; a keyless publisher route or a public bundle must not embed a query
# api_key or an HTTP authorization token.
LEAK_PATTERNS = (
    re.compile(rb"api[_-]?key\s*=", re.IGNORECASE),
    re.compile(rb"\bauthorization\b\s*[:=]\s*(?:bearer|basic)\b", re.IGNORECASE),
    re.compile(rb"\b(?:bearer|basic)\s+[A-Za-z0-9._~+/-]{8,}=*", re.IGNORECASE),
)

# Launchd labels quiesced during a store-mutating batch, in bootout order. The
# scheduler (live-data) is booted out last is unnecessary here; order is only
# cosmetic because each bootout is independent, but keep the scheduler first so
# no refresh tick can start after the barrier check.
AGENT_LABELS = (
    "com.anthonyhall.recession-monitor-v2.live-data",
    "com.anthonyhall.recession-monitor-v2.watchdog",
    "com.anthonyhall.recession-monitor-v2.data-autopilot",
)

# The admission runner is the single sanctioned store writer, but it runs
# ON-DEMAND only: an operator invokes live_data/scripts/admission_runner.command
# (or `python -m live_data.rmv2_admission ... cycle`). It is deliberately NOT a
# resident or scheduled launchd job. A StartInterval admission-runner tick was a
# SECOND, uncoordinated writer that raced a manual batch and half-admitted a
# source with stale code (PHASE2 B1.3 root cause); its plist is quarantined
# under _quarantined_plists/. Its label must never appear in AGENT_LABELS: it
# cannot quiesce itself, and start_agents() re-bootstraps every AGENT_LABELS
# member, which would re-arm exactly that rogue timer.
#
# AGENT_LABELS is not trusted to stay hand-correct. The launchd source dir
# live_data/launchd/ is the source of truth for what the installers deploy;
# assert_agent_labels_cover_launchd_source() fails if any plist there is not a
# known resident agent, so a newly-dropped writer cannot drift in silently.


def launchd_source_labels(project_root):
    """Labels of every reviewed launchd plist in live_data/launchd/."""
    launchd_dir = Path(project_root).resolve() / "live_data" / "launchd"
    labels = set()
    if not launchd_dir.is_dir():
        return labels
    for path in sorted(launchd_dir.glob("*.plist")):
        with path.open("rb") as handle:
            value = plistlib.load(handle)
        label = value.get("Label")
        if isinstance(label, str) and label:
            labels.add(label)
    return labels


def assert_agent_labels_cover_launchd_source(project_root):
    """Raise if any deployed launchd plist is not in AGENT_LABELS (drift)."""
    installed = launchd_source_labels(project_root)
    uncovered = installed - set(AGENT_LABELS)
    if uncovered:
        raise AdmissionContractError(
            "launchd plists not registered in AGENT_LABELS (uncoordinated "
            "writers): %s" % ", ".join(sorted(uncovered))
        )
    return installed


# The two functions above police the repo *source* dir (live_data/launchd/).
# B-SAFE-1 §1.4 closes the other half of the drift: the plists actually
# INSTALLED under ~/Library/LaunchAgents/. This batch owns only V2, not the
# predecessor (Codex BHI2 / Bristow-Hall) program (owner decision, B-SAFE-1 Q1).
#
# The discriminator is the plist's TARGET PATH, not its label string: several
# predecessor jobs (monitor-v2, p4-v2, p4-v2-sync, p4-v2-watchdog) carry a "v2"
# token in the label yet run scripts under ~/.local/share/recession-monitor/ or
# ~/Projects/RecessionMonitor/ — the predecessor tree, out of scope. A plist is
# V2-scoped iff it references the V2 repo root, i.e. it can write into THIS
# store. That is exactly the second-writer class §1.5 protects against.
INSTALLED_LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"


def _v2_repo_root():
    """Repo root inferred from this module's location (…/live_data/rmv2_admission/runner.py)."""
    return Path(__file__).resolve().parents[2]


def _plist_path_tokens(value):
    """Every filesystem string a plist can launch or watch, as a token list."""
    prog = value.get("ProgramArguments") or ([value.get("Program")] if value.get("Program") else [])
    parts = [str(x) for x in (prog or [])]
    parts.extend(str(w) for w in (value.get("WatchPaths") or []))
    wd = value.get("WorkingDirectory")
    if wd:
        parts.append(str(wd))
    return parts


def _plist_program_haystack(value):
    """Every filesystem string a plist can launch or watch, joined for matching."""
    return " ".join(_plist_path_tokens(value))


def plist_targets_v2_repo(value, v2_repo=None):
    """True if a loaded plist launches or watches anything inside the V2 repo.

    Both sides are resolved with os.path.realpath before comparing, so a plist
    that froze a PRE-RELOCATION absolute path (e.g. a quarantined copy under
    ~/Desktop/RecessionMonitor 2/) still classifies against the current repo
    location when a relocation shim symlink resolves it there (B-RELO-TESTFIX,
    §18.1 — test untouched). Match is COMPONENT-WISE (descendant-or-equal),
    never substring, so a sibling tree like ``<repo>-evil`` cannot match."""
    repo = PurePosixPath(os.path.realpath(str(v2_repo) if v2_repo else str(_v2_repo_root()))).parts
    for token in _plist_path_tokens(value):
        token = str(token)
        # Only ABSOLUTE tokens are filesystem targets; a bare arg ("-dimsu",
        # "cycle", "-m") must not be realpath-joined onto the CWD and mistaken
        # for a repo write. realpath resolves relocation shims (frozen
        # pre-move paths) for the absolute ones.
        if not os.path.isabs(token):
            continue
        tok = PurePosixPath(os.path.realpath(token)).parts
        if len(tok) >= len(repo) and tok[: len(repo)] == repo:
            return True
    return False


# The V2 external read-set — every path OUTSIDE the repo that a model component
# reads as an input — is DECLARED, not hand-listed (§1.6). The declaration is
# the source of truth; this checker DERIVES its second-writer read-roots from it,
# so a new declared input widens the check automatically and a comment listing
# paths can never drift out of sync with what code actually reads.
EXTERNAL_READ_ROOTS_CONFIG = "live_data/config/external_read_roots.v1.json"


def declared_external_read_roots(v2_repo=None):
    """Absolute read-root path strings declared in external_read_roots.v1.json,
    or [] if the manifest is absent/unreadable."""
    repo = Path(v2_repo) if v2_repo else _v2_repo_root()
    config = repo / EXTERNAL_READ_ROOTS_CONFIG
    try:
        data = strict_json_loads(config.read_text(encoding="utf-8"))
    except (OSError, ValueError, CanonicalDataError):
        return []
    roots = []
    for entry in data.get("roots", []):
        path = entry.get("path")
        if isinstance(path, str) and path:
            roots.append(path)
    return roots


def _paths_comparable(token, root):
    """True iff filesystem paths ``token`` and ``root`` lie on one root-to-leaf
    line: one is an ancestor of, or equal to, the other — compared COMPONENT-WISE,
    never by substring. A job targeting an ANCESTOR of a read-root can write into
    it; a DESCENDANT writes inside it; a SIBLING subtree cannot. This is the
    'bidirectional containment' the read-set blocker measured: only the jobs whose
    WorkingDirectory is the raw tree's parent (or the tree itself) intersect it."""
    t = PurePosixPath(token).parts
    r = PurePosixPath(root).parts
    if not t or not r:
        return False
    n = min(len(t), len(r))
    return t[:n] == r[:n]


def plist_targets_external_read_root(value, read_roots=None):
    """True if any path a plist launches or watches is comparable to (ancestor
    of / equal to / inside) a declared external read-root — i.e. the job can
    write into a tree the V2 model reads."""
    if read_roots is None:
        read_roots = declared_external_read_roots()
    for token in _plist_path_tokens(value):
        for root in read_roots:
            if _paths_comparable(token, root):
                return True
    return False


def installed_v2_repo_labels(launch_agents_dir=None, v2_repo=None):
    """{label: path} for every installed plist that targets the V2 repo.

    Classifies on the plist body (ProgramArguments/WatchPaths), never the
    filename, so the _quarantined_plists/ `installed__<label>.plist` copies and
    predecessor "v2"-named labels both resolve correctly.
    """
    directory = Path(launch_agents_dir) if launch_agents_dir else INSTALLED_LAUNCH_AGENTS_DIR
    found = {}
    if not directory.is_dir():
        return found
    for path in sorted(directory.glob("*.plist")):
        try:
            with path.open("rb") as handle:
                value = plistlib.load(handle)
        except Exception:
            continue
        label = value.get("Label")
        if not (isinstance(label, str) and label):
            continue
        if plist_targets_v2_repo(value, v2_repo):
            found[label] = path
    return found


def installed_v2_scoped_labels(launch_agents_dir=None, v2_repo=None, read_roots=None):
    """{label: path} for every installed plist that can WRITE into either THIS
    store (V2 repo root) OR any declared external read-root the V2 model reads
    (external_read_roots.v1.json). The read-set is DERIVED from that file, never
    hand-listed (§1.6). Classifies on the plist body, never the filename."""
    if read_roots is None:
        read_roots = declared_external_read_roots(v2_repo)
    directory = Path(launch_agents_dir) if launch_agents_dir else INSTALLED_LAUNCH_AGENTS_DIR
    found = {}
    if not directory.is_dir():
        return found
    for path in sorted(directory.glob("*.plist")):
        try:
            with path.open("rb") as handle:
                value = plistlib.load(handle)
        except Exception:
            continue
        label = value.get("Label")
        if not (isinstance(label, str) and label):
            continue
        if plist_targets_v2_repo(value, v2_repo) or plist_targets_external_read_root(
            value, read_roots
        ):
            found[label] = path
    return found


def assert_installed_v2_plists_registered(launch_agents_dir=None, v2_repo=None, read_roots=None):
    """Raise if any INSTALLED plist that can write into THIS store OR a declared
    external read-root is not in AGENT_LABELS (B-SAFE-1 §1.4 + B-EXTREAD-DECLARE).
    A newly-dropped writer into a tree the V2 model reads cannot drift in
    silently; the failure names the exact offending label(s)."""
    scoped = installed_v2_scoped_labels(launch_agents_dir, v2_repo, read_roots)
    uncovered = sorted(label for label in scoped if label not in set(AGENT_LABELS))
    if uncovered:
        raise AdmissionContractError(
            "installed launchd plists targeting the V2 repo or a declared "
            "external read-root but not registered in AGENT_LABELS "
            "(uncoordinated writers): %s" % ", ".join(uncovered)
        )
    return set(scoped)

# Terminal cycle states.
STATE_ALL_ADMITTED = "ALL_ADMITTED"
STATE_BATCH_GREEN_MORE_PENDING = "BATCH_GREEN_MORE_PENDING"
STATE_NOOP_ALL_ADMITTED = "NOOP_ALL_ADMITTED"
STATE_DEFERRED_BARRIER_HELD = "DEFERRED_BARRIER_HELD"
STATE_LOCKED_OUT = "LOCKED_OUT"
STATE_HALTED_GREEN = "HALTED_GREEN"
STATE_HALTED_DEGRADED = "HALTED_DEGRADED"

GREEN_TERMINAL_STATES = frozenset((
    STATE_ALL_ADMITTED,
    STATE_BATCH_GREEN_MORE_PENDING,
    STATE_NOOP_ALL_ADMITTED,
    STATE_DEFERRED_BARRIER_HELD,
    STATE_HALTED_GREEN,
))


class AdmissionContractError(CanonicalDataError):
    """The approved-draft queue or a bound draft failed a fail-closed check."""


class AdmissionOperationError(RuntimeError):
    """An injected admission operation failed exactly once during a cycle."""


# ---------------------------------------------------------------------------
# Safe path + file helpers (mirrors the autopilot runner's fail-closed reads).
# ---------------------------------------------------------------------------


def _safe_project_relative(value):
    if (
        not isinstance(value, str) or
        not value or
        "\\" in value or
        "\x00" in value
    ):
        raise AdmissionContractError("unsafe project-relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(
        part in ("", ".", "..") for part in path.parts
    ):
        raise AdmissionContractError("unsafe project-relative path")
    return path


def _reject_linked_ancestors(path, root):
    root = Path(root).resolve()
    path = Path(path)
    try:
        relative = path.relative_to(root)
    except ValueError:
        raise AdmissionContractError("path escaped the project root")
    cursor = root
    for part in relative.parts[:-1]:
        cursor = cursor / part
        info = cursor.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise AdmissionContractError("project path ancestor is unsafe")


def _safe_regular_bytes(path, allowed_root, missing_ok=False):
    root = Path(allowed_root).resolve()
    input_path = Path(path)
    path = input_path.parent.resolve() / input_path.name
    try:
        path.relative_to(root)
    except ValueError:
        raise AdmissionContractError("path escaped the allowed root")
    try:
        _reject_linked_ancestors(path, root)
        final_info = path.lstat()
        if (
            stat.S_ISLNK(final_info.st_mode) or
            not stat.S_ISREG(final_info.st_mode) or
            final_info.st_nlink != 1
        ):
            raise AdmissionContractError(
                "path must be one regular unlinked file: %s" % path
            )
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(str(path), flags)
    except FileNotFoundError:
        if missing_ok:
            return None
        raise AdmissionContractError("required file is missing: %s" % path)
    except OSError as exc:
        raise AdmissionContractError(
            "file cannot be safely opened: %s" % path
        ) from exc
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise AdmissionContractError(
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
                raise AdmissionContractError("file exceeds read limit")
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _require_keys(mapping, expected, context):
    if not isinstance(mapping, dict):
        raise AdmissionContractError("%s must be an object" % context)
    missing = sorted(set(expected) - set(mapping))
    extra = sorted(set(mapping) - set(expected))
    if missing or extra:
        raise AdmissionContractError(
            "%s key mismatch; missing=%r extra=%r" % (context, missing, extra)
        )


def _scan_secret_values(value, context):
    """Reject embedded secret VALUES; secret NAMES (``secret_env``) are fine."""
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "secret_env":
                if item is not None and (
                    not isinstance(item, str) or not TOKEN_RE.match(item)
                ):
                    raise AdmissionContractError(
                        "%s secret_env must be a NAME token" % context
                    )
                continue
            if key == "secret_required":
                continue
            lowered = key.lower()
            # Substring match for markers with no benign homograph in config key
            # names. 'token' is matched only as a whole delimiter-bounded word so
            # the benign 'missing_tokens' (a missing-value token list) is not a
            # false positive, while 'token'/'api_token'/'access_token'/'auth_token'
            # are still caught. This narrows (never widens) what passes: the only
            # keys newly allowed are token-as-substring names like 'missing_tokens'.
            if (
                (any(tok in lowered for tok in ("api_key", "apikey",
                                                "password", "secret")) or
                 "token" in re.split(r"[^a-z0-9]+", lowered)) and
                item not in (None, False, "")
            ):
                raise AdmissionContractError(
                    "%s embeds a secret-like value at %s" % (context, key)
                )
            _scan_secret_values(item, context)
    elif isinstance(value, list):
        for item in value:
            _scan_secret_values(item, context)
    elif isinstance(value, str):
        if value.lower().startswith(("bearer ", "basic ")):
            raise AdmissionContractError(
                "%s embeds an authorization token" % context
            )


# ---------------------------------------------------------------------------
# Queue loading + validation.
# ---------------------------------------------------------------------------


def default_queue_path(project_root):
    return (
        Path(project_root) / "live_data" / "config" /
        "admission_queue.v1.json"
    )


# ---------------------------------------------------------------------------
# Shape gating (B-FAST-1 §3). A "shape" is the deterministic, byte-derived
# triple (adapter_id, parser_version, response_schema_sha256). A shape is
# PROVEN iff the content-addressed store already holds a green acquisition
# receipt for a currently-configured source with that exact shape. This is a
# measurement, not a judgement (amended §1.1a): unknown is never proven.
#
# Today ``parser_version`` and ``response_schema_sha256`` are not yet declared
# on drafts or in sources.v1.json, so the shape collapses to adapter
# granularity. That is a conservative coarsening, NOT an oracle weakening: the
# shape gate only controls how many NEW code paths admit per cycle; every
# admitted source, proven or new, still runs the full per-draft prepare/apply/
# refresh plus the post-batch verify + key-leak scan + hard-stop-to-green. The
# moment a draft declares parser_version/response_schema_sha256 the shape
# auto-refines with no code change. A parser code change not reflected in a
# declared parser_version would not re-gate — recorded as a known limitation.
# ---------------------------------------------------------------------------

GREEN_RECEIPT_OUTCOMES = ("retrieved_and_validated",)


def _shape_from_source(source):
    """Byte-derived shape triple for a source/draft-source mapping."""
    return (
        source.get("adapter"),
        source.get("parser_version"),
        source.get("response_schema_sha256"),
    )


def shape_of(draft):
    """Return the (adapter_id, parser_version, response_schema_sha256) triple.

    Accepts either a resolved queue entry (carries a precomputed ``shape``) or a
    full feed-discovery draft (carries ``source``).
    """
    if isinstance(draft, dict) and "shape" in draft:
        return tuple(draft["shape"])
    source = draft.get("source", draft) if isinstance(draft, dict) else {}
    return _shape_from_source(source)


def _load_config_sources(project_root):
    path = Path(project_root) / "live_data" / "config" / "sources.v1.json"
    try:
        data = path.read_bytes()
        config = strict_json_loads(data)
    except (OSError, CanonicalDataError, UnicodeError, ValueError):
        return []
    sources = config.get("sources") if isinstance(config, dict) else config
    return sources if isinstance(sources, list) else []


def _has_green_receipt(project_root, source_id):
    """True iff store/receipts/<source_id>/ holds >=1 green acquisition receipt."""
    if not isinstance(source_id, str) or not source_id:
        return False
    receipt_dir = (
        Path(project_root) / "live_data" / "store" / "receipts" / source_id
    )
    if not receipt_dir.is_dir():
        return False
    for entry in sorted(receipt_dir.iterdir()):
        if entry.suffix != ".json" or not entry.is_file():
            continue
        try:
            receipt = strict_json_loads(entry.read_bytes())
        except (OSError, CanonicalDataError, UnicodeError, ValueError):
            continue
        if receipt.get("outcome") in GREEN_RECEIPT_OUTCOMES:
            return True
    return False


def _shape_index(sources):
    index = {}
    for source in sources:
        if not isinstance(source, dict):
            continue
        index.setdefault(_shape_from_source(source), []).append(
            source.get("source_id")
        )
    return index


def is_proven_shape(project_root, shape):
    """True iff a configured source with this exact shape has a green receipt.

    An unmeasurable shape (missing adapter) is never proven; a corpus that
    cannot answer returns False.
    """
    shape = tuple(shape)
    if shape[0] is None:
        return False
    index = _shape_index(_load_config_sources(project_root))
    for source_id in index.get(shape, []):
        if _has_green_receipt(project_root, source_id):
            return True
    return False


def _proven_shape_set(project_root, candidate_shapes):
    """Resolve which of ``candidate_shapes`` are proven, reading the corpus once."""
    candidates = {tuple(s) for s in candidate_shapes if s[0] is not None}
    if not candidates:
        return frozenset()
    index = _shape_index(_load_config_sources(project_root))
    proven = set()
    for shape in candidates:
        for source_id in index.get(shape, []):
            if _has_green_receipt(project_root, source_id):
                proven.add(shape)
                break
    return frozenset(proven)


def load_queue(project_root, queue_path=None):
    """Read and fail-closed validate one approved-draft queue (no execution)."""
    project_root = Path(project_root).resolve()
    if queue_path is None:
        queue_path = default_queue_path(project_root)
    queue_path = Path(queue_path)
    if not queue_path.is_absolute():
        queue_path = project_root / queue_path
    data = _safe_regular_bytes(queue_path, project_root)
    try:
        queue = strict_json_loads(data)
    except (CanonicalDataError, UnicodeError, ValueError) as exc:
        raise AdmissionContractError("queue is not strict JSON") from exc
    _require_keys(
        queue,
        ("drafts", "policy", "queue_id", "schema_version"),
        "queue",
    )
    if queue["schema_version"] != QUEUE_SCHEMA:
        raise AdmissionContractError("unsupported queue schema")
    if (
        not isinstance(queue["queue_id"], str) or
        not TOKEN_RE.match(queue["queue_id"])
    ):
        raise AdmissionContractError("queue_id is invalid")
    _validate_policy(queue["policy"])
    max_batch = queue["policy"]["max_batch"]
    drafts = queue["drafts"]
    if not isinstance(drafts, list) or not drafts:
        raise AdmissionContractError("queue drafts must be a nonempty list")
    seen_ids = set()
    seen_paths = set()
    resolved = []
    for index, entry in enumerate(drafts):
        resolved.append(_validate_draft_entry(
            project_root, entry, seen_ids, seen_paths, index,
        ))
    canonical = canonical_json_bytes(queue)
    if data not in (canonical, canonical + b"\n"):
        raise AdmissionContractError("queue must use canonical JSON bytes")
    return {
        "path": queue_path,
        "queue_id": queue["queue_id"],
        "queue_sha256": sha256_bytes(data),
        "max_batch": max_batch,
        "drafts": resolved,
    }


def _validate_policy(policy):
    _require_keys(
        policy,
        (
            "allow_store_mutation",
            "max_batch",
            "no_ai",
            "scientific_binding",
        ),
        "policy",
    )
    for field in ("allow_store_mutation", "no_ai", "scientific_binding"):
        if not isinstance(policy[field], bool):
            raise AdmissionContractError("policy.%s must be boolean" % field)
    if not policy["no_ai"]:
        raise AdmissionContractError("policy no_ai must remain true")
    if policy["scientific_binding"]:
        raise AdmissionContractError(
            "policy scientific_binding must remain false"
        )
    if not policy["allow_store_mutation"]:
        raise AdmissionContractError(
            "policy allow_store_mutation must be true to admit"
        )
    # policy.max_batch is the per-cycle limit on NEW parser shapes (§6.1); it no
    # longer bounds total sources, because proven shapes are unlimited (§6.2).
    max_batch = policy["max_batch"]
    if (
        not isinstance(max_batch, int) or
        isinstance(max_batch, bool) or
        max_batch < 1 or
        max_batch > MAX_NEW_SHAPES_PER_BATCH
    ):
        raise AdmissionContractError(
            "policy.max_batch (new-shape limit) must be an integer in 1..%d"
            % MAX_NEW_SHAPES_PER_BATCH
        )


def _validate_draft_entry(project_root, entry, seen_ids, seen_paths, index):
    context = "drafts[%d]" % index
    _require_keys(
        entry,
        ("draft_path", "reviewed", "sha256", "source_id"),
        context,
    )
    if entry["reviewed"] is not True:
        raise AdmissionContractError("%s reviewed must be true" % context)
    source_id = entry["source_id"]
    if not isinstance(source_id, str) or not TOKEN_RE.match(source_id):
        raise AdmissionContractError("%s source_id is invalid" % context)
    if source_id in seen_ids:
        raise AdmissionContractError("duplicate source_id: %s" % source_id)
    seen_ids.add(source_id)
    relative = _safe_project_relative(entry["draft_path"])
    if entry["draft_path"] in seen_paths:
        raise AdmissionContractError("duplicate draft_path")
    seen_paths.add(entry["draft_path"])
    if (
        not isinstance(entry["sha256"], str) or
        not SHA256_RE.match(entry["sha256"])
    ):
        raise AdmissionContractError("%s sha256 is invalid" % context)
    draft_path = project_root.joinpath(*relative.parts)
    draft_bytes = _safe_regular_bytes(draft_path, project_root)
    if sha256_bytes(draft_bytes) != entry["sha256"]:
        raise AdmissionContractError(
            "%s draft bytes do not match the reviewed sha256" % context
        )
    try:
        draft = strict_json_loads(draft_bytes)
    except (CanonicalDataError, UnicodeError, ValueError) as exc:
        raise AdmissionContractError("%s draft is not strict JSON" % context) \
            from exc
    if not isinstance(draft, dict) or draft.get("schema_version") != \
            DISCOVERY_SCHEMA:
        raise AdmissionContractError(
            "%s draft is not a feed-discovery-spec" % context
        )
    source = draft.get("source")
    if not isinstance(source, dict):
        raise AdmissionContractError("%s draft source is invalid" % context)
    if source.get("source_id") != source_id:
        raise AdmissionContractError(
            "%s draft source_id does not match the entry" % context
        )
    if source.get("enabled") is not True:
        raise AdmissionContractError(
            "%s draft source must be enabled" % context
        )
    _scan_secret_values(draft, "%s draft" % context)
    return {
        "draft_path": entry["draft_path"],
        "source_id": source_id,
        "sha256": entry["sha256"],
        # Byte-derived shape triple for §3 gating; append-only extra field.
        "shape": list(_shape_from_source(source)),
    }


# ---------------------------------------------------------------------------
# Default (production) operations. Every method is individually injectable.
# ---------------------------------------------------------------------------


def _subprocess_json(project_root, arguments, timeout):
    command = [
        sys.executable, "-B", "-m", "live_data.rmv2_live",
        "--project-root", str(project_root),
    ] + list(arguments)
    environment = dict(os.environ)
    environment.update({
        "PYTHONDONTWRITEBYTECODE": "1",
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
        timeout=timeout,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise AdmissionOperationError(
            "delegated command failed (%d): %s" %
            (completed.returncode, detail[-2000:])
        )
    try:
        value = strict_json_loads(completed.stdout)
    except (CanonicalDataError, UnicodeError, ValueError) as exc:
        raise AdmissionOperationError(
            "delegated command did not return strict JSON"
        ) from exc
    if not isinstance(value, dict):
        raise AdmissionOperationError("delegated result must be an object")
    return value


def keyless_leak_scan(project_root, roots=None):
    """Structural scan for embedded api_key/authorization tokens.

    Never reads ``local.env`` (secret policy): local.env is excluded even if it
    lives under a scanned root. Returns a dict; ``status`` is PASS/FAIL.
    """
    project_root = Path(project_root).resolve()
    if roots is None:
        roots = (
            project_root / "live_data" / "public_deploy",
            project_root / "live_data" / "runtime" / "source_heads",
            project_root / "live_data" / "config" / "sources.v1.json",
            project_root / "live_data" / "config" / "planned_sources.v1.json",
        )
    findings = []
    scanned = 0
    for root in roots:
        root = Path(root)
        if not root.exists():
            continue
        files = [root] if root.is_file() else sorted(
            p for p in root.rglob("*") if p.is_file()
        )
        for path in files:
            if path.name == "local.env":
                continue
            try:
                data = path.read_bytes()
            except OSError:
                continue
            scanned += 1
            for pattern in LEAK_PATTERNS:
                if pattern.search(data):
                    try:
                        name = str(path.resolve().relative_to(project_root))
                    except ValueError:
                        name = str(path)
                    findings.append(name)
                    break
    return {
        "files_scanned": scanned,
        "findings": sorted(set(findings)),
        "status": "PASS" if not findings else "FAIL",
    }


class DefaultOperations(object):
    """Wire the injectable operations to the real subprocess/launchd system."""

    def __init__(
        self,
        project_root,
        cli_timeout=1800,
        refresh_timeout=1800,
        verify_timeout=1800,
    ):
        self.project_root = Path(project_root).resolve()
        self.cli_timeout = cli_timeout
        self.refresh_timeout = refresh_timeout
        self.verify_timeout = verify_timeout

    def now(self):
        return utc_now()

    def barrier_free(self):
        """True iff the live-data publication barrier is currently free."""
        path = self.project_root / "live_data" / "runtime" / "refresh.lock"
        if not path.parent.is_dir():
            raise AdmissionContractError(
                "live publication barrier is unavailable"
            )
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(str(path), flags, 0o644)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        else:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            return True
        finally:
            os.close(descriptor)

    def read_state(self):
        """Read the current enabled/healthy sources from operational status."""
        public = self.project_root / "live_data" / "public"
        path = public / "operational_status.json"
        if not path.exists():
            path = public / "live_status.json"
        data = _safe_regular_bytes(path, public, missing_ok=True)
        if data is None:
            return {
                "service_state": None,
                "healthy_source_ids": frozenset(),
                "head_count": 0,
            }
        status = strict_json_loads(data)
        health = status.get("current_source_health")
        healthy = frozenset(
            source_id for source_id, state in (health or {}).items()
            if state == "healthy"
        ) if isinstance(health, dict) else frozenset()
        return {
            "service_state": status.get("service_state"),
            "healthy_source_ids": healthy,
            "head_count": status.get("snapshot_source_count", len(healthy)),
        }

    def run_cli(self, arguments):
        timeout = self.cli_timeout
        if arguments[:1] == ["refresh"]:
            timeout = self.refresh_timeout
        elif arguments[:1] == ["verify"]:
            timeout = self.verify_timeout
        return _subprocess_json(self.project_root, arguments, timeout)

    def _launchctl(self, verb, arguments):
        subprocess.run(
            ["/bin/launchctl", verb] + list(arguments),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
        )

    def stop_agents(self):
        domain = "gui/%d" % os.getuid()
        actions = []
        for label in AGENT_LABELS:
            self._launchctl("bootout", ["%s/%s" % (domain, label)])
            actions.append(("bootout", label))
        return actions

    def start_agents(self):
        scripts = self.project_root / "live_data" / "scripts"
        domain = "gui/%d" % os.getuid()
        actions = []
        # live-data + watchdog own idempotent installers that copy the plist,
        # bootstrap, and wait for readiness. data-autopilot is relaunched by a
        # direct bootstrap of its reviewed plist (its installer's dry-run gate
        # is for first install, not for reload).
        subprocess.run(
            ["/bin/bash", str(scripts / "install_launchd.sh")],
            check=False, timeout=600,
        )
        actions.append(("bootstrap", AGENT_LABELS[0]))
        subprocess.run(
            ["/bin/bash", str(scripts / "install_watchdog.sh")],
            check=False, timeout=300,
        )
        actions.append(("bootstrap", AGENT_LABELS[1]))
        plist = (
            self.project_root / "live_data" / "launchd" /
            ("%s.plist" % AGENT_LABELS[2])
        )
        if plist.exists():
            self._launchctl("bootstrap", [domain, str(plist)])
            self._launchctl("kickstart", ["%s/%s" % (domain, AGENT_LABELS[2])])
        actions.append(("bootstrap", AGENT_LABELS[2]))
        return actions

    def publish_bundle(self):
        from live_data.publish_public_bundle import build
        return build(str(self.project_root))

    def key_scan(self):
        return keyless_leak_scan(self.project_root)


# ---------------------------------------------------------------------------
# Journal + status.
# ---------------------------------------------------------------------------


def _admission_root(project_root):
    project_root = Path(project_root).resolve()
    runtime = project_root / "live_data" / "runtime"
    admission = runtime / "admission"
    for path in (runtime, admission):
        if path.exists():
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                raise AdmissionContractError(
                    "admission runtime directory is unsafe"
                )
        else:
            path.mkdir(mode=0o755)
    return admission


def _open_lock(path):
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(str(path), flags, 0o644)
    info = os.fstat(descriptor)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        os.close(descriptor)
        raise AdmissionContractError("admission lock is unsafe")
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(descriptor)
        return None
    return descriptor


def _append_journal(admission_root, record):
    """Append one canonical JSON line to the immutable journal."""
    path = admission_root / "journal.jsonl"
    line = canonical_json_bytes(record) + b"\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(str(path), flags, 0o644)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise AdmissionContractError("admission journal is unsafe")
        os.write(descriptor, line)
    finally:
        os.close(descriptor)


# ---------------------------------------------------------------------------
# The cycle.
# ---------------------------------------------------------------------------


def _cli_error(exc):
    return "%s: %s" % (type(exc).__name__, exc)


def _timed(started_at, mono_start, ops, entry):
    """Append-only per-step instrumentation (B-FAST-1 §2.2).

    Stamps a completed step entry with wall ``started_at``/``ended_at`` and a
    monotonic elapsed measure so a later batch can attribute admission cost to a
    specific step from evidence. Never removes or renames an existing field;
    existing downstream journal readers keep working.

    The elapsed measure is recorded as ``elapsed_ms`` (integer milliseconds =
    3-decimal-second precision). The canonical journal serialiser bans
    floating-point values outright (``canonical._validate_tree``) to keep the
    content-addressed store byte-deterministic, so the runbook's literal
    ``elapsed_s`` float would fail to persist. An integer millisecond preserves
    the intended 3-decimal-second resolution while honouring that store law.
    """
    entry["started_at"] = started_at
    entry["ended_at"] = ops.now()
    entry["elapsed_ms"] = int(round((time.monotonic() - mono_start) * 1000.0))
    return entry


def _admit_one_draft(ops, draft, steps):
    """Run prepare -> apply -> refresh for one draft; raise on any bad check."""
    source_id = draft["source_id"]
    _sa = ops.now()
    _m0 = time.monotonic()
    prepare = ops.run_cli(
        ["feed-factory", "prepare", "--draft", draft["draft_path"]]
    )
    if prepare.get("status") != "CANDIDATE_NOT_ACTIVE" or not isinstance(
        prepare.get("manifest_path"), str
    ):
        raise AdmissionOperationError(
            "prepare did not produce an inactive candidate for %s" % source_id
        )
    manifest_path = prepare["manifest_path"]
    steps.append(_timed(
        _sa, _m0, ops,
        {"source_id": source_id, "step": "prepare", "ok": True},
    ))
    _sa = ops.now()
    _m0 = time.monotonic()
    apply_result = ops.run_cli(
        ["feed-factory", "apply", "--bundle", manifest_path]
    )
    if (
        apply_result.get("status") != "APPLIED_CONFIG_ONLY_REFRESH_REQUIRED" or
        apply_result.get("source_id") != source_id
    ):
        raise AdmissionOperationError(
            "apply did not report config-only admission for %s" % source_id
        )
    steps.append(_timed(
        _sa, _m0, ops,
        {"source_id": source_id, "step": "apply", "ok": True},
    ))
    _sa = ops.now()
    _m0 = time.monotonic()
    refresh = ops.run_cli(["refresh", "--source", source_id])
    if not isinstance(refresh.get("snapshot_source_count"), int) or not \
            isinstance(refresh.get("outcomes"), list):
        raise AdmissionOperationError(
            "targeted refresh did not return a source snapshot for %s"
            % source_id
        )
    steps.append(_timed(_sa, _m0, ops, {
        "source_id": source_id,
        "step": "refresh",
        "ok": True,
        "snapshot_source_count": refresh["snapshot_source_count"],
    }))


def _hard_stop_to_green(ops, steps):
    """One clean full refresh + verify to leave the store green after failure."""
    _sa = ops.now()
    _m0 = time.monotonic()
    try:
        ops.run_cli(["refresh"])
        verify = ops.run_cli(["verify"])
    except Exception as exc:  # noqa: BLE001 - recovery must not raise
        steps.append(_timed(
            _sa, _m0, ops,
            {"step": "self_heal", "ok": False, "error": _cli_error(exc)},
        ))
        return STATE_HALTED_DEGRADED, None
    healed = (
        verify.get("status") == "PASS" and
        verify.get("config_generation_closure", {}).get("status") == "PASS"
    )
    steps.append(_timed(_sa, _m0, ops, {
        "step": "self_heal",
        "ok": bool(healed),
        "head_count": len(verify.get("checked_source_heads", []))
        if isinstance(verify.get("checked_source_heads"), list) else None,
    }))
    return (STATE_HALTED_GREEN if healed else STATE_HALTED_DEGRADED), verify


def run_cycle(project_root, queue_path=None, ops=None, process_id=None):
    """Run one at-most-one-batch admission cycle. Never retries internally."""
    project_root = Path(project_root).resolve()
    loaded = load_queue(project_root, queue_path)
    ops = ops or DefaultOperations(project_root)
    process_id = os.getpid() if process_id is None else process_id
    started_at = ops.now()
    cycle_id = sha256_bytes(canonical_json_bytes({
        "process_id": process_id,
        "queue_sha256": loaded["queue_sha256"],
        "started_at": started_at,
    }))

    admission_root = _admission_root(project_root)
    descriptor = _open_lock(admission_root / "runner.lock")
    if descriptor is None:
        return _finish(
            ops, admission_root, loaded, cycle_id, started_at, process_id,
            STATE_LOCKED_OUT, steps=[], batch=[], persist=False,
        )
    try:
        return _run_locked(
            ops, project_root, admission_root, loaded, cycle_id,
            started_at, process_id,
        )
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _run_locked(
    ops, project_root, admission_root, loaded, cycle_id, started_at,
    process_id,
):
    state = ops.read_state()
    already_live = state["healthy_source_ids"]
    pending = [
        draft for draft in loaded["drafts"]
        if draft["source_id"] not in already_live
    ]
    if not pending:
        # Transient non-event (queue drained): an idle launchd tick must not
        # append a journal line or bootout anything.
        return _finish(
            ops, admission_root, loaded, cycle_id, started_at, process_id,
            STATE_NOOP_ALL_ADMITTED, steps=[], batch=[], persist=False,
            baseline_head_count=state["head_count"],
        )
    # Shape-gated selection (B-FAST-1 §3): take EVERY pending draft whose shape
    # is already proven, plus at most ``max_batch`` drafts of NEW (unproven)
    # shapes. Order is preserved; unadmitted drafts stay pending for the next
    # cycle. This replaces the prior ``pending[:max_batch]`` total cap.
    max_new_shapes = loaded["max_batch"]
    proven = _proven_shape_set(
        project_root, [shape_of(draft) for draft in pending]
    )
    batch = []
    new_shape_count = 0
    for draft in pending:
        if shape_of(draft) in proven:
            batch.append(draft)
        elif new_shape_count < max_new_shapes:
            batch.append(draft)
            new_shape_count += 1
    more_pending = len(pending) > len(batch)

    # Never bootout the scheduler while a live refresh holds the barrier.
    if not ops.barrier_free():
        return _finish(
            ops, admission_root, loaded, cycle_id, started_at, process_id,
            STATE_DEFERRED_BARRIER_HELD, steps=[], batch=batch,
            baseline_head_count=state["head_count"],
        )

    steps = []
    agent_actions = {"stopped": ops.stop_agents()}
    verify_result = None
    bundle_receipt = None
    key_scan_result = None
    try:
        for draft in batch:
            _admit_one_draft(ops, draft, steps)
        _sa = ops.now()
        _m0 = time.monotonic()
        verify_result = ops.run_cli(["verify"])
        head_count = len(verify_result.get("checked_source_heads", [])) \
            if isinstance(verify_result.get("checked_source_heads"), list) \
            else None
        closure = verify_result.get("config_generation_closure", {})
        expected_heads = state["head_count"] + len(batch)
        if (
            verify_result.get("status") != "PASS" or
            closure.get("status") != "PASS" or
            head_count != expected_heads
        ):
            raise AdmissionOperationError(
                "post-batch verify failed (status=%r closure=%r heads=%r "
                "expected=%r)" % (
                    verify_result.get("status"),
                    closure.get("status"),
                    head_count,
                    expected_heads,
                )
            )
        steps.append(_timed(
            _sa, _m0, ops,
            {"step": "verify", "ok": True, "head_count": head_count},
        ))
        _sa = ops.now()
        _m0 = time.monotonic()
        bundle_receipt = ops.publish_bundle()
        steps.append(_timed(
            _sa, _m0, ops, {"step": "publish_bundle", "ok": True},
        ))
        _sa = ops.now()
        _m0 = time.monotonic()
        key_scan_result = ops.key_scan()
        if key_scan_result.get("status") != "PASS":
            raise AdmissionOperationError(
                "key-leak scan failed: %r" % key_scan_result.get("findings")
            )
        steps.append(_timed(
            _sa, _m0, ops, {"step": "key_scan", "ok": True},
        ))
        terminal = (
            STATE_BATCH_GREEN_MORE_PENDING if more_pending
            else STATE_ALL_ADMITTED
        )
    except Exception as exc:  # noqa: BLE001 - any failure hard-stops to green
        _sa = ops.now()
        _m0 = time.monotonic()
        steps.append(_timed(
            _sa, _m0, ops,
            {"step": "failure", "ok": False, "error": _cli_error(exc)},
        ))
        terminal, verify_result = _hard_stop_to_green(ops, steps)
    finally:
        agent_actions["started"] = ops.start_agents()

    return _finish(
        ops, admission_root, loaded, cycle_id, started_at, process_id,
        terminal, steps=steps, batch=batch,
        baseline_head_count=state["head_count"],
        agent_actions=agent_actions,
        verify_result=verify_result,
        bundle_receipt=bundle_receipt,
        key_scan_result=key_scan_result,
    )


def _finish(
    ops, admission_root, loaded, cycle_id, started_at, process_id, terminal,
    steps, batch, persist=True, baseline_head_count=None, agent_actions=None,
    verify_result=None, bundle_receipt=None, key_scan_result=None,
):
    finished_at = ops.now()
    active_generation = None
    verify_head_count = None
    if isinstance(verify_result, dict):
        heads = verify_result.get("checked_source_heads")
        if isinstance(heads, list):
            verify_head_count = len(heads)
    if isinstance(bundle_receipt, dict):
        candidate = bundle_receipt.get("generation_sha256")
        if isinstance(candidate, str) and SHA256_RE.match(candidate):
            active_generation = candidate
    # Store-head bounds for the cycle (B-FAST-1 §2.2): lets a later batch
    # correlate per-step cost with store size. ``baseline_head_count`` is
    # retained unchanged for existing readers; these are append-only aliases
    # with the after-bound resolved from the post-batch verify when present.
    store_heads_after = (
        verify_head_count if verify_head_count is not None
        else baseline_head_count
    )
    record = {
        "batch_source_ids": [draft["source_id"] for draft in batch],
        "baseline_head_count": baseline_head_count,
        "bundle_generation": active_generation,
        "store_heads_before": baseline_head_count,
        "store_heads_after": store_heads_after,
        "cycle_id": cycle_id,
        "finished_at": finished_at,
        "green": terminal in GREEN_TERMINAL_STATES,
        "key_scan_status": (
            key_scan_result.get("status")
            if isinstance(key_scan_result, dict) else None
        ),
        "process_id": process_id,
        "queue_id": loaded["queue_id"],
        "queue_sha256": loaded["queue_sha256"],
        "schema_version": JOURNAL_SCHEMA,
        "scientific_binding": False,
        "started_at": started_at,
        "steps": steps,
        "terminal_state": terminal,
        "verify_head_count": verify_head_count,
    }
    if persist:
        _append_journal(admission_root, record)
        latest = {
            "cycle_id": cycle_id,
            "green": record["green"],
            "queue_id": loaded["queue_id"],
            "queue_sha256": loaded["queue_sha256"],
            "schema_version": STATUS_SCHEMA,
            "terminal_state": terminal,
            "updated_at": finished_at,
            "verify_head_count": verify_head_count,
        }
        atomic_write(
            admission_root / "latest_status.json",
            canonical_json_bytes(latest),
        )
    return record


def read_latest_status(project_root):
    project_root = Path(project_root).resolve()
    path = (
        project_root / "live_data" / "runtime" / "admission" /
        "latest_status.json"
    )
    admission_root = path.parent
    if not admission_root.is_dir():
        return {"schema_version": STATUS_SCHEMA, "terminal_state": "NOT_RUN"}
    data = _safe_regular_bytes(path, admission_root, missing_ok=True)
    if data is None:
        return {"schema_version": STATUS_SCHEMA, "terminal_state": "NOT_RUN"}
    return strict_json_loads(data)
