# Style module: HOST (one recurring character sells one thing, comedy first)

For AnglerMind ads and character-led Shorts. Sits on top of the house rules (CLAUDE.md, the polygon budget, Look v3,
the honesty rules and docs/BRAND.md). It replaces the calm diorama narrator with **one loud, likeable, recurring
host** who talks straight to the lens.

Source: a study on 2026-11-26 of nine character-led product ads Caesar shared (a stylised 3D host selling his own
product), measured from frames every 0.5 s, scene cuts, Whisper word timings, pixel colours and loudness. Private
analysis copies stay on Caesar's PC (`D:\CounterPhysical\research\reference-obc\`, `STYLE.md` there has every
number); never commit or re-publish them. This file is the *technique only*. We never copy that host, his look, his
sidekicks, his lines, his sets or his shots. Our host is our own (`renderer/characters.js` `host()`,
`tools/blender/host_v1.py`).

## 1. What makes the format work (measured, ranked)

| # | Thing | Measured in the references | Rule for us |
|---|---|---|---|
| 1 | One host, one silhouette | host on screen about 83 % of runtime, recognisable from one frame | host in 75 %+ of the runtime, same costume every video |
| 2 | Grandiose stakes for an ordinary thing | the whole joke: a small purchase treated like a crusade | our host treats "guessing" in fishing like an arch-enemy |
| 3 | Speech on frame 0 | first word at 0.0 s in 8 of 9; no logo, no title | first word within 0.3 s |
| 4 | A new striking set each video | 9 videos, 9 sets, each with an atmosphere layer | a new fishing location each time: dawn mist, rain, ice, dusk |
| 5 | Every number is shown | each number gets a numeral caption and an insert of the hand on it | same, with real numbers only |
| 6 | Early anchor | the "expensive enemy" is named by about 12 s (median) | name the problem by 6 s |
| 7 | Edit rhythm | average shot 3.2 s (median 3.0, quartiles 2.1 / 3.9), first cut at 1-3.6 s | ASL 2.5-3.5 s, no shot over 6 s |
| 8 | Comic beat | one comic turn, usually an excuse or a self-own; silent reaction cutaways | at least one comic beat per 15 s |
| 9 | Reassurance | 4 of 9 have a "you can't lose" line before the CTA | one honest reassurance line (free, no sign-up if true) |
| 10 | Fixed physical CTA | same CTA words every video, finger pointing down, video ends within 0.6 s | "Try it free at anglermind.com", point down, end |
| 11 | Plain captions | white, no box, no highlights, lowercase, 4-5 words per caption | see section 5 |

Engagement note: the skit-style references averaged about 1.7 % likes per view, the straight "deal" ones about 0.5 %.
Story and character carry the ad; the offer rides on them.

## 2. The host (principles; our design is `host()`)

- Realistic adult proportions, 6.5-7 heads, slightly heroic shoulders, **hands 10-15 % oversized** (hands do half the
  acting: presenting, pointing, counting).
- **One iconic eye accessory that hides the eyes** and throws a white specular glint (it reads as "eyes" at thumbnail
  size). Acting moves to the **mouth and brows**: wide shout on the key word, smug smirk, worried brows, big laugh.
- **Three value levels plus one warm/cool split** in the costume, so he reads in any lighting.
- One long flowing garment so motion reads (a coat or jacket hem).
- Game-engine PBR, soft subsurface on skin, no outlines, no toon ramp.
- Persona: confident, slightly grandiose expert, always on the viewer's side, never mean to the viewer.

Recurring gestures (use them as a vocabulary): hold the thing up beside the face toward the lens; present it with
both hands from a low angle; arms wide in triumph; hand on chin; raised palm "stop"; lean in close and conspiratorial;
POV hand tapping each item; **point down for the CTA**.

Supporting characters: rarely speak, mostly react in 1-3 s close-ups so the host's line lands. Ours are original
fishing-world creatures (a deadpan pike, a gull), never parodies of anyone else's characters.

## 3. World, light and look

- Warm key, cool fill (mean R-B about +30 in 7 of 9 references). Mid-dark overall (mean luma 75-120 of 255) with
  strong highlights (luma SD 43-67): low sun, glowing screens, light shafts.
- Medium saturation (0.34-0.48). Never neon.
- **Atmosphere in every shot**: mist, dust in light shafts, spray, rain, snow. Volumetric light is the signature.
- Shallow depth of field on close-ups and over-the-shoulder shots, deep on establishing wides (Look v3 does this).
- Lighting preset for our sets: `dawnmist` (low warm sun, cool blue-grey fill, ground fog).

## 4. Camera grammar

| Shot | Share in the references | Use |
|---|---|---|
| Medium / medium close-up, holding the thing | about 38 % | the pitch, direct address |
| Close-up / extreme close-up | about 26 % | the key word, a reaction |
| Wide / establishing, host full figure | about 21 % | a new place, triumph, scale jokes |
| Insert / POV (hand on the item, the phone screen) | about 14 % | every number, every feature |

Lens: about 28-40 mm on mediums (face and prop both big), longer on close-ups. Many low angles for swagger, a slight
Dutch tilt on comic close-ups. Slow push-ins and drifts, static on punchlines. Punch-ins are hard cuts to a tighter
shot, not digital zooms. One slow-motion moment per video at most.

Hook frame (0-2.5 s), one of three: (a) host MCU holding the thing beside his face, already talking; (b) a striking wide
of the new set with the host small and centred; (c) we join a conversation mid-line.

Vertical: compose natively in 9:16 (do not crop 4:3). Keep the host in the middle 60 % of the width and bring props
up in front of the chest or beside the face, not out at arm's length.

## 5. Captions (`caption_style: host`)

- Neo-grotesque sans, medium weight, white `#ffffff`, thin grey outline (about 2 px) plus a soft dark drop shadow, no box.
- Lowercase sentence text; capitals only for "I", names and numbers. No ALL CAPS, no colour highlights, no emoji.
- 3-6 words per caption (max 10), 1-2 lines, about 28 characters per line, about 1.2-1.5 s each, cut in and out on
  phrase boundaries, no pop or bounce.
- Cap height 2.7-4 % of the 9:16 frame height, centred at 60-66 % of the height.

## 6. Writing (the beat template)

1. **Hook** (0-3 s): a vow, a confession or a striking claim, spoken on frame 0.
2. **Enemy** (by 6 s): the angler's real problem (guessing, wasted trips, the wrong colour).
3. **Weapon**: the AnglerMind tool, shown on the phone in his hand.
4. **Proof**: real tool output on screen, one item per caption, a hand touching each one.
5. **Comic turn**: a self-own or a reaction cutaway.
6. **Reassurance**: one true line (it's free).
7. **CTA** (last 2-4 s): "Try it free at anglermind.com", pointing down. End within 0.6 s.

Pace: 170-230 wpm for a pitch, with at least two held pauses of 0.5 s for reactions. Short lines. Energetic,
grandiose, warm. Every claim and number is real and listed in `claims:` (docs/QA.md). No profanity, no edgy jokes,
no references to other people's characters, shows or memes. No em dashes in AnglerMind copy (docs/BRAND.md).

## 7. Side-by-side checklist (score 0/1 each; target 15 of 18)

1. First word within 0.3 s. 2. Host in frame 0, centred in the middle 60 % of the width. 3. Host recognisable from a
100 px tall thumbnail. 4. Host on screen 75 %+ of runtime. 5. First cut at 1.0-3.5 s. 6. ASL 2.5-3.5 s, no shot over
6 s unless planned. 7. Shot mix within ±10 points of medium 38 / close 26 / wide 21 / insert 14 %. 8. Warm key, cool
fill (mean R-B +15 to +60) unless the set is meant to be cold. 9. An atmosphere layer in every set. 10. The problem is
named by 6 s and the first number (if any) by 15 s. 11. Every number has a numeral caption and a visual. 12. Every
claim is true and in `claims:`. 13. A comic beat at least every 15 s. 14. One reassurance line before the CTA. 15. CTA
is the last line, same words, pointing down, ends within 0.6 s. 16. Captions match section 5. 17. 170-230 wpm with 2+
held pauses. 18. No borrowed characters, logos, catchphrases or scenes; brand-safe.
