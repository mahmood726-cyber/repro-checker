"""Parse a submitted meta-analysis into a normalized Submission.

A Submission carries (a) what the paper CLAIMS -- the pooled estimate, CI,
heterogeneity, and study count k -- and (b) the included trials with their
per-arm / effect data and citations, so we can independently re-source and
re-pool. Input may be:

  * a structured study table (dict / JSON)  -- the authoritative path
  * pasted manuscript text                  -- regex heuristics (count + effect)
  * a cloned RapidMeta dashboard directory  -- reuses extract.py patterns

Nothing here invents data: a field that is absent stays absent, and the checker
reports "cannot-verify" rather than guessing.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


class SubmissionError(ValueError):
    """Raised when a submission cannot be parsed into a valid Submission.

    Public entry points (`Submission.from_dict`, `from_json_file`) fail closed
    with this error on malformed input rather than propagating an opaque
    ``AttributeError``/``TypeError`` from deep inside the pipeline or, worse,
    silently accepting a semantically impossible study table. The message names
    the offending field so an editor or caller can fix the submission.
    """


def _as_number(value, field_name: str):
    """Coerce ``value`` to a float, or None if absent. Fails closed otherwise.

    Accepts int/float and numeric strings (a JSON study table exported from a
    spreadsheet often carries "1.42" rather than 1.42). Rejects booleans and
    non-numeric text so a stray label never becomes a silent 0/1.
    """
    if value is None or value == "":
        return None
    if isinstance(value, bool):  # bool is a subclass of int; reject explicitly
        raise SubmissionError(f"{field_name}: expected a number, got boolean {value!r}")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            raise SubmissionError(
                f"{field_name}: expected a number, got non-numeric {value!r}")
    raise SubmissionError(
        f"{field_name}: expected a number, got {type(value).__name__}")


def _as_count(value, field_name: str):
    """Coerce to a non-negative integer count, or None if absent. Fails closed.

    Event counts and arm sizes are cardinalities: a negative or fractional value
    is a data error, and the parser refuses it here rather than letting it flow
    into the recompute engine and produce a nonsense pooled estimate.
    """
    num = _as_number(value, field_name)
    if num is None:
        return None
    if num < 0:
        raise SubmissionError(f"{field_name}: count must be >= 0, got {num:g}")
    if num != int(num):
        raise SubmissionError(f"{field_name}: count must be a whole number, got {num:g}")
    return int(num)


@dataclass
class Trial:
    name: str
    pmid: str = ""
    doi: str = ""
    nct: str = ""
    year: int | None = None
    # count shape
    tE: int | None = None
    tN: int | None = None
    cE: int | None = None
    cN: int | None = None
    # effect shape
    effect: float | None = None
    elci: float | None = None
    euci: float | None = None

    @property
    def shape(self) -> str | None:
        if None not in (self.tE, self.tN, self.cE, self.cN):
            return "count"
        if None not in (self.effect, self.elci, self.euci):
            return "effect"
        return None

    def to_study(self) -> dict | None:
        """Convert to the dict shape recompute.meta_analyze expects."""
        sh = self.shape
        if sh == "count":
            return {"name": self.name, "shape": "count", "tE": self.tE,
                    "tN": self.tN, "cE": self.cE, "cN": self.cN}
        if sh == "effect":
            return {"name": self.name, "shape": "effect", "effect": self.effect,
                    "elci": self.elci, "euci": self.euci,
                    "tN": self.tN or 0, "cN": self.cN or 0}
        return None

    def ref(self) -> dict:
        return {"name": self.name, "pmid": self.pmid, "doi": self.doi,
                "nct": self.nct}


@dataclass
class Claimed:
    measure: str = ""
    est: float | None = None
    lci: float | None = None
    uci: float | None = None
    I2: float | None = None
    Q: float | None = None
    tau2: float | None = None
    pi_lci: float | None = None
    pi_uci: float | None = None
    k: int | None = None            # number of trials the paper claims to pool
    n_stated: int | None = None     # stated participant total
    method: str = ""                # e.g. "DerSimonian-Laird random effects"


@dataclass
class Submission:
    title: str = ""
    claimed: Claimed = field(default_factory=Claimed)
    trials: list[Trial] = field(default_factory=list)
    raw_text: str = ""              # manuscript body, for placeholder scanning
    source: str = ""                # where this came from

    @classmethod
    def from_dict(cls, d: dict) -> "Submission":
        """Build a validated Submission from a study-table dict.

        Fails closed with :class:`SubmissionError` (naming the field) on
        malformed input: a non-dict payload, a ``trials`` value that is not a
        list, a ``claimed`` value that is not a mapping, non-numeric effect/CI
        fields, or negative/fractional counts. Absent fields stay absent — the
        checker still reports "cannot-verify" rather than guessing.
        """
        if not isinstance(d, dict):
            raise SubmissionError(
                f"submission must be a JSON object, got {type(d).__name__}")

        c = d.get("claimed", {})
        if c is None:
            c = {}
        if not isinstance(c, dict):
            raise SubmissionError(
                f"'claimed' must be an object, got {type(c).__name__}")
        k = c.get("k")
        k = _as_count(k, "claimed.k") if k is not None else None
        n_stated = c.get("n_stated")
        n_stated = _as_count(n_stated, "claimed.n_stated") if n_stated is not None else None
        claimed = Claimed(
            measure=str(c.get("measure", "") or ""),
            est=_as_number(c.get("est"), "claimed.est"),
            lci=_as_number(c.get("lci"), "claimed.lci"),
            uci=_as_number(c.get("uci"), "claimed.uci"),
            I2=_as_number(c.get("I2"), "claimed.I2"),
            Q=_as_number(c.get("Q"), "claimed.Q"),
            tau2=_as_number(c.get("tau2"), "claimed.tau2"),
            pi_lci=_as_number(c.get("pi_lci"), "claimed.pi_lci"),
            pi_uci=_as_number(c.get("pi_uci"), "claimed.pi_uci"),
            k=k, n_stated=n_stated, method=str(c.get("method", "") or ""),
        )

        raw_trials = d.get("trials", [])
        if raw_trials is None:
            raw_trials = []
        if not isinstance(raw_trials, list):
            raise SubmissionError(
                f"'trials' must be a list, got {type(raw_trials).__name__}")
        trials = []
        for i, t in enumerate(raw_trials):
            if not isinstance(t, dict):
                raise SubmissionError(
                    f"trials[{i}] must be an object, got {type(t).__name__}")
            yr = t.get("year")
            year = _as_count(yr, f"trials[{i}].year") if yr is not None else None
            trials.append(Trial(
                name=str(t.get("name", "") or ""),
                pmid=str(t.get("pmid", "") or ""),
                doi=str(t.get("doi", "") or ""), nct=str(t.get("nct", "") or ""),
                year=year,
                tE=_as_count(t.get("tE"), f"trials[{i}].tE"),
                tN=_as_count(t.get("tN"), f"trials[{i}].tN"),
                cE=_as_count(t.get("cE"), f"trials[{i}].cE"),
                cN=_as_count(t.get("cN"), f"trials[{i}].cN"),
                effect=_as_number(t.get("effect"), f"trials[{i}].effect"),
                elci=_as_number(t.get("elci"), f"trials[{i}].elci"),
                euci=_as_number(t.get("euci"), f"trials[{i}].euci"),
            ))
        return cls(title=str(d.get("title", "") or ""), claimed=claimed,
                   trials=trials, raw_text=str(d.get("raw_text", "") or ""),
                   source=str(d.get("source", "dict") or "dict"))

    @classmethod
    def from_json_file(cls, path: str) -> "Submission":
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError as e:
            raise SubmissionError(f"cannot read submission file {path}: {e}")
        try:
            d = json.loads(text)
        except json.JSONDecodeError as e:
            raise SubmissionError(f"invalid JSON in {path}: {e}")
        sub = cls.from_dict(d)
        sub.source = sub.source or f"json:{path}"
        return sub


# --------------------------------------------------------------------------
# free-text manuscript parsing (heuristic; for the standalone paste path)
# --------------------------------------------------------------------------

_CI = r"(\d+(?:\.\d+)?)\s*(?:to|[-–,]|and)\s*(\d+(?:\.\d+)?)"

# Negation words that, if they appear just before a "<N> trials/participants"
# phrase, invert its meaning ("not included 5 trials" is NOT k=5). See
# lessons.md#negated-counts-silent-corruption.
_NEGATION = re.compile(r"\b(?:not|non|never|without|excluding|excluded|"
                       r"minus|besides|apart from)\b", re.I)


# A clause separator between a negation word and the count means the negation
# governs a different clause ("excluded 3 studies but included 12 trials").
_CLAUSE_BREAK = re.compile(r"[.;:]|\b(?:but|and|however|whereas|while)\b", re.I)


def _negated_before(text: str, start: int, window: int = 30) -> bool:
    """True if a governing negation word occurs in the `window` chars preceding
    `start` with no clause break between it and the count.

    Guards against the negated-count corruption ("not included 5 trials" is not
    k=5) without swallowing legitimate counts in compound sentences where the
    negation belongs to an earlier clause.
    """
    lead = text[max(0, start - window):start]
    neg = None
    for neg in _NEGATION.finditer(lead):
        pass  # take the last (closest) negation in the window
    if neg is None:
        return False
    return _CLAUSE_BREAK.search(lead[neg.end():]) is None


def _first_unnegated(pattern: str, text: str, flags=0):
    """First regex match whose lead-in is not negated, else None."""
    for m in re.finditer(pattern, text, flags):
        if not _negated_before(text, m.start()):
            return m
    return None


def parse_claimed_text(text: str) -> Claimed:
    """Best-effort scrape of the claimed pooled result from manuscript prose."""
    c = Claimed()
    m = re.search(
        r"(?:pooled\s+)?(OR|RR|HR|SMD|MD|odds ratio|risk ratio|rate ratio|"
        r"hazard ratio)\D{0,20}?(\d+\.\d+)\D{0,15}?95%\s*CI[^0-9]{0,6}" + _CI,
        text, re.I)
    if m:
        meas = m.group(1).upper()
        c.measure = {"ODDS RATIO": "OR", "RISK RATIO": "RR", "RATE RATIO": "RR",
                     "HAZARD RATIO": "HR"}.get(meas, meas)
        c.est, c.lci, c.uci = float(m.group(2)), float(m.group(3)), float(m.group(4))
    m = re.search(r"I[²2]\s*=?\s*(\d+(?:\.\d+)?)\s*%", text)
    if m:
        c.I2 = float(m.group(1))
    m = re.search(r"\bQ\s*=\s*(\d+(?:\.\d+)?)", text)
    if m:
        c.Q = float(m.group(1))
    # k: "we included N trials/studies/RCTs" -- skip negated lead-ins so
    # "not included 5 trials" does not silently become k=5.
    m = _first_unnegated(
        r"\b(?:included|pooled|comprising|across|identified)\s+"
        r"(\d{1,3})\s+(?:trials|studies|RCTs|randomi[sz]ed)", text, re.I)
    if m:
        c.k = int(m.group(1))
    m = _first_unnegated(
        r"(\d[\d,]{2,})\s*(?:analysed\s+)?participants", text, re.I)
    if m:
        c.n_stated = int(m.group(1).replace(",", ""))
    if re.search(r"random[- ]?effects", text, re.I):
        c.method = "random-effects"
    return c


def from_text(text: str, title: str = "") -> Submission:
    """Build a Submission from pasted manuscript text. Trials are parsed only if
    the text carries a machine-readable study table block; otherwise trials is
    empty and the checker can still run structural/claim checks."""
    return Submission(title=title, claimed=parse_claimed_text(text),
                      trials=[], raw_text=text, source="text")


def count_cited_trials(text: str) -> int:
    """Count distinct trial citations (PMIDs or NCT ids) referenced in prose --
    used for the k-mismatch flag when a structured table is not provided."""
    ids = set(re.findall(r"\bNCT\d{8}\b", text))
    ids |= set("PMID:" + p for p in re.findall(r"PMID:?\s*(\d{6,9})", text))
    return len(ids)
