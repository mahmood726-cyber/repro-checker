"""Independent meta-analysis recomputation engine.

VENDORED VERBATIM from synthesis-paper-spec/metapaper/stats.py (audited,
R-cross-checked against metafor, scipy-free) and extended with thin wrappers
used by the reproducibility checker. The vendored core is the single source of
truth for pooling; do not re-derive the math here.

Purpose: TRUTH CHECK. We recompute the per-study and pooled effects directly
from re-sourced trial data and compare them with the values a paper *claims*.
Nothing is reported as reproduced unless it traces back to these numbers.

Effect measures supported: odds ratio (OR), risk ratio (RR). Pooling is
inverse-variance random-effects (DerSimonian-Laird, cross-checked against a REML
iteration), reported on the log scale and back-transformed (Cochrane Handbook
v6.5). Continuity correction adds 0.5 ONLY when a cell is zero (advanced-stats
rule). Prediction interval uses t_{k-1} (Cochrane v6.5), undefined for k<2.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


# ---- normal / t helpers (no scipy dependency) -----------------------------

def _norm_ppf(p: float) -> float:
    """Inverse standard-normal CDF (Acklam's algorithm)."""
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def _norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


@dataclass
class StudyEffect:
    name: str
    est: float          # back-transformed effect (OR or RR)
    lci: float
    uci: float
    log_est: float      # effect on log scale
    se: float           # SE of log effect
    weight_pct: float = 0.0  # random-effects weight (%)


@dataclass
class PooledEffect:
    measure: str
    est: float
    lci: float
    uci: float
    log_est: float
    se: float
    Q: float
    Qdf: int
    Qp: float
    I2: float
    tau2: float          # tau^2 used for pooling (REML)
    tau2_dl: float = 0.0  # DerSimonian-Laird tau^2 (cross-check)
    pi_lci: float = float("nan")
    pi_uci: float = float("nan")
    k: int = 0
    estimator: str = "REML"

    def as_dict(self) -> dict:
        return {
            "measure": self.measure, "est": self.est, "lci": self.lci,
            "uci": self.uci, "log_est": self.log_est, "se": self.se,
            "Q": self.Q, "Qdf": self.Qdf, "Qp": self.Qp, "I2": self.I2,
            "tau2": self.tau2, "tau2_dl": self.tau2_dl,
            "pi_lci": self.pi_lci, "pi_uci": self.pi_uci, "k": self.k,
            "estimator": self.estimator,
        }


def _study_log_effect(s: dict, measure: str):
    """Return (log_effect, var, est, lci, uci) for one study.

    Handles both real data shapes:
      * 'effect' shape: a pre-computed effect + 95% CI is given directly; we
        recover SE from the CI width on the log scale (generic inverse-variance).
      * 'count' shape: a 2x2 table; we compute the OR/RR from the counts.

    Continuity correction (count shape): add 0.5 to all cells ONLY if at least
    one cell is zero (per advanced-stats rule -- unconditional correction biases
    toward 1).
    """
    if s.get("shape") == "effect":
        eff, lci, uci = s["effect"], s["elci"], s["euci"]
        log_eff = math.log(eff)
        z = _norm_ppf(0.975)
        se = (math.log(uci) - math.log(lci)) / (2 * z)
        var = se * se
        return log_eff, var, eff, lci, uci

    tE, tN, cE, cN = s["tE"], s["tN"], s["cE"], s["cN"]
    a, b = tE, tN - tE          # treatment event / non-event
    c, d = cE, cN - cE          # control   event / non-event
    if min(a, b, c, d) == 0:
        a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5

    if measure == "OR":
        log_eff = math.log((a * d) / (b * c))
        var = 1 / a + 1 / b + 1 / c + 1 / d
    elif measure == "RR":
        r1, r2 = a / (a + b), c / (c + d)
        log_eff = math.log(r1 / r2)
        var = 1 / a - 1 / (a + b) + 1 / c - 1 / (c + d)
    else:
        raise ValueError(f"Unsupported measure {measure!r}")

    se = math.sqrt(var)
    z = _norm_ppf(0.975)
    est = math.exp(log_eff)
    return log_eff, var, est, math.exp(log_eff - z * se), math.exp(log_eff + z * se)


def meta_analyze(studies: list[dict], measure: str = "OR") -> tuple[list[StudyEffect], PooledEffect]:
    """Inverse-variance random-effects pooling (DerSimonian-Laird + REML).

    Returns per-study effects and the pooled effect, all computed directly from
    the re-sourced data -- the independent recomputation used to verify a
    paper's published numbers.
    """
    logs, vars_ = [], []
    per_study: list[StudyEffect] = []
    for s in studies:
        log_eff, var, est, lci, uci = _study_log_effect(s, measure)
        logs.append(log_eff)
        vars_.append(var)
        per_study.append(StudyEffect(s["name"], est, lci, uci, log_eff, math.sqrt(var)))

    k = len(studies)
    w_fixed = [1 / v for v in vars_]
    sw = sum(w_fixed)
    mu_fixed = sum(w * l for w, l in zip(w_fixed, logs)) / sw

    # Cochran's Q and DerSimonian-Laird tau^2 (cross-check estimator)
    Q = sum(w * (l - mu_fixed) ** 2 for w, l in zip(w_fixed, logs))
    Qdf = k - 1
    c_dl = sw - sum(w * w for w in w_fixed) / sw
    tau2_dl = max(0.0, (Q - Qdf) / c_dl) if c_dl > 0 else 0.0

    # REML tau^2 (primary; matches the dashboard engine) -- fixed-point iteration
    tau2 = _reml_tau2(logs, vars_, init=tau2_dl)

    # random-effects weights (REML)
    w_re = [1 / (v + tau2) for v in vars_]
    sw_re = sum(w_re)
    mu = sum(w * l for w, l in zip(w_re, logs)) / sw_re
    se = math.sqrt(1 / sw_re)

    z = _norm_ppf(0.975)
    I2 = max(0.0, (Q - Qdf) / Q) * 100 if Q > 0 else 0.0

    # t-based 95% prediction interval (Cochrane v6.5: t_{k-1}); undefined for k<2
    if k >= 2:
        from_t = _t_ppf(0.975, k - 1)
        pi_half = from_t * math.sqrt(tau2 + se * se)
        pi_lci, pi_uci = math.exp(mu - pi_half), math.exp(mu + pi_half)
    else:
        pi_lci = pi_uci = float("nan")

    for st, w in zip(per_study, w_re):
        st.weight_pct = 100 * w / sw_re

    # Q p-value via chi-square survival
    Qp = _chisq_sf(Q, Qdf)

    pooled = PooledEffect(
        measure=measure, est=math.exp(mu), lci=math.exp(mu - z * se),
        uci=math.exp(mu + z * se), log_est=mu, se=se,
        Q=Q, Qdf=Qdf, Qp=Qp, I2=I2, tau2=tau2, tau2_dl=tau2_dl,
        pi_lci=pi_lci, pi_uci=pi_uci, k=k, estimator="REML",
    )
    return per_study, pooled


def _reml_tau2(logs, vars_, init=0.0, max_iter=200, tol=1e-10):
    """REML estimate of the between-study variance via fixed-point iteration.

    tau2_{new} = [ sum w_i^2 ((y_i-mu)^2 - v_i) ] / sum w_i^2  +  1 / sum w_i
    with w_i = 1/(v_i + tau2), mu the weighted mean. Floored at 0.
    """
    tau2 = max(0.0, init)
    for _ in range(max_iter):
        w = [1.0 / (v + tau2) for v in vars_]
        sw = sum(w)
        mu = sum(wi * li for wi, li in zip(w, logs)) / sw
        sw2 = sum(wi * wi for wi in w)
        num = sum(wi * wi * ((li - mu) ** 2 - vi)
                  for wi, li, vi in zip(w, logs, vars_))
        new = max(0.0, num / sw2 + 1.0 / sw)
        if abs(new - tau2) < tol:
            tau2 = new
            break
        tau2 = new
    return tau2


def _t_ppf(p: float, df: int) -> float:
    """Student-t inverse CDF via Cornish-Fisher expansion off the normal quantile."""
    if df <= 0:
        return _norm_ppf(p)
    x = _norm_ppf(p)
    g1 = (x ** 3 + x) / 4
    g2 = (5 * x ** 5 + 16 * x ** 3 + 3 * x) / 96
    g3 = (3 * x ** 7 + 19 * x ** 5 + 17 * x ** 3 - 15 * x) / 384
    g4 = (79 * x ** 9 + 776 * x ** 7 + 1482 * x ** 5 - 1920 * x ** 3 - 945 * x) / 92160
    return x + g1 / df + g2 / df ** 2 + g3 / df ** 3 + g4 / df ** 4


def _chisq_sf(x: float, k: int) -> float:
    """Survival function of chi-square with k df (regularized upper gamma)."""
    if x <= 0:
        return 1.0
    return _gammaincc(k / 2.0, x / 2.0)


def _gammaincc(a: float, x: float) -> float:
    """Regularized upper incomplete gamma Q(a,x) via series / continued fraction."""
    if x < a + 1:
        ap, s, term = a, 1.0 / a, 1.0 / a
        for _ in range(500):
            ap += 1
            term *= x / ap
            s += term
            if abs(term) < abs(s) * 1e-12:
                break
        return 1.0 - s * math.exp(-x + a * math.log(x) - math.lgamma(a))
    tiny = 1e-300
    b = x + 1 - a
    c = 1 / tiny
    d = 1 / b
    h = d
    for i in range(1, 500):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-12:
            break
    return h * math.exp(-x + a * math.log(x) - math.lgamma(a))


# ---- thin wrapper used by the checker -------------------------------------

def pool(studies: list[dict], measure: str = "OR") -> PooledEffect:
    """Convenience: pool and return only the PooledEffect."""
    _, pooled = meta_analyze(studies, measure)
    return pooled
