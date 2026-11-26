from factory.production import clipping_blockers, CLIP_GARMENT_VERTS


def row(hits, feet="on deck"):
    return {"shot": 3, "at": "mid", "t": 8.8, "hits": hits, "feet": feet}


def test_clean_row_passes():
    assert clipping_blockers([row([])]) == []


def test_prop_crossing_blocks():
    out = clipping_blockers([row([["phone", "finn_gloves", 12]])])
    assert out and "phone x finn_gloves" in out[0]


def test_lift_advice_alone_does_not_block():
    assert clipping_blockers([row([["phone", "clear of the hand after lifting along the palm normal (m)", 0.01]])]) == []


def test_small_garment_poke_is_a_hem_not_a_blocker():
    assert clipping_blockers([row([["finn_waders through finn_boots", "verts", CLIP_GARMENT_VERTS - 1]])]) == []


def test_large_garment_poke_blocks():
    out = clipping_blockers([row([["finn_knit through finn_jacket", "verts", 2541]])])
    assert out and "2541" in out[0]


def test_feet_off_the_floor_block():
    assert clipping_blockers([row([], feet="floating 2.0 cm")])
