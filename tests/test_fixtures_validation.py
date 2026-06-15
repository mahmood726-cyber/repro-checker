"""End-to-end offline validation on the fixtures (no network).

Reproduce cases must reproduce; corrupted / over-stated cases must diverge.
The high-severity citation flags for #30 need live re-sourcing and are exercised
separately in test_resource.py (network-gated).
"""
import json

import pytest

from conftest import FIXTURES
from reprocheck.claims import Submission
from reprocheck.report import check


def _check(name):
    sub = Submission.from_json_file(str(FIXTURES / name))
    return check(sub, resolver=None, generated="test")


@pytest.mark.parametrize("name,prefix", [
    ("paper105_jak_ra.json", "REPRODUCES"),
    ("paper106_asthma.json", "REPRODUCES"),
    ("paper105_corrupted.json", "DIVERGES"),
    ("paper106_corrupted.json", "DIVERGES"),
    ("glp1_elixa.json", "DIVERGES"),
])
def test_overall_verdicts_offline(name, prefix):
    assert _check(name).overall.startswith(prefix)


def test_105_recomputes_to_claimed():
    rep = _check("paper105_jak_ra.json")
    assert abs(rep.recomputed["est"] - 3.40) < 0.03
    assert all(c.verdict == "reproduces" for c in rep.claims
               if c.quantity in ("pooled OR", "k (studies pooled)"))


def test_glp1_recomputes_near_086_not_062():
    rep = _check("glp1_elixa.json")
    assert abs(rep.recomputed["est"] - 0.86) < 0.03   # real literature value
    pooled = next(c for c in rep.claims if c.quantity == "pooled HR")
    assert pooled.verdict == "diverges"
    assert pooled.claimed == 0.62


def test_corrupted_106_flags_effect_outside_ci():
    rep = _check("paper106_corrupted.json")
    assert any(f.id == "effect-outside-ci" for f in rep.flags)


def test_paper30_has_structural_flags_offline():
    rep = _check("paper30_structural.json")
    ids = {f.id for f in rep.flags}
    assert "k-mismatch" in ids
    assert "placeholder-artifact" in ids
