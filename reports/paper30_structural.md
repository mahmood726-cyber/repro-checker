# Reproducibility report — Synthetic structural-defect meta-analysis (#30 stand-in)

**Overall verdict: FAIL — integrity issue**  
2 high-severity flag(s) (e.g. Citation is not a primary trial: PMID 42009258 is ['Journal Article', 'Systematic Review', 'Meta-Analysis'], not a primary trial). The pooled number may be unsafe regardless of arithmetic.

_Source: fixture:paper30-structural (SYNTHETIC; exercises k-mismatch, fabricated NCT, miscited review, placeholder artifact) · generated 2026-06-15 20:44 UTC_

## Per-claim verdicts

| Quantity | Claimed | Recomputed | Verdict | Tolerance | Note |
|---|---|---|---|---|---|
| pooled RR | 0.7 | 0.5532 | ✗ DIVERGES | ±5% relative (log scale) |  |
| 95% CI lower | 0.6 | 0.4248 | ✗ DIVERGES | ±8% relative (log scale) |  |
| 95% CI upper | 0.82 | 0.7203 | ✗ DIVERGES | ±8% relative (log scale) |  |
| I^2 (%) | 30 | 94.2 | ✗ DIVERGES | ±5.0 pts |  |
| k (studies pooled) | 8 | 5 | ✗ DIVERGES | exact |  |

## Flags

- **[HIGH] Citation is not a primary trial**: PMID 42009258 is ['Journal Article', 'Systematic Review', 'Meta-Analysis'], not a primary trial — _Miscited synthesis (a GLP-1 systematic review/meta-analysis)_
- **[HIGH] Cited trial does not exist**: NCT09999999 does not exist on ClinicalTrials.gov — _Phantom Trial (fabricated registration)_
- **[MEDIUM] Study-count (k) mismatch**: paper claims k=8 trials but the study table lists 5
- **[LOW] Template/placeholder artifact**: literal 'n participants' (unfilled count token) — _...ight randomized trials across n participants and found a rate ratio of 0.7..._

## Re-sourced citations

| Trial | Verdict | Identifiers | Notes |
|---|---|---|---|
| Real RCT A (NAVIGATOR) | real-trial | pmid=33979488, nct=NCT03347279 |  |
| Real RCT B (MENSA) | real-trial | pmid=25199059, nct=NCT01691521 |  |
| Real RCT C (SIROCCO) | real-trial | pmid=27609408, nct=NCT01928771 |  |
| Miscited synthesis (a GLP-1 systematic review/meta-analysis) | not-a-trial | pmid=42009258 | PMID 42009258 is ['Journal Article', 'Systematic Review', 'Meta-Analysis'], not a primary trial |
| Phantom Trial (fabricated registration) | not-real | nct=NCT09999999 | NCT09999999 does not exist on ClinicalTrials.gov |
