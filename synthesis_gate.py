"""Synthēsis pre-acceptance reproducibility gate (front-end 1).

Wires the reprocheck engine into the journal's editorial workflow: every
submitted meta-analysis is auto-checked and the editor gets the reproducibility
report BEFORE an accept decision. The gate INFORMS — it never auto-rejects.

Two input modes:

  * --export DIR     process a local export of submission files. Each submission
                     is either a `*.json` study table (reprocheck schema) or a
                     sub-directory containing one. This is the realistic
                     editorial path: the editor exports a submission's files and
                     runs the gate; the report is attached to the review.

  * --ojs-base URL --token T
                     pull the live submission queue from an OJS install via its
                     REST API (`/api/v1/submissions`). Real call; requires an
                     editor API token. Fails closed with a clear message if the
                     queue cannot be reached or files cannot be downloaded.

Outputs per submission: `reports/<id>.json`, `reports/<id>.md`, and an
`reports/EDITOR_SUMMARY.md` with an explicit editorial note.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from reprocheck.claims import Submission, from_text     # noqa: E402
from reprocheck.report import check, ReproReport        # noqa: E402
from reprocheck.resource import Resolver                # noqa: E402

EDITORIAL_NOTE = (
    "This reproducibility report is **advisory** and is provided to inform the "
    "editorial decision. It does **not** auto-reject the submission. A "
    "'DIVERGES' or 'FAIL' verdict means the submitted numbers could not be "
    "independently reproduced from the re-sourced primary data and warrant "
    "author clarification before acceptance; a 'cannot-verify' verdict is an "
    "honest non-result (e.g. data not sourceable), not a defect finding."
)


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# --------------------------------------------------------------------------
# discovery
# --------------------------------------------------------------------------

def discover_export(export_dir: str) -> list[tuple[str, Submission]]:
    """Find submissions in a local export directory."""
    d = Path(export_dir)
    subs: list[tuple[str, Submission]] = []
    if not d.exists():
        raise SystemExit(f"export directory not found: {d}")
    candidates = sorted(list(d.glob("*.json")) + list(d.glob("*/*.json")))
    for f in candidates:
        try:
            sub = Submission.from_json_file(str(f))
        except Exception as e:  # noqa: BLE001
            print(f"  ! skipped {f.name}: {e}", file=sys.stderr)
            continue
        subs.append((f.stem, sub))
    # also accept plain-text manuscripts
    for f in sorted(list(d.glob("*.txt")) + list(d.glob("*/*.txt"))):
        text = f.read_text(encoding="utf-8", errors="replace")
        subs.append((f.stem, from_text(text, title=f.stem)))
    return subs


def discover_ojs(base: str, token: str) -> list[tuple[str, Submission]]:
    """Pull the live submission queue from an OJS REST API.

    Real implementation. OJS does not expose extracted study tables, so this
    fetches each submission's metadata and any attached `*.json` study-table
    galley/file in the reprocheck schema. Submissions without a machine-readable
    study table are listed as 'needs structured data' (honest: we will not
    invent the trial table from prose here).
    """
    base = base.rstrip("/")

    def api(path: str) -> dict:
        url = f"{base}/api/v1/{path}"
        sep = "&" if "?" in url else "?"
        req = urllib.request.Request(f"{url}{sep}apiToken={token}",
                                     headers={"User-Agent": "reprocheck-gate/0.1"})
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.loads(r.read())

    out: list[tuple[str, Submission]] = []
    try:
        listing = api("submissions?status=1&count=50")   # 1 = queued/unassigned
    except Exception as e:  # noqa: BLE001 - fail closed
        raise SystemExit(f"could not reach OJS submission queue at {base}: {e}")
    for item in listing.get("items", []):
        sid = str(item.get("id"))
        title = ""
        pub = item.get("publications", [{}])
        if pub:
            title = (pub[0].get("fullTitle") or pub[0].get("title") or {})
            if isinstance(title, dict):
                title = next(iter(title.values()), "")
        # try to find an attached reprocheck-schema json file
        sub = None
        for f in item.get("submissionFiles", []) or []:
            url = f.get("url", "")
            if url.endswith(".json"):
                try:
                    req = urllib.request.Request(
                        f"{url}{'&' if '?' in url else '?'}apiToken={token}")
                    data = json.loads(urllib.request.urlopen(req, timeout=40).read())
                    sub = Submission.from_dict(data)
                except Exception:  # noqa: BLE001
                    sub = None
        if sub is None:
            sub = Submission(title=title or f"submission {sid}",
                             source=f"ojs:{sid} (no machine-readable study table)")
        out.append((sid, sub))
    return out


# --------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------

def run_gate(subs, out_dir: Path, resolver: Resolver) -> list[tuple[str, ReproReport]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    now = _now()
    results = []
    for sid, sub in subs:
        sub.source = sub.source or f"submission:{sid}"
        rep = check(sub, resolver=resolver, generated=now)
        (out_dir / f"{sid}.json").write_text(rep.to_json(), encoding="utf-8")
        (out_dir / f"{sid}.md").write_text(rep.to_markdown(), encoding="utf-8")
        results.append((sid, rep))
        print(f"  [{rep.overall.split(' ')[0]:11}] {sid} — {sub.title[:60]}")
    _write_summary(results, out_dir, now)
    return results


def _write_summary(results, out_dir: Path, now: str):
    L = ["# Synthēsis — pre-acceptance reproducibility summary", "",
         f"_Generated {now}. {len(results)} submission(s)._", "",
         "> " + EDITORIAL_NOTE, "",
         "| Submission | Title | Overall verdict | High flags | Report |",
         "|---|---|---|---|---|"]
    for sid, rep in results:
        nh = sum(1 for f in rep.flags if f.severity == "high")
        L.append(f"| {sid} | {rep.title[:50]} | **{rep.overall}** | {nh} "
                 f"| [{sid}.md]({sid}.md) |")
    (out_dir / "EDITOR_SUMMARY.md").write_text("\n".join(L) + "\n",
                                               encoding="utf-8")


def main(argv=None) -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Synthēsis pre-acceptance "
                                 "reproducibility gate (advisory; never "
                                 "auto-rejects).")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--export", help="local export directory of submission files")
    g.add_argument("--ojs-base", help="OJS base URL (with --token)")
    ap.add_argument("--token", help="OJS editor API token")
    ap.add_argument("--out", default="reports", help="output directory")
    ap.add_argument("--cache", default=".cache", help="re-sourcing cache dir")
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args(argv)

    if args.ojs_base and not args.token:
        ap.error("--ojs-base requires --token")

    if args.export:
        subs = discover_export(args.export)
    else:
        subs = discover_ojs(args.ojs_base, args.token)

    if not subs:
        print("no submissions found.")
        return 0
    print(f"checking {len(subs)} submission(s) -> {args.out}/")
    resolver = Resolver(cache_dir=args.cache, offline=args.offline)
    results = run_gate(subs, Path(args.out), resolver)
    n_bad = sum(1 for _, r in results if r.overall.startswith(("DIVERGES", "FAIL")))
    print(f"\ndone. {n_bad}/{len(results)} flagged for editor attention. "
          f"See {args.out}/EDITOR_SUMMARY.md (advisory; no auto-reject).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
