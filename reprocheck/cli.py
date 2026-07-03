"""Command-line front-end for the reproducibility checker.

Examples:
  python -m reprocheck.cli check submission.json
  python -m reprocheck.cli check manuscript.txt --format md --out report.md
  python -m reprocheck.cli check submission.json --offline   # skip re-sourcing
  python -m reprocheck.cli check submission.json --cache .cache --format json
"""
from __future__ import annotations

import argparse
import datetime as _dt
import sys
from pathlib import Path

from .claims import Submission, SubmissionError, from_text
from .report import check
from .resource import Resolver


def _load_submission(path: str) -> Submission:
    p = Path(path)
    if p.suffix.lower() == ".json":
        return Submission.from_json_file(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    return from_text(text, title=p.stem)


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def cmd_check(args) -> int:
    try:
        sub = _load_submission(args.input)
    except SubmissionError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    resolver = None
    if not args.no_source:
        resolver = Resolver(cache_dir=args.cache, offline=args.offline)
    report = check(sub, resolver=resolver, recompute=True, generated=_now())

    if args.format == "json":
        rendered = report.to_json()
    elif args.format == "html":
        rendered = report.to_html()
    else:
        rendered = report.to_markdown()

    if args.out:
        Path(args.out).write_text(rendered, encoding="utf-8")
        print(f"wrote {args.format} report -> {args.out}")
        print(f"overall: {report.overall}")
    else:
        print(rendered)

    # exit code: 0 reproduces/inconclusive(informational), 2 diverges/fail
    bad = report.overall.startswith(("DIVERGES", "FAIL"))
    return 2 if bad else 0


def cmd_validate(args) -> int:
    """Run the bundled reproducibility benchmark and print the result table.

    Offline by default (deterministic, network-free). Exit code is 0 when every
    fixture matched its expected verdict, 1 otherwise — usable as a CI gate.
    """
    from .benchmark import run_benchmark, render_table
    try:
        result = run_benchmark(offline=not args.live, cache_dir=args.cache)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"# reprocheck validation benchmark "
          f"({'live re-sourcing' if args.live else 'offline'})\n")
    print(render_table(result))
    print(f"\n{result.passed}/{result.total} passed.")
    return 0 if result.all_passed else 1


def build_parser() -> argparse.ArgumentParser:
    from . import __version__
    p = argparse.ArgumentParser(
        prog="reprocheck",
        description="Re-derive a meta-analysis's statistics from primary "
                    "sources and report what does not hold up.")
    p.add_argument("--version", action="version",
                   version=f"reprocheck {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="check a submission")
    c.add_argument("input", help="submission .json or manuscript .txt")
    c.add_argument("--format", choices=["md", "json", "html"], default="md")
    c.add_argument("--out", help="write report to this file")
    c.add_argument("--cache", default=None, help="re-sourcing cache directory")
    c.add_argument("--offline", action="store_true",
                   help="do not hit the network; use cache only")
    c.add_argument("--no-source", action="store_true",
                   help="skip independent re-sourcing entirely")
    c.set_defaults(func=cmd_check)

    v = sub.add_parser("validate",
                       help="run the bundled reproducibility benchmark")
    v.add_argument("--live", action="store_true",
                   help="add live citation re-sourcing (default: offline)")
    v.add_argument("--cache", default=None, help="re-sourcing cache directory")
    v.set_defaults(func=cmd_validate)
    return p


def main(argv=None) -> int:
    # Windows consoles default to cp1252 and choke on the ✓/✗ glyphs; force UTF-8
    # here (inside main, not at module import, so pytest's capture is untouched).
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001 - not a real terminal / already wrapped
            pass
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
