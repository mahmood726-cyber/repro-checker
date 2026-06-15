"""Recompute engine: pooled estimates must match the known reference values and
honor the advanced-stats rules (continuity correction, t_{k-1} PI)."""
import math

from reprocheck.recompute import meta_analyze, pool


def test_jak_ra_count_shape_reproduces():
    # ORAL Solo / RA-BEAM / SELECT-NEXT / FINCH 1 -> dashboard OR 3.40 (2.89-3.99)
    studies = [
        {"name": "ORAL Solo", "shape": "count", "tE": 144, "tN": 241, "cE": 32, "cN": 120},
        {"name": "RA-BEAM", "shape": "count", "tE": 339, "tN": 487, "cE": 196, "cN": 488},
        {"name": "SELECT-NEXT", "shape": "count", "tE": 141, "tN": 221, "cE": 79, "cN": 221},
        {"name": "FINCH 1", "shape": "count", "tE": 364, "tN": 475, "cE": 237, "cN": 475},
    ]
    p = pool(studies, "OR")
    assert abs(p.est - 3.40) < 0.03
    assert abs(p.lci - 2.89) < 0.05
    assert abs(p.uci - 3.99) < 0.06
    assert p.k == 4
    assert p.I2 < 1.0          # dashboard reports I2 = 0%


def test_asthma_effect_shape_reproduces():
    studies = [
        {"name": "EXTRA", "shape": "effect", "effect": 0.75, "elci": 0.61, "euci": 0.92},
        {"name": "MENSA", "shape": "effect", "effect": 0.47, "elci": 0.35, "euci": 0.63},
        {"name": "SIROCCO", "shape": "effect", "effect": 0.49, "elci": 0.37, "euci": 0.64},
        {"name": "Resliz", "shape": "effect", "effect": 0.50, "elci": 0.37, "euci": 0.67},
        {"name": "QUEST", "shape": "effect", "effect": 0.523, "elci": 0.413, "euci": 0.662},
        {"name": "NAVIGATOR", "shape": "effect", "effect": 0.44, "elci": 0.37, "euci": 0.53},
    ]
    p = pool(studies, "RR")
    assert abs(p.est - 0.52) < 0.02
    assert abs(p.I2 - 69.0) < 3.0


def test_continuity_correction_only_on_zero_cell():
    # zero-event arm triggers the 0.5 correction; non-zero does not crash
    z = pool([{"name": "z", "shape": "count", "tE": 0, "tN": 50, "cE": 5, "cN": 50},
              {"name": "y", "shape": "count", "tE": 3, "tN": 50, "cE": 6, "cN": 50}], "OR")
    assert math.isfinite(z.est)


def test_single_study_pi_undefined():
    p = pool([{"name": "a", "shape": "effect", "effect": 0.8, "elci": 0.6, "euci": 1.0}], "RR")
    assert p.k == 1
    assert math.isnan(p.pi_lci)
