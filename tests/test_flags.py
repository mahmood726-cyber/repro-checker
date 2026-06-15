"""Flag detectors: placeholders, arithmetic sanity, k mismatch, sourcing."""
from reprocheck.claims import Submission, Trial, Claimed
from reprocheck.flags import (flag_placeholders, flag_data_sanity,
                              flag_k_mismatch, flag_sourcing)


def _ids(flags):
    return {f.id for f in flags}


def test_placeholder_artifacts():
    sub = Submission(title="x", raw_text="pooled across n participants; TODO fix")
    ids = _ids(flag_placeholders(sub))
    assert "placeholder-artifact" in ids


def test_impossible_count_events_exceed_n():
    sub = Submission(trials=[Trial("bad", tE=999, tN=100, cE=5, cN=100)])
    flags = flag_data_sanity(sub)
    assert any(f.id == "impossible-count" and f.severity == "high" for f in flags)


def test_effect_outside_its_own_ci():
    sub = Submission(trials=[Trial("slip", effect=0.047, elci=0.35, euci=0.63)])
    flags = flag_data_sanity(sub)
    assert any(f.id == "effect-outside-ci" for f in flags)


def test_k_mismatch():
    sub = Submission(claimed=Claimed(k=8),
                     trials=[Trial("a", effect=0.5, elci=0.4, euci=0.6),
                             Trial("b", effect=0.6, elci=0.5, euci=0.7)])
    flags = flag_k_mismatch(sub)
    assert any(f.id == "k-mismatch" for f in flags)


def test_sourcing_flags_translate_verdicts():
    sourcing = [
        {"name": "fake", "verdict": "not-real", "notes": ["NCT missing"]},
        {"name": "rev", "verdict": "not-a-trial", "notes": ["Meta-Analysis"]},
        {"name": "net", "verdict": "cannot-verify", "notes": ["offline"]},
        {"name": "ok", "verdict": "real-trial", "notes": []},
    ]
    flags = flag_sourcing(sourcing)
    ids = _ids(flags)
    assert "citation-not-real" in ids and "citation-not-a-trial" in ids
    assert any(f.id == "citation-not-real" and f.severity == "high" for f in flags)
    # a real trial yields no flag
    assert not any(f.subject == "ok" for f in flags)
