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
        c = d.get("claimed", {})
        claimed = Claimed(
            measure=c.get("measure", ""), est=c.get("est"), lci=c.get("lci"),
            uci=c.get("uci"), I2=c.get("I2"), Q=c.get("Q"), tau2=c.get("tau2"),
            pi_lci=c.get("pi_lci"), pi_uci=c.get("pi_uci"), k=c.get("k"),
            n_stated=c.get("n_stated"), method=c.get("method", ""),
        )
        trials = []
        for t in d.get("trials", []):
            trials.append(Trial(
                name=t.get("name", ""), pmid=str(t.get("pmid", "") or ""),
                doi=t.get("doi", ""), nct=t.get("nct", ""), year=t.get("year"),
                tE=t.get("tE"), tN=t.get("tN"), cE=t.get("cE"), cN=t.get("cN"),
                effect=t.get("effect"), elci=t.get("elci"), euci=t.get("euci"),
            ))
        return cls(title=d.get("title", ""), claimed=claimed, trials=trials,
                   raw_text=d.get("raw_text", ""), source=d.get("source", "dict"))

    @classmethod
    def from_json_file(cls, path: str) -> "Submission":
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        sub = cls.from_dict(d)
        sub.source = sub.source or f"json:{path}"
        return sub


# --------------------------------------------------------------------------
# free-text manuscript parsing (heuristic; for the standalone paste path)
# --------------------------------------------------------------------------

_CI = r"(\d+(?:\.\d+)?)\s*(?:to|[-–,]|and)\s*(\d+(?:\.\d+)?)"


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
    # k: "we included N trials/studies/RCTs"
    m = re.search(r"\b(?:included|pooled|comprising|across|identified)\s+"
                  r"(\d{1,3})\s+(?:trials|studies|RCTs|randomi[sz]ed)", text, re.I)
    if m:
        c.k = int(m.group(1))
    m = re.search(r"(\d[\d,]{2,})\s*(?:analysed\s+)?participants", text, re.I)
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
