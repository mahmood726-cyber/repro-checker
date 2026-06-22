# Methods Proof & Coverage Dossier

> **RESOLUTION (2026-06-22):** DEFECT-1 (`_t_ppf`) has been **FIXED** in this change.
> `_t_ppf` (and the JS `tPpf` in `docs/engine.js`) were replaced with an exact
> stdlib inverse-t: closed forms for df=1 (Cauchy) and df=2, and bisection on the
> t-CDF via a regularized incomplete beta (`_betai`/`_betacf`, Numerical Recipes)
> for df>=3. Now matches `scipy.stats.t.ppf` to ~1.5e-11 across df in [1,200]
> (df=1: 12.7062047362, was 11.30). Locked by `tests/test_proof_baselines.py::
> test_t_ppf_baseline`; Python/JS parity reverified (`node tests/verify_js_engine.cjs`).
> The sections below are the original proof record that identified the defect.

 — `reprocheck/recompute.py`

**Target:** `repro-checker\reprocheck\recompute.py` (stdlib-only statistics engine)
**Oracle:** SciPy (`scipy.stats`, `scipy.special`), computed in an independent process that never imports the repo functions.
**Design constraint:** the engine uses only Python's `math` + `dataclasses`; no NumPy/SciPy at runtime. SciPy is used purely as an external truth oracle for this audit.

---

## 1. Executive summary

Eight functions were verified against an independent SciPy oracle.

- **7 of 8 proven correct** (`verdict ∈ {correct}`) to within their stated tolerances.
- **1 confirmed defect** at the function level (`_t_ppf`, `confirmedReal=true`), which propagates into two composite verdicts (`meta_analyze` → `suspect`; `pool` → `correct`-with-noted-limitation). There is exactly **one underlying root cause** across all flags: the Student-t quantile helper.
- **Core pooling math is correct.** Pooled effect, log-scale mean, SE, confidence interval, Q, I², τ²(DL), τ²(REML), and the Q p-value all reproduce the oracle to ≤ ~1.5e-9.
- **The sole defect** is `_t_ppf`, a Cornish-Fisher asymptotic series, which is materially inaccurate at small df. It feeds **only the prediction interval**, not the named primary estimand.

**Tolerance bands used (and met except where noted):**

| Class | Tolerance | Rationale |
|---|---|---|
| Closed-form helpers (`_norm_cdf`, log-effect, var, pooled mean/SE/CI/Q/I²/τ²) | 1e-9 abs | exact identities, no rational approximation |
| Rational approximation (`_norm_ppf`, Acklam) | ~1e-7 abs | Acklam's documented ~1.15e-9 relative accuracy, no Halley refinement |
| Hand-rolled special fns (`_gammaincc`, `_chisq_sf`) | 1e-9 rel | Numerical-Recipes series/continued-fraction floor |
| Student-t quantile (`_t_ppf`) | 1e-7..1e-9 target | **Failed for df ≤ 30; catastrophic for df ≤ 5** |

---

## 2. Per-function coverage table

| Function (location) | SciPy oracle | maxAbsDiff | Verdict | Gotcha checks (key) |
|---|---|---|---|---|
| `_norm_cdf` (51–52) | `norm.cdf` / `special.ndtr` | **1.11e-16** over [−40,40] | **correct** | Exact `Φ(x)=0.5(1+erf(x/√2))`; deep-tail underflow to 0.0 is the IEEE-754 double floor (abs err ≤ ~7.6e-24), not logic. `1/√2` exact. Both tails + p≈0/1 checked. |
| `_norm_ppf` (28–36 consts) | `norm.ppf` | **5.01e-9** (p=1e-6); 1.58e-9 at p=0.975 | **correct** | Acklam rational, canonical coeffs. Symmetry `ppf(p)=−ppf(1−p)` exact; `ppf(0.5)=0`. Branch switch at plow=0.02425 continuous. **No clamp** of p→(1e-10,1−1e-10): raises `ValueError` at p∈{0,1} vs SciPy ±inf — outside production domain, robustness note only. |
| `_t_ppf` (221–230) | `t.ppf` | **202.647** (df=1, p=0.999); 1.406 at df=1,p=0.975 | **BUG (major)** | Cornish-Fisher series in 1/df — asymptotic only. df=1 Cauchy 11% low at p=0.975; df=2 0.75%; meets ~1e-9 only at df≥200. Df convention (t_{k−1}) is correct; defect is purely quantile accuracy at small df. |
| `_chisq_sf` (233–237) → `_gammaincc` | `chi2.sf` = `gammaincc(k/2,x/2)` | **6.48e-14** (rel 1.30e-12) at (3.84, df=1) | **correct** | Series/CF switch at x<a+1 verified both sides. Half-integer a (df=1,3,5,7) correct via `lgamma`. Deep tails (sf(100,1)=1.5e-23) accurate. Q-heterogeneity df=4..7 range covered. |
| `_gammaincc` (240–270) | `special.gammaincc` | **1.58e-13** (rel 9.18e-13) at a=1.5,x=2.5 | **correct** | NR `gammq`: series (x<a+1) + modified-Lentz CF (x≥a+1); boundary continuous. Half-integer a, deep tails to 1.5e-23, near-zero x all exact. |
| `_study_log_effect` (112–130) | independent reimpl | log_eff/est **0.0** exact; var 3.20e-11; CI 3.70e-9 | **correct** | **Conditional** +0.5 only when `min cell==0` (no unconditional OR→1 bias). logOR var=1/a+1/b+1/c+1/d; logRR var=1/a−1/(a+b)+1/c−1/(c+d). Log-scale return + exp back-transform. MD → fail-closed `ValueError`. |
| `meta_analyze` (138; calls all helpers) | scipy pooling + special fns | pooled qty ~4.4e-10; **_t_ppf outlier** df=1 PI 1.41 | **suspect (minor)** | Pooling correct to ~1e-9. PI defect at k=2: engine [0.148,2.925] vs correct [0.123,3.522]. t_{k−1} convention correct (not t_{k−2}/z). Conditional continuity, log-scale, DL/REML τ² all PASS. |
| `pool` (275) → `meta_analyze` | scipy pooling + special fns | OR 2.21e-10; RR 1.48e-9; **PI 4.23e-5 at k=6** | **correct (minor PI note)** | Core ≤1.5e-9. REML matches independent fixed-point to 1.9e-11. PI uses t_{k−1}; undefined k<2 → nan confirmed. Only weak link is `_t_ppf` feeding PI. |

---

## 3. Confirmed defects (`confirmedReal=true`)

Exactly one underlying defect was confirmed real. It is reported once at the function level and surfaces in two composite verdicts.

### DEFECT-1 — `_t_ppf` Student-t quantile is an asymptotic series, inaccurate at small df

**Severity:** major (at `_t_ppf` itself) / minor (at the `meta_analyze`/`pool` use-site, because it feeds only the prediction interval, not the primary estimand).
**Location:** `recompute.py:221–230`.

**Nature.** `_t_ppf` uses a 4-term Cornish-Fisher (Fisher-Cornish) expansion off the normal quantile,
`t ≈ x + g₁/df + g₂/df² + g₃/df³ + g₄/df⁴` with `x = _norm_ppf(p)`.
This is only asymptotically valid as df→∞; it is **not** the exact Student-t quantile.

**Measured error at the canonical α/2 = 0.975:**

| df | engine vs exact | rel error |
|---|---|---|
| 1 (Cauchy) | 11.300 vs 12.706 | **11.07%** |
| 2 | 4.271 vs 4.303 | 0.75% |
| 3 | 3.179 vs 3.182 | 0.12% |
| 5 | — | 1.1e-4 |
| 10 | — | 7.95e-6 |
| 30 | — | 2.93e-8 |
| 200 | — | 1.60e-9 (meets target) |

Far-tail is worse: df=1, p=0.999 gives 115.7 vs 318.3 (|diff| = 202.6).

**Why load-bearing.** `meta_analyze` (recompute.py:178) computes the prediction interval as
`exp(μ ± t_{k−1}·√(τ²+SE²))`. For small-k meta-analyses — exactly where prediction intervals matter and where a reproducibility checker operates — the t-critical is too small, so `pi_lci`/`pi_uci` are biased **too narrow**:

- k=2 (df=1): PI width ~11% too narrow; engine `[0.148, 2.925]` vs correct `[0.123, 3.522]` (upper bound ~17% too low).
- k=3 (df=2): ~0.75% off.
- k=4 (df=3): ~0.12% off.
- k≥6 (df≥5): < 3e-4, negligible; k≥8: negligible.

**Not a false flag.** The df convention (t_{k−1}, Cochrane v6.5) is correct and the df→∞→normal limit is correct (df=200 matches oracle to 1.6e-9). The docstring itself lists "verify df=1 (Cauchy), small df tails" as intended behavior — precisely the regime the function gets wrong. The pooled effect, CI, Q, Qp, I², and τ² are all unaffected.

**Confirmed fix (verbatim recommended).** Replace the unconditional Cornish-Fisher expansion in `_t_ppf` (recompute.py:221–230) with exact handling:

- **df=1:** closed form `math.tan(math.pi*(p-0.5))` (exact Cauchy).
- **df=2:** `a = 2*p - 1; a*math.sqrt(2/(1-a*a))` (exact closed form).
- **df≥3:** bisection/Newton inversion of the Student-t CDF via the regularized incomplete beta `I_x(df/2, 1/2)`, implemented as a Lentz continued fraction (analogous to the existing `_gammaincc` CF). The existing Cornish-Fisher may be retained only as the Newton starting guess.
- Keep the existing `df ≤ 0 → _norm_ppf` fallback and the t_{k−1} convention unchanged.

**Conservative alternative.** Special-case df∈{1,2} as above, keep the 4-term Cornish-Fisher only for df≥4 (|diff|<8e-6); optionally special-case or document df=3 (0.12%). Or restrict the prediction interval to k≥4 and document df<3 as undefined. Core pooling stays untouched in every variant.

**Regression anchors to assert (all verified correct against `scipy.stats.t.ppf`):**

| df | `_t_ppf(0.975, df)` target | tol |
|---|---|---|
| 1 | 12.7062047362 | 1e-6 |
| 2 | 4.3026527297 | 1e-6 |
| 5 | 2.5705818356 | 1e-6 |

---

## 4. Honest boundaries

**Special-function accuracy is approximation-floored, not machine-precision.** Three families have intrinsic accuracy floors above 2⁻⁵³ and are correctly *not* held to machine precision:

- `_norm_ppf` (Acklam rational): ~1e-9 relative; no Halley/Newton refinement, so absolute error grows mildly in deep tails (5.0e-9 at p=1e-6). Held to ~1e-7; achieved ~1.6e-9 in production range.
- `_gammaincc` / `_chisq_sf` (NR series + Lentz CF): floor ~1e-12 relative from the 1e-12 CF termination and tiny-guard. Held to 1e-9 rel; achieved ~1e-13..1e-14.
- `_norm_cdf`: this one *is* effectively machine-precision (1.11e-16) because `math.erf` is itself ~1e-16 accurate and the identity is exact. Its only deviation is the deep-left-tail underflow to 0.0 (abs err ≤ ~7.6e-24), an IEEE-754 double floor, not a logic error. Max *relative* diff of 1.0 occurs only at x=−10 where both values are ~0 and the function is never evaluated in CI/p-value use.

**Property-verified vs point-verified.** The following were verified as *properties*, not just sampled points:

- `_norm_ppf`: symmetry `ppf(p) = −ppf(1−p)` (exact), `ppf(0.5)=0` (exact), branch continuity at plow/phigh.
- `_study_log_effect`: conditionality of the +0.5 continuity correction (added iff `min cell==0`; non-zero studies untouched → no unconditional OR→1 bias).
- `_gammaincc`/`_chisq_sf`: series/CF branch continuity across x=a+1, and half-integer-a correctness (df odd → a∈{0.5,1.5,2.5,3.5}).
- `pool`: PI undefined for k<2 → nan (confirmed), t_{k−1} (not t_{k−2}, not z) convention.

The remaining quantities (deep tails, specific df, specific cell tables) are **point-verified** over a designed grid, not exhaustively.

**Known un-clamped edge (not a numerical defect).** `_norm_ppf` does **not** clamp p to (1e-10, 1−1e-10): at p∈{0,1} or out-of-range it raises `ValueError` (math domain error from `math.log`) where SciPy returns ±inf/nan. This is outside the verified (1e-6..1−1e-6) domain and the engine only calls it with fixed interior probabilities (0.975 for CIs, and via `_t_ppf`), so it is never exercised. Robustness note only.

**The stdlib-no-SciPy design tradeoff.** Shipping with `math`-only buys zero heavy dependencies and a fully portable checker, at the cost of (a) hand-rolled special functions whose accuracy floor is the approximation method rather than the hardware, and (b) the `_t_ppf` defect, which a SciPy-backed engine would not have. The audit confirms this tradeoff is *acceptable for every function except `_t_ppf`*: the closed-form identities (`_norm_cdf`) and the NR special functions (`_gammaincc`) are within ~1e-12..1e-16, indistinguishable from a SciPy backend in practice. Only the Student-t quantile pays a real accuracy penalty for the stdlib choice, and only at small df.

**Oracle independence (anti-circularity).** For every function, the SciPy oracle was computed in a separate process that never imported `reprocheck`. This rules out the in-sample circularity failure mode where an engine is "validated" against itself.

---

## 5. What was locked into CI

The following regression coverage is the contract this dossier recommends be enforced (anchors all independently verified against SciPy):

1. **`_t_ppf` exact anchors** (guards DEFECT-1's fix and prevents regression to Cornish-Fisher):
   `_t_ppf(0.975, 1)=12.7062047362`, `(0.975, 2)=4.3026527297`, `(0.975, 5)=2.5705818356`, each to 1e-6.
2. **`_norm_cdf`**: agreement with `norm.cdf` to 1e-9 over [−8, 8]; deep-tail underflow-to-0.0 accepted as correct-by-construction.
3. **`_norm_ppf`**: agreement to 1e-7 over [1e-6, 1−1e-6]; symmetry and `ppf(0.5)=0` as exact-property assertions.
4. **`_gammaincc` / `_chisq_sf`**: agreement with `scipy.special.gammaincc` / `chi2.sf` to 1e-9 relative, including the series/CF boundary (x≈a+1), half-integer a (odd df), and deep right tail (sf≈1e-20).
5. **`_study_log_effect`**: conditional-continuity property (correction applied iff a cell is zero), logOR var = 1/a+1/b+1/c+1/d, logRR var = 1/a−1/(a+b)+1/c−1/(c+d), MD → `ValueError`.
6. **`meta_analyze` / `pool`**: pooled est/CI/Q/Qp/I²/τ²(DL)/τ²(REML) to 1e-9 vs the independent oracle; t_{k−1} PI convention; PI undefined for k<2 → nan. The PI itself is held to the df-dependent accuracy of `_t_ppf` until DEFECT-1 is fixed, at which point it should be tightened to 1e-6.

**Status:** 7/8 functions ship green. The single confirmed defect (`_t_ppf`, DEFECT-1) is the gating item; until fixed, prediction intervals for k∈{2,3} are biased too narrow (~11% at k=2, ~0.75% at k=3) while the primary pooled estimand and its CI remain correct to ~1e-9.

Source file confirmed present at `repro-checker\reprocheck\recompute.py`.