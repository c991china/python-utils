"""Command line entry point for the helpers.

    python -m python_utils.cli human-bytes 1536
    python -m python_utils.cli slugify "Café déjà vu"
    python -m python_utils.cli duration 2h30m
    python -m python_utils.cli ls ./src --ext .py

Exit codes: 0 success, 1 bad input (ValueError/TypeError from a helper),
2 argparse usage error. I keep the helpers' exceptions unwrapped so the
message you see is the one the function wrote.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from . import fs, text, time_utils


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python-utils",
        description="Small text/fs/time helpers. No network, no surprises.",
    )
    parser.add_argument("--version", action="version", version="python-utils 0.4.2")
    sub = parser.add_subparsers(dest="command", required=True)

    p_bytes = sub.add_parser("human-bytes", help="format a byte count")
    p_bytes.add_argument("value", type=float)
    p_bytes.add_argument(
        "--decimal",
        action="store_true",
        help="use 1000-based units (kB/MB) instead of 1024 (KiB/MiB)",
    )
    p_bytes.add_argument("--precision", type=int, default=1)

    p_slug = sub.add_parser("slugify", help="turn text into a URL slug")
    p_slug.add_argument("value")
    p_slug.add_argument("--max-length", type=int, default=None)

    p_trunc = sub.add_parser("truncate", help="cut text to a length")
    p_trunc.add_argument("value")
    p_trunc.add_argument("length", type=int)
    p_trunc.add_argument("--suffix", default="\u2026")
    p_trunc.add_argument(
        "--no-word-boundary",
        dest="word_boundary",
        action="store_false",
        help="cut mid-word instead of backing up to a space",
    )

    p_dur = sub.add_parser("duration", help="parse a duration like 2h30m to seconds")
    p_dur.add_argument("value")

    p_hum = sub.add_parser("humanize", help="turn seconds into 2h 30m form")
    p_hum.add_argument("seconds", type=float)
    p_hum.add_argument("--precision", type=int, default=2)

    p_ls = sub.add_parser("ls", help="list files under a path")
    p_ls.add_argument("root")
    p_ls.add_argument("--ext", action="append", default=None)
    p_ls.add_argument(
        "--all",
        dest="skip_hidden",
        action="store_false",
        help="include dotfiles and dot-directories",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        if args.command == "human-bytes":
            print(fs.human_bytes(args.value, binary=not args.decimal, precision=args.precision))

        elif args.command == "slugify":
            print(text.slugify(args.value, max_length=args.max_length))

        elif args.command == "truncate":
            print(
                text.truncate(
                    args.value,
                    args.length,
                    suffix=args.suffix,
                    word_boundary=args.word_boundary,
                )
            )

        elif args.command == "duration":
            print(f"{time_utils.parse_duration(args.value):g}")

        elif args.command == "humanize":
            print(time_utils.humanize_delta(args.seconds, precision=args.precision))

        elif args.command == "ls":
            for path in fs.iter_files(args.root, args.ext, skip_hidden=args.skip_hidden):
                print(path)

        else:  # pragma: no cover - argparse rejects unknown commands first
            print(f"unhandled command {args.command!r}", file=sys.stderr)
            return 2

    except (ValueError, TypeError, FileNotFoundError, NotADirectoryError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
