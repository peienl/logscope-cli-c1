"""argparse wiring and dispatch for the logscope CLI."""
from __future__ import annotations

import argparse
import sys
from typing import List, Optional, Sequence

from . import output as out
from .commands import grep, summary, timeline
from .parsing import KNOWN_LEVELS, normalize_level
from .timeutil import parse_duration, parse_user_datetime

DEFAULT_BUCKET = "15m"


def _add_global_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "file",
        help="Path to the log file to analyze.",
    )
    parser.add_argument(
        "--format",
        dest="format",
        choices=out.VALID_FORMATS,
        default="text",
        help="Output format (default: text). 'md' always writes a report file.",
    )
    parser.add_argument(
        "--output",
        "-o",
        dest="output",
        default=None,
        help=(
            "Destination file path. Required behavior for 'md' is to always "
            "write a file (defaults to '<logfile>_<command>_report.md' if "
            "omitted); for 'text'/'json' this writes to stdout unless given."
        ),
    )
    parser.add_argument(
        "--encoding",
        dest="encoding",
        default="utf-8",
        help="Input file encoding (default: utf-8).",
    )
    parser.add_argument(
        "--errors",
        dest="errors",
        choices=("strict", "replace", "ignore"),
        default="replace",
        help="Decoding error policy for the input file (default: replace).",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="logscope",
        description=(
            "Summarize application logs after an incident, without opening "
            "a dashboard."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    summary_parser = subparsers.add_parser(
        "summary",
        help="Counts by level, top 5 error messages, first/last timestamp.",
    )
    _add_global_options(summary_parser)

    timeline_parser = subparsers.add_parser(
        "timeline",
        help="Error count per time bucket, as a text bar chart.",
    )
    _add_global_options(timeline_parser)
    timeline_parser.add_argument(
        "--bucket",
        dest="bucket",
        default=DEFAULT_BUCKET,
        help=f"Bucket size, e.g. '30s', '15m', '2h', '1d' (default: {DEFAULT_BUCKET}).",
    )

    grep_parser = subparsers.add_parser(
        "grep",
        help="Filtered log lines by level and/or time range.",
    )
    _add_global_options(grep_parser)
    grep_parser.add_argument(
        "--level",
        dest="level",
        default=None,
        help=(
            "Comma-separated list of levels to match, e.g. 'ERROR' or "
            "'ERROR,WARN'. Matches any level if omitted."
        ),
    )
    grep_parser.add_argument(
        "--since",
        dest="since",
        default=None,
        help="Only include entries at or after this datetime, e.g. '2026-10-01 09:00'.",
    )
    grep_parser.add_argument(
        "--until",
        dest="until",
        default=None,
        help="Only include entries at or before this datetime.",
    )

    return parser


def _parse_levels(raw: Optional[str]) -> Optional[set]:
    if not raw:
        return None
    levels = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        level = normalize_level(part)
        if level not in KNOWN_LEVELS:
            raise ValueError(
                f"Unknown level {part!r}. Expected one of: "
                f"{', '.join(sorted(KNOWN_LEVELS))}."
            )
        levels.add(level)
    return levels or None


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "summary":
            summary.run(
                args.file,
                fmt=args.format,
                output=args.output,
                encoding=args.encoding,
                errors=args.errors,
            )
        elif args.command == "timeline":
            bucket = parse_duration(args.bucket)
            timeline.run(
                args.file,
                bucket=bucket,
                fmt=args.format,
                output=args.output,
                encoding=args.encoding,
                errors=args.errors,
            )
        elif args.command == "grep":
            levels = _parse_levels(args.level)
            since = parse_user_datetime(args.since) if args.since else None
            until = parse_user_datetime(args.until) if args.until else None
            grep.run(
                args.file,
                levels=levels,
                since=since,
                until=until,
                fmt=args.format,
                output=args.output,
                encoding=args.encoding,
                errors=args.errors,
            )
        else:  # pragma: no cover - argparse enforces valid subcommands
            parser.error(f"Unknown command {args.command!r}")
    except FileNotFoundError:
        print(f"logscope: error: file not found: {args.file}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as exc:
        print(f"logscope: error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
