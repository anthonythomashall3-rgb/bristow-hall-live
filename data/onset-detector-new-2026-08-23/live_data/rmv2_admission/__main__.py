"""Command-line entry point for one-shot admission runner cycles."""

from __future__ import absolute_import, print_function

import argparse
import sys
from pathlib import Path

from live_data.rmv2_live.canonical import pretty_json_bytes

from .runner import (
    AdmissionContractError,
    GREEN_TERMINAL_STATES,
    read_latest_status,
    run_cycle,
)


def _default_root():
    return Path(__file__).resolve().parents[2]


def _print(value):
    sys.stdout.buffer.write(pretty_json_bytes(value))


def _parser():
    parser = argparse.ArgumentParser(
        description="Recession Monitor V2 one-shot admission runner",
    )
    parser.add_argument("--project-root", help="Recession Monitor V2 root")
    parser.add_argument("--queue", help="explicit approved-draft queue path")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "cycle",
        help="drain one batch (<=5) of the approved-draft queue and exit",
    )
    commands.add_parser(
        "status",
        help="print the latest persisted admission status",
    )
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    project_root = Path(args.project_root or _default_root()).resolve()
    try:
        if args.command == "status":
            result = read_latest_status(project_root)
            _print(result)
            return 0
        result = run_cycle(project_root, queue_path=args.queue)
        _print(result)
        return 0 if result.get("terminal_state") in GREEN_TERMINAL_STATES \
            else 1
    except (AdmissionContractError, OSError, RuntimeError, ValueError) as exc:
        print("%s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
