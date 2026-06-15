"""Network-gated re-sourcing tests (PubMed / ClinicalTrials.gov).

Run only when online:   pytest -m network
Skip when offline:      pytest -m 'not network'
"""
import pytest

from reprocheck.resource import Resolver, resolve_trial

pytestmark = pytest.mark.network


@pytest.fixture(scope="module")
def resolver(tmp_path_factory):
    return Resolver(cache_dir=str(tmp_path_factory.mktemp("rc_cache")))


def test_real_rct_resolves(resolver):
    # ORAL Solo (tofacitinib RCT, NEJM 2012)
    r = resolve_trial({"name": "ORAL Solo", "pmid": "22873530"}, resolver)
    assert r["verdict"] == "real-trial"
    assert r["pubmed"]["is_trial"] is True


def test_meta_analysis_flagged_not_a_trial(resolver):
    # a GLP-1 systematic review/meta-analysis (PublicationType Meta-Analysis)
    r = resolve_trial({"name": "review", "pmid": "42009258"}, resolver)
    assert r["verdict"] == "not-a-trial"
    assert r["pubmed"]["is_synthesis"] is True


def test_fabricated_nct_is_not_real(resolver):
    r = resolve_trial({"name": "phantom", "nct": "NCT09999999"}, resolver)
    assert r["verdict"] == "not-real"


def test_real_nct_resolves(resolver):
    r = resolve_trial({"name": "ELIXA", "nct": "NCT01147250"}, resolver)
    assert r["ctgov"]["exists"] is True
