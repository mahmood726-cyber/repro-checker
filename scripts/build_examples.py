"""Emit docs/examples.js (embedded example submissions) from the fixtures, so the
offline web tool ships working examples without transcription drift.

Run:  python scripts/build_examples.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "fixtures"
PICK = [
    ("105 — JAK/RA (reproduces)", "paper105_jak_ra.json"),
    ("106 — asthma biologics (reproduces)", "paper106_asthma.json"),
    ("GLP-1 / ELIXA (diverges: claimed 0.62 vs ~0.86)", "glp1_elixa.json"),
    ("#30 structural defects (fails)", "paper30_structural.json"),
    ("105 corrupted (diverges)", "paper105_corrupted.json"),
]
examples = {label: json.loads((FIX / f).read_text(encoding="utf-8"))
            for label, f in PICK}
out = ("/* AUTO-GENERATED from fixtures by scripts/build_examples.py. */\n"
       "window.RC_EXAMPLES = " + json.dumps(examples, indent=2) + ";\n")
(ROOT / "docs" / "examples.js").write_text(out, encoding="utf-8")
print("wrote docs/examples.js with", len(examples), "examples")
