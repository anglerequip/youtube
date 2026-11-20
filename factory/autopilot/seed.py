"""Seed the ledger with every video made or planned before autopilot (run once; safe to re-run)."""
from __future__ import annotations

from .ledger import Ledger, Topic

PAST = [
    # (id, status, title, area, core claim, keywords)
    ("falling-slinky", "published", "Drop a Slinky and the Bottom Just... Floats", "waves",
     "a dropped slinky's bottom hangs still until the collapse wave reaches it", ["slinky", "tension wave", "free fall"]),
    ("other-lane-faster", "published", "The Other Lane Really Is Faster (Mostly)", "traffic",
     "the next lane seems faster because you spend more time being overtaken in slow traffic", ["traffic", "lane", "selection effect"]),
    ("spaghetti-two-pieces", "published", "Why Spaghetti Won't Snap in Two", "fracture",
     "dry spaghetti bent until it snaps breaks into three or more pieces because of flexural waves", ["spaghetti", "fracture", "flexural wave"]),
    ("chain-fountain", "published", "The Chain That Jumps Out of the Jar", "momentum",
     "a bead chain pouring out of a jar rises in an arch above the rim (chain fountain)", ["chain fountain", "momentum"]),
    ("head-ages-faster", "published", "Your Head Is Older Than Your Feet", "relativity",
     "your head ages faster than your feet because of gravitational time dilation", ["time dilation", "gravity"]),
    ("touchscreen-field", "published", "Your Phone Can't Feel You Press It", "electricity",
     "capacitive touchscreens sense your finger disturbing an electric field, not pressure", ["touchscreen", "capacitive", "electric field"]),
    ("why-ocean-blue", "published", "Why The Ocean Is Blue", "light",
     "water is intrinsically blue because it absorbs red light, not because it reflects the sky", ["ocean", "absorption", "colour"]),
    ("banana-radioactive", "published", "Your Banana Is Radioactive", "nuclear",
     "bananas are slightly radioactive because of potassium-40", ["banana", "potassium-40", "radioactive"]),
    ("crystal-caper", "published", "We Cooked Crystals and the Cops Showed Up", "chemistry",
     "rock candy crystals grow from a supersaturated sugar solution (comedy caper)", ["crystal", "supersaturation", "rock candy"]),
    ("cat-stare", "published", "Why Your Cat Stares While You Eat", "biology",
     "a cat staring while you eat is not judging you as selfish; the myth checked against behaviour research", ["cat", "myth", "behaviour"]),
    # Caesar's backlog and earlier picks: ideas, so they are not made twice by accident either
    ("never-touch", "idea", "You Never Really Touch Anything", "electromagnetism",
     "you never truly touch anything because electron repulsion stops atoms meeting", ["electron", "repulsion", "touch"]),
    ("sun-is-white", "idea", "The Sun Is Actually White", "light",
     "the sun is white; it looks yellow because the atmosphere scatters blue light", ["sun", "scattering", "colour"]),
    ("gps-relativity", "idea", "Your GPS Needs Einstein", "relativity",
     "GPS satellites must correct for relativity or positions drift by kilometres a day", ["gps", "relativity", "satellite"]),
    ("drain-coriolis-myth", "idea", "The Drain Swirl Myth", "rotation",
     "the swirl direction of a sink drain is not decided by the hemisphere (Coriolis myth)", ["drain", "coriolis", "myth"]),
    ("braess-paradox", "idea", "Adding a Road Makes Traffic Worse", "traffic",
     "adding a new road can make everyone's journey slower (Braess's paradox)", ["braess", "traffic", "road"]),
    ("toast-butter-side", "idea", "Toast Lands Butter-Side Down", "rotation",
     "toast falling off a table usually lands butter-side down because of table height and rotation", ["toast", "rotation", "table"]),
    ("pillar-exit-door", "idea", "A Pillar Makes Evacuation Faster", "crowds",
     "a pillar in front of an exit door can make a crowd leave faster", ["crowd", "exit", "pillar"]),
]


def seed(ledger: Ledger | None = None) -> int:
    led = ledger or Ledger()
    have = led.topics()
    n = 0
    for tid, status, title, area, claim, kw in PAST:
        if tid in have:
            continue
        led.add(Topic(id=tid, core_claim=claim, title=title, area=area, keywords=kw, status=status, slug=tid,
                      reason="seeded from videos made before autopilot"), force=True)
        n += 1
    return n


if __name__ == "__main__":
    print(f"added {seed()} topics")
