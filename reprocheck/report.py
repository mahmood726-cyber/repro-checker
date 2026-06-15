"""Assemble the reproducibility report — the engine's main entrypoint.

check(submission, resolver) runs the whole pipeline:
  1. structural flags (placeholders, impossible counts, k mismatch)
  2. independently re-source each cited trial (PubMed/PMC + CT.gov)
  3. recompute the pooled effect + CI + heterogeneity from the trial data
  4. compare recomputed vs claimed -> per-claim verdicts
  5. fold sourcing verdicts into citation-integrity flags
  6. derive an overall verdict

Truth-first: a quantity is only "reproduces" if it actually recomputed and
agreed; missing sourceable data is "cannot-verify"; nothing is fabricated.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from .claims import Submission
from .recompute import meta_analyze, PooledEffect
from .compare import compare, Tolerances, ClaimVerdict
from .flags import all_structural_flags, flag_sourcing, Flag
from .resource import Resolver, resolve_trial


@dataclass
class ReproReport:
    title: str
    source: str
    overall: str
    overall_detail: str
    claims: list[ClaimVerdict] = field(default_factory=list)
    flags: list[Flag] = field(default_factory=list)
    sourcing: list[dict] = field(default_factory=list)
    recomputed: dict | None = None
    measure: str = ""
    generated: str = ""

    def to_dict(self) -> dict:
        return {
            "title": self.title, "source": self.source,
            "overall": self.overall, "overall_detail": self.overall_detail,
            "measure": self.measure, "generated": self.generated,
            "recomputed": self.recomputed,
            "claims": [c.as_dict() for c in self.claims],
            "flags": [f.as_dict() for f in self.flags],
            "sourcing": self.sourcing,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    # ---- renders ----------------------------------------------------------

    def to_markdown(self) -> str:
        L = []
        L.append(f"# Reproducibility report — {self.title or '(untitled)'}")
        L.append("")
        L.append(f"**Overall verdict: {self.overall}**  ")
        L.append(self.overall_detail)
        L.append("")
        L.append(f"_Source: {self.source} · generated {self.generated}_")
        L.append("")
        L.append("## Per-claim verdicts")
        L.append("")
        L.append("| Quantity | Claimed | Recomputed | Verdict | Tolerance | Note |")
        L.append("|---|---|---|---|---|---|")
        sym = {"reproduces": "✓ reproduces", "diverges": "✗ DIVERGES",
               "cannot-verify": "– cannot-verify"}
        for c in self.claims:
            L.append(f"| {c.quantity} | {_fmt(c.claimed)} | {_fmt(c.recomputed)} "
                     f"| {sym.get(c.verdict, c.verdict)} | {c.tolerance} "
                     f"| {c.reason} |")
        L.append("")
        if self.flags:
            L.append("## Flags")
            L.append("")
            order = {"high": 0, "medium": 1, "low": 2, "info": 3}
            for f in sorted(self.flags, key=lambda x: order.get(x.severity, 9)):
                subj = f" — _{f.subject}_" if f.subject else ""
                L.append(f"- **[{f.severity.upper()}] {f.title}**: {f.detail}{subj}")
            L.append("")
        else:
            L.append("## Flags\n\nNone.\n")
        L.append("## Re-sourced citations")
        L.append("")
        if self.sourcing:
            L.append("| Trial | Verdict | Identifiers | Notes |")
            L.append("|---|---|---|---|")
            for s in self.sourcing:
                ids = ", ".join(f"{k}={v}" for k, v in s.get("queried", {}).items())
                L.append(f"| {s.get('name','?')} | {s.get('verdict')} | {ids} "
                         f"| {'; '.join(s.get('notes', []))} |")
        else:
            L.append("_No independent re-sourcing was performed (offline or no "
                     "identifiers)._")
        L.append("")
        return "\n".join(L)

    def to_html(self) -> str:
        rows = ""
        sym = {"reproduces": "reproduces", "diverges": "DIVERGES",
               "cannot-verify": "cannot-verify"}
        for c in self.claims:
            rows += (f"<tr class='{c.verdict}'><td>{_esc(c.quantity)}</td>"
                     f"<td>{_fmt(c.claimed)}</td><td>{_fmt(c.recomputed)}</td>"
                     f"<td>{sym.get(c.verdict)}</td><td>{_esc(c.reason)}</td></tr>")
        flagrows = "".join(
            f"<li class='{f.severity}'><b>[{f.severity.upper()}] {_esc(f.title)}"
            f"</b>: {_esc(f.detail)} {('— ' + _esc(f.subject)) if f.subject else ''}"
            f"</li>" for f in self.flags) or "<li>None.</li>"
        return f"""<!doctype html><meta charset=utf-8>
<title>Reproducibility report — {_esc(self.title)}</title>
<style>body{{font:15px/1.5 system-ui,sans-serif;max-width:900px;margin:2rem auto;
padding:0 1rem;color:#0f172a}}h1{{font-size:1.4rem}}table{{border-collapse:collapse;
width:100%}}td,th{{border:1px solid #cbd5e1;padding:.4rem .6rem;text-align:left}}
.diverges{{background:#fee2e2}}.reproduces{{background:#dcfce7}}
.cannot-verify{{background:#fef9c3}}.high{{color:#b91c1c}}.medium{{color:#b45309}}
.verdict{{font-weight:700;font-size:1.1rem}}</style>
<h1>Reproducibility report — {_esc(self.title)}</h1>
<p class=verdict>Overall: {_esc(self.overall)}</p>
<p>{_esc(self.overall_detail)}</p>
<p><small>Source: {_esc(self.source)} · generated {_esc(self.generated)}</small></p>
<h2>Per-claim verdicts</h2>
<table><tr><th>Quantity</th><th>Claimed</th><th>Recomputed</th><th>Verdict</th>
<th>Note</th></tr>{rows}</table>
<h2>Flags</h2><ul>{flagrows}</ul>"""


def _fmt(v):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.4g}"
    return str(v)


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# --------------------------------------------------------------------------
# the pipeline
# --------------------------------------------------------------------------

def check(sub: Submission, resolver: Resolver | None = None,
          tol: Tolerances | None = None, recompute: bool = True,
          generated: str = "") -> ReproReport:
    measure = (sub.claimed.measure or "").upper() or "OR"

    # 1. recompute pooled from supplied trial data
    pooled: PooledEffect | None = None
    recompute_reason = ""
    studies = [t.to_study() for t in sub.trials]
    studies = [s for s in studies if s is not None]
    if recompute and len(studies) >= 1:
        try:
            _, pooled = meta_analyze(studies, measure if measure in
                                     ("OR", "RR") else "OR")
        except Exception as e:  # noqa: BLE001
            recompute_reason = f"recompute failed: {e}"
    elif not studies:
        recompute_reason = "no poolable trial data supplied"

    # 2. independently re-source each cited trial
    sourcing = []
    if resolver is not None:
        for t in sub.trials:
            sourcing.append(resolve_trial(t.ref(), resolver))

    # 3. compare recomputed vs claimed
    claims = compare(sub.claimed, pooled, tol, recompute_reason)

    # 4. flags
    flags = all_structural_flags(sub, sourcing if sourcing else None)

    # 5. overall verdict
    overall, detail = _overall(claims, flags, pooled, recompute_reason)

    return ReproReport(
        title=sub.title, source=sub.source, overall=overall,
        overall_detail=detail, claims=claims, flags=flags, sourcing=sourcing,
        recomputed=pooled.as_dict() if pooled else None, measure=measure,
        generated=generated,
    )


def _overall(claims, flags, pooled, recompute_reason):
    high = [f for f in flags if f.severity == "high"]
    est_claim = next((c for c in claims if c.quantity.startswith("pooled")), None)
    diverged = [c for c in claims if c.verdict == "diverges"]
    unverifiable = [c for c in claims if c.verdict == "cannot-verify"]

    if high:
        return ("FAIL — integrity issue",
                f"{len(high)} high-severity flag(s) (e.g. {high[0].title}: "
                f"{high[0].detail}). The pooled number may be unsafe regardless "
                f"of arithmetic.")
    if est_claim and est_claim.verdict == "diverges":
        return ("DIVERGES — does not reproduce",
                f"The pooled estimate recomputes to {_fmt(est_claim.recomputed)} "
                f"but the paper claims {_fmt(est_claim.claimed)}. "
                f"{len(diverged)} claimed quantity(ies) diverge.")
    if est_claim and est_claim.verdict == "cannot-verify":
        return ("INCONCLUSIVE — cannot verify",
                f"The pooled estimate could not be independently recomputed "
                f"({recompute_reason or est_claim.reason}). Honest non-result; "
                f"not a pass.")
    if diverged:
        return ("PARTIAL — pooled reproduces, secondary divergence",
                f"The pooled estimate reproduces, but {len(diverged)} secondary "
                f"quantity(ies) diverge (e.g. {diverged[0].quantity}).")
    if unverifiable and not pooled:
        return ("INCONCLUSIVE — cannot verify", "Insufficient sourceable data.")
    return ("REPRODUCES",
            "Every claimed quantity that could be recomputed agreed within "
            "tolerance with the independently recomputed values.")
