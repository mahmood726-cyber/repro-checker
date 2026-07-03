"""Reproducible validation benchmark for the reproducibility checker.

Runs the checker over the bundled honest validation fixtures and asserts each
one lands on its expected overall verdict. This is the repo's reproducible
benchmark: it runs offline (numeric reproduction only) or live (adds the
citation-integrity re-sourcing), produces a result table, and is exposed both
as ``python -m reprocheck.cli validate`` and via ``scripts/validate.py``.

Truth-first: the expected verdicts below are the *behaviour contract* of the
engine, not tuned targets. The scientific numbers live in the fixtures and are
never altered here; this module only checks that the pipeline classifies them
correctly.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .claims import Submission
from .report import check
from .resource import Resolver

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "fixtures"

# fixture -> (expected overall-verdict prefix, one-line purpose)
EXPECT: list[tuple[str, str, str]] = [
    ("paper105_jak_ra.json",    "REPRODUCES", "JAK/RA — must reproduce"),
    ("paper106_asthma.json",    "REPRODUCES", "asthma biologics — must reproduce"),
    ("paper105_corrupted.json", "DIVERGES",   "planted transcription error — must diverge"),
    ("paper106_corrupted.json", "DIVERGES",   "planted decimal error — must diverge"),
    ("glp1_elixa.json",         "DIVERGES",   "GLP-1/ELIXA over-stated pool — must diverge"),
    ("paper30_structural.json", "FAIL",       "#30 structural defects — must flag (FAIL)"),
]


@dataclass
class BenchRow:
    fixture: str
    purpose: str
    want: str
    overall: str
    ok: bool
    claimed_est: float | None
    recomputed_est: float | None
    n_high: int
    n_flags: int


@dataclass
class BenchResult:
    rows: list[BenchRow]
    passed: int
    failed: int

    @property
    def total(self) -> int:
        return self.passed + self.failed

    @property
    def all_passed(self) -> bool:
        return self.failed == 0


def run_benchmark(offline: bool = True, cache_dir: str | None = None,
                  fixtures_dir: Path | None = None) -> BenchResult:
    """Run the validation benchmark and return a structured result.

    Offline by default so it is deterministic and network-free (numeric
    reproduction still runs; the live citation-integrity re-sourcing is skipped).
    Pass ``offline=False`` to add the network re-sourcing checks.
    """
    fixtures_dir = fixtures_dir or FIXTURES
    resolver = Resolver(cache_dir=cache_dir or str(ROOT / ".cache"), offline=offline)
    rows: list[BenchRow] = []
    passed = failed = 0
    for fname, want, purpose in EXPECT:
        path = fixtures_dir / fname
        if not path.exists():
            raise FileNotFoundError(f"benchmark fixture missing: {path}")
        sub = Submission.from_json_file(str(path))
        rep = check(sub, resolver=resolver, generated="benchmark")
        ok = rep.overall.startswith(want)
        passed += ok
        failed += (not ok)
        rows.append(BenchRow(
            fixture=fname, purpose=purpose, want=want, overall=rep.overall,
            ok=ok, claimed_est=sub.claimed.est,
            recomputed_est=rep.recomputed["est"] if rep.recomputed else None,
            n_high=sum(1 for f in rep.flags if f.severity == "high"),
            n_flags=len(rep.flags),
        ))
    return BenchResult(rows=rows, passed=passed, failed=failed)


def render_table(result: BenchResult) -> str:
    """Render the benchmark result as a Markdown table."""
    L = [f"**{result.passed}/{result.total} fixtures matched their expected "
         f"verdict.**", "",
         "| Fixture | Purpose | Expected | Overall verdict | Claimed | "
         "Recomputed | High flags | Match |",
         "|---|---|---|---|---|---|---|---|"]
    for r in result.rows:
        ce = "—" if r.claimed_est is None else f"{r.claimed_est:g}"
        re_ = "—" if r.recomputed_est is None else f"{r.recomputed_est:.3g}"
        L.append(f"| `{r.fixture}` | {r.purpose} | {r.want} | {r.overall} "
                 f"| {ce} | {re_} | {r.n_high} | {'PASS' if r.ok else 'FAIL'} |")
    return "\n".join(L)
