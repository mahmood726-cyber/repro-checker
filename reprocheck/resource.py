"""Independent re-sourcing of cited trials from primary registries.

For each trial a meta-analysis claims to include, we go back to the primary
record -- PubMed/PMC (NCBI E-utilities) and ClinicalTrials.gov (API v2) -- and
confirm it exists, is the right *kind* of publication (a trial, not a methods
paper or review miscited as one), and pull whatever structured outcome data is
available. We never invent a record: a lookup that fails returns exists=None
with an error, which the checker reports as "cannot-verify", never as a pass.

Stdlib only (urllib). Responses are cached to JSON so re-runs are offline and
reproducible. Network calls use bounded retry/backoff and fail closed.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
CTGOV = "https://clinicaltrials.gov/api/v2"
DEFAULT_EMAIL = "mahmood726@gmail.com"

# PubMed publication types that indicate a primary trial vs. a synthesis/opinion.
TRIAL_PUBTYPES = {
    "Randomized Controlled Trial", "Controlled Clinical Trial", "Clinical Trial",
    "Clinical Trial, Phase I", "Clinical Trial, Phase II",
    "Clinical Trial, Phase III", "Clinical Trial, Phase IV",
    "Pragmatic Clinical Trial", "Equivalence Trial", "Multicenter Study",
}
NON_TRIAL_PUBTYPES = {
    "Meta-Analysis", "Systematic Review", "Review", "Editorial", "Comment",
    "Letter", "Practice Guideline", "Guideline", "Consensus Development Conference",
    "News", "Published Erratum", "Retraction of Publication",
}


class ResourceError(Exception):
    pass


def _get(url: str, email: str = DEFAULT_EMAIL, retries: int = 3,
         timeout: int = 40) -> bytes:
    """HTTP GET with bounded retry/backoff.

    A 404 is a definitive "not found" and is raised immediately (no retry) so
    callers can distinguish a fabricated identifier from a transient network
    failure. 429/5xx are retried; other failures fail closed via ResourceError.
    """
    req = urllib.request.Request(url, headers={
        "User-Agent": f"reprocheck/0.1 ({email})"})
    last = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise                      # definitive not-found
            if e.code == 429 or 500 <= e.code < 600:
                last = e                   # transient; back off and retry
                time.sleep(0.6 * (attempt + 1))
                continue
            raise ResourceError(f"HTTP {e.code} for {url}")
        except Exception as e:  # noqa: BLE001 - bounded retry, then fail closed
            last = e
            time.sleep(0.6 * (attempt + 1))
    raise ResourceError(f"GET failed after {retries} tries: {url}\n  {last}")


def _efetch_pubtypes(pmid: str, email: str = DEFAULT_EMAIL) -> list[str]:
    """Authoritative PublicationTypeList via efetch XML.

    esummary's `pubtype` field is unreliable (often just 'Journal Article' even
    for a meta-analysis), so we go to efetch for the real list -- this is what
    lets us catch a review/methods paper miscited as a primary trial.
    Returns [] on any failure (caller falls back to esummary pubtypes).
    """
    url = (f"{EUTILS}/efetch.fcgi?db=pubmed&retmode=xml"
           f"&id={urllib.parse.quote(pmid)}")
    try:
        xml = _get(url, email).decode("utf-8", "replace")
    except (ResourceError, urllib.error.HTTPError):
        return []
    return [m.strip() for m in re.findall(
        r"<PublicationType[^>]*>([^<]+)</PublicationType>", xml)]


class Resolver:
    """Caching resolver for PubMed and ClinicalTrials.gov records."""

    def __init__(self, cache_dir: str | None = None, email: str = DEFAULT_EMAIL,
                 offline: bool = False):
        self.email = email
        self.offline = offline
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self._mem: dict[str, dict] = {}
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ---- cache plumbing ---------------------------------------------------

    def _cache_path(self, key: str) -> Path | None:
        if not self.cache_dir:
            return None
        safe = key.replace(":", "_").replace("/", "_")
        return self.cache_dir / f"{safe}.json"

    def _cache_get(self, key: str):
        if key in self._mem:
            return self._mem[key]
        p = self._cache_path(key)
        if p and p.exists():
            val = json.loads(p.read_text(encoding="utf-8"))
            self._mem[key] = val
            return val
        return None

    def _cache_put(self, key: str, val: dict):
        self._mem[key] = val
        p = self._cache_path(key)
        if p:
            p.write_text(json.dumps(val, indent=2), encoding="utf-8")

    # ---- PubMed -----------------------------------------------------------

    def pubmed(self, pmid: str) -> dict:
        """Resolve a PMID via esummary. Returns a record with:
        exists(bool|None), title, authors, year, journal, doi, pubtypes,
        is_trial, is_synthesis, error.
        """
        pmid = str(pmid).strip()
        key = f"pubmed:{pmid}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        if self.offline:
            return {"id": pmid, "exists": None, "error": "offline; not cached"}
        url = (f"{EUTILS}/esummary.fcgi?db=pubmed&retmode=json"
               f"&id={urllib.parse.quote(pmid)}")
        try:
            data = json.loads(_get(url, self.email))
        except (ResourceError, json.JSONDecodeError) as e:
            return {"id": pmid, "exists": None, "error": str(e)}
        res = data.get("result", {})
        if pmid not in res or res.get(pmid, {}).get("error"):
            rec = {"id": pmid, "exists": False,
                   "error": res.get(pmid, {}).get("error", "PMID not found")}
            self._cache_put(key, rec)
            return rec
        a = res[pmid]
        doi = ""
        for aid in a.get("articleids", []):
            if aid.get("idtype") == "doi":
                doi = aid.get("value", "")
        # esummary pubtypes are incomplete; efetch gives the authoritative list.
        pubtypes = list(a.get("pubtype", []) or [])
        fetched = _efetch_pubtypes(pmid, self.email)
        for pt in fetched:
            if pt not in pubtypes:
                pubtypes.append(pt)
        rec = {
            "id": pmid, "exists": True,
            "title": (a.get("title", "") or "").rstrip("."),
            "authors": [au.get("name", "") for au in a.get("authors", [])],
            "year": (a.get("pubdate", "") or "").split(" ")[0],
            "journal": a.get("source", ""),
            "doi": doi,
            "pubtypes": pubtypes,
            "is_trial": any(pt in TRIAL_PUBTYPES for pt in pubtypes),
            "is_synthesis": any(pt in NON_TRIAL_PUBTYPES for pt in pubtypes),
            "error": None,
        }
        self._cache_put(key, rec)
        return rec

    def doi_to_pmid(self, doi: str) -> str | None:
        """Find a PMID for a DOI via esearch. None if not found / offline."""
        doi = str(doi).strip()
        key = f"doi:{doi}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached.get("pmid")
        if self.offline:
            return None
        url = (f"{EUTILS}/esearch.fcgi?db=pubmed&retmode=json"
               f"&term={urllib.parse.quote(doi)}%5BDOI%5D")
        try:
            data = json.loads(_get(url, self.email))
            ids = data.get("esearchresult", {}).get("idlist", [])
        except (ResourceError, json.JSONDecodeError):
            ids = []
        pmid = ids[0] if ids else None
        self._cache_put(key, {"doi": doi, "pmid": pmid})
        return pmid

    # ---- ClinicalTrials.gov ----------------------------------------------

    def ctgov(self, nct: str) -> dict:
        """Resolve an NCT id via CT.gov API v2. Returns exists/title/phase/
        enrollment/has_results/error."""
        nct = str(nct).strip().upper()
        key = f"ctgov:{nct}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        if self.offline:
            return {"id": nct, "exists": None, "error": "offline; not cached"}
        fields = "protocolSection.identificationModule," \
                 "protocolSection.designModule,protocolSection.statusModule," \
                 "hasResults"
        url = f"{CTGOV}/studies/{urllib.parse.quote(nct)}?fields={fields}"
        try:
            raw = _get(url, self.email)
            data = json.loads(raw)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                rec = {"id": nct, "exists": False,
                       "error": "NCT not found on ClinicalTrials.gov"}
                self._cache_put(key, rec)
                return rec
            return {"id": nct, "exists": None, "error": str(e)}
        except (ResourceError, json.JSONDecodeError) as e:
            return {"id": nct, "exists": None, "error": str(e)}
        if not data or "protocolSection" not in data:
            rec = {"id": nct, "exists": False, "error": "NCT not found"}
            self._cache_put(key, rec)
            return rec
        ps = data["protocolSection"]
        ident = ps.get("identificationModule", {})
        design = ps.get("designModule", {})
        rec = {
            "id": nct, "exists": True,
            "title": ident.get("briefTitle", ""),
            "phases": design.get("phases", []),
            "enrollment": (design.get("enrollmentInfo", {}) or {}).get("count"),
            "has_results": bool(data.get("hasResults")),
            "error": None,
        }
        self._cache_put(key, rec)
        return rec


def resolve_trial(ref: dict, resolver: Resolver) -> dict:
    """Independently re-source one cited trial.

    `ref` may carry any of: pmid, doi, nct, name. Returns a 'sourcing' dict the
    checker uses to flag miscitations and to confirm the trial is real and is a
    trial (not a synthesis paper miscited as one).
    """
    out = {"name": ref.get("name", ""), "queried": {}, "pubmed": None,
           "ctgov": None, "verdict": "cannot-verify", "notes": []}

    pmid = ref.get("pmid")
    doi = ref.get("doi")
    nct = ref.get("nct")

    if not pmid and doi:
        pmid = resolver.doi_to_pmid(doi)
        if pmid:
            out["notes"].append(f"DOI {doi} -> PMID {pmid}")
        else:
            out["notes"].append(f"DOI {doi} did not resolve to a PubMed record")

    if pmid:
        out["queried"]["pmid"] = pmid
        pm = resolver.pubmed(pmid)
        out["pubmed"] = pm
        if pm.get("exists") is True:
            if pm.get("is_synthesis") and not pm.get("is_trial"):
                out["verdict"] = "not-a-trial"
                out["notes"].append(
                    f"PMID {pmid} is {pm.get('pubtypes')}, not a primary trial")
            else:
                out["verdict"] = "real-trial"
        elif pm.get("exists") is False:
            out["verdict"] = "not-real"
            out["notes"].append(f"PMID {pmid} does not exist in PubMed")
        # exists is None -> network/offline -> stays cannot-verify

    if nct:
        out["queried"]["nct"] = nct
        ct = resolver.ctgov(nct)
        out["ctgov"] = ct
        if ct.get("exists") is False and out["verdict"] == "cannot-verify":
            out["verdict"] = "not-real"
            out["notes"].append(f"{nct} does not exist on ClinicalTrials.gov")
        elif ct.get("exists") is True and out["verdict"] == "cannot-verify":
            out["verdict"] = "real-trial"

    if not pmid and not nct and not doi:
        out["notes"].append("no resolvable identifier (pmid/doi/nct) on this study")

    return out
