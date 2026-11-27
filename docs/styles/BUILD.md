# Style module: BUILD (one object transforms, step by step, to solve a problem)

Optional. Use it for "why is X shaped like this?" or "what would it take to survive Y?" topics, where one hero
object changes in place, one fix at a time. It sits on top of the house Visual Blueprint (CLAUDE.md sections 1-11 and 13):
same honesty rules and polygon budget. It can be used whole, or you can take single building blocks from it
(any overlay, the weather, a caption style) into a normal episode.

Source: a study on 2026-11-20 of a second TikTok Caesar shared (vm.tiktok.com/ZN8mJ59bo, 50.2 s, 1080x1920, 30 fps),
from frames every 0.25 s, scene-cut detection at two thresholds, pixel colours and a word-timed Whisper transcript.
Private analysis copies stay on Caesar's PC in `D:\CounterPhysical\research\reference-tiktok-2\` (never commit or
re-publish them). This file describes technique only. We never copy its animal, models, script or shots; every
asset below is our own procedural code.

## 1. What the reference does (measured)

| Thing | Measured | What we take |
|---|---|---|
| Length / speech | 50.2 s, 179 words, about 215 words per minute | brisk narration, one idea per sentence |
| Structure | 13 problem-then-fix steps: "But X... so you Y." | the **problem, fix, new problem** chain |
| Voice | second person throughout ("so you grow...") | the viewer is the one building it |
| Hard cuts | 17 at threshold 0.3 (21 at 0.15), one every 2.9 s | a new angle for every step |
| On-screen change | about every 0.5-1 s: a caption word, a label, a meter moving | something always moves |
| Payoff | the last line names the finished thing over a wide hero shot | end on the complete object, ready to loop |
| Grade | overcast cold day: sky `#8390a4`-`#8b98ac`, snow `#c9d0d4`-`#d2d1dd` | lighting preset `blizzard` |

## 2. The script pattern

1. **Setup** (1 line): drop a familiar thing into a hostile situation.
2. **Problem** ("But..."): one concrete failure, shown happening (freezing, cracking, a meter dropping).
3. **Fix** ("So you..."): one change, shown as a transformation of the hero object.
4. Repeat 2-3 eight to twelve times. Each fix creates or reveals the next problem.
5. **Payoff**: "And that's why..." over the finished object. Keep it true: if a step is simplified, say so in the
   storyboard caveats, and don't present a guess as evolution or physics fact.

Writing rules: 6-15 words per sentence, second person, verbs of change (shrink, grow, curve, fold, harden).

## 3. Building blocks (all opt-in)

### 2D overlays: `renderer/overlays.js`
List them in the plan as `overlays: [...]`, each with `start`, `end` and `type`. `at: [x, y, z]` pins it to a
3D point (it follows the camera); `xy: [0..1, 0..1]` pins it to the screen.

| type | use | key fields |
|---|---|---|
| `callout` | small ALL-CAPS label with a thin leader line and arrowhead to a part | `at`, `text`, `dx`, `dy` |
| `pill` | rounded dark badge, warm-yellow outline, icon + bold word, springs in | `text`, `icon` (check, clock, snow, lock, warn, drop), `xy` |
| `gauge` | thermometer-style meter whose level and colour animate (heat, food, oxygen) | `at`/`xy`, `label`, `from`, `to`, `color0`, `color1` |
| `arrows` | four red arrows pointing in (shrink) or out (grow), pulsing | `at`, `mode`, `r` |
| `dim` | dimension bracket with a size label | `a`, `b`, `text` |
| `xmark` | red X inside a ring that draws itself ("blocked") | `at`, `r` |
| `ring` | thin white ring that draws itself around a part | `at`, `r` |
| `flash` | quick full-frame flash for a hard moment (a break, a cut on impact) | `color`, `peak` |
| `tint` | full-frame colour wash (night, cold, time passing) | `color`, `alpha` |

House limits still apply: at most one pill and one gauge on screen, labels never in the caption band, and the
number on a pill or gauge must be a real claim in `claims:` (docs/QA.md).

### 3D effects: `renderer/effects3d.js`
- `snow(world, {count, size, wind})`: falling snow that becomes sideways streaks as `wind` rises (blizzard).
- `freeze(obj, amount)`: blends an object's materials toward pale ice.
- `growTo(obj, from, to, u)`: grow or shrink with a small overshoot.
- `shards(world, {center, start, count})`: an object bursts into faceted pieces that fall under gravity.
- `xray(obj, opacity)`: turns a shell see-through, for cutaways of what's inside.

### Lighting: `renderer/world.js`
- `blizzard`: cold overcast snow day (soft light, short pale shadows, fog close in).
- `clear` (from the DUO module): crisp blue-sky day.

### Captions: `caption_style: build` in storyboard.yaml
One word at a time, ALL CAPS, Poppins ExtraBold, white with a dark outline, centred at 73 % height
(`factory/caption_engine.py`, `STYLES["build"]`).

## 4. Camera
- A new angle for every step (2-4 s), always moving slowly.
- Push in to a macro shot of the part that changes, then cut wide to show the whole object after the change.
- Micro-scale cutaways (inside a material, a cell, a crystal) are allowed when the step is about structure.

## 5. Sound
- A soft whoosh on cuts. A designed sfx for each transformation (crackle for freezing, a crunch for shattering,
  a rising tone while something grows). Narration stays on top.

## 6. Showcase render
`renderer/scenes/build3d.js` with `tools/build_demo_plan.py`: every block on one original red sphere in a snowfield.
Result: `counterphysical/style-tests/build-effects-demo-v1.mp4` in the project files.
