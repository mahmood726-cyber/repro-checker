"""Flag detectors for a submitted meta-analysis.

Each detector returns zero or more Flag records. Flags are independent of the
numeric reproduction verdict (a paper can reproduce its pooled number and still
carry a placeholder artifact, or fail to reproduce with no structural flag).

Severity:
  high   -- likely invalidates a claim (fake/miscited trial, impossible counts)
  medium -- needs editor attention (k mismatch, effect outside its own CI)
  low    -- cosmetic / template hygiene (placeholder token, stated-N drift)
  info   -- contextual note
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, asdict

from .claims import Submission, Trial

PLACEHOLDER_PATTERNS = [
    (r"\bn participants\b", "literal 'n participants' (unfilled count token)"),
    (r"\bN participants\b", "literal 'N participants' (unfilled count token)"),
    (r"\{\{[^}]+\}\}", "mustache placeholder {{...}}"),
    (r"\bREPLACE_ME\b", "REPLACE_ME placeholder"),
    (r"__PLACEHOLDER__", "__PLACEHOLDER__ token"),
    (r"\bTODO\b", "TODO marker in body"),
    (r"\bLorem ipsum\b", "Lorem ipsum filler"),
    (r"\bAuthor(?:s)? et al\.?(?=\s|$)", "unfilled 'Author et al' citation"),
    (r"\bNone trials\b", "Python None leaked into text"),
    (r"\bNone participants\b", "Python None leaked into text"),
    (r"\baggregates\s+\w+\s+trials with n\b", "unfilled count template"),
    (r"/None\b", "URL ending in /None (None leak)"),
]


@dataclass
class Flag:
    id: str
    severity: str          # high | medium | low | info
    title: str
    detail: str
    subject: str = ""      # trial name / location, if applicable

    def as_dict(self) -> dict:
        return asdict(self)


def flag_placeholders(sub: Submission) -> list[Flag]:
    out = []
    blob = (sub.raw_text or "") + "\n" + sub.title + "\n" + \
        "\n".join(t.name for t in sub.trials)
    for pat, desc in PLACEHOLDER_PATTERNS:
        for m in re.finditer(pat, blob):
            ctx = blob[max(0, m.start() - 30):m.end() + 30].replace("\n", " ")
            out.append(Flag(
                id="placeholder-artifact", severity="low",
                title="Template/placeholder artifact", detail=desc,
                subject=f"...{ctx.strip()}..."))
            break  # one flag per pattern is enough to surface it
    return out


def flag_data_sanity(sub: Submission) -> list[Flag]:
    """Per-trial arithmetic / unit consistency on the supplied data."""
    out = []
    for t in sub.trials:
        sh = t.shape
        if sh == "count":
            for arm, (e, n) in {"treatment": (t.tE, t.tN),
                                "control": (t.cE, t.cN)}.items():
                if e is None or n is None:
                    continue
                if e < 0 or n < 0:
                    out.append(Flag("impossible-count", "high",
                                    "Negative count",
                                    f"{arm}: events={e}, n={n}", t.name))
                elif e > n:
                    out.append(Flag("impossible-count", "high",
                                    "Events exceed arm size",
                                    f"{arm}: events={e} > n={n} "
                                    f"(extraction or unit error)", t.name))
        elif sh == "effect":
            e, lo, hi = t.effect, t.elci, t.euci
            if e is not None and (e <= 0):
                out.append(Flag("impossible-effect", "high",
                                "Non-positive ratio effect",
                                f"effect={e} (ratios must be > 0)", t.name))
            if None not in (lo, hi) and lo > hi:
                out.append(Flag("ci-order", "medium", "CI bounds reversed",
                                f"lci={lo} > uci={hi}", t.name))
            if None not in (e, lo, hi) and not (lo <= e <= hi):
                out.append(Flag("effect-outside-ci", "medium",
                                "Point estimate lies outside its own 95% CI",
                                f"effect={e}, CI {lo}-{hi} "
                                f"(arithmetic/transcription error)", t.name))
        else:
            out.append(Flag("no-usable-data", "info",
                            "Trial has no usable per-arm or effect data",
                            "cannot recompute this study's contribution", t.name))
    return out


def flag_k_mismatch(sub: Submission) -> list[Flag]:
    """Claimed k vs trials actually provided with usable data."""
    out = []
    usable = [t for t in sub.trials if t.shape is not None]
    k_claim = sub.claimed.k
    if k_claim is not None and sub.trials:
        if k_claim != len(sub.trials):
            out.append(Flag(
                "k-mismatch", "medium",
                "Study-count (k) mismatch",
                f"paper claims k={k_claim} trials but the study table lists "
                f"{len(sub.trials)}", ""))
        if len(usable) < len(sub.trials):
            out.append(Flag(
                "k-poolable-mismatch", "medium",
                "Fewer poolable trials than listed",
                f"{len(sub.trials)} trials listed, only {len(usable)} carry "
                f"usable data to re-pool", ""))
    return out


def flag_sourcing(sourcing: list[dict]) -> list[Flag]:
    """Translate resolver verdicts into citation-integrity flags."""
    out = []
    for s in sourcing:
        v = s.get("verdict")
        name = s.get("name", "?")
        note = "; ".join(s.get("notes", []))
        if v == "not-real":
            out.append(Flag("citation-not-real", "high",
                            "Cited trial does not exist",
                            note or "identifier did not resolve", name))
        elif v == "not-a-trial":
            out.append(Flag("citation-not-a-trial", "high",
                            "Citation is not a primary trial",
                            note or "publication type is a review/methods paper",
                            name))
        elif v == "cannot-verify":
            out.append(Flag("citation-unverified", "info",
                            "Citation could not be independently re-sourced",
                            note or "no resolvable identifier / network", name))
    return out


def all_structural_flags(sub: Submission, sourcing: list[dict] | None = None) -> list[Flag]:
    flags = []
    flags += flag_placeholders(sub)
    flags += flag_data_sanity(sub)
    flags += flag_k_mismatch(sub)
    if sourcing:
        flags += flag_sourcing(sourcing)
    return flags
