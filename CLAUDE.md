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
   - 5-14 beats. Beat 1 is the hook: a surprising claim in under 3 s.
   - Length follows the story (Caesar, 2026-11-19): typically 18-45 s, up to 60 s only when the story earns it.
     Never pad, recap or stretch to hit a length. QC allows 15-60 s (`MIN_SECONDS`, `MAX_SECONDS`).
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
   independent reviewers (fresh context, never the generator) write `out/<slug>/qa/review/critique.json` and `critique_2.json` (two picture reviewers, averaged) and `out/<slug>/qa/review_audio/critique_audio.json` (sound);
   then `python -m factory qa-gate <slug>`. Never write or edit a critique yourself.
   At most two review rounds per video (Caesar): after round 2 the verdict is `deliver`, and the video goes to
   Caesar with its score and the reviewers' notes, whatever it scored. Caesar decides; don't start round 3.
   Fix anything QC flags. Commit the episode folder only (never `out/`, `data/`, `.env`).

## Rules

- Nothing is ever published without the human's approval in Telegram. Do not add code paths that
  upload from the production workflow.
- Secrets only in `.env` / environment variables.
- Run `python -m pytest -q` before committing.

## Voices (Caesar, 2026-11-20)

- **Narrator** (solo episodes): ElevenLabs `TWutjvRaJqAX89preB4e` (`TTS_PROVIDER=elevenlabs`, `ELEVENLABS_VOICE_ID`).
  It replaces Kokoro `af_bella`, which stays as the free fallback (`TTS_PROVIDER=kokoro`).
- **Presenters** (two-character DUO episodes, `docs/styles/DUO.md`): man `3iY0r3RaYmOh6WfIwMIH` ("Matt", Caesar, 2026-11-21), woman `vChnJZ1Cu89g2XXumPfT` ("Lara", Caesar, 2026-11-21)
  (`ELEVENLABS_VOICE_MAN`, `ELEVENLABS_VOICE_WOMAN`).
- Don't re-voice an episode that is already published or scheduled.


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
- Real 3D with perspective cameras. Flat-shaded or very lightly smoothed geometry, at the **higher
  polygon budget in section 11** (Caesar, 2026-11-20): the faceted look stays, but facets are fine, not chunky.
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

## 11. Polygon budget (Caesar, 2026-11-20: "increase the poly in the videos")
Every new or edited model uses at least these segment counts. Prefer more on anything the camera gets close to.
| Geometry | Hero / close-up (presenters, the phenomenon object) | Background props (trees, cars, fences) |
|---|---|---|
| Sphere (width x height segments) | 48 x 36 or more | 24 x 16 or more |
| Cylinder / capsule radial segments | 24 or more (capsule cap segments 6) | 16 or more |
| Icosahedron detail (faceted crowns, hair locks) | 2 | 1 |
| Torus (tube x radial) | 12 x 32 | 8 x 20 |
| Lathe (segments x profile points) | 24 x 24 | 16 x 12 |
- Props and scenery may stay flat-shaded (stylised diorama). Presenters and other close-up characters are smooth-shaded
  high-poly: continuous lathe/tube bodies (40+ radial segments), heads 72 x 54, hair and beards built from tapered strands.
- Presenters come from `renderer/characters.js` (`man()` = the wizard, `woman()` = the young woman), already at this budget. Use them in place of
  the old wooden toy figure. They are Blender models: v7 (default, 2026-11-21) is built by `tools/blender/presenters_v7.py`
  (playful wizard, stylish art-student woman, about 3x the triangles of v6) and exported to
  `assets/characters/{wizard,woman}.glb`, run with the pip `bpy` module; the v6 pair (`tools/blender/presenters.py`) stays in
  `assets/characters/v6/` and a plan can ask for it with `"presenters": "v6"`; `renderer/boot.js` preloads them, so scene `build()` may stay
  synchronous and just call `man()`/`woman()`. Pose API: `p.pose({talk, blink, wave, point, headYaw, headPitch, headTilt, walk, t})`.
  Edit the Blender script and re-export rather than editing the GLBs. They are original designs: never restyle them, or any other model, to look like an
  existing character, celebrity or actor.
- Check render time after raising detail: a full 3D render must still finish in a reasonable time on Caesar's PC.


## 12. Optional style modules (Caesar, 2026-11-20)
Two extra looks studied from TikToks Caesar shared. Use either one whole when the topic fits, or borrow single blocks
(an overlay, the weather, a caption style) into a normal episode. Both sit on top of sections 1-11 and the honesty rules.
- **DUO** (`docs/styles/DUO.md`): our two presenters as skeptic + explainer, fast alternating short lines, punch-in
  reaction close-ups, speaker-coloured captions (`caption_style: duo`, beat field `speaker: man|woman`), lighting `clear`.
- **BUILD** (`docs/styles/BUILD.md`): one hero object transforms step by step ("But X... so you Y"), callout labels,
  pill badges, gauges, shrink/grow arrows, dimension brackets, snow/blizzard, freeze and shatter, one-word ALL-CAPS
  captions (`caption_style: build`), lighting `blizzard`.
- Building blocks: `renderer/overlays.js` (2D, plan `overlays:`), `renderer/effects3d.js` (3D), presets in `renderer/world.js`.
- Copy techniques only. Never copy a reference's characters, creatures, models, scripts, screens or exact shots.

## Autopilot efficiency (Caesar, 2026-11-20, via the project coordinator)

These rules keep the hands-free pipeline cheap. They don't override the rules above.

1. **Reusable scene sets.** Build a small library (bedroom, street/traffic, kitchen, lab, outdoors) and
   have each new episode swap props and camera rather than model from scratch. A new set is added only
   when no existing one fits.
2. **One AI review round by default.** A second round runs only if round one scores under 3.0. The
   two-round maximum still applies, and after round two the verdict is `deliver`.
3. **Model per step.** Use the strongest model for scripts, fact checks and scene building. Use a
   cheaper model (Sonnet or Haiku) for routine work: packaging, topic-ledger checks, QA summaries.
4. **Fewer chat messages.** Post to the project chat only for a result, a blocker or a question that
   needs Caesar. Routine progress goes on the checklist.

## YouTube packaging (audit 2026-11-21)

Evidence: our first 11 Shorts (public counts 21 Nov). Like ratio was best on animal "how/why" topics with
slow motion (falling cat 3.5%, dog drinking 2.2%, cat stare 2.0%) and worst on gadget facts (touchscreen 0.6%).
Four Shorts made public within 7 h on 20 Nov (two in the same minute) got almost no views; the next three,
4-5 h apart, each reached 700-1,100. Sources: YouTube Help "Disclosing use of altered or synthetic content"
(answer 14328491), vidIQ "How does the YouTube Shorts algorithm work in 2026".

- **Spacing:** the cloud job (`factory/autopilot/cloud_post.py`) moves any publish time that is within 4 h of
  another Short on the channel. Plan at most 2-3 Shorts a day while the channel is new.
- **Title:** about 40-60 characters, the plain thing people search for plus the surprise ("Why Your Cat
  Stares While You Eat"). It must be true to the video; no bait the video doesn't pay off.
- **Description:** first line restates the hook as a question, then the answer in one or two sentences,
  sources, the how-it's-made line, the tagline, then 3-5 topical hashtags. More than 15 hashtags and YouTube
  ignores all of them (the job trims to 5). Tags are minor; the job dedupes them and keeps them under 500 chars.
- **Settings:** category 28 (Science & Technology), not made for kids, language en. Keep
  `contains_synthetic_media: true` because the voices are AI; YouTube says the label alone does not limit reach.
- **Comments:** the last beat may end on one specific question a viewer can answer in a word or two, drawn
  from the video ("Would you have guessed the dog or the cat?"). Never "like and subscribe". It counts inside
  the normal beat budget, not as extra length.
- **Loop:** the final shot and line should lead back into the hook frame so a replay feels seamless.
- **Playlists:** the job adds every Short to a series playlist picked from its tags (`tagline.playlist`), or
  `playlist` in the package.
- **Studio only (no API):** the Shorts "related video" link and pinning a comment. Do these in Studio when a
  signed-in browser is available; link each Short to the best-performing Short in the same series.
