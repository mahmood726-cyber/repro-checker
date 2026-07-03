"""reprocheck — meta-analysis reproducibility checker.

Re-derives a meta-analysis's pooled statistics from independently re-sourced
primary trial data and reports, per claim, whether the published number
*reproduces*, *diverges* (showing both values), or *cannot be verified* (with
the reason). Truth-first: a number is only reported as reproduced when it
actually recomputes from sourced data; missing sourceable data yields an
honest "cannot-verify", never a fabricated pass.

Shared engine behind two front-ends:
  * the Synthēsis pre-acceptance editorial gate (synthesis_gate.py)
  * the standalone allmeta web tool + CLI (web/index.html, reprocheck.cli)

Reuses audited pieces from the allmeta ecosystem:
  * pooling + verification gate  -> vendored from synthesis-paper-spec/metapaper/stats.py
  * live PubMed/PMC re-sourcing  -> NCBI E-utilities (esummary/efetch)
  * live trial re-sourcing       -> ClinicalTrials.gov API v2
"""

__version__ = "0.1.0"

from .claims import Submission, SubmissionError  # noqa: E402,F401
