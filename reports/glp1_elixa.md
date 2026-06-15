# Reproducibility report — GLP-1 receptor agonists and 3-point MACE in type 2 diabetes

**Overall verdict: DIVERGES — does not reproduce**  
The pooled estimate recomputes to 0.8621 but the paper claims 0.62. 3 claimed quantity(ies) diverge.

_Source: fixture:glp1-elixa (REAL published per-trial MACE HRs; the claimed pooled HR of 0.62 is a planted over-statement reproducing the documented INCRETIN-style extraction error) · generated 2026-06-15 20:44 UTC_

## Per-claim verdicts

| Quantity | Claimed | Recomputed | Verdict | Tolerance | Note |
|---|---|---|---|---|---|
| pooled HR | 0.62 | 0.8621 | ✗ DIVERGES | ±5% relative (log scale) |  |
| 95% CI lower | 0.55 | 0.8021 | ✗ DIVERGES | ±8% relative (log scale) |  |
| 95% CI upper | 0.7 | 0.9265 | ✗ DIVERGES | ±8% relative (log scale) |  |
| I^2 (%) | 40 | 44.5 | ✓ reproduces | ±5.0 pts |  |
| k (studies pooled) | 8 | 8 | ✓ reproduces | exact |  |

## Flags

None.

## Re-sourced citations

| Trial | Verdict | Identifiers | Notes |
|---|---|---|---|
| ELIXA (lixisenatide) | real-trial | pmid=26630143, nct=NCT01147250 |  |
| LEADER (liraglutide) | real-trial | pmid=27295427, nct=NCT01179048 |  |
| SUSTAIN-6 (semaglutide SC) | real-trial | pmid=27633186, nct=NCT01720446 |  |
| EXSCEL (exenatide QW) | real-trial | pmid=28910237, nct=NCT01144338 |  |
| HARMONY Outcomes (albiglutide) | real-trial | pmid=30293770, nct=NCT02465515 |  |
| REWIND (dulaglutide) | real-trial | pmid=31189511, nct=NCT01394952 |  |
| PIONEER 6 (oral semaglutide) | real-trial | pmid=31185157, nct=NCT02692716 |  |
| AMPLITUDE-O (efpeglenatide) | real-trial | pmid=34010530, nct=NCT03496298 |  |
