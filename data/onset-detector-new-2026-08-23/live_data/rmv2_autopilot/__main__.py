"""Command-line entry point for one-shot data-autopilot cycles."""

from __future__ import absolute_import, print_function

import argparse
import sys
from pathlib import Path

from live_data.rmv2_live.canonical import pretty_json_bytes

from .runner import QueueContractError, read_latest_status, run_cycle


SUCCESSFUL_CLI_STATES = frozenset((
    "BLOCKED_EXCEPTIONS_ONLY",
    "READY_FOR_REVIEW",
    "SCOPED_WORK_COMPLETE",
    "WORKING",
))


def _default_root():
    return Path(__file__).resolve().parents[2]


def _print(value):
    sys.stdout.buffer.write(pretty_json_bytes(value))


def _result_exit_code(value):
    if not isinstance(value, dict):
        return 2
    return 0 if value.get("overall_state") in SUCCESSFUL_CLI_STATES else 1


def _parser():
    parser = argparse.ArgumentParser(
        description="Recession Monitor V2 one-shot data autopilot",
    )
    parser.add_argument("--project-root", help="Recession Monitor V2 root")
    parser.add_argument("--queue", help="explicit queue path")
    commands = parser.add_subparsers(dest="command", required=True)
    cycle = commands.add_parser(
        "cycle",
        help="run one at-most-once queue cycle and exit",
    )
    cycle.add_argument("--dry-run", action="store_true")
    commands.add_parser(
        "status",
        help="print the latest persisted autopilot status",
    )
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    project_root = Path(args.project_root or _default_root()).resolve()
    try:
        if args.command == "status":
            result = read_latest_status(
                project_root,
                queue_path=args.queue,
            )
        else:
            result = run_cycle(
                project_root,
                queue_path=args.queue,
                dry_run=args.dry_run,
            )
        _print(result)
        return _result_exit_code(result)
    except (QueueContractError, OSError, RuntimeError, ValueError) as exc:
        print("%s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
