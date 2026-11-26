# HOST render rules (every character-led video, Finn and Nils Brack alike)

Source: the 2026-11-26 audit of the rough Finn cut (`finn-lure-finder`) against three reference character ads Caesar
picked, measured frame by frame. The full audit (with the reference frames) is private research on Caesar's PC
(`D:\CounterPhysical\research\reference-obc\AUDIT_finn_vs_reference.md`); this file keeps only the rules. Technique
only: our characters, sets and shots stay our own.

These sit on top of `docs/styles/HOST.md` (format, writing, captions) and CLAUDE.md. Where they disagree, this file
wins for anything rendered in Blender.

## 0. The top rule: stylised and blocky, never photoreal (Caesar, 2026-11-26)

"My videos are trying to be realistic, meanwhile the reference has a nice high-poly but still blocky visual."
Every character, prop and set is **stylised, with chunky, faceted, planar forms carrying dense detail**: high polygon
counts spent on crisp planes, bevels, folds and sculpted shapes, not on smoothing toward realism. Big simple masses,
readable planes where light turns (brow, cheekbone, jaw, nose wedge, garment panels, boot toes), exaggerated hands
and features, painted surface detail at a scale the phone can show. **Never photoreal:** no realistic body bases
(MakeHuman/MPFB), no scanned or photo textures as the look, no strand hair, no realistic skin pores, no
anatomy-correct proportions for their own sake. When a choice is between "more real" and "more designed", pick
designed. This rule outranks everything below.

## 1. Build the character for the camera, not for anatomy

1. **Stylised sculpted masses, not a realistic body base.** The rough cut used a MakeHuman (MPFB) realistic body with
   fitted CC0 clothes. Under a phone-size picture that reads as a waxy mannequin: realistic proportions, no designed
   silhouette, no shape language. The references are designed game characters: simple big shapes, a strong silhouette,
   exaggerated hands and features. Nils is built that way (`tools/blender/lake_committee/nils_build.py`); no new
   character starts from MPFB.
2. **No strand/particle hair on anything the camera gets close to.** Finn's 14,000-guide particle beard rendered as a
   sponge at 1080x1920 in Eevee. Hair, beards, brows and sideburns are sculpted meshes with painted strand direction
   (the references do the same). A shell texture on a coarse face mesh does not replace sculpting (tried in
   `charkit.sculpted_beard`; it read as corduroy skin).
3. **Detail at the scale the phone shows.** Real-scale fabric weave (1.4 mm) and skin pores are invisible on a phone,
   so the rough cut's surfaces read as flat clay. Paint the big things: seam and fold cavities, wear on edges and
   contact points, value breakup over 10-30 cm, warm/cool shifts. `charkit.macro_paint` adds cavity + breakup to any
   material; a sculpted character bakes the same into its base colour (Nils brief, "Generate the textures").
4. **Clip-resistant design** (staging study): chunky hands or mitts, garments that hang straight, gestures that open
   outward from the body, no thin fingers wrapped around thin props.

## 2. Layers and contacts: no clipping reaches a render

1. **Every inner garment layer loses what the outer layer covers.** `charkit.cull_covered(rig, [(outer, inner), ...],
   body)` masks inner vertices covered by the outer layer at rest (an inverted MASK straight after the armature, eroded
   one ring so no gap opens at the edge). On Finn it removed 4,560 knit, 4,032 wader and 994 turtleneck vertices, which
   is where the 2,000-3,500-vertex poke-throughs in every keyframe of the rough cut came from.
2. **The clipping check is a gate, not a report.** `factory/production.py` now runs `--check-clipping` before every
   full Blender render and refuses to render on a prop crossing the character, 200+ garment vertices through an outer
   layer, or feet off the floor (`clipping_blockers`). The rough cut had findings in 54 of 54 keyframes and rendered
   anyway. `allow_clipping: true` in a storyboard overrides it for a throwaway test only.
3. Staging rules from `research/reference-skit-staging-study.md` stay in force: cut around contact, split grips on a
   shared prop, two-shots stacked in depth, hand + prop actions as posed inserts, hands entering from the frame edge.

## 3. Light and grade (measured targets)

| | rough cut | references (3 videos) | rule |
|---|---|---|---|
| mean luma (top 70 % of frame) | 144 | 75-120 | 80-120 |
| luma SD (contrast) | 51 | 43-66 | 50+ |
| saturation | 0.26 | 0.34-0.48 | 0.34+ |
| warmth R-B | +31 | -19 to +44 | per set |

- `charkit.grade(scene, 'host')`: AgX Punchy, exposure -1.05.
- Key:fill about 5:1 (the rough cut was nearer 3:1, so faces went flat), a strong rim from behind, the background
  darker than the subject. Haze is a layer in the distance, never a wash over the subject.
- One atmosphere element per shot that moves (mist, dust in light, spray, particles).

## 4. Camera

1. **Handheld-prop inserts: 40 mm or longer, camera 0.24 m or more from the prop.** The rough cut shot the phone at
   30-32 mm from 12-17 cm away, which ballooned the fingers into the frame. If the screen faces the character, shoot
   over the shoulder; if it faces the lens, hold the phone beside the face and let the face go soft behind it
   (the best-looking new frames).
2. **Inserts are at most 14 % of the runtime and at most 2.5 s each.** The rough cut spent about 36 % on screens and
   trays (13 s of 36 s). Cut back to the character's reaction between screens.
3. Character on screen 75 %+ of the runtime (rough cut: about 60 %).

## 5. Sound and finish

1. Always finish through `factory/production.py` (`sound_design.build_mix`): music bed, ambience, SFX, mastered to
   about -15 LUFS. The rough cut was muxed by hand from the bare voice: -19.6 LUFS, no music, 0.4-1.0 s of dead air
   between lines. The references run a continuous bed at about -12 LUFS.
2. Close the gaps between per-beat voice clips to 0.15-0.3 s unless the gap is a planned reaction beat.

## 6. Animation (not fixed yet; Nils stage 1+)

The rough cut animates by blending between whole-body pose presets over 0.35 s with a jaw-only mouth. That is why
it feels stiff next to the references, whose hosts act with brows, mouth shapes, head tilts and overlapping hands.
Nils needs: visemes (at least 6 mouth shapes), brow poses, a head-and-shoulders "talk" layer that never stops, and
pose transitions with anticipation and overshoot.
