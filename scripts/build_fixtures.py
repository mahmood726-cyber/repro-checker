"""Generate the validation fixtures as self-contained JSON.

Run:  python scripts/build_fixtures.py   (writes to ../fixtures)

Provenance:
  * 105 (JAK-RA) and 106 (asthma biologics) trial data are snapshotted from the
    real RapidMeta dashboards (synthesis-paper-spec/dashboards/*), whose pooled
    numbers were independently verified by metapaper/stats.py. These MUST
    reproduce.
  * corrupted-105 / corrupted-106 apply a single realistic transcription error
    to a real fixture so the pooled number no longer reproduces. These MUST
    diverge (and surface the per-trial error).
  * glp1-elixa uses the REAL published 3-point-MACE hazard ratios of the eight
    GLP-1 receptor-agonist cardiovascular-outcome trials (ELIXA is the neutral
    anchor). The CLAIMED pooled HR of 0.62 is a PLANTED over-statement that
    reproduces the documented "claimed-too-strong" extraction failure (the
    INCRETIN-set QA case): the correct random-effects pool is ~0.87. MUST diverge.
  * paper30-structural is a SYNTHETIC structural-defect case (the prior session's
    specific workbook #30 identity was not recoverable after the restart). It
    exercises k-mismatch, a fabricated NCT, a methods/review paper miscited as a
    trial, and a placeholder artifact. MUST flag (integrity FAIL).
  * INCRETIN: the specific "0.62-vs-0.41" QA fixture is NOT present on disk and
    is reported as not-found (see VALIDATION.md). No fixture is fabricated for it.
"""
import copy
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "fixtures"
OUT.mkdir(exist_ok=True)


def write(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2), encoding="utf-8")
    print(f"wrote fixtures/{name}")


# --- 105: JAK inhibitors for ACR20 in RA (count shape, OR; reproduces) -------
paper105 = {
    "title": "JAK inhibitors for ACR20 response in rheumatoid arthritis",
    "source": "fixture:105 (snapshot of RapidMeta JAK-RA dashboard)",
    "claimed": {"measure": "OR", "est": 3.40, "lci": 2.89, "uci": 3.99,
                "I2": 0.0, "Q": 0.74, "pi_lci": 2.61, "pi_uci": 4.42,
                "k": 4, "n_stated": 2228,
                "method": "inverse-variance random-effects (DL/REML)"},
    "trials": [
        {"name": "ORAL Solo", "pmid": "22873530", "nct": "NCT00814307",
         "year": 2012, "tE": 144, "tN": 241, "cE": 32, "cN": 120},
        {"name": "RA-BEAM", "pmid": "28199814", "nct": "NCT01710358",
         "year": 2017, "tE": 339, "tN": 487, "cE": 196, "cN": 488},
        {"name": "SELECT-NEXT", "pmid": "29908669", "nct": "NCT02675426",
         "year": 2018, "tE": 141, "tN": 221, "cE": 79, "cN": 221},
        {"name": "FINCH 1", "pmid": "33504485", "nct": "NCT02889796",
         "year": 2021, "tE": 364, "tN": 475, "cE": 237, "cN": 475},
    ],
    "raw_text": "Across four randomized trials (n = 2228 participants), the "
                "pooled odds ratio for ACR20 was 3.40 (95% CI 2.89 to 3.99), "
                "with no heterogeneity (I2 = 0%).",
}
write("paper105_jak_ra.json", paper105)

# --- 106: add-on biologics for severe asthma (effect shape, RR; reproduces) --
paper106 = {
    "title": "Add-on biologics for severe-asthma exacerbations",
    "source": "fixture:106 (snapshot of RapidMeta asthma-biologics dashboard)",
    "claimed": {"measure": "RR", "est": 0.52, "lci": 0.44, "uci": 0.62,
                "I2": 69.0, "Q": 16.2, "pi_lci": 0.32, "pi_uci": 0.85,
                "k": 6, "method": "inverse-variance random-effects (DL/REML)"},
    "trials": [
        {"name": "EXTRA", "pmid": "21536936", "nct": "NCT00314574",
         "year": 2011, "effect": 0.75, "elci": 0.61, "euci": 0.92,
         "tN": 427, "cN": 423},
        {"name": "MENSA", "pmid": "25199059", "nct": "NCT01691521",
         "year": 2014, "effect": 0.47, "elci": 0.35, "euci": 0.63,
         "tN": 194, "cN": 191},
        {"name": "SIROCCO", "pmid": "27609408", "nct": "NCT01928771",
         "year": 2016, "effect": 0.49, "elci": 0.37, "euci": 0.64,
         "tN": 267, "cN": 267},
        {"name": "Reslizumab 3082 (Castro 2015, Study 1)", "pmid": "25736990",
         "nct": "NCT01287039", "year": 2015, "effect": 0.50, "elci": 0.37,
         "euci": 0.67, "tN": 245, "cN": 244},
        {"name": "QUEST", "pmid": "29782217", "nct": "NCT02414854",
         "year": 2018, "effect": 0.523, "elci": 0.413, "euci": 0.662,
         "tN": 631, "cN": 317},
        {"name": "NAVIGATOR", "pmid": "33979488", "nct": "NCT03347279",
         "year": 2021, "effect": 0.44, "elci": 0.37, "euci": 0.53,
         "tN": 529, "cN": 532},
    ],
    "raw_text": "Six randomized trials of add-on biologics reduced severe "
                "exacerbations (pooled rate ratio 0.52, 95% CI 0.44 to 0.62; "
                "I2 = 69%).",
}
write("paper106_asthma.json", paper106)

# --- corrupted 105: a single transcription error in RA-BEAM control events ---
corr105 = copy.deepcopy(paper105)
corr105["title"] += " [corrupted: RA-BEAM control events 196->396]"
corr105["source"] = "fixture:105-corrupted (planted transcription error)"
for t in corr105["trials"]:
    if t["name"] == "RA-BEAM":
        t["cE"] = 396           # real value is 196; 396 is still < cN=488 (valid)
write("paper105_corrupted.json", corr105)

# --- corrupted 106: a decimal slip in MENSA's effect (0.47 -> 0.047) ---------
corr106 = copy.deepcopy(paper106)
corr106["title"] += " [corrupted: MENSA effect 0.47->0.047]"
corr106["source"] = "fixture:106-corrupted (planted decimal/unit error)"
for t in corr106["trials"]:
    if t["name"] == "MENSA":
        t["effect"] = 0.047     # decimal slip; now outside its own CI 0.35-0.63
write("paper106_corrupted.json", corr106)

# --- GLP-1 / ELIXA: real per-trial MACE HRs, planted over-stated pooled -------
glp1 = {
    "title": "GLP-1 receptor agonists and 3-point MACE in type 2 diabetes",
    "source": "fixture:glp1-elixa (REAL published per-trial MACE HRs; the "
              "claimed pooled HR of 0.62 is a planted over-statement "
              "reproducing the documented INCRETIN-style extraction error)",
    "claimed": {"measure": "HR", "est": 0.62, "lci": 0.55, "uci": 0.70,
                "I2": 40.0, "k": 8,
                "method": "inverse-variance random-effects"},
    "trials": [
        {"name": "ELIXA (lixisenatide)", "pmid": "26630143",
         "nct": "NCT01147250", "year": 2015,
         "effect": 1.02, "elci": 0.89, "euci": 1.17},
        {"name": "LEADER (liraglutide)", "pmid": "27295427",
         "nct": "NCT01179048", "year": 2016,
         "effect": 0.87, "elci": 0.78, "euci": 0.97},
        {"name": "SUSTAIN-6 (semaglutide SC)", "pmid": "27633186",
         "nct": "NCT01720446", "year": 2016,
         "effect": 0.74, "elci": 0.58, "euci": 0.95},
        {"name": "EXSCEL (exenatide QW)", "pmid": "28910237",
         "nct": "NCT01144338", "year": 2017,
         "effect": 0.91, "elci": 0.83, "euci": 1.00},
        {"name": "HARMONY Outcomes (albiglutide)", "pmid": "30293770",
         "nct": "NCT02465515", "year": 2018,
         "effect": 0.78, "elci": 0.68, "euci": 0.90},
        {"name": "REWIND (dulaglutide)", "pmid": "31189511",
         "nct": "NCT01394952", "year": 2019,
         "effect": 0.88, "elci": 0.79, "euci": 0.99},
        {"name": "PIONEER 6 (oral semaglutide)", "pmid": "31185157",
         "nct": "NCT02692716", "year": 2019,
         "effect": 0.79, "elci": 0.57, "euci": 1.11},
        {"name": "AMPLITUDE-O (efpeglenatide)", "pmid": "34010530",
         "nct": "NCT03496298", "year": 2021,
         "effect": 0.73, "elci": 0.58, "euci": 0.92},
    ],
    "raw_text": "Pooling eight cardiovascular-outcome trials, GLP-1 receptor "
                "agonists reduced 3-point MACE (pooled HR 0.62, 95% CI 0.55 to "
                "0.70).",
}
write("glp1_elixa.json", glp1)

# --- synthetic structural-defect case (stands in for workbook #30) -----------
paper30 = {
    "title": "Synthetic structural-defect meta-analysis (#30 stand-in)",
    "source": "fixture:paper30-structural (SYNTHETIC; exercises k-mismatch, "
              "fabricated NCT, miscited review, placeholder artifact)",
    "claimed": {"measure": "RR", "est": 0.70, "lci": 0.60, "uci": 0.82,
                "I2": 30.0, "k": 8,   # claims 8 but lists 5 -> k-mismatch
                "method": "random-effects"},
    "trials": [
        {"name": "Real RCT A (NAVIGATOR)", "pmid": "33979488",
         "nct": "NCT03347279", "year": 2021,
         "effect": 0.44, "elci": 0.37, "euci": 0.53},
        {"name": "Real RCT B (MENSA)", "pmid": "25199059",
         "nct": "NCT01691521", "year": 2014,
         "effect": 0.47, "elci": 0.35, "euci": 0.63},
        {"name": "Real RCT C (SIROCCO)", "pmid": "27609408",
         "nct": "NCT01928771", "year": 2016,
         "effect": 0.49, "elci": 0.37, "euci": 0.64},
        {"name": "Miscited synthesis (a GLP-1 systematic review/meta-analysis)",
         "pmid": "42009258", "year": 2025,
         "effect": 0.86, "elci": 0.80, "euci": 0.93},
        {"name": "Phantom Trial (fabricated registration)",
         "nct": "NCT09999999", "year": 2020,
         "effect": 0.55, "elci": 0.40, "euci": 0.75},
    ],
    "raw_text": "We pooled eight randomized trials across n participants and "
                "found a rate ratio of 0.70 (95% CI 0.60 to 0.82).",
}
write("paper30_structural.json", paper30)

print("\nfixtures written to", OUT)
