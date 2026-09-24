"""bh produce / bh commit-staged — the many-producers / one-committer split
(B-PROD-1). See live_data/rmv2_live/staging.py for the contract.

`produce` is the parallel half: N terminal windows may each fetch a different
source (or a disjoint split) into its OWN exclusive staging dir. No store,
config, receipt, or pointer write happens here.

`commit-staged` is the serial half: it takes the writer lock, admits every
staged draft through the proven binding path, and publishes ONE generation over
the resulting heads — the only writer of truth. Its publish sequence is the
exact non-refetch composition pipeline.refresh() uses (build_source_matrix +
write_source_matrix + build_snapshot/status/coverage + publish_generation), so a
staged landing is byte-for-byte the same generation a live refresh would emit.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from . import paths, writer_lock


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _config_path(repo: Path) -> Path:
    return repo / "live_data" / "config" / "sources.v1.json"


def staging_root(repo: Path) -> Path:
    return repo / "live_data" / "staging"


def load_pipeline(repo: Path, http_client=None):
    from live_data.rmv2_live.config import load_config, load_env_file
    from live_data.rmv2_live.pipeline import RefreshPipeline

    config_path = _config_path(repo)
    load_env_file(config_path.parent / "local.env")
    config = load_config(config_path)
    return RefreshPipeline(repo, config, http_client), config


def resolve_sources(config, selector):
    """A selector matches a source_id exactly or a coverage family id."""
    return [
        s for s in config["sources"]
        if s["source_id"] == selector
        or selector in (s.get("coverage_source_ids") or [])
    ]


def run_produce(repo, selector, split=None, http_client=None, now=None,
                source_specs=None):
    """Fetch every source matching selector into its own staging dir.

    ``source_specs`` supplies authored specs for a NOT-YET-LANDED family (the
    B-LAND-4 authored-reservation path): a new source is absent from active
    config until the committer lands it, so it cannot be resolved from config.
    When omitted, the selector resolves against active config (re-fetch of an
    already-landed source into staging).
    """
    from live_data.rmv2_live import staging

    repo = Path(repo)
    pipeline, config = load_pipeline(repo, http_client)
    pool = list(source_specs) if source_specs is not None else config["sources"]
    sources = [
        s for s in pool
        if s["source_id"] == selector
        or selector in (s.get("coverage_source_ids") or [])
    ]
    if not sources:
        raise SystemExit("bh produce: no source matches %r" % selector)
    stamp = now or _utc_now()
    drafts = []
    for source in sources:
        drafts.append(staging.produce(
            pipeline.http_client, source, stamp, staging_root(repo),
            split=split))
    return drafts


def _publish_current_heads(pipeline, attempted_at):
    """The exact non-refetch publish pipeline.refresh() runs over current heads."""
    from live_data.rmv2_live.matrix import build_source_matrix, write_source_matrix

    coverage = pipeline.build_coverage(attempted_at)
    matrix = build_source_matrix(
        pipeline.project_root, pipeline.config, pipeline.store, coverage,
        attempted_at)
    snapshot = pipeline.build_snapshot(attempted_at)
    matrix_receipt = write_source_matrix(pipeline.project_root, matrix)
    status = pipeline.build_status(attempted_at, [], snapshot, coverage)
    status["source_matrix"] = {
        "csv_bytes": matrix_receipt["csv_bytes"],
        "csv_sha256": matrix_receipt["csv_sha256"],
        "definition_sha256": matrix_receipt["definition_sha256"],
        "json_bytes": matrix_receipt["json_bytes"],
        "json_sha256": matrix_receipt["json_sha256"],
        "row_count": matrix_receipt["row_count"],
    }
    return pipeline.store.publish_generation(snapshot, status, coverage)


def run_commit(repo, http_client=None, now=None, publish=True):
    """Admit every staged draft serially and publish ONE generation.

    Holds the writer lock for the whole commit + publish. Returns the per-draft
    results plus the published pointer (None when nothing new committed).
    """
    from live_data.rmv2_live import staging
    from live_data.rmv2_live.canonical import atomic_write_json

    repo = Path(repo)
    pipeline, config = load_pipeline(repo, http_client)
    stamp = now or _utc_now()
    with writer_lock.writer_lock("bh commit-staged", repo):
        results = staging.commit_staged(pipeline, staging_root(repo), stamp)
        landed = [r for r in results
                  if r["outcome"] in ("committed", "unchanged")]
        active = {s["source_id"] for s in config["sources"]}
        newly = [r["source"] for r in landed
                 if r["source_id"] not in active]
        pointer = None
        if any(r["outcome"] == "committed" for r in results):
            # the committer is the ONE config writer: append newly-landed
            # sources, persist, then publish the generation over all heads.
            config["sources"].extend(newly)
            if publish:
                atomic_write_json(_config_path(repo), config)
                pointer = _publish_current_heads(pipeline, stamp)
    return {"pointer": pointer, "results": results}


# --------------------------------------------------------------------------- #
# argparse adapters (bh/cli.py).
# --------------------------------------------------------------------------- #

def cmd_produce(args) -> int:
    repo = paths.resolve_repo(args.repo)
    drafts = run_produce(repo, args.source, split=args.split)
    for draft in drafts:
        print("produced %s -> %s (%d bytes, sha %s)" % (
            draft["source_id"], draft["producer_id"],
            draft["payload"]["byte_length"], draft["payload"]["sha256"][:12]))
    print("staged %d draft(s); store/config/receipts untouched" % len(drafts))
    return 0


def cmd_commit_staged(args) -> int:
    from . import quiesce

    repo = paths.resolve_repo(args.repo)
    ops = quiesce.LaunchctlOps(repo)
    state = quiesce.state_path(repo)
    quiesced = False
    try:
        quiesce.quiesce(ops, state)
        quiesced = True
    except Exception as exc:  # quiesce is best-effort on non-agent hosts
        print("commit-staged: quiesce skipped (%s)" % exc)
    try:
        outcome = run_commit(repo, publish=not args.no_publish)
    finally:
        if quiesced:
            try:
                quiesce.restore(ops, state)
            except Exception as exc:
                print("commit-staged: restore FAILED (%s)" % exc)
    for r in outcome["results"]:
        if r["outcome"] == "rejected":
            print("rejected %s (%s): %s" % (
                r.get("source_id"), r["producer_id"], r["reason"]))
        else:
            print("%s %s (%s)" % (
                r["outcome"], r["source_id"], r["producer_id"]))
    pointer = outcome["pointer"]
    print("commit-staged: published %s" % (
        pointer["generation_sha256"][:12] if pointer else "nothing new"))
    return 0
