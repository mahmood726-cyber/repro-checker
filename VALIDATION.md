# Validation results — reprocheck

_Generated 2026-06-15 20:41 UTC (live re-sourcing)._

**6/6 fixtures matched their expected verdict.**

| Fixture | Purpose | Expected | Overall verdict | Claimed | Recomputed | High flags | Match |
|---|---|---|---|---|---|---|---|
| `paper105_jak_ra.json` | JAK/RA — must reproduce | REPRODUCES | REPRODUCES | 3.4 | 3.4 | 0 | ✅ |
| `paper106_asthma.json` | asthma biologics — must reproduce | REPRODUCES | REPRODUCES | 0.52 | 0.523 | 0 | ✅ |
| `paper105_corrupted.json` | planted transcription error — must diverge | DIVERGES | DIVERGES — does not reproduce | 3.4 | 2.17 | 0 | ✅ |
| `paper106_corrupted.json` | planted decimal error — must diverge | DIVERGES | DIVERGES — does not reproduce | 0.52 | 0.355 | 0 | ✅ |
| `glp1_elixa.json` | GLP-1/ELIXA over-stated pool — must diverge | DIVERGES | DIVERGES — does not reproduce | 0.62 | 0.862 | 0 | ✅ |
| `paper30_structural.json` | #30 structural defects — must flag (FAIL) | FAIL | FAIL — integrity issue | 0.7 | 0.553 | 2 | ✅ |

## INCRETIN / GLP-1 '0.62-vs-0.41' QA case — NOT FOUND

The specific INCRETIN-set fixture with documented wrong extraction and a 0.62-vs-0.41 benchmark could **not be located on disk** (no `incretin` QA notes; the `glp1-cvot-engine` dashboard contains no `0.41`). It is therefore reported honestly as **not-found**, and no fixture was fabricated for it. The `glp1_elixa.json` fixture instead reproduces the *same failure mode* (a claimed pool that is too strong) using the real, live-resourceable published MACE hazard ratios of the eight GLP-1 CVOTs (ELIXA the neutral anchor); the checker recomputes ~0.86 against the claimed 0.62 and flags the divergence.
