# Hook engine specification

Counterphysical research lab, v1, 2026-11-19. Builds on `RESEARCH_REPORT_02_ATTENTION_AND_COGNITION.md`
(cited as R2-F#) and the Visual Blueprint in `CLAUDE.md`.

## 1. What "the hook" is here

The hook is the first 0-3 seconds: **first frame + first spoken sentence + optional opening text**,
plus the promise they make together. It is judged on two things:

1. Does the viewer understand the premise fast enough to decide to stay? (measured by stayed-to-watch, R2-F2)
2. Does the rest of the video pay off what the hook promised? (measured by average percentage viewed
   and comments; a hook that over-promises may raise stayed-to-watch and lower everything after it)

A hook is one coherent package. The engine never mixes a visual from one strategy with a sentence
from another unless they describe the same premise.

## 2. Hard rules (machine-checkable, enforced by QC)

| ID | Rule | Default | Tier | Why |
|---|---|---|---|---|
| HK-1 | The focal object of the premise is visible and in motion (or about to move) in frame 0 | required | E, supported by R2-F5, F10 | Costs nothing; the reference Short's hook line was strong but its picture didn't show the ring until 4.5 s |
| HK-2 | First spoken word starts by 0.3 s | `hook.max_voice_start_s = 0.3` | E | No dead air; matches reference practice |
| HK-3 | The premise is fully stated (spoken) by 3.0 s | `hook.max_premise_end_s = 3.0` | D/E | Common creator practice; checked from beat timings |
| HK-4 | First sentence ≤ 14 words | `hook.max_first_sentence_words = 14` | E | At ~170 wpm, 14 words ≈ 4.9 s, so the *premise clause* must come first; see HK-5 |
| HK-5 | The premise noun (the object or system) is spoken within the first 6 words | `hook.premise_noun_within = 6` | E | "If you drop a hanging slinky..." passes (word 5) |
| HK-6 | Opening text, if any, ≤ 6 words, visible by 0.2 s, gone by 3.5 s | `hook.text_max_words = 6` | E | Leaves the eyes for the picture (R2-F15/F16) |
| HK-7 | The hook declares a `promise` and a `payoff_beat`; the payoff beat exists and is not the last beat unless it is short | required | C (R2-F6 curiosity must be satisfied) | Prevents bait hooks |
| HK-8 | No phrase from the scrutiny list (section 6) unless `hook.allow_phrase` is set with a reason | flag, not fail | E | They delay the premise |
| HK-9 | Prediction-challenge hooks hold the setup for a `prediction_window_s` (1.0-1.5 s) before the outcome begins | required for that family | C (R2-F7) | Prediction only helps if there is time to make one |
| HK-10 | Every numeric claim in the hook appears in the storyboard's `sources` or `self_checks()` | required | brief rule | No unverified numbers up front |
| HK-11 | Hook must not state a result the simulation contradicts (e.g., "doesn't move at all" when the sim shows 1 mm) unless the caveat is voiced or on screen within the video | required | brief rule | Honesty; the slinky hook "Not even a little" is borderline and should be checked against its own caveat |

HK-1 and HK-6 are checked from render metadata (focal object bounding box at t=0 inside the frame
and inside the vertical 20-80% band; text events). HK-2 to HK-5 and HK-9 are checked from beat
timings and text. HK-7, HK-10 and HK-11 are checked from the storyboard.

## 3. Hook taxonomy

Sixteen families from the brief, grouped by the psychological mechanism they use (R2-F19):
**suspense** (outcome pending, stakes known), **curiosity** (outcome known, cause unknown) and
**surprise** (expectation set, then broken). Ratings are our initial judgement (Tier E) and become
data once episodes are tagged and measured.

Legend for the table: Premise time = typical time to understand the premise. Sim fit = how well a
physics simulation can carry it (H/M/L). Prior = prior knowledge needed. Risk = main failure mode.

| # | Family | Mechanism | Premise time | Sim fit | Prior | Main risk | Ending it supports |
|---|---|---|---|---|---|---|---|
| 1 | Impossible-looking result | curiosity | <1 s if the visual is clear | H | none | Looks fake or edited; needs "simulated with real physics" credibility | Mechanism reveal |
| 2 | Prediction challenge | suspense → surprise | 1-2 s | H | low | Result not actually surprising; viewer doesn't commit | Reveal + why |
| 3 | Ordinary mystery | curiosity | 1-2 s | M | none (relies on experience) | Familiar but already understood | "So next time you..." |
| 4 | Counterintuitive mechanism | surprise | 2-3 s (verbal) | M | low | Sounds like a claim, needs immediate visual proof | Demonstration |
| 5 | Visual experiment | curiosity | <1 s | H | none | Ambiguous what to watch | Result + explanation |
| 6 | Escalating variable | suspense | 1-2 s | H | low | Slow; needs a visible threshold | Threshold/tipping point |
| 7 | Mistaken assumption | surprise | 2-3 s | M | low | Preachy ("you're wrong"); must name a belief people actually hold | Corrected model |
| 8 | Hidden cause | curiosity | 1-2 s | M | none | Cause not visualisable | Cause shown |
| 9 | Comparison | suspense | 1-2 s | H | none | Two things on screen halves size; needs split or same-scene setup | Winner + why |
| 10 | Countdown to a result | suspense | 1-2 s | H | none | False suspense if the countdown is padding | The moment |
| 11 | Causal chain | suspense/curiosity | 1-2 s | H | none | Chain too long for 40 s | Final consequence |
| 12 | Reverse explanation | curiosity | 1 s | M | none | Confusing order if the result isn't self-explanatory | Back at the start (natural loop) |
| 13 | Constraint ("what if gravity...") | curiosity | 2-3 s | H | low | Hypothetical feels arbitrary | New behaviour explained |
| 14 | Scale shift | surprise | 1-2 s | M | low | Scale cues hard to read on a phone | Comparison to familiar scale |
| 15 | Paradox | curiosity | 2-3 s | M | medium | Two claims at once overloads 3 s | Reconciliation |
| 16 | Question answered by simulation | curiosity | 1-2 s | H | none | Overlaps 2/5; must be a question only a sim can settle | Visible answer |

Families with the strongest support for *understanding* (not proven for retention): 2 (R2-F7),
7 (R2-F8 misconception-refutation, Tier B) and 1/5 (visual premise immediately, R2-F10). These are
the default candidates; the others are explored at a lower rate (section 8).

### 3.1 Family details

For each family the engine needs: a visual template, a narration template, and red flags. The
templates are shapes, not wording to reuse verbatim.

**1. Impossible-looking result.** Visual: the anomaly already happening in frame 0 (bottom of the
slinky hanging in midair while the top falls). Narration: name what the viewer is seeing as a flat
statement. Red flag: if the anomaly is a single frame, the viewer may miss it; loop it or hold it.

**2. Prediction challenge.** Visual: a controlled setup, both options visible, nothing moving except
a subtle cue that something is about to happen (a hand, a countdown light). Narration: one question
with two or three named options. Then `prediction_window_s` of held setup (HK-9). Red flag: if
more than about 80% of viewers would guess right, it is not a challenge (R2-F6). Use the offline
guess panel (section 9).

**3. Ordinary mystery.** Visual: the everyday situation, rendered recognisably (a queue of cars, a
kettle). Narration: "Why does X happen when Y?" in the viewer's own words. Red flag: if the answer
is common knowledge, it is not a mystery.

**4. Counterintuitive mechanism.** Visual: must show the mechanism *starting* within 2 s or the
claim is just words. Narration: the claim, concrete and qualified ("can", "under these conditions").
Red flag: absolutes that the sim's assumptions don't support.

**5. Visual experiment.** Visual: the experiment running from frame 0 with a clear subject.
Narration may start slightly after (0.2-0.3 s) and should tell the viewer where to look. Red flag:
two moving things and no cue which matters.

**6. Escalating variable.** Visual: a parameter readout (label card per Blueprint section 7) that
changes, with the system's response visible. Narration: what is being increased and the question
"at what point does...". Red flag: no visible threshold.

**7. Mistaken assumption.** Visual: show the intuitive (wrong) version first, labelled as the
intuition, then the real behaviour. Narration: state the belief in neutral words people actually
use ("Heavier things fall faster, right?"). Red flag: the belief must be common; check sources or
misconception literature. Never mock the viewer.

**8. Hidden cause.** Visual: the familiar outcome. Narration: "The cause of this is X metres
behind / minutes earlier / invisible." Red flag: the cause must be rendered later, or the hook is a tease.

**9. Comparison.** Visual: two systems differing by one controlled variable, side by side or in the
same world with a colour difference (keep to the Blueprint's muted palette plus one accent).
Narration: name the one difference. Red flag: on a 9:16 frame, side-by-side halves the object
width; prefer stacked (top/bottom) or the same scene.

**10. Countdown.** Visual: visible progress toward an event (a ball rolling toward a gap). Narration:
what will happen when it arrives. Red flag: total countdown > 5 s without new information.

**11. Causal chain.** Visual: the first small cause, highlighted (Blueprint white ring). Narration:
"This tap of the brakes will stop cars two kilometres back." Red flag: needs ≥ 3 visible links; fewer
is just cause-effect.

**12. Reverse explanation.** Visual: the end state. Narration: "This jam started with one driver,
four minutes ago." Then rewind or cut back. Red flag: the end state must be understandable alone.

**13. Constraint.** Visual: familiar system with one change visibly applied (gravity label set to
1/6, friction set to zero). Narration: the change and the question. Red flag: needs real physics in
the changed regime, not a guess.

**14. Scale shift.** Visual: familiar object, then the camera reveals the scale. Narration: anchor to
a known size or time. Red flag: needs a scale reference in frame (a car, a person, a clock).

**15. Paradox.** Visual: both truths in one frame if possible. Narration: two short clauses joined
by "but" or "and yet". Red flag: if it takes more than 3 s to state, choose another family.

**16. Question answered by simulation.** Visual: the setup of a question that intuition and
everyday experience can't settle (what if 100 people all do X). Narration: the question.
Red flag: if a quick mental model settles it, use family 2 instead.

## 4. Generation procedure (per topic)

Input: an approved topic record (see `TOPIC_INTELLIGENCE_SYSTEM.md`) with its scientific question,
`misconception`, key visual moment and sources.

Steps:

1. **Choose 5 hook strategies** from at least 4 different families. Always include family 2 or 7 if
   the topic has a documented misconception, and family 1 or 5 if the key visual moment is striking
   in a single frame. Exploration slot: one strategy from a family used in fewer than 10% of produced
   episodes (section 8).
2. **For each strategy, draft one coherent package:** opening visual (shot, focal object, what
   moves), first sentence, optional opening text, promise, payoff beat.
3. **Expand the best two packages** into 3 opening-visual variants (shot choices from the Blueprint
   camera list) and 3 first-sentence variants each, and 2 opening-text treatments (none vs ≤ 6
   words). Do not generate the full cross product; keep only pairs where the sentence names what the
   visual shows (coherence check: the premise noun in the sentence is the focal object of the shot).
4. **Score** every surviving package (section 5). Record the rationale for every score.
5. **Select** the top package, plus a runner-up stored for later experiments.

Typical output: 5 strategies → 2 expanded → up to 18 coherent packages, of which ~8-10 pass the
coherence check. That is enough to choose from without flooding review.

### 4.1 Output schema (`content/episodes/<slug>/hooks.yaml`)

```yaml
topic_id: T-014
selected: H3
candidates:
  - id: H3
    family: prediction_challenge        # one of the 16 family keys
    mechanism: suspense                 # suspense | curiosity | surprise
    opening_visual:
      shot: overhead_3_4                # Blueprint camera key
      focal_object: "two balls on the ledge"
      motion_at_t0: "both balls at rest, hand about to release"
    first_sentence: "One ball is dropped, one is fired sideways. Which lands first?"
    opening_text: null                  # or ≤ 6 words
    prediction_window_s: 1.2
    promise: "show which ball lands first and why"
    payoff_beat: reveal
    misconception_addressed: "a ball fired sideways stays up longer"
    scores: {clarity: 5, curiosity: 4, visual_distinctiveness: 3, accuracy: 5, relevance: 3,
             comprehension: 5, payoff_strength: 4, originality: 3, feasibility: 5, disappointment_risk: 4}
    rationale:
      clarity: "Both objects and the question are visible and spoken within 2.5 s."
      curiosity: "Guess panel not yet run; many adults expect the fired ball to land later."
      # ... one line per criterion
    total: 4.18
```

## 5. Scoring

Ten criteria from the brief, each scored 0-5 with anchors. A model-generated score is advice; the
human review in Telegram is the real gate (brief Part XXI).

| Criterion | 0 | 3 | 5 |
|---|---|---|---|
| Immediate clarity | Can't tell what the video is about after 3 s | Understood by 3 s with narration | Understood from frame 0 with sound off |
| Genuine curiosity | Answer obvious or irrelevant | Mild interest | Viewer holds a confident guess that is likely wrong (R2-F6) |
| Visual distinctiveness | Generic shot, could be any video | Clear but ordinary | A frame you'd recognise as this video |
| Scientific accuracy | Wrong or unsupported | Correct with unstated assumptions | Correct, assumptions stated in the video |
| Audience relevance | Specialist only | Interesting to science fans | Something most viewers have experienced or wondered |
| Ease of comprehension | Needs jargon or prior knowledge | One new term | No new terms |
| Strength of implied payoff | No promise | Vague promise | Specific promise the viewer can picture |
| Originality | Same premise and framing as a known video | Familiar topic, new framing | Topic or framing not seen in the competitor set |
| Feasibility | Sim can't show it faithfully | Needs a new component | Existing component renders it |
| Risk of disappointment (inverted: 5 = low risk) | Payoff smaller than promise | Payoff matches | Payoff exceeds promise |

**Hard gates** (any one rejects the package regardless of total): accuracy < 4, clarity < 3,
disappointment risk < 3, feasibility < 2.

**Weights** live in `config/hook_weights.yaml` and start equal except:

```yaml
weights:
  clarity: 1.5
  curiosity: 1.5
  visual_distinctiveness: 1.0
  accuracy: 1.0          # mainly enforced by the gate
  relevance: 1.0
  comprehension: 1.0
  payoff_strength: 1.0
  originality: 1.0
  feasibility: 0.5       # mainly enforced by the gate
  disappointment_risk: 1.0
version: 1
updated: 2026-11-19
basis: "Initial judgement (Tier E). Clarity and curiosity up-weighted per R2-F6/F10."
```

Total = weighted mean. Weights are re-estimated (section 8) once at least 30 published episodes have
hook tags and 7-day metrics; until then, changes require a note in `basis`.

## 6. Writing constraints

**Scrutiny list** (flagged by HK-8; allowed only with a written reason):

- "Have you ever wondered", "Did you know", "In today's video", "Scientists have discovered",
  "You won't believe", "This will blow your mind", "Wait for it", "Watch till the end",
  "Nobody talks about", "The truth about".

Regex (case-insensitive) for QC:
`\b(have you ever wondered|did you know|in today'?s video|scientists (have )?discovered|you won'?t believe|blow your mind|wait for it|watch (un)?till the end|nobody talks about|the truth about)\b`

**Style rules** (checked by a lint pass, warnings not failures):

- Start with the object, not with "So", "Okay", "Hey" or the channel name.
- Present tense for what is on screen ("The top races down.").
- Concrete numbers only if they are sourced (HK-10), spelled out as spoken (CLAUDE.md rule).
- No second-person accusation ("You're doing it wrong"). Second person for the viewer's experience
  is fine ("You've been in this jam").
- Hedge exactly as much as the science requires: "can", "under these conditions", "in this model".
  Don't hedge what the sim proves.
- Never reuse another creator's opening line or its distinctive structure word-for-word. The
  originality check (script spec) compares against the competitor transcript set.

## 7. Worked examples

### 7.1 Falling slinky (existing episode)

Current hook: "If you drop a hanging slinky, the bottom doesn't fall. Not even a little."
- HK-5 passes (slinky at word 6). HK-1: the opening frame shows the hanging slinky, passes.
- HK-11 concern: the storyboard caveat says the real bottom moves "by a millimetre or so". "Not even
  a little" is true of the ideal model and visually true at phone scale, but should be softened or
  the caveat voiced. Suggested: "...the bottom doesn't fall. It just hangs there."
- Family: 1 (impossible-looking result), but the anomaly isn't visible until release. Stronger as
  family 2: "Let go of the top of this slinky. What does the bottom do?" + 1.2 s held frame + release.
  Or keep family 1 and open *mid-fall* with the bottom hovering (frame 0 = the anomaly), then rewind.

| Candidate | Family | First sentence | Visual at t=0 | Notes |
|---|---|---|---|---|
| A | 1 | "The top of this slinky is falling. The bottom isn't." | Mid-collapse, bottom hovering | Anomaly in frame 0; reverse to setup after |
| B | 2 | "Let go of the top of this slinky. What does the bottom do?" | Hanging, hand at top | Prediction window 1.2 s |
| C | 7 | "Everything you drop falls straight away. Except this." | Hanging slinky | Names the intuition (R2-F8) |
| D | 11 | "Release the top, and the bottom won't know for a quarter of a second." | Hanging, timer label | Sourced number (Calkin 1993 / centre-of-mass check) |
| E | 14 | (slow-motion scale shift) "This quarter second, slowed down forty times." | Slow-mo collapse | Needs time-scale label |

### 7.2 Traffic waves (Pilot A)

| Candidate | Family | First sentence | Visual at t=0 |
|---|---|---|---|
| A | 1 | "Twenty-two cars, an empty ring road, and a traffic jam anyway." | Top-down ring, cars bunching |
| B | 11 | "One driver taps the brakes. Watch what it does to the car thirty places back." | Chase cam behind the highlighted car, brake glow |
| C | 3 | "Why do you stop on the motorway when nothing is ahead?" | Highway centreline, stopped queue |
| D | 12 | "This jam started four minutes ago, with one small brake." | Dense jam, then rewind |
| E | 9 | "Same road, same cars. One driver keeps a steady speed." | Two rings stacked, one flowing |

A is closest to the reference Short's premise (the Sugiyama experiment). Originality score is low
for A; prefer B or D framing and our own simulation. Note: the reference Short's opening (chase
cam on one car) failed HK-1 because the ring wasn't visible; B fixes this by making the single car
*the* focal object.

### 7.3 Horizontal vs dropped bullet (Pilot B candidate)

| Candidate | Family | First sentence | Visual at t=0 |
|---|---|---|---|
| A | 2 | "One ball is dropped, one is fired sideways. Which lands first?" | Side view, two balls at the same height |
| B | 7 | "Fire something fast enough sideways and it stays up longer. It doesn't." | Same, with "intuition" label |

Physics: with no air resistance both land together (independent horizontal and vertical motion).
Caveat: air drag and Earth's curvature change this at high speeds; must be stated.

## 8. Experimentation and learning

**Tagging.** Every published episode stores `hook.family`, `mechanism`, `opening_text` (yes/no),
`premise_end_s`, `prediction_window_s`, the selected package scores and the runner-up.

**Allocation.** Before data exists: 70% of episodes use the top-scored family, 30% are assigned an
under-explored family (an epsilon-greedy rule; stops us locking in early). Families are compared only
after ≥ 8 episodes each.

**Primary metric:** stayed-to-watch (R2-F2). **Secondary:** average percentage viewed, subscribers per
1,000 engaged views, mechanism-discussing comments.

**Confounders to record:** topic family, duration, publish day/hour, whether the episode is part of a
series, voice, caption mode. Compare hook families within topic family when possible.

**Analysis.** Hierarchical (partial-pooling) model of stayed-to-watch with hook family as a factor and
topic family as a grouping factor; report intervals, not just point estimates. Do not declare a
winner on fewer than 8 episodes per arm or an interval that overlaps zero.

**Weight updates.** Every 30 new episodes: regress stayed-to-watch on the ten criterion scores
(ridge regression, standardised), blend 50/50 with the prior weights, bump `version`, write the
`basis`. If the model's scores don't predict outcomes better than chance (rank correlation < 0.1),
say so and keep the weights; the human review remains primary.

**Never:** re-upload the same video with a different hook to "test" it (brief Part IX, Part XVII;
also an inauthentic-content risk, R2-F4).

## 9. Offline guess panel (cheap pre-test)

For prediction-challenge and mistaken-assumption hooks, before rendering: show 5-10 people the
opening frame and first sentence (a still + text is enough) and ask "What happens?" and "How sure are
you (0-100)?". Keep the hook if ≥ 40% guess wrong and mean confidence is 40-80% (the curiosity peak,
R2-F6). Record results in `hooks.yaml` under `panel:`.

## 10. Conflicts with the Visual Blueprint (flagged, not overridden)

| Blueprint says | This spec says | Proposal |
|---|---|---|
| Opening frame: chase cam low behind a car | HK-1: the premise must be visible at frame 0 | Chase cam is fine when the chased car *is* the focal object (traffic B above). For system-level premises (the whole ring), open on the top-down or 3/4 shot instead |
| No title card; reference had no opening text | HK-6 allows ≤ 6 words of opening text | Default `opening_text: null` (matches Blueprint); test text vs no text as Experiment T1 in the caption spec |
| Ending loops visually | Loops only where they explain (R2 "not automated") | Use loops for reverse-explanation hooks (family 12) and cyclical systems; don't force them |
