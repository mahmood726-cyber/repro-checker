"""compare(): per-claim reproduces / diverges / cannot-verify verdicts."""
from reprocheck.claims import Claimed
from reprocheck.compare import compare
from reprocheck.recompute import pool


def _pooled():
    return pool([
        {"name": "a", "shape": "effect", "effect": 0.80, "elci": 0.70, "euci": 0.91},
        {"name": "b", "shape": "effect", "effect": 0.90, "elci": 0.80, "euci": 1.01},
    ], "RR")


def test_reproduces_within_tolerance():
    p = _pooled()
    claimed = Claimed(measure="RR", est=round(p.est, 2), lci=round(p.lci, 2),
                      uci=round(p.uci, 2))
    verds = {c.quantity: c.verdict for c in compare(claimed, p)}
    assert verds["pooled RR"] == "reproduces"


def test_diverges_shows_both_values():
    p = _pooled()
    claimed = Claimed(measure="RR", est=0.40)   # far from recomputed ~0.85
    pooled_claim = next(c for c in compare(claimed, p) if c.quantity == "pooled RR")
    assert pooled_claim.verdict == "diverges"
    assert pooled_claim.claimed == 0.40
    assert pooled_claim.recomputed is not None


def test_cannot_verify_when_no_recompute():
    claimed = Claimed(measure="OR", est=2.0)
    pooled_claim = next(c for c in compare(claimed, None) if c.quantity == "pooled OR")
    assert pooled_claim.verdict == "cannot-verify"
    assert "recompute" in pooled_claim.reason or "sourceable" in pooled_claim.reason


def test_cannot_verify_when_paper_silent():
    p = _pooled()
    claimed = Claimed(measure="RR")    # est is None
    pooled_claim = next(c for c in compare(claimed, p) if c.quantity == "pooled RR")
    assert pooled_claim.verdict == "cannot-verify"
    assert "did not state" in pooled_claim.reason


def test_k_mismatch_diverges():
    p = _pooled()      # k = 2
    claimed = Claimed(measure="RR", est=round(p.est, 2), k=5)
    kc = next(c for c in compare(claimed, p) if c.quantity.startswith("k "))
    assert kc.verdict == "diverges"
    assert kc.claimed == 5 and kc.recomputed == 2
