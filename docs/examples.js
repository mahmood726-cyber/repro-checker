/* AUTO-GENERATED from fixtures by scripts/build_examples.py. */
window.RC_EXAMPLES = {
  "105 \u2014 JAK/RA (reproduces)": {
    "title": "JAK inhibitors for ACR20 response in rheumatoid arthritis",
    "source": "fixture:105 (snapshot of RapidMeta JAK-RA dashboard)",
    "claimed": {
      "measure": "OR",
      "est": 3.4,
      "lci": 2.89,
      "uci": 3.99,
      "I2": 0.0,
      "Q": 0.74,
      "pi_lci": 2.61,
      "pi_uci": 4.42,
      "k": 4,
      "n_stated": 2228,
      "method": "inverse-variance random-effects (DL/REML)"
    },
    "trials": [
      {
        "name": "ORAL Solo",
        "pmid": "22873530",
        "nct": "NCT00814307",
        "year": 2012,
        "tE": 144,
        "tN": 241,
        "cE": 32,
        "cN": 120
      },
      {
        "name": "RA-BEAM",
        "pmid": "28199814",
        "nct": "NCT01710358",
        "year": 2017,
        "tE": 339,
        "tN": 487,
        "cE": 196,
        "cN": 488
      },
      {
        "name": "SELECT-NEXT",
        "pmid": "29908669",
        "nct": "NCT02675426",
        "year": 2018,
        "tE": 141,
        "tN": 221,
        "cE": 79,
        "cN": 221
      },
      {
        "name": "FINCH 1",
        "pmid": "33504485",
        "nct": "NCT02889796",
        "year": 2021,
        "tE": 364,
        "tN": 475,
        "cE": 237,
        "cN": 475
      }
    ],
    "raw_text": "Across four randomized trials (n = 2228 participants), the pooled odds ratio for ACR20 was 3.40 (95% CI 2.89 to 3.99), with no heterogeneity (I2 = 0%)."
  },
  "106 \u2014 asthma biologics (reproduces)": {
    "title": "Add-on biologics for severe-asthma exacerbations",
    "source": "fixture:106 (snapshot of RapidMeta asthma-biologics dashboard)",
    "claimed": {
      "measure": "RR",
      "est": 0.52,
      "lci": 0.44,
      "uci": 0.62,
      "I2": 69.0,
      "Q": 16.2,
      "pi_lci": 0.32,
      "pi_uci": 0.85,
      "k": 6,
      "method": "inverse-variance random-effects (DL/REML)"
    },
    "trials": [
      {
        "name": "EXTRA",
        "pmid": "21536936",
        "nct": "NCT00314574",
        "year": 2011,
        "effect": 0.75,
        "elci": 0.61,
        "euci": 0.92,
        "tN": 427,
        "cN": 423
      },
      {
        "name": "MENSA",
        "pmid": "25199059",
        "nct": "NCT01691521",
        "year": 2014,
        "effect": 0.47,
        "elci": 0.35,
        "euci": 0.63,
        "tN": 194,
        "cN": 191
      },
      {
        "name": "SIROCCO",
        "pmid": "27609408",
        "nct": "NCT01928771",
        "year": 2016,
        "effect": 0.49,
        "elci": 0.37,
        "euci": 0.64,
        "tN": 267,
        "cN": 267
      },
      {
        "name": "Reslizumab 3082 (Castro 2015, Study 1)",
        "pmid": "25736990",
        "nct": "NCT01287039",
        "year": 2015,
        "effect": 0.5,
        "elci": 0.37,
        "euci": 0.67,
        "tN": 245,
        "cN": 244
      },
      {
        "name": "QUEST",
        "pmid": "29782217",
        "nct": "NCT02414854",
        "year": 2018,
        "effect": 0.523,
        "elci": 0.413,
        "euci": 0.662,
        "tN": 631,
        "cN": 317
      },
      {
        "name": "NAVIGATOR",
        "pmid": "33979488",
        "nct": "NCT03347279",
        "year": 2021,
        "effect": 0.44,
        "elci": 0.37,
        "euci": 0.53,
        "tN": 529,
        "cN": 532
      }
    ],
    "raw_text": "Six randomized trials of add-on biologics reduced severe exacerbations (pooled rate ratio 0.52, 95% CI 0.44 to 0.62; I2 = 69%)."
  },
  "GLP-1 / ELIXA (diverges: claimed 0.62 vs ~0.86)": {
    "title": "GLP-1 receptor agonists and 3-point MACE in type 2 diabetes",
    "source": "fixture:glp1-elixa (REAL published per-trial MACE HRs; the claimed pooled HR of 0.62 is a planted over-statement reproducing the documented INCRETIN-style extraction error)",
    "claimed": {
      "measure": "HR",
      "est": 0.62,
      "lci": 0.55,
      "uci": 0.7,
      "I2": 40.0,
      "k": 8,
      "method": "inverse-variance random-effects"
    },
    "trials": [
      {
        "name": "ELIXA (lixisenatide)",
        "pmid": "26630143",
        "nct": "NCT01147250",
        "year": 2015,
        "effect": 1.02,
        "elci": 0.89,
        "euci": 1.17
      },
      {
        "name": "LEADER (liraglutide)",
        "pmid": "27295427",
        "nct": "NCT01179048",
        "year": 2016,
        "effect": 0.87,
        "elci": 0.78,
        "euci": 0.97
      },
      {
        "name": "SUSTAIN-6 (semaglutide SC)",
        "pmid": "27633186",
        "nct": "NCT01720446",
        "year": 2016,
        "effect": 0.74,
        "elci": 0.58,
        "euci": 0.95
      },
      {
        "name": "EXSCEL (exenatide QW)",
        "pmid": "28910237",
        "nct": "NCT01144338",
        "year": 2017,
        "effect": 0.91,
        "elci": 0.83,
        "euci": 1.0
      },
      {
        "name": "HARMONY Outcomes (albiglutide)",
        "pmid": "30293770",
        "nct": "NCT02465515",
        "year": 2018,
        "effect": 0.78,
        "elci": 0.68,
        "euci": 0.9
      },
      {
        "name": "REWIND (dulaglutide)",
        "pmid": "31189511",
        "nct": "NCT01394952",
        "year": 2019,
        "effect": 0.88,
        "elci": 0.79,
        "euci": 0.99
      },
      {
        "name": "PIONEER 6 (oral semaglutide)",
        "pmid": "31185157",
        "nct": "NCT02692716",
        "year": 2019,
        "effect": 0.79,
        "elci": 0.57,
        "euci": 1.11
      },
      {
        "name": "AMPLITUDE-O (efpeglenatide)",
        "pmid": "34010530",
        "nct": "NCT03496298",
        "year": 2021,
        "effect": 0.73,
        "elci": 0.58,
        "euci": 0.92
      }
    ],
    "raw_text": "Pooling eight cardiovascular-outcome trials, GLP-1 receptor agonists reduced 3-point MACE (pooled HR 0.62, 95% CI 0.55 to 0.70)."
  },
  "#30 structural defects (fails)": {
    "title": "Synthetic structural-defect meta-analysis (#30 stand-in)",
    "source": "fixture:paper30-structural (SYNTHETIC; exercises k-mismatch, fabricated NCT, miscited review, placeholder artifact)",
    "claimed": {
      "measure": "RR",
      "est": 0.7,
      "lci": 0.6,
      "uci": 0.82,
      "I2": 30.0,
      "k": 8,
      "method": "random-effects"
    },
    "trials": [
      {
        "name": "Real RCT A (NAVIGATOR)",
        "pmid": "33979488",
        "nct": "NCT03347279",
        "year": 2021,
        "effect": 0.44,
        "elci": 0.37,
        "euci": 0.53
      },
      {
        "name": "Real RCT B (MENSA)",
        "pmid": "25199059",
        "nct": "NCT01691521",
        "year": 2014,
        "effect": 0.47,
        "elci": 0.35,
        "euci": 0.63
      },
      {
        "name": "Real RCT C (SIROCCO)",
        "pmid": "27609408",
        "nct": "NCT01928771",
        "year": 2016,
        "effect": 0.49,
        "elci": 0.37,
        "euci": 0.64
      },
      {
        "name": "Miscited synthesis (a GLP-1 systematic review/meta-analysis)",
        "pmid": "42009258",
        "year": 2025,
        "effect": 0.86,
        "elci": 0.8,
        "euci": 0.93
      },
      {
        "name": "Phantom Trial (fabricated registration)",
        "nct": "NCT09999999",
        "year": 2020,
        "effect": 0.55,
        "elci": 0.4,
        "euci": 0.75
      }
    ],
    "raw_text": "We pooled eight randomized trials across n participants and found a rate ratio of 0.70 (95% CI 0.60 to 0.82)."
  },
  "105 corrupted (diverges)": {
    "title": "JAK inhibitors for ACR20 response in rheumatoid arthritis [corrupted: RA-BEAM control events 196->396]",
    "source": "fixture:105-corrupted (planted transcription error)",
    "claimed": {
      "measure": "OR",
      "est": 3.4,
      "lci": 2.89,
      "uci": 3.99,
      "I2": 0.0,
      "Q": 0.74,
      "pi_lci": 2.61,
      "pi_uci": 4.42,
      "k": 4,
      "n_stated": 2228,
      "method": "inverse-variance random-effects (DL/REML)"
    },
    "trials": [
      {
        "name": "ORAL Solo",
        "pmid": "22873530",
        "nct": "NCT00814307",
        "year": 2012,
        "tE": 144,
        "tN": 241,
        "cE": 32,
        "cN": 120
      },
      {
        "name": "RA-BEAM",
        "pmid": "28199814",
        "nct": "NCT01710358",
        "year": 2017,
        "tE": 339,
        "tN": 487,
        "cE": 396,
        "cN": 488
      },
      {
        "name": "SELECT-NEXT",
        "pmid": "29908669",
        "nct": "NCT02675426",
        "year": 2018,
        "tE": 141,
        "tN": 221,
        "cE": 79,
        "cN": 221
      },
      {
        "name": "FINCH 1",
        "pmid": "33504485",
        "nct": "NCT02889796",
        "year": 2021,
        "tE": 364,
        "tN": 475,
        "cE": 237,
        "cN": 475
      }
    ],
    "raw_text": "Across four randomized trials (n = 2228 participants), the pooled odds ratio for ACR20 was 3.40 (95% CI 2.89 to 3.99), with no heterogeneity (I2 = 0%)."
  }
};
