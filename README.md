# reprocheck — meta-analysis reproducibility checker

Re-derives a meta-analysis's pooled statistics from **independently re-sourced
primary trial data** and reports, per claim, what does **not** hold up — the
check peer review almost never runs.

**Truth-first.** A number is reported as *reproduced* only when it actually
recomputes from sourced data. When the data is not sourceable, the verdict is an
honest *cannot-verify* (with the reason). The tool never fabricates a check
result.

**Standalone tool (live):** <https://mahmood726-cyber.github.io/repro-checker/>

One shared engine, two front-ends:

- **Synthēsis editorial gate** (`synthesis_gate.py`) — every submitted
  meta-analysis is auto-checked on submission; the editor gets the
  reproducibility report **before** an accept decision. It *informs*; it does
  not auto-reject. Runs against a submission-files export or the live OJS REST
  submission queue.
- **Standalone allmeta tool** (`docs/`, hosted on Pages, + the CLI) — paste a
  study table (or load an example) and get the report fully offline; opt-in
  in-browser live re-sourcing.

```bash
# Synthēsis gate — process an export of submission files
python synthesis_gate.py --export ./submissions --out reports
#   -> reports/EDITOR_SUMMARY.md (advisory) + reports/<id>.md per submission
# or the live OJS queue:
python synthesis_gate.py --ojs-base https://www.synthesis-medicine.org/index.php/journal --token $OJS_TOKEN
```

## What it does (pipeline)

1. **Extract** the included trials + claimed pooled stats from the submission
   (`claims.py`; rct-extractor-v2 for full PDFs).
2. **Re-source** each trial independently from PubMed/PMC (NCBI E-utilities) and
   ClinicalTrials.gov v2 (`resource.py`) — confirms the trial is real and is a
   *trial* (not a review/methods paper miscited as one).
3. **Recompute** the pooled effect + 95% CI + I²/τ²/Q + k with inverse-variance
   random-effects (DerSimonian–Laird + REML), on the log scale (`recompute.py`,
   vendored from the audited `synthesis-paper-spec/metapaper/stats.py`).
4. **Compare** recomputed vs claimed → per-claim verdicts (`compare.py`).
5. **Flag** non-reproducing pools (both values shown), per-trial extraction /
   arithmetic / unit errors, fake or miscited citations, k mismatches, and
   template/placeholder artifacts (`flags.py`).
6. **Report** a structured reproducibility report — JSON / Markdown / HTML — with
   an overall verdict (`report.py`).

## Use

```bash
# CLI
python -m reprocheck.cli check fixtures/paper105_jak_ra.json            # live re-source
python -m reprocheck.cli check submission.json --offline --format json  # no network
python -m reprocheck.cli check manuscript.txt  --format html --out report.html

# Validation (the honest validation set)
python scripts/validate.py --write     # runs all fixtures live, writes VALIDATION.md
```

Engine + CLI are **standard-library only**. `pytest` is the only dev dependency.

## Validation

See [`VALIDATION.md`](VALIDATION.md). On the agreed set, with **live**
re-sourcing:

| Case | Expected | Result |
|---|---|---|
| 105 JAK/RA | reproduces | ✅ OR 3.40 recomputes |
| 106 asthma biologics | reproduces | ✅ RR 0.52 recomputes |
| corrupted 105 / 106 | diverge | ✅ both flagged |
| GLP-1 / ELIXA | diverge | ✅ recomputes 0.86 vs claimed 0.62 |
| #30 structural | flag (FAIL) | ✅ fake NCT + miscited review + k-mismatch |
| INCRETIN 0.62-vs-0.41 | — | reported **not-found** (not on disk; nothing fabricated) |

## Layout

| Path | Purpose |
|---|---|
| `reprocheck/` | the shared engine + CLI |
| `synthesis_gate.py` | Synthēsis OJS pre-acceptance gate |
| `docs/index.html` | standalone offline web UI |
| `fixtures/` | validation fixtures (self-contained JSON) |
| `scripts/` | fixture generator + validation runner |
| `tests/` | pytest (offline-deterministic + network-gated) |

## License

MIT.
