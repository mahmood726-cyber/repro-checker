"""The bundled reproducibility benchmark (offline) must pass on every fixture
and produce a rendered table. This is the reproducible-benchmark contract also
exposed as `python -m reprocheck.cli validate`.
"""
from reprocheck.benchmark import run_benchmark, render_table, EXPECT


def test_offline_benchmark_all_pass():
    result = run_benchmark(offline=True)
    assert result.total == len(EXPECT)
    assert result.all_passed, [r.fixture for r in result.rows if not r.ok]
    assert result.passed == result.total


def test_benchmark_rows_carry_recomputed_values():
    result = run_benchmark(offline=True)
    by_name = {r.fixture: r for r in result.rows}
    # the reproducing JAK/RA fixture recomputes near its claimed OR 3.40
    jak = by_name["paper105_jak_ra.json"]
    assert jak.recomputed_est is not None
    assert abs(jak.recomputed_est - 3.40) < 0.03
    # the structural fixture carries high-severity flags
    assert by_name["paper30_structural.json"].n_high >= 1


def test_render_table_is_markdown():
    result = run_benchmark(offline=True)
    md = render_table(result)
    assert "| Fixture |" in md
    assert "PASS" in md
    assert "matched their expected verdict" in md
