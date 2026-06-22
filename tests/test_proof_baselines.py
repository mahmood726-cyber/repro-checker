"""Oracle-locked numerical baselines for reprocheck/recompute.py — generated 2026-06-22.

Each estimator was cross-checked against an independent scipy oracle (scipy NOT
imported here; values baked in). The stdlib-only engine is held to its method's
accuracy floor (closed-form/NR special fns ~1e-9..1e-16; Acklam _norm_ppf ~1e-7).
_t_ppf was a confirmed bug (Cornish-Fisher series, ~11%% off at df=1) now fixed to
an exact inverse-t; this file locks the fix. Proof: prove-repro-checker workflow.
"""


# --- _norm_cdf ---
def test_norm_cdf_baseline():
    from reprocheck.recompute import _norm_cdf
    # Verified against scipy.stats.norm.cdf to <= 1.2e-16 over a tail+body grid.
    expected = {
        -8.0: 6.106226635438361e-16,
        -5.0: 2.8665157186802404e-07,
        -4.0: 3.167124183311998e-05,
        -3.0: 0.0013498980316301035,
        -2.0: 0.022750131948179153,
        -1.0: 0.15865525393145713,
        -0.5: 0.30853753872598694,
        0.0: 0.5,
        0.5: 0.691462461274013,
        1.0: 0.8413447460685428,
        2.0: 0.9772498680518209,
        3.0: 0.9986501019683699,
        4.0: 0.9999683287581669,
        5.0: 0.9999997133484282,
        6.0: 0.9999999990134123,
        8.0: 0.9999999999999993,
    }
    for x, exp in expected.items():
        assert abs(_norm_cdf(x) - exp) <= 1e-12, (x, _norm_cdf(x), exp)
    # symmetry Phi(-x) = 1 - Phi(x)
    for x in (0.3, 1.1, 2.7, 4.2):
        assert abs(_norm_cdf(-x) - (1.0 - _norm_cdf(x))) <= 1e-12
    # bounds
    assert _norm_cdf(-40.0) == 0.0 and _norm_cdf(40.0) == 1.0

# --- _norm_ppf ---
def test_norm_ppf_baseline():
    from reprocheck.recompute import _norm_ppf
    cases = {
        0.975: 1.959963984540054,
        0.025: -1.959963984540054,
        0.5: 0.0,
        0.99: 2.3263478740408408,
        0.1: -1.2815515655446004,
        1e-6: -4.753424308822899,
        1 - 1e-6: 4.753424308817087,
    }
    for p, oracle in cases.items():
        assert abs(_norm_ppf(p) - oracle) < 1e-7, (p, _norm_ppf(p), oracle)

# --- _chisq_sf ---
def test_chisq_sf_baseline():
    """Independent scipy-verified anchors for stdlib _chisq_sf (chi-square SF = Q(k/2, x/2))."""
    from reprocheck.recompute import _chisq_sf
    # (x, df, expected) verified against scipy.stats.chi2.sf
    anchors = [
        (3.84, 1, 0.05004352124870519),
        (5.99, 2, 0.05003662708658629),
        (11.07, 5, 0.050009618622405425),
        (15.51, 8, 0.0499552237239108),
        (1.0, 3, 0.8012519569012009),
        (50.0, 7, 1.4444852779215397e-08),
        (100.0, 1, 1.5239706048320995e-23),
        (200.0, 50, 7.857610724654791e-20),
        (0.0, 1, 1.0),
    ]
    for x, df, expect in anchors:
        got = _chisq_sf(x, df)
        if expect == 0.0:
            assert abs(got - expect) < 1e-9, (x, df, got, expect)
        else:
            rel = abs(got - expect) / abs(expect)
            assert rel < 1e-9 or abs(got - expect) < 1e-9, (x, df, got, expect, rel)

# --- _gammaincc ---
def test_gammaincc_baseline():
    import math
    from reprocheck.recompute import _gammaincc, _chisq_sf
    # scipy-verified anchors covering series (x<a+1), continued-fraction (x>=a+1),
    # half-integer a (=df/2), and deep tails. Oracle = scipy.special.gammaincc.
    cases = {
        (0.5, 0.1):  0.65472084601857683,
        (0.5, 1.0):  0.15729920705028105,
        (0.5, 5.0):  0.0015654022580025490,
        (0.5, 20.0): 2.5396285894708639e-10,
        (1.5, 2.5):  0.1717971442967335,
        (2.5, 0.5):  0.96256577324729642,
        (5.0, 6.0):  0.28505650031663121,
        (10.0, 11.0):0.34051064246566110,
        (10.0, 50.0):1.2596084591660847e-12,
        (0.5, 50.0): 1.5239706048320995e-23,
    }
    for (a, x), oracle in cases.items():
        got = _gammaincc(a, x)
        assert math.isclose(got, oracle, rel_tol=1e-7, abs_tol=1e-12), (a, x, got, oracle)
    # chi2.sf path: _chisq_sf(Q, df) == gammaincc(df/2, Q/2)
    assert math.isclose(_chisq_sf(10.0, 5), 0.07523524614651, rel_tol=1e-7)
    assert _chisq_sf(0.0, 3) == 1.0
    assert _chisq_sf(-1.0, 3) == 1.0

# --- _study_log_effect ---
def test_study_log_effect_baseline():
    import math
    from reprocheck.recompute import _study_log_effect
    # OR, no zero cell: closed-form exact to 1e-9
    le, var, est, lci, uci = _study_log_effect(
        {"shape": "count", "tE": 40, "tN": 100, "cE": 30, "cN": 100}, "OR")
    assert abs(le - 0.44183275227903923) < 1e-9
    assert abs(var - 0.0892857142857143) < 1e-9   # 1/a+1/b+1/c+1/d
    assert abs(est - 1.5555555555555556) < 1e-9
    assert abs(lci - 0.8660449169492748) < 1e-7   # CI uses _norm_ppf approx
    assert abs(uci - 2.7940272369977786) < 1e-7
    # OR with zero cell -> conditional 0.5 continuity correction
    le0, var0, est0, _, _ = _study_log_effect(
        {"shape": "count", "tE": 0, "tN": 50, "cE": 5, "cN": 50}, "OR")
    assert abs(le0 - (-2.50215628312278)) < 1e-9
    assert abs(var0 - 2.2235981839942234) < 1e-9
    # RR variance = 1/a - 1/(a+b) + 1/c - 1/(c+d)
    leR, varR, estR, _, _ = _study_log_effect(
        {"shape": "count", "tE": 40, "tN": 100, "cE": 30, "cN": 100}, "RR")
    assert abs(leR - 0.287682072451781) < 1e-9
    assert abs(varR - 0.03833333333333333) < 1e-9
    assert abs(estR - 1.3333333333333335) < 1e-9
    # effect-shape: SE recovered from log-CI width (generic inverse-variance / logHR-from-CI)
    leE, varE, estE, lciE, uciE = _study_log_effect(
        {"shape": "effect", "effect": 1.45, "elci": 1.10, "euci": 1.91}, "OR")
    assert abs(leE - 0.371563556432483) < 1e-9
    assert abs(varE - 0.019815101356264558) < 1e-7  # var via _norm_ppf z
    assert (estE, lciE, uciE) == (1.45, 1.10, 1.91)

# --- meta_analyze ---
def test_meta_analyze_baseline():
    # Verified against an independent scipy oracle (scipy NOT imported here).
    # Core pooled estimand + Q/I2/tau2/Qp are correct to ~1e-9; this baseline
    # locks those values. (Known minor defect: _t_ppf at df<=2 -> PI too narrow
    # for k<=3; this test deliberately uses k=6 (df=5) where PI error <3e-4.)
    from reprocheck.recompute import meta_analyze
    studies = [
        {'name': 'S1', 'shape': 'count', 'tE': 15, 'tN': 100, 'cE': 25, 'cN': 100},
        {'name': 'S2', 'shape': 'count', 'tE': 8,  'tN': 80,  'cE': 14, 'cN': 82},
        {'name': 'S3', 'shape': 'count', 'tE': 30, 'tN': 150, 'cE': 40, 'cN': 150},
        {'name': 'S4', 'shape': 'count', 'tE': 0,  'tN': 50,  'cE': 6,  'cN': 52},
        {'name': 'S5', 'shape': 'count', 'tE': 12, 'tN': 90,  'cE': 18, 'cN': 88},
        {'name': 'S6', 'shape': 'count', 'tE': 22, 'tN': 120, 'cE': 28, 'cN': 118},
    ]
    _, p = meta_analyze(studies, 'OR')
    # oracle (independent scipy reimpl) values:
    assert abs(p.log_est - (-0.48222676816889587)) < 1e-9
    assert abs(p.se     -   0.1552849132168705)   < 1e-9
    assert abs(p.est    -   0.6174070376253855)   < 1e-9
    assert abs(p.lci    -   0.45539978137895604)  < 1e-7
    assert abs(p.uci    -   0.8370479427001521)   < 1e-7
    assert abs(p.Q      -   2.7913968273322842)   < 1e-9
    assert abs(p.I2     -   0.0)                   < 1e-9
    assert abs(p.tau2_dl-   0.0)                   < 1e-12
    assert abs(p.Qp     -   0.7321081001252299)   < 1e-7
    assert p.Qdf == 5 and p.k == 6
    # only the zero-cell study (S4) is continuity-corrected:
    _, prr = meta_analyze(studies, 'RR')
    assert abs(prr.est - 0.6850281591323066) < 1e-9
    assert abs(prr.Qp  - 0.7068285069801052) < 1e-7
    # special-function spot checks vs scipy oracle (df>=5 region is accurate):
    from reprocheck.recompute import _norm_ppf, _gammaincc, _chisq_sf, _t_ppf
    assert abs(_norm_ppf(0.975) - 1.959963984540054) < 5e-9
    assert abs(_gammaincc(2.5, 3.0) - 0.30621891841327875) < 1e-9
    assert abs(_chisq_sf(11.07, 5) - 0.050009618622405425) < 1e-9
    assert abs(_t_ppf(0.975, 100) - 1.9839715185235518) < 1e-7
    assert abs(_t_ppf(0.975, 10) - 2.2281388519862744) < 5e-5

# --- pool ---
def test_pool_baseline():
    import math
    from reprocheck.recompute import pool, meta_analyze
    studies = [
        {'name': 'S1', 'shape': 'count', 'tE': 12, 'tN': 100, 'cE': 20, 'cN': 100},
        {'name': 'S2', 'shape': 'count', 'tE': 5,  'tN': 80,  'cE': 9,  'cN': 82},
        {'name': 'S3', 'shape': 'count', 'tE': 0,  'tN': 50,  'cE': 4,  'cN': 50},  # zero-cell -> conditional +0.5
        {'name': 'S4', 'shape': 'count', 'tE': 30, 'tN': 150, 'cE': 40, 'cN': 150},
        {'name': 'S5', 'shape': 'count', 'tE': 8,  'tN': 90,  'cE': 15, 'cN': 95},
        {'name': 'S6', 'shape': 'count', 'tE': 22, 'tN': 120, 'cE': 28, 'cN': 118},
    ]
    p = pool(studies, 'OR')
    # consistency: pool == meta_analyze pooled
    _, m = meta_analyze(studies, 'OR')
    assert p.as_dict() == m.as_dict()
    # scipy-oracle-verified pooled quantities (closed-form, tol 1e-9)
    assert math.isclose(p.est,     0.6203167393867882, abs_tol=1e-9)
    assert math.isclose(p.lci,     0.4501067351028031, abs_tol=1e-8)
    assert math.isclose(p.uci,     0.8548924669513577, abs_tol=1e-8)
    assert math.isclose(p.log_est, -0.47752506141395,  abs_tol=1e-9)
    assert math.isclose(p.se,      0.1636486569862367, abs_tol=1e-9)
    assert math.isclose(p.Q,       2.1013646873873624, abs_tol=1e-9)
    assert math.isclose(p.Qp,      0.8349490125128529, abs_tol=1e-7)
    assert p.I2 == 0.0 and p.tau2 == 0.0 and p.tau2_dl == 0.0
    assert p.k == 6 and p.Qdf == 5
    # RR heterogeneous REML cross-check (scipy-oracle tau2)
    rr = [
        {'name': 'A', 'shape': 'count', 'tE': 10, 'tN': 100, 'cE': 30, 'cN': 100},
        {'name': 'B', 'shape': 'count', 'tE': 40, 'tN': 100, 'cE': 35, 'cN': 100},
        {'name': 'C', 'shape': 'count', 'tE': 5,  'tN': 100, 'cE': 25, 'cN': 100},
        {'name': 'D', 'shape': 'count', 'tE': 0,  'tN': 50,  'cE': 6,  'cN': 50},
        {'name': 'E', 'shape': 'count', 'tE': 50, 'tN': 120, 'cE': 20, 'cN': 120},
    ]
    pr = pool(rr, 'RR')
    assert math.isclose(pr.tau2, 1.277961575537937, abs_tol=1e-7)
    assert math.isclose(pr.I2, 90.40077006684244, abs_tol=1e-6)
    # k=1 -> prediction interval undefined
    p1 = pool([{'name': 'X', 'shape': 'count', 'tE': 10, 'tN': 100, 'cE': 20, 'cN': 100}], 'OR')
    assert math.isnan(p1.pi_lci) and math.isnan(p1.pi_uci)

# --- _t_ppf (fixed: exact inverse-t) ---
def test_t_ppf_baseline():
    """Fixed _t_ppf: exact Student-t quantile (was Cornish-Fisher, ~11%% off at df=1).
    Anchors verified vs scipy.stats.t.ppf to ~1e-11; scipy not imported here.
    """
    import math
    from reprocheck.recompute import _t_ppf
    anchors = {
        1: 12.706204736174694,
        2: 4.302652729749462,
        3: 3.1824463052837078,
        4: 2.7764451051977934,
        5: 2.570581835636315,
        7: 2.364624251592784,
        10: 2.2281388519862744,
        30: 2.0422724563012378,
        100: 1.9839715185235518,
        200: 1.9718962236339088,
    }
    for df, exp in anchors.items():
        assert abs(_t_ppf(0.975, df) - exp) < 1e-6, (df, _t_ppf(0.975, df), exp)
    assert abs(_t_ppf(0.975, 1) - math.tan(math.pi * (0.975 - 0.5))) < 1e-12
    assert abs(_t_ppf(0.025, 5) + _t_ppf(0.975, 5)) < 1e-9
    assert abs(_t_ppf(0.975, 100000) - 1.959963984540054) < 1e-4

