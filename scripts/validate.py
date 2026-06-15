"""Run the reproducibility checker on the honest validation set and assert the
expected verdicts. Writes VALIDATION.md.

Validation set (agreed):
  * 105 (JAK-RA), 106 (asthma biologics)      -> MUST reproduce
  * corrupted 105/106, #30 stand-in, GLP-1    -> MUST flag / diverge
  * INCRETIN "0.62-vs-0.41" QA fixture         -> reported NOT FOUND (honest)

Use --offline to skip live re-sourcing (numeric reproduction still runs; the
citation-integrity checks that need the network are noted as skipped).
"""
import argparse
import datetime as _dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from reprocheck.claims import Submission          # noqa: E402
from reprocheck.report import check               # noqa: E402
from reprocheck.resource import Resolver          # noqa: E402

FIX = ROOT / "fixtures"

# fixture -> (expected overall-verdict prefix, one-line purpose)
EXPECT = [
    ("paper105_jak_ra.json",   "REPRODUCES", "JAK/RA — must reproduce"),
    ("paper106_asthma.json",   "REPRODUCES", "asthma biologics — must reproduce"),
    ("paper105_corrupted.json", "DIVERGES",  "planted transcription error — must diverge"),
    ("paper106_corrupted.json", "DIVERGES",  "planted decimal error — must diverge"),
    ("glp1_elixa.json",         "DIVERGES",  "GLP-1/ELIXA over-stated pool — must diverge"),
    ("paper30_structural.json", "FAIL",      "#30 structural defects — must flag (FAIL)"),
]


def run(offline: bool):
    resolver = Resolver(cache_dir=str(ROOT / ".cache"), offline=offline)
    now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    rows, passed, failed = [], 0, 0
    for fname, want, purpose in EXPECT:
        sub = Submission.from_json_file(str(FIX / fname))
        rep = check(sub, resolver=resolver, generated=now)
        got = rep.overall.split(" ")[0].split("—")[0].strip()
        ok = rep.overall.startswith(want)
        passed += ok
        failed += (not ok)
        est = rep.recomputed["est"] if rep.recomputed else None
        claim = sub.claimed.est
        rows.append({
            "fixture": fname, "purpose": purpose, "want": want,
            "overall": rep.overall, "ok": ok,
            "claimed_est": claim, "recomputed_est": est,
            "n_high": sum(1 for f in rep.flags if f.severity == "high"),
            "n_flags": len(rep.flags),
        })
    return rows, passed, failed, now


def render_md(rows, passed, failed, now, offline):
    L = [f"# Validation results — reprocheck", "",
         f"_Generated {now}{' (offline)' if offline else ' (live re-sourcing)'}._",
         "",
         f"**{passed}/{passed + failed} fixtures matched their expected verdict.**",
         "",
         "| Fixture | Purpose | Expected | Overall verdict | Claimed | Recomputed | High flags | Match |",
         "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        ce = "—" if r["claimed_est"] is None else f"{r['claimed_est']:g}"
        re_ = "—" if r["recomputed_est"] is None else f"{r['recomputed_est']:.3g}"
        L.append(f"| `{r['fixture']}` | {r['purpose']} | {r['want']} "
                 f"| {r['overall']} | {ce} | {re_} | {r['n_high']} "
                 f"| {'✅' if r['ok'] else '❌'} |")
    L += ["",
          "## INCRETIN / GLP-1 '0.62-vs-0.41' QA case — NOT FOUND",
          "",
          "The specific INCRETIN-set fixture with documented wrong extraction and a "
          "0.62-vs-0.41 benchmark could **not be located on disk** (no `incretin` "
          "QA notes; the `glp1-cvot-engine` dashboard contains no `0.41`). It is "
          "therefore reported honestly as **not-found**, and no fixture was "
          "fabricated for it. The `glp1_elixa.json` fixture instead reproduces the "
          "*same failure mode* (a claimed pool that is too strong) using the real, "
          "live-resourceable published MACE hazard ratios of the eight GLP-1 CVOTs "
          "(ELIXA the neutral anchor); the checker recomputes ~0.86 against the "
          "claimed 0.62 and flags the divergence.", ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--write", action="store_true", help="write VALIDATION.md")
    args = ap.parse_args()
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    rows, passed, failed, now = run(args.offline)
    md = render_md(rows, passed, failed, now, args.offline)
    print(md)
    if args.write:
        (ROOT / "VALIDATION.md").write_text(md, encoding="utf-8")
        print(f"\nwrote {ROOT / 'VALIDATION.md'}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
