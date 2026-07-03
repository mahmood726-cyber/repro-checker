"""Run the reproducibility checker on the honest validation set and assert the
expected verdicts. Writes VALIDATION.md.

Validation set (agreed):
  * 105 (JAK-RA), 106 (asthma biologics)      -> MUST reproduce
  * corrupted 105/106, #30 stand-in, GLP-1    -> MUST flag / diverge
  * INCRETIN "0.62-vs-0.41" QA fixture         -> reported NOT FOUND (honest)

The verdict contract + fixture set live in `reprocheck.benchmark` (one source of
truth, also exposed as `python -m reprocheck.cli validate`); this script layers
on the VALIDATION.md writer and the INCRETIN not-found note.

Use --offline to skip live re-sourcing (numeric reproduction still runs; the
citation-integrity checks that need the network are noted as skipped).
"""
import argparse
import datetime as _dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from reprocheck.benchmark import run_benchmark, ROOT as BROOT   # noqa: E402


def render_md(result, now, offline):
    L = [f"# Validation results — reprocheck", "",
         f"_Generated {now}{' (offline)' if offline else ' (live re-sourcing)'}._",
         "",
         f"**{result.passed}/{result.total} fixtures matched their expected verdict.**",
         "",
         "| Fixture | Purpose | Expected | Overall verdict | Claimed | Recomputed | High flags | Match |",
         "|---|---|---|---|---|---|---|---|"]
    for r in result.rows:
        ce = "—" if r.claimed_est is None else f"{r.claimed_est:g}"
        re_ = "—" if r.recomputed_est is None else f"{r.recomputed_est:.3g}"
        L.append(f"| `{r.fixture}` | {r.purpose} | {r.want} "
                 f"| {r.overall} | {ce} | {re_} | {r.n_high} "
                 f"| {'✅' if r.ok else '❌'} |")
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
    now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    result = run_benchmark(offline=args.offline, cache_dir=str(BROOT / ".cache"))
    md = render_md(result, now, args.offline)
    print(md)
    if args.write:
        (BROOT / "VALIDATION.md").write_text(md, encoding="utf-8")
        print(f"\nwrote {BROOT / 'VALIDATION.md'}")
    return 0 if result.all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
