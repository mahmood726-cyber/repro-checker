"""Regression tests from the P55 validation (metafor oracle + verdict-rule requirements).

Each test failed on commit b8aee89. Oracle values: metafor 5.2-1 / R 4.6.0 (qnorm, rma REML).
"""
import math

from reprocheck.claims import Submission
from reprocheck.recompute import meta_analyze, _norm_ppf
from reprocheck.report import check
from reprocheck.resource import Resolver


def _sub(claimed, trials):
    return Submission.from_dict({"title": "t", "claimed": claimed, "trials": trials})


# --- D1: single study ---------------------------------------------------------------------
def test_single_study_does_not_crash_and_has_no_heterogeneity():
    # k=1 configuration from the P55 corpus whose fixed-effect mean differs from y_1 by one ulp;
    # b8aee89 raised ZeroDivisionError (chi-square sf with 0 df) and the page reported I2 = 100%.
    for m, st in (("OR", {"tE": 23, "tN": 257, "cE": 17, "cN": 237}),
                  ("OR", {"tE": 7, "tN": 73, "cE": 28, "cN": 197}),
                  ("OR", {"tE": 21, "tN": 146, "cE": 30, "cN": 256}),
                  ("RR", {"tE": 64, "tN": 256, "cE": 101, "cN": 392})):
        s = dict(st, name="s1", shape="count")
        _, p = meta_analyze([s], m)
        assert p.Q == 0.0 and p.I2 == 0.0 and p.tau2 == 0.0
        assert math.isnan(p.Qp)          # Q test with 0 df is undefined
        assert math.isnan(p.pi_lci) and math.isnan(p.pi_uci)


# --- D2: 97.5% normal quantile ------------------------------------------------------------
def test_effect_shape_se_uses_exact_normal_quantile():
    z = 1.959963984540054                 # qnorm(0.975), R 4.6.0
    s = {"name": "e", "shape": "effect", "effect": 0.8, "elci": 0.6, "euci": 1.1}
    per, _ = meta_analyze([s, dict(s, name="f", effect=0.7)], "HR")
    se = (math.log(1.1) - math.log(0.6)) / (2 * z)
    assert abs(per[0].se - se) <= 1e-15
    assert abs(_norm_ppf(0.975) - z) <= 1e-15


# --- D3/D4: claims that cannot be checked must stay visible --------------------------------
def test_claimed_pi_with_one_study_is_cannot_verify_not_dropped():
    rep = check(_sub({"measure": "OR", "est": 2.0, "pi_lci": 0.2, "pi_uci": 2.0},
                     [{"name": "a", "tE": 15, "tN": 100, "cE": 25, "cN": 100}]))
    pis = [c for c in rep.claims if c.quantity.startswith("prediction interval")]
    assert len(pis) == 2 and all(c.verdict == "cannot-verify" for c in pis)


def test_claimed_tau2_is_listed():
    rep = check(_sub({"measure": "OR", "est": 0.6, "tau2": 0.05},
                     [{"name": "a", "tE": 15, "tN": 100, "cE": 25, "cN": 100},
                      {"name": "b", "tE": 30, "tN": 120, "cE": 32, "cN": 118}]))
    assert any("tau" in c.quantity.lower() for c in rep.claims)


# --- D6/D7: unsupported measures are cannot-verify, not a number or FAIL --------------------
def test_difference_measure_is_cannot_verify():
    for m, rows in (("MD", [(1.2, 0.4, 2.0), (1.8, 0.9, 2.7)]),
                    ("SMD", [(-0.2, -0.5, 0.1), (-0.4, -0.7, -0.1)])):
        tr = [{"name": f"r{i}", "effect": e, "elci": l, "euci": u} for i, (e, l, u) in enumerate(rows)]
        rep = check(_sub({"measure": m, "est": 1.0}, tr))
        est = next(c for c in rep.claims if c.quantity.startswith("pooled"))
        assert est.verdict == "cannot-verify", (m, est)
        assert not rep.overall.startswith("FAIL"), (m, rep.overall)


def test_hr_claim_from_counts_is_cannot_verify():
    rep = check(_sub({"measure": "HR", "est": 0.6},
                     [{"name": "a", "tE": 15, "tN": 100, "cE": 25, "cN": 100},
                      {"name": "b", "tE": 30, "tN": 120, "cE": 32, "cN": 118}]))
    est = next(c for c in rep.claims if c.quantity.startswith("pooled"))
    assert est.verdict == "cannot-verify"


# --- D5: an unsourced REPRODUCES must say so ------------------------------------------------
def test_reproduces_discloses_unsourced_citations():
    tr = [{"name": "a", "nct": "NCT00000001", "tE": 15, "tN": 100, "cE": 25, "cN": 100},
          {"name": "b", "nct": "NCT00000002", "tE": 30, "tN": 120, "cE": 32, "cN": 118}]
    base = check(_sub({"measure": "OR", "est": 0.5}, tr))
    rep = check(_sub({"measure": "OR", "est": base.recomputed["est"]}, tr),
                resolver=Resolver(cache_dir=None, offline=True, email=""))
    assert rep.overall.startswith("REPRODUCES")
    assert "re-sourced" in rep.overall_detail


# --- D9: no personal e-mail default ---------------------------------------------------------
def test_no_hardcoded_email_default(monkeypatch):
    monkeypatch.delenv("REPROCHECK_EMAIL", raising=False)
    assert Resolver().email == ""
