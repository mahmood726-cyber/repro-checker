"""Input validation on the public entry points: Submission.from_dict /
from_json_file must fail closed on malformed input (SubmissionError) and must
coerce well-formed numeric strings, without ever silently accepting a
semantically impossible study table.
"""
import json

import pytest

from conftest import FIXTURES
from reprocheck.claims import Submission, SubmissionError


def test_all_fixtures_still_load():
    # regression guard: validation must not reject any real fixture
    for name in ("paper105_jak_ra.json", "paper106_asthma.json",
                 "paper105_corrupted.json", "paper106_corrupted.json",
                 "glp1_elixa.json", "paper30_structural.json"):
        sub = Submission.from_json_file(str(FIXTURES / name))
        assert sub.claimed is not None


def test_non_dict_submission_fails_closed():
    with pytest.raises(SubmissionError):
        Submission.from_dict("not a dict")
    with pytest.raises(SubmissionError):
        Submission.from_dict([1, 2, 3])


def test_trials_must_be_a_list():
    with pytest.raises(SubmissionError) as e:
        Submission.from_dict({"trials": "oops"})
    assert "trials" in str(e.value)


def test_claimed_must_be_an_object():
    with pytest.raises(SubmissionError) as e:
        Submission.from_dict({"claimed": "oops"})
    assert "claimed" in str(e.value)


def test_trial_element_must_be_object():
    with pytest.raises(SubmissionError):
        Submission.from_dict({"trials": [42]})


def test_negative_count_rejected():
    with pytest.raises(SubmissionError) as e:
        Submission.from_dict({"trials": [{"tE": -5, "tN": 10, "cE": 1, "cN": 10}]})
    assert "count must be >= 0" in str(e.value)


def test_fractional_count_rejected():
    with pytest.raises(SubmissionError) as e:
        Submission.from_dict({"trials": [{"tE": 1.5, "tN": 10, "cE": 1, "cN": 10}]})
    assert "whole number" in str(e.value)


def test_non_numeric_effect_rejected():
    with pytest.raises(SubmissionError) as e:
        Submission.from_dict({"claimed": {"est": "high"}})
    assert "non-numeric" in str(e.value)


def test_boolean_is_not_a_number():
    # bool is a subclass of int; must not be silently read as 0/1
    with pytest.raises(SubmissionError):
        Submission.from_dict({"claimed": {"est": True}})


def test_numeric_strings_are_coerced():
    # a spreadsheet-exported table often carries quoted numbers
    sub = Submission.from_dict({
        "claimed": {"measure": "OR", "est": "1.42", "k": "4"},
        "trials": [{"name": "a", "tE": "10", "tN": "20", "cE": "5", "cN": "20"}],
    })
    assert sub.claimed.est == 1.42
    assert sub.claimed.k == 4
    assert sub.trials[0].tE == 10 and isinstance(sub.trials[0].tE, int)


def test_absent_fields_stay_absent():
    sub = Submission.from_dict({"claimed": {"measure": "RR"}})
    assert sub.claimed.est is None
    assert sub.trials == []


def test_invalid_json_file_fails_closed(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{ not valid json ]", encoding="utf-8")
    with pytest.raises(SubmissionError) as e:
        Submission.from_json_file(str(p))
    assert "invalid JSON" in str(e.value)


def test_missing_file_fails_closed(tmp_path):
    with pytest.raises(SubmissionError):
        Submission.from_json_file(str(tmp_path / "nope.json"))
