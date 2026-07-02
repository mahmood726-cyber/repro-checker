"""parse_claimed_text(): manuscript-prose scraping, incl. negation guard.

The negation guard implements lessons.md#negated-counts-silent-corruption:
"not included 5 trials" must NOT be scraped as k=5.
"""
from reprocheck.claims import parse_claimed_text


def test_scrapes_pooled_effect_and_ci():
    c = parse_claimed_text(
        "The pooled OR was 1.42 (95% CI 1.10 to 1.83), I2 = 40%.")
    assert c.measure == "OR"
    assert c.est == 1.42 and c.lci == 1.10 and c.uci == 1.83
    assert c.I2 == 40.0


def test_scrapes_k_and_participants():
    c = parse_claimed_text(
        "We included 12 trials with 3,400 participants.")
    assert c.k == 12
    assert c.n_stated == 3400


def test_negated_k_is_not_scraped():
    # the exact corruption class: a negated count must not become k
    assert parse_claimed_text("We had not included 5 trials.").k is None
    assert parse_claimed_text("We did not pool 7 studies.").k is None


def test_negated_participants_not_scraped():
    assert parse_claimed_text(
        "The analysis excluded 1,200 participants.").n_stated is None


def test_negation_in_earlier_clause_does_not_suppress_positive_count():
    # a clause break ("but"/"and") between the negation and the count means the
    # negation belongs to a different clause and must not suppress the real k
    c = parse_claimed_text("We excluded 3 studies but included 12 trials.")
    assert c.k == 12
    c = parse_claimed_text(
        "We excluded 1,200 participants and included 8 studies "
        "with 5,050 participants.")
    assert c.k == 8
    assert c.n_stated == 5050
