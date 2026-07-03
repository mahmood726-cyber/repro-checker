"""CLI surface: check exit codes, the validate subcommand, malformed-input
fail-closed handling, and offline check on a fixture.
"""
import json

import pytest

from conftest import FIXTURES
from reprocheck.cli import main


def test_validate_subcommand_offline_exit_zero(capsys):
    rc = main(["validate"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "6/6 passed" in out
    assert "validation benchmark" in out


def test_check_reproducing_fixture_offline_exit_zero(capsys):
    rc = main(["check", str(FIXTURES / "paper105_jak_ra.json"),
               "--no-source", "--format", "json"])
    out = capsys.readouterr().out
    assert rc == 0
    data = json.loads(out)
    assert data["overall"].startswith("REPRODUCES")


def test_check_diverging_fixture_exit_two(capsys):
    rc = main(["check", str(FIXTURES / "glp1_elixa.json"), "--no-source"])
    capsys.readouterr()
    assert rc == 2


def test_check_malformed_json_fails_closed(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text('{"trials": "not a list"}', encoding="utf-8")
    rc = main(["check", str(bad), "--no-source"])
    err = capsys.readouterr().err
    assert rc == 1
    assert "error:" in err and "trials" in err


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as e:
        main(["--version"])
    assert e.value.code == 0
    assert "reprocheck" in capsys.readouterr().out
