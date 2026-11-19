# Counterphysical Shorts factory

Read `docs/ARCHITECTURE.md` first. This file is the guide for a Claude session writing new episodes.
**Every visual must follow the Visual Blueprint below.** It is Caesar's chosen art style.

## Writing a new episode

1. Pick a topic that is genuinely counterintuitive *and* simulatable with real physics or maths.
   Check `content/episodes/` so you don't repeat one. Never copy another channel's scripts,
   footage, branding or exact video concepts.
2. Research it. Put real, checkable sources and honest caveats in the storyboard. Never invent data
   or overstate a result to make it more dramatic.
3. Create `content/episodes/<slug>/storyboard.yaml` (copy the structure of `falling-slinky`):
   - 8-14 beats, 61-75 s total (hard rule: every video must be longer than 60 s; QC rejects anything shorter). Extend with real content, never filler. Beat 1 is the hook: a surprising claim in under 3 s.
   - Short spoken sentences; spell numbers the way they should be read.
   - `on_screen` for an occasional key phrase or equation, `sfx` (whoosh, thud, pop, tick, rise, ding).
   - Write for the voice (factory/voice_engine/expressive.py turns this into delivery, free):
     vary sentence length and keep it sounding like a person, not a summary; `*word*` stresses one key
     word (at most one or two per beat); `...` is a deliberate pause before a reveal; `!` only for real
     surprise; questions end in `?` (they get a longer pause). Captions drop the stars automatically.
4. Create `sim.py` with `class Sim(Scene)`. Sync to beats with `self.tl.start("<beat id>")`.
   Keep visuals between y=0.25 and y=0.90 of the frame (captions sit at about y=0.30).
   Add `self_checks()` comparing the simulation to theory, and `sfx_events()` for physical moments.
5. Fill in the single source of truth (docs/QA.md): `claims:` for every number spoken or shown (value or
   `sim:` from plan facts, scope, evidence), `absolute_ok:` for absolute words, `entities:` with risk
   category and visual contract, `hero:`. Export `facts` (and `events` + `observe()`) from plan.py and
   `probes()` from the scene.
6. Run `python -m factory produce <slug> --previews`. The pre-render gate blocks before the long render
   on any blocker; read `out/<slug>/qa/report.md` and fix the cause, not the symptom. After the render,
   an independent reviewer (fresh context, never the generator) writes `out/<slug>/qa/review/critique.json`;
   then `python -m factory qa-gate <slug>`. Never write or edit a critique yourself.
   Fix anything QC flags. Commit the episode folder only (never `out/`, `data/`, `.env`).

## Rules

- Nothing is ever published without the human's approval in Telegram. Do not add code paths that
  upload from the production workflow.
- Secrets only in `.env` / environment variables.
- Run `python -m pytest -q` before committing.


---

# VISUAL BLUEPRINT (the house art style)

Source: frame-by-frame study of the reference Short youtube.com/shorts/jBTahEPAr-I (60.6 s,
608x1080 source), sampled every 2.5-3 s on 2026-11-19, with pixel colours read from the frames.
This describes the *style only*. We build every asset ourselves (procedural geometry, our own
colours tuned from these measurements, our own label and caption designs, our own branding).
Never reuse their footage, models, logo, wording or exact shots.

## 1. Overall look in one sentence
A **stylised low-poly 3D miniature world**, rendered like a real-time game engine (Blender Eevee /
three.js look): soft, warm, slightly desaturated daylight, hard sun shadows, gentle atmospheric haze,
and simple chunky vehicles that read instantly at phone size. It feels like a calm, tidy toy-model
diorama filmed by a drone, not a diagram and not photorealism.

## 2. Rendering
- Real 3D with perspective cameras. Flat-shaded or very lightly smoothed low-poly geometry.
- One strong directional "sun" light + soft sky fill. **Hard-edged cast shadows** (cars, trees,
  posts) that are long and diagonal (low sun, roughly 25-35 deg elevation).
- Subtle ambient occlusion where objects meet the ground (cars sit "in" the world).
- **Bloom on emissive lights only** (brake lights, headlights, street lamps). Brake lights spill a red
  glow onto the asphalt behind the car. This glow is the main storytelling signal.
- Mild filmic tone mapping (ACES/AgX-like): no pure white, no pure black, soft highlight roll-off.
- Distance haze / fog that fades to a pale sky colour at the horizon (strong on long highway shots).
- Slight grain/texture on grass; everything else is clean, untextured colour.

## 3. Palette
Ground, road, sky, night and label values were read from frame pixels. Tree and car colours are
estimated by eye from the frames (marked *est.*), so tune them on our own renders.
| Element | Day | Notes |
|---|---|---|
| Grass, main | `#5a5725` `#64662d` `#676b32` | olive / khaki green, mottled with darker `#1c2912` patches |
| Grass, sunlit highway verges | `#848a4c` `#8c9355` | lighter, yellower |
| Asphalt, overhead shots | `#352b22` `#2d241b` `#495254` | **warm** very dark brown-grey, not blue-black |
| Asphalt, highway daylight | `#5a544a` `#534d44` | warm mid grey |
| Kerbs / shoulders / concrete | `#a89684` `#beb7a4` `#c7c7c7` | sandy light grey |
| Road markings | near-white `#e8e6df` | solid edge lines, dashed lane lines |
| Sky (day) | `#c7c8c7` → `#b8bdc3` | hazy pale grey-blue, almost no saturation |
| Low-poly trees (*est.*) | lime `#a7b84a`, olive `#7d8c35`, dark conifer `#3f5a2a` | faceted spheres and cones |
| Night base | `#121622` `#0d131a` `#080b16` | deep navy-black; grass `#1b271b` |
| Sunset highway | asphalt `#0d0e13`, warm shadow bands `#291c1b`, low orange sun | long tree-shadow stripes across lanes |
| Brake light / alert red | `#c92a2e` (glow `#ff3b30` at bloom) | used for "braking" and for label text |
| Label card | off-white `#e5e2d6` | |

Car body colours (*est.*) are muted pastels: cream `#d9c7a0`, off-white `#e6e3dc`, silver `#b9bdc2`,
powder blue `#8fa6c8`, lavender `#a99bc4`, butter yellow `#e2c45a`, teal `#2e8f86`, sand `#c9a77c`.
Never neon, never fully saturated. Mix colours randomly but evenly.

## 4. Objects
- **Cars:** chunky 1990s-style boxy hatchbacks, estates and sedans (one or two box bodies, a cabin box,
  dark tinted windows `#2b3038`, four dark wheels, rectangular red tail lights, small light plate).
  Some have roof racks. About 1.5-2 car lengths apart at rest. Same scale everywhere.
- **Roads:** clean asphalt, white edge lines, light concrete shoulder/kerb strip on both sides.
  Ring roads are perfect circles; highways are dead straight to a vanishing point.
- **Scenery:** faceted low-poly round trees and cone conifers, scattered, casting long shadows;
  wooden fence posts along highways; occasional tiny props (traffic cone, small white tent/shed,
  street lamps at night). Rolling low hills on the horizon. Sparse: scenery frames the action, never
  competes with it.

## 5. Camera
Five recurring shots, cut between every **2.5-4 s** (hard cuts, no wipes):
1. **Chase cam** low behind a car (about 1.5 m high, 6 m back), looking along the road. Used for the
   opening frame: motion and a car filling the lower third straight away.
2. **Overhead 3/4 aerial**, tilted 50-70 deg down, slowly drifting/orbiting.
3. **Straight top-down** "map" view of the whole system (e.g. the whole circuit), slowly rotating.
4. **Highway centreline** shot: camera above the lanes looking straight down the road, symmetric,
   strong vanishing point, cars receding into haze. Used for the causal chain beats.
5. **Big-picture pull-out**: very high, many lanes / long queue, shows scale.
Every shot moves a little: slow dolly, drift or orbit, eased. No shaky cam, no fast zooms.
Subject stays inside the vertical middle 60% of frame; captions own the band at about 72-75% height.

## 6. Captions (burned in)
- 1-3 words at a time, synced to the voice, **centred at about 73% of frame height**
  (about 27% up from the bottom).
- **White, no box, soft dark drop shadow** (blurred, low-opacity black), not a thick outline.
- Font: clean geometric sans, semi-bold/bold, sentence case as spoken (mostly lowercase; capital only
  at a sentence start, e.g. "So when a jam"). Cap height about 3% of frame height.
- No colour highlighting, no emoji, no pop-in bounce. Calm and readable.

## 7. Labels and annotations (sparingly)
- Small **off-white rounded card** with a soft shadow, red bold text for the key number, a smaller red
  word beneath. Example layout: big line "≈ 20 km/h", small line "backward".
- Appears near the top third, close to the thing it describes, only for the one number that matters.
- Ground-level highlight: a thin white ring/ellipse drawn on the road around the car in question.
- No arrows-everywhere, no HUD clutter, no graphs on top of the 3D world.

## 8. Transitions and pacing
- Hard cuts between camera angles; each new beat of narration usually gets a new angle.
- Time of day can change between scenes for variety (day → night → sunset), same world.
- Opening frame is already in motion (no title card, no logo sting). Ending loops visually.

## 9. Mood
Calm, curious, quietly cinematic. A clean model world where one simple rule produces a surprising
result. Warm daylight, muted colours, soft haze; the only saturated thing on screen is usually the red
that signals the phenomenon.

## 10. Our branding inside this style
- Small "COUNTERPHYSICAL" wordmark is optional and must stay out of the caption band.
- Our label cards may use our accent colours, but keep the off-white card + one strong colour rule.
