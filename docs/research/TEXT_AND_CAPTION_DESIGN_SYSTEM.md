# Text and caption design system

Counterphysical research lab, v1, 2026-11-19. Builds on R2 (`RESEARCH_REPORT_02_ATTENTION_AND_COGNITION.md`),
the hook and script specs, and the Visual Blueprint (`CLAUDE.md`, sections 6-7), which sets the
caption look. This document adds the *rules for when, how much and where*, and flags the few places
where the evidence suggests testing something different.

## 1. Evidence summary

| Question | What we know | Tier |
|---|---|---|
| Can viewers read captions and still watch? | Yes, up to at least 20 characters/s with no comprehension loss, but captions took ~40-45% of viewing time even when the audio was understood (R2-F15, Szarkowska & Gerber-Morón 2018) | B |
| Does on-screen text that repeats narration help? | Over complex visuals, full redundant text often hurts learning; short keyword text and captions for muted/L2/hard-of-hearing viewers help (R2-F16) | C (conflicting) |
| Do highlighting and labels help? | Signalling (labels, highlights pointing at the relevant part) helps learning, moderately (R2-F14) | C |
| What share of Shorts viewers watch muted? | Unknown. No YouTube figure exists; circulating figures are old Facebook-era claims and are not used | — |
| Does the reference Short use captions? | Yes: 1-3 words, white bold sans, soft shadow, mid-frame; they covered the braking car at 16 s, and its single label card ("≈ 20 km/h backward") was its clearest moment (channel review) | D |

Conclusion: keep captions on (accessibility, muted viewing), keep them small in word count and out of
the way, put the numbers that matter on deliberate label cards attached to the simulation, and never
let text compete with the reveal.

## 2. Text hierarchy

Five text roles, never given equal emphasis. Positions are fractions of frame height measured **from
the top** (0 = top edge, 1 = bottom edge) on the 1080 × 1920 frame.

| Level | Role | Default | Position | Size (cap height, % of frame height) | Max words | Dwell |
|---|---|---|---|---|---|---|
| 1 | Hook headline | **off** (Blueprint: no title card); enabled only for Experiment T1 | 0.12-0.20 | 3.6% | 6 | visible by 0.2 s, gone by 3.5 s |
| 2 | Spoken captions | on | centred at 0.73 (Blueprint), band 0.69-0.77 | 3.0% (Blueprint) | 3 per chunk | synced to voice (section 4) |
| 3 | Diagram labels | as needed | attached to the object, offset ≥ 1 object height | 2.0% | 3 | while the object is relevant, ≥ 1.5 s |
| 4 | Scientific measurement card | for the one number that matters per beat | top third, 0.10-0.33, near its object (Blueprint section 7) | big line 3.6%, small line 2.2% | big line ≤ 3 tokens ("≈ 20 km/h"), small line ≤ 2 words | ≥ max(2.0 s, 1.0 s + 0.3 s × words) |
| 5 | Final takeaway | **off** by default (the spoken takeaway + caption is enough) | 0.15-0.30 | 3.0% | 7 | ≥ 2.5 s, through the final hold |

Rules:

- **TX-1** At most two text roles visible at once, one of which may be captions. (Tier E, from R2-F16 and F10: text adds complexity.)
- **TX-2** At most 9 words on screen at any moment, counting all roles. (Tier E.)
- **TX-3** At most one measurement card visible at a time. (Blueprint section 7, R2-F14.)
- **TX-4** Every number spoken in a reveal or "why" beat that the viewer must remember gets a measurement card *or* is visible as a diagram label for ≥ 2 s. Numbers that are only colour (e.g., "twenty-two cars" in a hook) don't need one. (C, signalling; D, reference Short.)
- **TX-5** Formulas and calculations are never left to captions. If an equation is shown, it is a level-4 card built deliberately, with ≤ 7 symbols, dwell ≥ 3 s, and the narration reads it in words. (Brief Part IX.)

## 3. Placement and safe areas

The Shorts player overlays the bottom of the frame (title, channel name, music, description) and the
right edge (like, dislike, comment, share, remix buttons). YouTube does not publish exact safe-area
coordinates for Shorts; widely used creator templates keep the bottom ~20% and the right ~15% free of
essential content (Tier D). Verify with a phone screenshot of our first published Short and update.

| Zone (from top) | Use |
|---|---|
| 0.00-0.08 | Nothing essential (status bar, search/back icons) |
| 0.08-0.35 | Hook headline, measurement cards, takeaway |
| 0.20-0.66 | **Focal action zone**: the focal object and its motion must stay here (see conflict note) |
| 0.69-0.77 | Caption band (Blueprint) |
| 0.80-1.00 | Nothing essential (title and channel overlay) |
| Right 0.85-1.00 of width, from 0.45 down | Nothing essential (action buttons) |

- **TX-6** Caption band and the focal object's bounding box must not overlap at any frame. QC checks per frame from the renderer's focal-object box (render metadata). (C/D: reference Short's captions covered the braking car.)
- **TX-7** Diagram labels and cards must not overlap the focal object, the caption band or the right-edge button zone.
- **TX-8** Horizontal text width ≤ 80% of frame width, centred (captions) or anchored to their object (labels).

**Conflict with the Blueprint, flagged:** Blueprint section 5 keeps the subject "inside the vertical
middle 60%" (0.20-0.80) while captions sit at 0.73, inside that range. Both can hold if the focal
object stays above 0.66. Proposal: framing rule "focal object in 0.20-0.66", with secondary scenery
allowed behind the caption band (the soft shadow keeps captions readable over the low-contrast world).

## 4. Caption timing

Captions come from the narration text the writer wrote (the storyboard), **not** from the
pronunciation-normalised text sent to the voice. So the caption shows "20 km/h" where the voice says
"twenty kilometres per hour", and technical terms keep their correct spelling (Brief: preserve terms,
numbers and units). The engineering thread's `factory/narration/pronounce.py` output must only feed TTS.

| ID | Rule | Default | Tier |
|---|---|---|---|
| CP-1 | Chunk size | 1-3 words, ≤ 16 characters; never split a number from its unit, or "not" from its verb | Blueprint; E |
| CP-2 | Chunk breaks prefer phrase boundaries (after punctuation, before conjunctions/prepositions) over a fixed count | — | E (readability) |
| CP-3 | Onset | chunk appears at the onset of its first word, tolerance −0.10 s to +0.05 s | E (captions slightly ahead of speech read naturally; late captions feel broken) |
| CP-4 | Minimum display | 0.6 s; if speech is faster, merge chunks rather than flash | B/E (R2-F15) |
| CP-5 | Maximum rate | 17 characters/s averaged over any 3 s window | B (R2-F15: 12-20 cps tested without loss) |
| CP-6 | Gaps | no caption shown during pauses > 0.4 s; caption clears at word end + 0.15 s | E |
| CP-7 | Timing accuracy | onset error ≤ 80 ms vs voice | E; word timings from per-beat synthesis or forced alignment |
| CP-8 | Case and punctuation | sentence case as spoken (Blueprint), no trailing full stops, keep "?" | Blueprint |
| CP-9 | Emphasis | none in captions (Blueprint: no colour highlighting). Emphasis goes to level-3/4 text instead | Blueprint + C |

Current `factory/caption_engine.py` uses `MAX_WORDS = 3` with fixed chunking. CP-1/CP-2/CP-4/CP-5
need word-level timing; until forced alignment is added, distribute each beat's duration across its
words weighted by syllable count, which is far closer than equal splitting.

## 5. Caption modes

Three modes, selectable per episode and per beat (`captions.mode`):

- `full`: every spoken word captioned (default, matches Blueprint).
- `phrase`: captions only for sentences that carry a claim; skipped for short connective lines ("Watch the bottom.") when the visual already says it. Fewer words on screen.
- `keywords`: only nouns, numbers and the key verb, 1-2 words per sentence. For dense diagram beats.

Per-beat override: `captions: off` for `hold` beats and optionally for the reveal moment (Experiment T7).

Default: `full` until Experiment T2 says otherwise.

## 6. Text motion

| Allowed | Not allowed (during explanation beats) |
|---|---|
| Fade in/out 0.12-0.2 s | Bounce, shake, pop-in overshoot, spin |
| Card slides 20-40 px with ease-out, 0.25 s | Per-word scale pulsing ("karaoke" zoom) |
| Label follows its object (tracking), with smoothing so it never jitters | Text crossing the focal object |
| Number counting up on a card when the quantity is actually changing in the sim | Counting animations for static numbers |

(R2-F13: decorative motion gives no learning benefit and adds complexity; Blueprint section 6: no pop-in bounce.)

**TX-9** Text density drops as visual complexity rises: if the frame's complexity proxy is in the top
quartile for the episode, only captions may be visible. (C/E, R2-F10.)

## 7. Typography and colour

From the Blueprint: white captions, soft dark drop shadow, clean geometric sans, semi-bold/bold; label
cards off-white `#e5e2d6` with red `#c92a2e` key text. Additional rules:

- Font: one family for everything (an open-licence geometric sans, e.g. Inter, Manrope or Outfit, licensed SIL OFL; record the licence in the asset register).
- Captions: weight 600-700. Cards: big line 800, small line 600.
- Contrast: caption text needs a luminance contrast ≥ 4.5:1 against the 95th-percentile background luminance under it (measured on rendered frames); if it fails, darken the shadow, never add a box (Blueprint). (WCAG AA as a proxy, Tier C.)
- Line length: captions one line; cards ≤ 2 lines; labels one line.
- Minimum size: nothing under 2.0% cap height (≈ 38 px on 1920) because Shorts are watched on phones.

## 8. Number formatting

- Use digits and symbols in text ("22 cars", "≈ 20 km/h", "0.26 s"); the voice reads words.
- Round to what the evidence supports: two significant figures unless the source gives more.
- "≈" for model-derived or rounded values; never "exactly" unless the physics is exact (e.g., the two balls land in the same frame in an ideal model).
- Units always shown; metric first. For US-heavy topics, a second line may give mph.

## 9. Machine-checkable summary for QC

```yaml
text:
  max_roles_visible: 2          # TX-1
  max_words_on_screen: 9        # TX-2
  max_cards_visible: 1          # TX-3
  card_min_dwell_s: 2.0         # level 4
  card_dwell_per_word_s: 0.3
  label_min_dwell_s: 1.5        # level 3
  hook_text_max_words: 6        # level 1, off by default
  hook_text_off_by_s: 3.5
  min_cap_height_frac: 0.020
  caption_band: [0.69, 0.77]    # from top
  focal_zone: [0.20, 0.66]      # from top
  no_text_zones:
    - {y: [0.00, 0.08]}
    - {y: [0.80, 1.00]}
    - {x: [0.85, 1.00], y: [0.45, 1.00]}
captions:
  mode: full                    # full | phrase | keywords
  max_words_per_chunk: 3
  max_chars_per_chunk: 16
  min_chunk_s: 0.6
  max_cps: 17
  onset_tolerance_s: [-0.10, 0.05]
  clear_after_word_s: 0.15
  hide_in_pauses_over_s: 0.4
  min_contrast_ratio: 4.5
```

## 10. Experiments

Run offline first (a 10-20 person panel watching on their phones, then a 3-question quiz and a
"which would you keep watching?" choice), then confirm with analytics on different but comparable
topics. Never re-upload a near-duplicate to test text (brief Part IX).

| Exp | Comparison | Primary measure | Notes |
|---|---|---|---|
| T1 | Opening text (≤ 6 words) vs none | stayed-to-watch | Blueprint default is none |
| T2 | `full` vs `phrase` captions | APV; quiz score | |
| T3 | Measurement cards vs spoken-only numbers | quiz recall of the number; APV | Expect cards to win (R2-F14) |
| T4 | Caption band at 0.73 vs upper band 0.25 (for top-down shots) | quiz score, panel preference | The earlier review suggested the upper third for top-down shots |
| T5 | Static captions vs subtle word highlight (current word brighter, no motion) | APV | Blueprint says no highlight; test only if T2 shows caption effects matter |
| T6 | Takeaway text card vs caption only | comments quoting the takeaway; APV | |
| T7 | Captions hidden during the 1-2 s reveal vs shown | quiz on the reveal; APV | R2-F9: calm frame at the payoff |
