"""Regression tests for the science / cross-modal checker (factory/qa/science.py).

Case A from the failed spaghetti video: the narration said it breaks into three pieces while the
simulation and the picture showed four. That must block; correctly qualified wording must pass.
"""
from pathlib import Path
from types import SimpleNamespace as NS

from factory.qa import science

FACTS = {"plain_pieces": 4, "twisted_pieces": 2, "twist_turns": 1.0, "slow_factors": [38, 2000]}
CLAIM = {"id": "plain_count", "beat": "setup", "unit": "pieces", "sim": "plain_pieces", "scope": "specific",
         "evidence": {"quality": 1, "source": "simulation; Audoly & Neukirch 2005", "range": [3, None]}}


def sb(text, claims=(CLAIM,), absolute_ok=()):
    return NS(path=Path("."), beats=[NS(id="setup", text=text)],
              extra={"claims": list(claims), "absolute_ok": list(absolute_ok)})


def blockers(F):
    return [f for f in F if f.severity <= 1]


def test_old_spaghetti_line_contradicts_simulation():
    F = science.check(sb("Bend a dry stick from both ends, and it snaps into three pieces."), FACTS)
    assert any(f.id == "science.mismatch.plain_count" and f.severity == 0 for f in F)


def test_fixed_line_passes():
    F = science.check(sb("Bend a dry stick from both ends, and it shatters into several pieces. Here, four of them."), FACTS)
    assert blockers(F) == []


def test_qualified_generalisation_is_not_a_contradiction():
    typical = dict(CLAIM, scope="typical")
    F = science.check(sb("It usually breaks into three pieces or more.", claims=[typical]), FACTS)
    assert blockers(F) == []


def test_overstated_universal_is_flagged():
    universal = dict(CLAIM, scope="typical", value=3, sim=None)
    F = science.check(sb("Every strand always breaks into exactly three pieces.", claims=[universal]), FACTS)
    assert blockers(F), "absolute wording for a result that varies must be flagged"


def test_unbound_number_is_flagged():
    F = science.check(sb("Here, four of them. It took seven tries.", claims=[CLAIM]), FACTS)
    assert any(f.id.startswith("science.unverified_number") for f in F)


def test_beautiful_but_wrong_card_blocks():
    """A correct narration with a wrong on-screen number still blocks (cards are checked too)."""
    F = science.check(sb("Here, four of them."), FACTS, cards=[{"big": "3 pieces", "small": "from one snap"}])
    assert any(f.id.startswith("science.card_mismatch") and f.severity == 0 for f in F)


def test_badges_must_match_simulation():
    ok = science.check(sb("Here, four of them."), FACTS, badges=["SLOWED 2,000×", "TRY 2 · 4 PIECES"])
    bad = science.check(sb("Here, four of them."), FACTS, badges=["SLOWED 500×"])
    assert not [f for f in ok if f.id.startswith("science.badge")]
    assert [f for f in bad if f.id.startswith("science.badge")]


def test_number_parsing():
    m = science.mentions("Turn it almost a full turn, about three quarters of a turn, in two thousand eighteen.")
    vals = [(x["value"], x["unit"], x["qualifier"]) for x in m]
    assert (1.0, "turn", "almost") in vals and (0.75, "turn", "approx") in vals and (2018, "year", "exact") in vals
    assert not [x for x in m if x["unit"] == "pieces"], "'in two thousand' is a year, not 'in two (pieces)'"


def test_almost_never_is_qualified():
    assert science.absolutes("You almost never can.") == []
    assert science.absolutes("You never can.") != []


def test_large_scales_ordinal_times_and_parts_in():
    """head-ages-faster wording: stacked scales, 'half a millionth of a second', 'one part in ...', µs/ns."""
    from factory.qa.science import mentions
    m = mentions("About one part in ten million billion... per metre.")
    assert [(x["value"], x["unit"]) for x in m] == [(1e16, "parts")]
    m = mentions("your head ends up about half a millionth of a second older")
    assert [(x["value"], x["unit"], x["qualifier"]) for x in m] == [(5e-7, "s", "approx")]
    assert [(x["value"], x["unit"]) for x in mentions("gain about forty-five microseconds a day")] == [(45.0, "µs")]
    assert mentions("two million three thousand cars")[0]["value"] == 2_003_000
