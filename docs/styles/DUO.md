# Style module: DUO (two presenters playing off each other)

Optional. Use it when a topic has a natural "wait, what?" moment that a person would argue with. It sits on top of
the house Visual Blueprint (CLAUDE.md sections 1-11): same diorama world, same polygon budget, same honesty rules.
Only the pacing, the camera grammar around the characters, the captions and the writing change.

Source: a study on 2026-11-20 of a TikTok Caesar shared (vm.tiktok.com/ZN8m14TmC, 117.7 s, 1080x1920, 30 fps), read
from frames every 0.5 s, scene-cut detection, pixel colours and a Whisper transcript. Private analysis copies stay on
Caesar's PC in `D:\CounterPhysical\research\reference-tiktok-duo\` (never commit or re-publish them).
This file describes the *dynamic and style only*. We never copy its characters, its mascot, its script, its screens
or its shots. Our duo is our own `man()` and `woman()` from `renderer/characters.js`.

## 1. What makes the reference work (measured)

| Thing | Measured | What we take |
|---|---|---|
| Length / speech | 117.7 s, about 296 words, about 155 words per minute | slower than our solo narration (about 200 wpm): leave room for reactions |
| Turns | 48 spoken lines, so a speaker change about every 2.4 s; most lines 1-6 words | short lines, alternate fast |
| Hard cuts | about 15 distinct cuts (threshold 0.3), so about one every 8 s | cuts are not the engine |
| Something changes on screen | about every 2-3 s: punch-in to a face, a card arrives, a word is highlighted, a cutaway | change the picture on every turn, even inside one shot |
| Cutaways | a visual metaphor for the one key idea (a ladder with its bottom rungs gone, a "closed" barrier) | one metaphor scene per video, built from our props |
| Data cards | a floating window card holds the one statistic, builds up step by step (bar, then label, then number) | our off-white label card, building in 2-3 steps |
| Ending | the expert character says one short line straight to camera | the explainer gets the last sincere line, the skeptic gets the last joke |

## 2. The roles (the core of the dynamic)

Two fixed roles, kept for the whole channel so viewers learn them:

- **The skeptic** asks the viewer's question out loud, states the wrong intuition with total confidence, and
  reacts. Short, punchy lines. Allowed one deadpan look into the camera per video.
- **The explainer** is calm and dry. Never mocks; answers in one clean sentence, then the next. Uses the physics.

Default casting: the woman is the skeptic, the man is the explainer. Swap them in some episodes so neither looks
"always wrong". Never make the skeptic stupid: she's right about everyday experience, and the physics is the twist.

The beat pattern (repeat 2-4 times per video):

1. **Claim** (skeptic, 1 line, confident): "Heavy ball lands first. Obviously."
2. **Challenge** (explainer, 1-3 words): "Drop them."
3. **Proof** (no dialogue or one word; the simulation shows it, slow motion if fast).
4. **Reaction** (skeptic, punch-in close-up): "Okay... that's rigged."
5. **Reason** (explainer, 2-3 short sentences, one card with the number).
6. **Button** (skeptic, a joke that shows she half-learned it): "Fine. I'm getting a bigger ball."

Writing rules on top of CLAUDE.md "Write for the voice":
- No line over 12 words. Most lines 2-7 words.
- Every explainer reason must be true and checkable (same claims/sources rules as solo episodes).
- Jokes come from character (stubbornness, a small personal story), never from mocking real people or groups.
- A beat ends on the skeptic about half the time: it's what makes people rewatch.

## 3. Camera grammar for two people

| Shot | When | Framing |
|---|---|---|
| Two-shot | claims, the button | both full figure, camera 4-4.5 m back, slow push in |
| Punch-in close-up | every reaction, short challenges | head and shoulders, camera 1-1.7 m away, slight push |
| Proof shot | the physics moment | low or 3/4 angle on the phenomenon, slow motion with the badge |
| Overhead 3/4 | the reason, with the card | slow orbit 15-40 deg over both people and the result |

- Cut on the speaker change; hold no shot longer than about 4 s when two people are talking.
- The listener reacts (head turns to the speaker, small tilt) while the other talks. `duo3d.js` shows how: heads
  turn with `headYaw`, reactions use `headTilt`, mouths only move on that speaker's lines.
- The house rules still apply: every shot moves a little, no shaky cam, subject in the middle 60 % of frame.

## 4. Captions (DUO variant)

The reference uses big rounded bold words, white with a thick dark outline, one word highlighted. Our version:
- 1-3 words, Poppins ExtraBold, cap height about 4 % of frame height (bigger than the solo 3 %).
- White fill, dark outline (`#15161a`, about 13 % of font size). No box.
- **One highlighted word per chunk, coloured by speaker**: skeptic amber `#ffb547`, explainer sky blue `#8ecbff`.
  This tells the viewer who is talking without names on screen. It's the one deliberate exception to the
  "no colour highlighting" rule in Blueprint section 6, and only in DUO episodes.
- Centred at about 66 % of frame height (below the faces, over the bodies).

## 5. Look

- Lighting preset `clear` in `renderer/world.js`: deeper blue sky overhead (reference sky measured `#3160a1` at the
  top of frame), less haze, a rim light for separation on close shots. Opt-in per shot (`"lighting": "clear"`).
- Keep the house palette for everything else. The red `#c92a2e` stays the phenomenon colour (the heavy ball).

## 6. Sound

- Each line is its own ElevenLabs take (presenter voices: man `3iY0r3RaYmOh6WfIwMIH` ("Matt", Caesar, 2026-11-21; replaced `zYcjlYFOd3taleS0gkk3`), woman `vChnJZ1Cu89g2XXumPfT` ("Lara", Caesar, 2026-11-21; replaced `0ggs85h7hrWz8ExXnsBc`)),
  placed with 0.1-0.3 s gaps; leave a longer gap before a reaction line.
- A soft whoosh on each hard cut, a real-sounding sfx for the physical moment (thud on landing).

## 7. Test render

`renderer/scenes/duo3d.js` is the reference implementation (not an episode): two-ball drop, 22 s, 7 shots.
Result for Caesar: `counterphysical/style-tests/duo-style-test-v1.mp4` in the project files.
