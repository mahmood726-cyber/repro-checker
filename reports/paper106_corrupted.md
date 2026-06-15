# Reproducibility report — Add-on biologics for severe-asthma exacerbations [corrupted: MENSA effect 0.47->0.047]

**Overall verdict: DIVERGES — does not reproduce**  
The pooled estimate recomputes to 0.3555 but the paper claims 0.52. 7 claimed quantity(ies) diverge.

_Source: fixture:106-corrupted (planted decimal/unit error) · generated 2026-06-15 20:44 UTC_

## Per-claim verdicts

| Quantity | Claimed | Recomputed | Verdict | Tolerance | Note |
|---|---|---|---|---|---|
| pooled RR | 0.52 | 0.3555 | ✗ DIVERGES | ±5% relative (log scale) |  |
| 95% CI lower | 0.44 | 0.1594 | ✗ DIVERGES | ±8% relative (log scale) |  |
| 95% CI upper | 0.62 | 0.7927 | ✗ DIVERGES | ±8% relative (log scale) |  |
| I^2 (%) | 69 | 98 | ✗ DIVERGES | ±5.0 pts |  |
| Cochran's Q | 16.2 | 249.9 | ✗ DIVERGES | ±1.0 |  |
| k (studies pooled) | 6 | 6 | ✓ reproduces | exact |  |
| prediction interval lower | 0.32 | 0.022 | ✗ DIVERGES | ±15% |  |
| prediction interval upper | 0.85 | 5.632 | ✗ DIVERGES | ±15% |  |

## Flags

- **[MEDIUM] Point estimate lies outside its own 95% CI**: effect=0.047, CI 0.35-0.63 (arithmetic/transcription error) — _MENSA_

## Re-sourced citations

| Trial | Verdict | Identifiers | Notes |
|---|---|---|---|
| EXTRA | real-trial | pmid=21536936, nct=NCT00314574 |  |
| MENSA | real-trial | pmid=25199059, nct=NCT01691521 |  |
| SIROCCO | real-trial | pmid=27609408, nct=NCT01928771 |  |
| Reslizumab 3082 (Castro 2015, Study 1) | real-trial | pmid=25736990, nct=NCT01287039 |  |
| QUEST | real-trial | pmid=29782217, nct=NCT02414854 |  |
| NAVIGATOR | real-trial | pmid=33979488, nct=NCT03347279 |  |
