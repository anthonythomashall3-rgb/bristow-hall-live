"""bh command dispatch — A2 §35.

Bare `bh` prints the subcommand list and nothing else; it never mutates
(A2 §35.6). Subcommand handlers lazy-import their modules so the CLI stays
importable and `--version`/`install` work even while the rest of the spine is
being built.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import GENERATION_BINDING, paths

BH_VERSION = "0.1.0-a2-spine"


def _last_receipt_id(repo: Path) -> str:
    """Most recent batch receipt filename (A2 §35.5). Never reads its bytes."""
    receipts = sorted(
        repo.glob("*.v1.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    return receipts[0].name if receipts else "none"


def cmd_version(_args) -> int:
    """A2 §35.5 — one line each; the first thing any report or blocker quotes."""
    try:
        repo = paths.resolve_repo()
        repo_s = str(repo)
        last = _last_receipt_id(repo)
    except paths.ResolutionError as exc:
        repo_s = f"UNRESOLVED ({exc})"
        last = "unknown"
    try:
        interp = str(paths.resolve_interpreter())
    except paths.ResolutionError as exc:
        interp = f"UNRESOLVED ({exc})"
    print(f"bh version: {BH_VERSION}")
    print(f"repo: {repo_s}")
    print(f"generation binding: {GENERATION_BINDING}")
    print(f"interpreter: {sys.executable} (python {sys.version.split()[0]})")
    print(f"recorded interpreter: {interp}")
    print(f"last receipt: {last}")
    return 0


def cmd_install(args) -> int:
    from . import install as installer

    report = installer.install(Path(args.repo) if args.repo else None)
    for key in ("shim", "repo", "interpreter", "repo_path_file", "interpreter_path_file"):
        print(f"{key}: {report[key]}")
    print("install: ok (idempotent)")
    return 0


def cmd_blockers(args) -> int:
    from . import blockers

    return blockers.cli_list(args)


def cmd_lock(args) -> int:
    from . import writer_lock

    return writer_lock.cli(args)


def cmd_params(args) -> int:
    from . import params

    return params.cli(args)


def cmd_credentials(args) -> int:
    from . import creds

    return creds.cli(args)


def cmd_doctor(args) -> int:
    from . import doctor

    return doctor.cli(args)


def cmd_report(args) -> int:
    from . import report

    return report.cli(args)


def cmd_discover(args) -> int:
    from . import discover

    return discover.cli(args)


def cmd_gc(args) -> int:
    from . import gc

    return gc.cli(args)


def cmd_quiesce(args) -> int:
    from . import quiesce

    return quiesce.cli(args)


def cmd_receipt(args) -> int:
    from . import receipts

    return receipts.cli(args)


def cmd_queue(args) -> int:
    from . import queue

    return queue.cli(args)


def cmd_nightly(args) -> int:
    from . import nightly

    return nightly.cli(args)


def cmd_ledger_lint(args) -> int:
    # B-HOUSE-3 Defect 1: flag DONE rows whose stamp precedes their brief's mtime.
    from pathlib import Path

    from . import ledger

    done = Path(args.done)
    briefs = Path(args.briefs) if args.briefs else done.parent.parent / "briefs"
    if not done.exists():
        print(f"ledger-lint: DONE file not found: {done}")
        return 2
    violations = ledger.lint_done_file(done, briefs)
    if not violations:
        print(f"ledger-lint: OK (no backdated rows in {done})")
        return 0
    print(f"ledger-lint: {len(violations)} row(s) with stamp before their brief mtime:")
    for v in sorted(violations, key=lambda x: -x["backdated_seconds"]):
        print(f"  {v['batch_id']}: stamp {v['stamp']} < brief {v['brief_mtime']} "
              f"(-{int(v['backdated_seconds'])}s)")
    return 1


def cmd_promotion(args) -> int:
    from . import promotion

    return promotion.cli(args)


def cmd_produce(args) -> int:
    from . import produce

    return produce.cmd_produce(args)


def cmd_commit_staged(args) -> int:
    from . import produce

    return produce.cmd_commit_staged(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bh", description="Bristow-Hall operations CLI (A2 spine)"
    )
    parser.add_argument("--version", action="store_true", help="print version block and exit (A2 §35.5)")
    sub = parser.add_subparsers(dest="command")

    p_install = sub.add_parser("install", help="install the bh shim + record repo/interpreter (A2 §35)")
    p_install.add_argument("--repo", default=None, help="explicit repo root (else resolved)")
    p_install.set_defaults(func=cmd_install)

    sub.add_parser("version", help="print version block (A2 §35.5)").set_defaults(func=cmd_version)

    p_block = sub.add_parser("blockers", help="list open typed blockers (A2 §5)")
    p_block.add_argument("--all", action="store_true", help="include resolved blockers")
    p_block.set_defaults(func=cmd_blockers)

    p_lock = sub.add_parser("lock", help="writer-lock status / break (A2 §37)")
    p_lock.add_argument("lock_action", choices=["status", "break"])
    p_lock.add_argument("--confirm", action="store_true", help="required to break a held lock (A2 §37.5)")
    p_lock.add_argument("--reason", default="", help="reason recorded when breaking")
    p_lock.set_defaults(func=cmd_lock)

    p_params = sub.add_parser("params", help="parameter provenance ledger (A2 §56.4)")
    p_params.add_argument("--json", action="store_true")
    p_params.set_defaults(func=cmd_params)

    p_creds = sub.add_parser("credentials", help="which credentials resolve, by name only (A2 §55.5)")
    p_creds.set_defaults(func=cmd_credentials)

    p_doctor = sub.add_parser("doctor", help="is everything fine? one verdict (A2 §20)")
    p_doctor.add_argument("--fix-install", action="store_true", help="reinstall shim without touching data (A2 §35.7)")
    p_doctor.set_defaults(func=cmd_doctor)

    p_report = sub.add_parser("report", help="derived batch brief (A2 §19)")
    p_report.add_argument("--brief", action="store_true")
    p_report.add_argument("--last", action="store_true")
    p_report.set_defaults(func=cmd_report)

    p_discover = sub.add_parser("discover", help="protocol-driven source discovery (SRC1) — metadata harvest, no AI, no data download")
    p_discover.add_argument("--json", action="store_true", help="print the full discovery receipt as JSON")
    p_discover.add_argument("--timeout", type=float, default=12.0, help="per-request timeout seconds")
    p_discover.set_defaults(func=cmd_discover)

    p_gc = sub.add_parser("gc", help="purge .DS_Store / __pycache__ / *.pyc tree cruft (B-SAFE-1 §3.2)")
    p_gc.add_argument("--dry-run", action="store_true", help="report what would be removed without touching disk")
    p_gc.add_argument("--json", action="store_true", help="print the removed-paths map as JSON")
    p_gc.set_defaults(func=cmd_gc)

    p_quiesce = sub.add_parser("quiesce", help="bootout resident agents, record prior state (B-SAFE-1 §4.1)")
    p_quiesce.set_defaults(func=cmd_quiesce, quiesce_action="quiesce")
    p_restore = sub.add_parser("restore", help="restore agents to measured prior state (B-SAFE-1 §4.1)")
    p_restore.set_defaults(func=cmd_quiesce, quiesce_action="restore")

    p_receipt = sub.add_parser("receipt", help="wrap a body with chain fields + key-leak scan, register into the chain (B-SAFE-1 §4.2)")
    p_receipt.add_argument("--body", required=True, help="path to the loose receipt body JSON")
    p_receipt.add_argument("--out", required=True, help="receipt filename (…v1.json)")
    p_receipt.add_argument("--batch-id", dest="batch_id", required=True)
    p_receipt.add_argument("--predecessor", required=True, help="predecessor receipt filename")
    p_receipt.add_argument("--store-start", dest="store_start", required=True)
    p_receipt.add_argument("--store-end", dest="store_end", required=True)
    p_receipt.add_argument("--gen-in", dest="gen_in", required=True)
    p_receipt.add_argument("--gen-out", dest="gen_out", required=True)
    p_receipt.add_argument("--repo", default=None)
    p_receipt.set_defaults(func=cmd_receipt)

    def _need_subaction(name):
        def _f(_a):
            print(f"bh {name}: subcommand required (see `bh {name} -h`)")
            return 2
        return _f

    p_queue = sub.add_parser("queue", help="serialized unattended runbook runner (B-AUTO-1 §1)")
    p_queue.set_defaults(func=_need_subaction("queue"))
    q_sub = p_queue.add_subparsers(dest="queue_action")
    p_queue_run = q_sub.add_parser("run", help="run a queuefile (one promoted-runbook path per line)")
    p_queue_run.add_argument("queuefile", help="path to the queuefile")
    p_queue_run.add_argument("--batch-id", dest="batch_id", default="B-AUTO-1-QUEUE")
    p_queue_run.set_defaults(func=cmd_queue)

    p_produce = sub.add_parser("produce", help="fetch one source's bytes into an exclusive staging dir; NO store write (B-PROD-1 §2)")
    p_produce.add_argument("--source", required=True, help="source_id or coverage family id to fetch")
    p_produce.add_argument("--split", default=None, help="disjoint variable selector (labels the producer dir)")
    p_produce.add_argument("--repo", default=None)
    p_produce.set_defaults(func=cmd_produce)

    p_commit = sub.add_parser("commit-staged", help="serial committer: admit every staged draft + publish ONE generation (B-PROD-1 §3)")
    p_commit.add_argument("--no-publish", dest="no_publish", action="store_true", help="admit heads but do not publish a generation")
    p_commit.add_argument("--repo", default=None)
    p_commit.set_defaults(func=cmd_commit_staged)

    p_nightly = sub.add_parser("nightly", help="nightly chores: verify --full, backup, publish, report (B-AUTO-1 §2)")
    p_nightly.set_defaults(func=cmd_nightly)

    p_ledger = sub.add_parser("ledger-lint", help="flag DONE.md rows backdated before their brief (B-HOUSE-3 D1)")
    p_ledger.add_argument("--done", required=True, help="path to DONE.md")
    p_ledger.add_argument("--briefs", default=None, help="briefs/ dir (default: ../briefs of DONE.md)")
    p_ledger.set_defaults(func=cmd_ledger_lint)

    p_promo = sub.add_parser("promotion", help="promotion ledger: which runbooks may run unattended (B-AUTO-1 §3)")
    p_promo.set_defaults(func=_need_subaction("promotion"))
    promo_sub = p_promo.add_subparsers(dest="promotion_action")
    promo_sub.add_parser("list", help="show the derived criterion + ledger").set_defaults(func=cmd_promotion)
    p_promo_rec = promo_sub.add_parser("record", help="run a read-only runbook once; count it if clean")
    p_promo_rec.add_argument("runbook_id")
    p_promo_rec.add_argument("path")
    p_promo_rec.add_argument("--read-only", dest="read_only", action="store_true")
    p_promo_rec.add_argument("--repo", default=None)
    p_promo_rec.set_defaults(func=cmd_promotion)

    return parser


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "version", False):
        return cmd_version(args)
    if not getattr(args, "command", None):
        # A2 §35.6 — bare bh prints the subcommand list and nothing else.
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    # `python3 -m bh.cli` used to import this module and fall off the end doing
    # nothing (exit 0) — a SILENT fail-open caught only because the receipt-chain
    # head never advanced (B-AUTO-1 director addendum). Refuse loudly and
    # nonzero; the entry point is `python3 -m bh` (see bh/__main__.py).
    print(
        "bh: invoke `python3 -m bh` (or the installed `bh` shim), not `-m bh.cli`",
        file=sys.stderr,
    )
    raise SystemExit(2)
