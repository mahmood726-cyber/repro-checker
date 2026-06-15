"""Compare independently recomputed pooled statistics with a paper's claims.

Produces one ClaimVerdict per claimed quantity (pooled effect, CI bounds, I^2,
Q, k, prediction interval). A claim is:

  * reproduces   -- recomputed value agrees within tolerance
  * diverges     -- recomputed value disagrees; BOTH values are reported
  * cannot-verify-- recomputed value unavailable (no sourceable data) or the
                    paper did not state the quantity (reason given)

Ratio measures (OR/RR/HR) are compared on the relative/log scale; difference
measures (MD/SMD) on the absolute scale.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict

from .claims import Claimed
from .recompute import PooledEffect

RATIO_MEASURES = {"OR", "RR", "HR", "IRR", "RATERATIO"}


@dataclass
class Tolerances:
    rel_est: float = 0.05      # ±5% relative on a ratio point estimate
    rel_ci: float = 0.08       # ±8% relative on a ratio CI bound
    abs_est: float = 0.05      # absolute, for difference measures
    abs_ci: float = 0.10
    i2_pts: float = 5.0        # ±5 percentage points on I^2
    q_abs: float = 1.0         # absolute on Q
    pi_rel: float = 0.15


@dataclass
class ClaimVerdict:
    quantity: str
    claimed: object
    recomputed: object
    verdict: str               # reproduces | diverges | cannot-verify
    tolerance: str
    reason: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def _ratio_close(a: float, b: float, rel: float) -> bool:
    if a is None or b is None or a <= 0 or b <= 0:
        return False
    return abs(math.log(a) - math.log(b)) <= math.log(1 + rel)


def _abs_close(a: float, b: float, tol: float) -> bool:
    return a is not None and b is not None and abs(a - b) <= tol


def _verdict(claimed, recomputed, ok: bool, tol_desc: str,
             quantity: str, missing_reason: str = "") -> ClaimVerdict:
    if claimed is None:
        return ClaimVerdict(quantity, None, recomputed, "cannot-verify",
                            tol_desc, "paper did not state this quantity")
    if recomputed is None:
        return ClaimVerdict(quantity, claimed, None, "cannot-verify",
                            tol_desc, missing_reason or "no sourceable data to recompute")
    return ClaimVerdict(quantity, claimed, recomputed,
                        "reproduces" if ok else "diverges", tol_desc)


def compare(claimed: Claimed, pooled: PooledEffect | None,
            tol: Tolerances | None = None,
            recompute_reason: str = "") -> list[ClaimVerdict]:
    tol = tol or Tolerances()
    measure = (claimed.measure or (pooled.measure if pooled else "")).upper()
    is_ratio = measure in RATIO_MEASURES
    out: list[ClaimVerdict] = []

    def cmp_effect(name, claim_v, recomp_v, rel, ab):
        if is_ratio:
            ok = _ratio_close(claim_v, recomp_v, rel)
            td = f"±{rel:.0%} relative (log scale)"
        else:
            ok = _abs_close(claim_v, recomp_v, ab)
            td = f"±{ab} absolute"
        return _verdict(claim_v, recomp_v, ok, td, name, recompute_reason)

    p = pooled
    out.append(cmp_effect(f"pooled {measure or 'effect'}", claimed.est,
                          p.est if p else None, tol.rel_est, tol.abs_est))
    out.append(cmp_effect("95% CI lower", claimed.lci,
                          p.lci if p else None, tol.rel_ci, tol.abs_ci))
    out.append(cmp_effect("95% CI upper", claimed.uci,
                          p.uci if p else None, tol.rel_ci, tol.abs_ci))

    # I^2
    ok = _abs_close(claimed.I2, p.I2 if p else None, tol.i2_pts)
    out.append(_verdict(claimed.I2, round(p.I2, 1) if p else None, ok,
                        f"±{tol.i2_pts} pts", "I^2 (%)", recompute_reason))

    # Q (only if claimed)
    if claimed.Q is not None:
        ok = _abs_close(claimed.Q, p.Q if p else None, tol.q_abs)
        out.append(_verdict(claimed.Q, round(p.Q, 3) if p else None, ok,
                            f"±{tol.q_abs}", "Cochran's Q", recompute_reason))

    # k (study count)
    k_recomp = p.k if p else None
    if claimed.k is not None:
        ok = (k_recomp is not None and claimed.k == k_recomp)
        out.append(_verdict(claimed.k, k_recomp, ok, "exact",
                            "k (studies pooled)",
                            "no poolable trials re-sourced"))

    # prediction interval (only if claimed and computable)
    if claimed.pi_lci is not None and p is not None and not math.isnan(p.pi_lci):
        if is_ratio:
            ok_lo = _ratio_close(claimed.pi_lci, p.pi_lci, tol.pi_rel)
            ok_hi = _ratio_close(claimed.pi_uci, p.pi_uci, tol.pi_rel)
        else:
            ok_lo = _abs_close(claimed.pi_lci, p.pi_lci, tol.abs_ci * 2)
            ok_hi = _abs_close(claimed.pi_uci, p.pi_uci, tol.abs_ci * 2)
        out.append(_verdict(claimed.pi_lci, round(p.pi_lci, 3), ok_lo,
                            f"±{tol.pi_rel:.0%}", "prediction interval lower"))
        out.append(_verdict(claimed.pi_uci, round(p.pi_uci, 3), ok_hi,
                            f"±{tol.pi_rel:.0%}", "prediction interval upper"))

    return out
