# Research report 02: attention and cognition

Counterphysical research lab. Written 2026-11-19. Sources retrieved 2026-11-19 unless marked otherwise.

## What this report is for

The production factory needs defaults for hooks, pacing, captions, speech rate and duration before
we have our own analytics. This report collects the evidence we can lean on, grades it, and turns
it into (a) defaults the code can use now, (b) things that must stay configurable hypotheses, and
(c) the experiments that will replace guesses with channel data.

The main conclusion: **almost nothing about short-form science video is established by direct
evidence.** The platform tells us what it measures, not what it rewards. Lab studies tell us a lot
about comprehension and attention in adjacent settings (lectures, adverts, multimedia lessons) and
very little about swiping. So the factory should hard-code only the few things that are well
supported and cheap to get right (clarity, signalling, readable text, honest payoffs), and treat
pacing rules, cut intervals, loop endings and caption style as tunable parameters.

## Evidence tiers (from the brief)

| Tier | Meaning | How we use it |
|---|---|---|
| A | Platform documentation and official metrics | Defines what we measure. Never treated as proof of what the ranking system rewards unless YouTube says so |
| B | Controlled studies close to short video viewing | Defaults, with experiments to confirm |
| C | Adjacent science (multimedia learning, advertising, cognitive psychology) | Design principles and hypotheses |
| D | Observations of successful videos, creator reports | Hypotheses only |
| E | Our own creative reasoning | Must be tested before it becomes a rule |

"Verified" in the registry at the bottom means the source was opened and read during this
research session (2026-11-19). "From prior knowledge" means a well-known paper cited from
memory; its bibliographic details are standard but its numbers were not rechecked today, so no
specific numbers from those papers are used in this report.

---

## Part 1. What the platform actually measures (Tier A)

### F1. A Shorts "view" now counts every start, so public view counts overstate real viewing

- **Finding.** Since 31 March 2025, a Shorts view is counted when the Short starts or replays, with
  no minimum watch time. The older metric survives as **engaged views**, defined by YouTube as "how
  many times viewers stayed to watch past the initial seconds, not including any loops". Average
  view duration and average percentage viewed are now calculated from engaged views only.
- **Evidence.** YouTube Help, "Understand your YouTube content performance" (answer 12220281,
  read 2026-11-19); TeamYouTube community announcement summarised by PPC Land (2025).
- **Source quality.** Tier A (primary platform documentation).
- **Scope.** All Shorts after 31 March 2025.
- **Uncertainty.** YouTube does not say how many "initial seconds" count, and does not say which
  metric the recommendation system uses.
- **Creative implication.** Competitor view counts from before and after March 2025 are not
  comparable. A 2026 Short's public count includes swipe-past starts. Likes per view and comments
  per view are therefore lower for newer Shorts for reasons that have nothing to do with quality.
- **Engineering.** `analytics_engine` must store `views`, `engaged_views` and the stayed-to-watch
  rate separately, and use engaged views as the denominator for every rate. The competitor dataset
  records the publication date so pre/post-change counts are never mixed in one comparison.
- **Experiment.** None needed; this is a measurement rule.

### F2. "Stayed to watch" is the closest public-facing measure of the hook

- **Finding.** Shorts analytics reports "the percentage of times viewers stayed to watch past the
  initial seconds of a Short". This is the best available measure of whether the opening worked.
- **Evidence.** YouTube Help, answer 12220281 (verified).
- **Source quality.** Tier A.
- **Uncertainty.** It is only visible in Studio for our own videos, not competitors'. It is not
  documented as an API field; the analytics engineer must verify whether the YouTube Analytics API
  exposes it before we design around it (brief, Part XVII).
- **Creative implication.** Hook experiments should be judged on stayed-to-watch first and average
  percentage viewed second, never on raw views.
- **Engineering.** If the API lacks the metric, the Telegram bot should ask Caesar to paste it from
  Studio at 72 hours, and store it as a manual field.
- **Experiment.** Every hook experiment in `HOOK_ENGINE_SPECIFICATION.md` uses it as the primary outcome.

### F3. Shorts can run up to three minutes

- **Finding.** Since 15 October 2024, square or vertical uploads up to 3 minutes are Shorts.
- **Evidence.** YouTube Official Blog, "Tall updates coming to Shorts", 3 October 2024 (verified).
- **Source quality.** Tier A.
- **Creative implication.** Duration is a creative choice, not a platform cap. There is no platform
  evidence that shorter is ranked higher. The current 25-45 s rule in `CLAUDE.md` is a reasonable
  starting band for single-idea physics demos, but it is a house hypothesis (Tier E), not a rule.
- **Engineering.** Make target duration a per-episode field chosen from the topic's information
  load (see script spec), with QC warning outside 20-75 s rather than failing.
- **Experiment.** Experiment 5 (duration) in the analytics plan.

### F4. Mass-produced, repetitive content is not monetisable

- **Finding.** From 15 July 2025, YouTube renamed its "repetitious content" monetisation policy to
  "inauthentic content", covering "repetitive or mass-produced content that users often consider
  spam". AI tools are allowed; realistic altered or synthetic content must be disclosed.
  YouTube's examples (as reported) are narrated stories that differ only superficially and
  slideshows reusing the same narration.
- **Evidence.** TeamYouTube announcement, summarised by PPC Land (2025, read 2026-11-19); multiple
  trade press reports. The full Help Center policy text was not retrieved in this session.
- **Source quality.** Tier A via secondary report. Must be re-checked against the live policy page
  before monetisation.
- **Creative implication.** A factory that renders 10 videos a day from shared components is fine
  only if each video has a distinct question, distinct visuals and its own explanation. "One Tiny
  Change, episode 14" made by swapping a parameter in last week's video is exactly the risk.
- **Engineering.** The topic system (see `TOPIC_INTELLIGENCE_SYSTEM.md`) needs a similarity gate:
  reject an idea whose scientific question, component and hook family all match a produced episode.
  Simulations are visibly animated, so the synthetic-content disclosure for realistic media should
  not apply, but descriptions should say "simulation" (they already do: "Simulated with 80 coils").
- **Experiment.** None; this is a compliance rule.

### F5. YouTube's own "hook in one second" advice is a creator's opinion, not platform data

- **Finding.** The official blog's Shorts deep dive (28 January 2025) quotes creator Jenny Hoyos:
  "you have one second to hook someone, especially on Shorts", and a three-part
  surprise → curiosity → payoff structure. The post does not describe ranking signals.
- **Source quality.** Tier D, even though it is on a YouTube domain. It reports one successful
  creator's experience.
- **Creative implication.** Plausible and consistent with F2, but "one second" is not a measured
  threshold. We treat "the premise must be visible in the first frame" as a hypothesis worth
  building in by default because it costs nothing.

---

## Part 2. Curiosity, surprise and prediction (Tier B/C)

### F6. Curiosity peaks at moderate uncertainty, and curiosity improves memory for the answer

- **Finding.** In trivia experiments, self-rated curiosity followed an inverted U against
  confidence: it peaked when people were about 50% sure of the answer (curiosity correlated with
  P(1−P), r = .44). For questions people got wrong, high-curiosity answers were better remembered
  one to two weeks later (d = 1.11, small sample of 12). People paid tokens and waited longer to
  learn answers they were curious about.
- **Evidence.** Kang et al. 2009, *Psychological Science* 20(8), 963-973 (verified). Consistent
  with Loewenstein's information-gap theory (1994) and Gruber, Gelman & Ranganath 2014, *Neuron*
  (curiosity states also improved memory for incidental material; prior knowledge).
- **Source quality.** Tier C (lab trivia, not video).
- **Scope.** Adults answering text questions in a scanner or lab.
- **Uncertainty.** Whether a 1-second visual premise produces the same state is untested. The
  samples are small.
- **Creative implication.** The best hook is a question the viewer feels they could answer but
  isn't sure about. "Which hits the ground first?" with two plausible options is near the peak.
  A question nobody could guess ("What is the Reynolds number of honey?") or that everybody knows
  ("Does a ball fall down?") sits on the flat ends of the curve.
- **Engineering.** Hook scoring includes a "guessability" item: can a non-specialist form a
  confident-ish guess in under 2 seconds, and is there a real chance it is wrong?
- **Experiment.** Offline panel: show 10 hook frames, ask "what do you think happens?" and "how
  sure are you?" (0-100). Hooks with mean confidence near 40-70% and a high wrong-guess rate are
  predicted to win. Compare with stayed-to-watch once published.

### F7. Asking people to predict first makes surprising results stick

- **Finding.** Making a prediction before seeing an outcome improved learning compared with seeing
  the outcome first and rating what one would have expected (d ≈ 0.5). Surprise (measured by pupil
  dilation) only appeared when people had predicted, and it correlated with learning (r = .34).
  Prediction improved memory specifically for outcomes that violated expectations.
- **Evidence.** Brod, Hasselhorn & Bunge 2018, *Learning and Instruction* 55, 22-31 (verified).
- **Source quality.** Tier C (lab tasks with 36 students; within-subject).
- **Uncertainty.** In a feed, the viewer may not actually commit to a prediction, and a forced
  pause may cost swipes. The study had generous time; we have about a second.
- **Creative implication.** The prediction-challenge hook ("Which one lands first?") has the best
  theoretical support of any hook family for *understanding and memory*, provided the result really
  is counterintuitive. It is wasted on a non-surprising result.
- **Engineering.** Storyboards can declare `prediction_window: <s>`, a beat where the setup is held
  still or loops so a prediction can form. Default 1.0-1.5 s, configurable. QC checks that the
  outcome is not shown until the window ends.
- **Experiment.** Experiment 1 (prediction challenge vs direct demonstration) on matched topics.

### F8. Showing the wrong idea, then knocking it down, teaches physics better than clear exposition

- **Finding.** In a randomised study of short physics videos on Newton's first and second laws,
  versions that stated and refuted a common misconception (or showed a student-tutor dialogue that
  did) produced significantly larger learning gains than a clear exposition or an exposition with
  extra interesting material. Gains were largest for students with the least prior knowledge.
- **Evidence.** Muller, Bewes, Sharma & Reimann 2008, *Journal of Computer Assisted Learning*
  24(2), 144-155 (read via a 2023 summary by C. Mead; the paper itself was not opened, so effect
  sizes are not quoted). Consistent with the refutation-text literature (Tippett 2010, prior knowledge).
- **Source quality.** Tier B: controlled, physics content, video format. Not a feed setting.
- **Creative implication.** This is the strongest evidence-based argument for the channel's whole
  premise. "Physics that breaks your intuition" works pedagogically when the video *names the
  intuitive answer* and then shows it failing, rather than only stating the right answer.
- **Engineering.** Script spec: every episode records `misconception:` (the intuitive wrong model)
  and must voice or show it before the reveal. Script QA flags an episode with no stated misconception.
- **Experiment.** Comment analysis: do refutation-style episodes get more comments discussing the
  mechanism? Offline: a 3-question quiz after a misconception-first vs answer-first cut.

### F9. Surprise attracts gaze

- **Finding.** Regions of a video that are statistically surprising (in a Bayesian sense: they
  change the viewer's model of the scene) attract eye movements more than regions that are merely
  bright or high-contrast.
- **Evidence.** Itti & Baldi 2009, *Vision Research* 49(10), 1295-1306 (prior knowledge).
- **Source quality.** Tier C.
- **Creative implication.** The thing that behaves unexpectedly (the hovering slinky bottom, the
  car that brakes) will draw the eye on its own if the rest of the frame is calm. Extra motion
  elsewhere competes with it.
- **Engineering.** Motion design rule: at a reveal, everything except the focal object should be
  static or slow. QC can measure frame-difference energy outside the declared focal region.

---

## Part 3. Visual attention, cuts and complexity (Tier B/C)

### F10. In 30-second videos, short, visually simple scenes keep viewers looking at the same place

- **Finding.** Using eye tracking on 42 Dutch public service announcements (25-30 s, 2,520 viewing
  sessions, 30 viewers), scene cuts increased attentional synchrony (viewers looking at the same
  spot), peaking about 0.66 s after a cut. Visual complexity (spread of salient regions) reduced
  synchrony with a delay of about two thirds of a second. Each extra second of scene length was
  associated with about 5% lower synchrony. Median scene length in the sample was 2.1 s
  (interquartile range 1.5-3 s); no scenes were under 1 s. Cuts helped most in videos with longer
  scenes, with diminishing returns as cuts increased. Synchrony in turn related to immersion,
  liking and recognition.
- **Evidence.** Wals, Grewal, Wilms, Hilken, Briassouli & Wetzels, "The dynamic effects of visual
  complexity and scene cuts on viewer attention", *Journal of the Academy of Marketing Science*,
  published online 26 March 2026, doi:10.1007/s11747-025-01137-x (full text read, CC BY).
- **Source quality.** Tier B. Closest available evidence: video of Shorts length, eye tracking.
  But: adverts, not science; viewers were in a lab and could not swipe; live-action PSAs, not
  simulations; complexity was measured only by saliency spread.
- **Scope.** Attention synchrony in 25-30 s adverts. The authors themselves warn it may not extend
  to narrative or highly stylised content.
- **Uncertainty.** Synchrony is not comprehension and not retention. A cut that resets attention
  could still break the continuity of a physical process the viewer needs to follow. The study
  never tested scenes under 1 s, so it is no evidence for very rapid editing.
- **Creative implication.** Two things transfer well. (1) Keep each shot visually simple, with one
  salient region; complexity hurts with a lag, so a busy frame costs attention for the next half
  second. (2) Long unchanging shots lose attention. For simulations, the "cut" that matters may be
  any meaningful visual event (camera move, state change, reveal), which this study did not measure.
- **Engineering.** Storyboard annotates every visual event by type (hard cut, camera move,
  simulation state change, information reveal, object movement). QC warns when no event of any
  type occurs for more than a configurable gap (default 3.0 s, a hypothesis derived from the 1.5-3 s
  interquartile range) and computes a saliency-spread complexity score per second using a cheap
  proxy (fraction of the frame with significant edge or motion energy).
- **Experiment.** Experiment 4 (continuous tracked simulation vs multiple perspectives), and an
  offline check comparing gaze-free proxies: a 10-person panel answering "where were you looking?"
  is not reliable, so use comprehension questions instead.

### F11. Fast pacing raises arousal and memory until it overloads

- **Finding.** In television research, faster production pacing (more edits per unit time) increased
  self-reported arousal and attention, and improved memory for calm content, but with already
  arousing content very fast pacing reduced memory, consistent with capacity overload.
- **Evidence.** Lang, Bolls, Potter & Kawahara 1999, *Journal of Broadcasting & Electronic Media*,
  and Lang's limited capacity model (Lang 2000, *Journal of Communication*). Prior knowledge; numbers
  not rechecked.
- **Source quality.** Tier C (TV messages, 1990s).
- **Creative implication.** Calm, explanatory segments can carry more visual events; the dramatic
  reveal should have fewer. This matches F9: hold still at the payoff.
- **Engineering.** Pacing is a per-beat parameter (`pace: calm | build | reveal | hold`) rather than a
  global cuts-per-second target.

### F12. Continuity editing hides cuts; viewers miss cuts that follow motion

- **Finding.** Viewers often fail to notice cuts placed during motion that continues across the cut
  ("edit blindness"), which is why continuity editing feels seamless.
- **Evidence.** Smith & Henderson 2008, *Journal of Eye Movement Research*; Smith 2012, *Projections*
  (prior knowledge).
- **Source quality.** Tier C.
- **Creative implication.** When switching from a wide shot of a simulation to a close-up, cut on
  the movement (as the car brakes, as the coil collapses) so the viewer keeps track of the object.
- **Engineering.** The timeline engine should prefer to place a hard cut within 2 frames of a
  physical event on the focal object (`sfx_events()` already marks these moments).

### F13. Animations beat static pictures only when they show the change itself

- **Finding.** A meta-analysis of 76 comparisons found a small-to-medium advantage of animations
  over static pictures (d = 0.37). Animations that *represent the content being learned* helped
  (d = 0.40); decorative animations did not (d = −0.05). The advantage was largest for procedural
  knowledge (d = 1.06, only 5 comparisons).
- **Evidence.** Höffler & Leutner 2007, *Learning and Instruction* 17, 722-738 (verified).
- **Source quality.** Tier C.
- **Creative implication.** Movement should *be* the physics. Decorative motion (bouncing text,
  idle wobble, particles) has no learning benefit and adds complexity (F10).
- **Engineering.** Motion design system bans decorative motion during explanation beats. Every
  animated element in a sim should map to a physical quantity or a reveal.

### F14. Pointing at what matters helps

- **Finding.** Signalling (arrows, highlighting, colour coding, verbal cues that point to the
  relevant part of a picture) improves learning in meta-analyses of multimedia studies, with
  moderate effects on retention and smaller ones on transfer.
- **Evidence.** Schneider, Beege, Nebel & Rey 2018, *Educational Research Review*; Richter, Scheiter
  & Eitel 2016, *Educational Research Review* (located, abstracts not reread; numbers not quoted).
- **Source quality.** Tier C.
- **Creative implication.** Highlight the car that matters, label the number that matters, keep
  the highlight colour reserved for the focal object. The earlier channel review noted the hit
  traffic Short's best moment was its only labelled number ("≈20 km/h backward").
- **Engineering.** One reserved accent colour per video for the focal object; the motion system
  defines highlight, arrow and label primitives.

---

## Part 4. Words: narration, captions and text (Tier B/C)

### F15. Viewers can read fast subtitles and still watch the picture

- **Finding.** In an eye-tracking study (74 adults), subtitle speeds of 12, 16 and 20 characters
  per second (about 140-240 words per minute) made no difference to comprehension. Viewers spent a
  larger *share* of time reading faster subtitles (about 60% vs 50% when the audio was foreign) but
  still had time for the image. With understandable audio, the share was 40-45%, and many viewers
  preferred faster, verbatim subtitles.
- **Evidence.** Szarkowska & Gerber-Morón 2018, *PLoS ONE* 13(6), e0199331 (verified).
- **Source quality.** Tier B for reading speed; drama clips on a monitor, not a phone, not a feed.
- **Creative implication.** Our narration speed (about 150-180 wpm) is within what viewers can read
  along with. The concern is not reading speed but *where the eyes go*: even with audio, captions
  took around 40% of viewing time. That is attention taken from the simulation.
- **Engineering.** Caption engine caps at 17 characters per second and enforces a minimum display
  of 0.6 s per chunk (configurable). Measure caption coverage time per video.
- **Experiment.** Experiment 3 (minimal labels vs fuller captions).

### F16. Adding on-screen text that repeats the narration can hurt understanding of a diagram, but short keywords and captions have real benefits

- **Finding.** Multimedia research finds that adding full on-screen text that duplicates narration
  over a complex animation often reduces learning (the redundancy effect), because the eyes split
  between text and picture. Meta-analyses show the effect depends on conditions: short, keyword-style
  text and learner control reduce or reverse it, and captions benefit second-language viewers, people
  with hearing loss and people watching without sound.
- **Evidence.** Adesope & Nesbit 2012, *Journal of Educational Psychology* 104(1) (located; numbers
  not rechecked); Mayer's redundancy and signalling principles (Mayer 2021, *Multimedia Learning*,
  3rd ed.); Gernsbacher 2015, "Video captions benefit everyone", *Policy Insights from the
  Behavioral and Brain Sciences* (located).
- **Source quality.** Tier C, with real conflict between the two literatures.
- **Uncertainty.** How many Shorts viewers watch muted is not published by YouTube. Figures that
  circulate ("85% watch without sound") come from Facebook-era press reports and should not be used.
- **Creative implication.** Neither "always caption every word" nor "no captions" is supported. The
  defensible middle: short phrase captions (2-4 words) in a band that never covers the simulation,
  with numbers and key terms emphasised, and *deliberate labels* on the diagram for anything the
  viewer must read to understand the physics.
- **Engineering.** Captions stay on by default (accessibility, muted viewing) but the text system
  gets three modes (`full`, `phrase`, `keywords`) and per-beat suppression during reveals. See
  `TEXT_AND_CAPTION_DESIGN_SYSTEM.md`.
- **Experiment.** Experiment 3 on matched topics; offline comprehension quiz with sound on and off.

### F17. Speech can be faster than "comfortable" without hurting comprehension

- **Finding.** Watching a lecture at 1.5× or 2× (210-330 wpm) did not significantly reduce
  comprehension versus 1× (157-166 wpm); 2.5× (about 400 wpm) did. In a large edX log study, videos
  with faster speaking rates held students longer within the same length band; the authors
  attribute this to enthusiasm rather than speed alone.
- **Evidence.** Murphy et al. 2022, *Applied Cognitive Psychology* 36(1), 69-82 (verified); Guo, Kim
  & Rubin 2014, *Proc. ACM Learning@Scale* (verified; 6.9 million sessions, mean speaking rate 156
  wpm, range 48-254).
- **Source quality.** Tier C (lectures; voluntary viewing in a course; observational for Guo).
- **Creative implication.** There is no comprehension reason to slow narration below about 170 wpm
  for simple content. Energy and clarity matter more than a specific rate. TTS at high speed tends to
  sound rushed, so prosody, not wpm, should drive the speed setting.
- **Engineering.** QC measures actual wpm per beat (words ÷ synthesised duration) and warns outside
  140-200 wpm. The voice engine exposes per-beat speed so the hook can be brisk and the reveal slower.
- **Experiment.** Experiment 2 (neutral vs expressive delivery); speech rate logged as a creative
  attribute in every published video.

### F18. Short videos hold attention better than long ones in voluntary viewing, but this says little about 30 vs 60 seconds

- **Finding.** In edX logs, median engagement stayed under about 6 minutes whatever the video length,
  and videos under 3 minutes were watched most completely.
- **Evidence.** Guo, Kim & Rubin 2014 (verified).
- **Source quality.** Tier C, observational, MOOC learners.
- **Creative implication.** Supports "one idea per Short" in spirit. Gives no basis for choosing
  between 30 s and 60 s. The hit traffic Short in our reference review ran 61 s with 13M views,
  which shows length is not disqualifying (Tier D, one example).

---

## Part 5. Story, structure and satisfaction (Tier C/D)

### F19. Suspense, curiosity and surprise are different structures

- **Finding.** Story researchers distinguish suspense (the outcome is pending and the viewer knows
  what is at stake), curiosity (something has happened and the viewer wants the cause) and surprise
  (an unexpected outcome that forces reinterpretation). Different orderings of the same events
  produce different emotional responses and enjoyment.
- **Evidence.** Brewer & Lichtenstein 1982, *Journal of Pragmatics* (structural-affect theory;
  prior knowledge).
- **Source quality.** Tier C.
- **Creative implication.** These map directly onto hook families: countdown/prediction challenge =
  suspense; result-first or impossible-looking result = curiosity; misconception-then-reveal =
  surprise. The script spec uses this to pick a structure per topic instead of one template.

### F20. Being drawn into a story changes how people process it

- **Finding.** "Transportation" into a narrative reduces counter-arguing and increases story-consistent
  beliefs.
- **Evidence.** Green & Brock 2000, *Journal of Personality and Social Psychology* (prior knowledge).
- **Source quality.** Tier C.
- **Creative implication.** A double-edged result: stories help ideas land, and they also make
  viewers less critical, which raises our duty to keep caveats honest. Discovery stories (the 2008
  Japanese ring-road experiment) are a legitimate tool for science Shorts.

### F21. Long, unchanging stretches in the middle are a likely drop-off point (observational)

- **Finding.** In the earlier review of the 13M-view traffic Short, the weakest stretch was 12-23 s:
  one fixed camera on small cars while the core mechanism was narrated. Retention data was not
  available, so this is a judgement, not a measurement.
- **Evidence.** Channel review, 2026-11-19 (Tier D, one video, no retention curve).
- **Creative implication.** Consistent with F10: the explanation beat is where visual events are most
  needed and most often missing, because the explanation is spoken rather than shown.
- **Engineering.** The visual-event gap check (F10) applies with extra weight to `why` beats.

---

## Conflicting findings and how we resolve them for now

| Tension | One side | Other side | Working resolution |
|---|---|---|---|
| Cuts | Cuts increase attentional synchrony (F10) | Coherence and continuity: cuts can break tracking of a physical process (F12, cognitive load) | Use many *visual events* but few hard cuts inside a continuous process; cut on motion; reserve hard cuts for scene or scale changes |
| Text | Redundant on-screen text hurts diagram learning (F16) | Captions help muted, L2 and hard-of-hearing viewers (F16) | Short phrase captions outside the simulation area; labels on the diagram for essential numbers; captions suppressed during the reveal moment |
| Pace | Faster pacing raises arousal (F11) | Overload with arousing content (F11) | Busy setup, calm reveal |
| Suspense | Curiosity improves memory and willingness to wait (F6) | Delayed payoffs risk "false suspense" and swipes (Tier D) | Answer *something* every few seconds; withhold only the final mechanism, never the premise |
| Prediction | Predicting first improves learning (F7) | A pause in a feed may cost swipes (Tier E) | Keep prediction windows short (≈1-1.5 s) and keep motion (a looping setup) during them |

## Recommendations that should NOT be automated yet

These are popular rules with too little evidence. They stay as tunable parameters with no QC
failure attached.

1. A fixed cut interval or cuts-per-second target. The best study (F10) is adverts with no scenes
   under 1 s and no simulations.
2. Seamless loop endings. There is no public evidence that loops help ranking; YouTube excludes loops
   from engaged views (F1). Use a loop only when it explains something (the system returns to its
   start state).
3. Word-by-word "karaoke" captions with bouncing animation. No evidence either way for science
   content; decorative motion is a known cost (F13).
4. A fixed duration. Platform allows 3 minutes (F3); evidence does not pick a number.
5. "Expressive" vs "neutral" narration. Untested for our audience (Experiment 2).
6. Ending every Short with a call to follow. No evidence; it uses the final seconds that carry the
   takeaway. The current slinky outro does this; test removing it.

## Defaults the factory can use now

| Default | Value | Tier | Config key (proposed) |
|---|---|---|---|
| Premise object visible in first frame | required | E (cheap, consistent with F2, F5, F10) | `qc.first_frame_focal_required` |
| Stated misconception before reveal | required for counterintuitive episodes | B (F8) | `script.require_misconception` |
| Max gap between meaningful visual events | 3.0 s warning | B/E (F10) | `qc.max_visual_event_gap_s` |
| Prediction window for prediction hooks | 1.0-1.5 s | C/E (F7) | `storyboard.prediction_window_s` |
| Speech rate band | 140-200 wpm, warn outside | C (F17) | `qc.wpm_range` |
| Caption rate cap | 17 characters/s, min 0.6 s per chunk | B (F15) | `captions.max_cps`, `captions.min_chunk_s` |
| Captions never overlap declared focal region | required | C (F16), D (F21) | `qc.caption_focal_overlap` |
| Decorative motion during explanation | none | C (F13) | motion system rule |
| Reserved accent colour for focal object | one per video | C (F14) | `style.accent` |
| Calm frame at reveal | non-focal motion below threshold | C (F9, F11) | `qc.reveal_background_motion` |

## Testable hypotheses (feed the experiment plan)

| ID | Hypothesis | Primary metric | Notes |
|---|---|---|---|
| H1 | Prediction-challenge hooks raise average percentage viewed vs direct-demonstration hooks for counterintuitive results | APV (engaged views) | Different matched topics, not re-uploads |
| H2 | Showing the premise in frame 1 raises stayed-to-watch vs a 1-2 s establishing shot | Stayed to watch | Can be tested offline with a swipe-simulation panel first |
| H3 | Naming the misconception improves comments discussing the mechanism | Mechanism comments per 1k engaged views | Requires comment classifier |
| H4 | Visual-event gaps over 3 s in explanation beats coincide with retention dips | Retention curve slope | Only for our own videos with retention data |
| H5 | Phrase captions in a fixed band beat word-by-word mid-frame captions | APV, comprehension quiz | Offline first |
| H6 | Removing the "follow for more" outro does not reduce subscribers gained and raises APV | Subs per 1k engaged views, APV | Low-cost test |
| H7 | Episodes 40-60 s with a two-step mechanism beat 25-35 s single-step versions on APV × duration | Watch time per engaged view | Experiment 5 |

---

## Source registry

| # | Source | Type | Tier | Verified 2026-11-19 | URL |
|---|---|---|---|---|---|
| 1 | YouTube Help: Understand your YouTube content performance (engaged views, stayed to watch) | Platform docs | A | yes | https://support.google.com/youtube/answer/12220281 |
| 2 | YouTube Help: Content tab / video analytics (answer 12942217) | Platform docs | A | yes (contains no Shorts-specific definitions) | https://support.google.com/youtube/answer/12942217 |
| 3 | PPC Land, "YouTube changes how Shorts views are counted from March 31" (2025), summarising TeamYouTube | Secondary report of platform change | A (via secondary) | yes | https://ppc.land/youtube-changes-how-shorts-views-are-counted-from-march-31/ |
| 4 | YouTube Official Blog, "Tall updates coming to Shorts", 2024-10-03 | Platform announcement | A | yes | https://blog.youtube/news-and-events/tall-updates-coming-to-shorts/ |
| 5 | PPC Land, "YouTube clarifies inauthentic content policy changes" (2025) | Secondary report of policy | A (via secondary) | yes | https://ppc.land/youtube-clarifies-inauthentic-content-policy-changes/ |
| 6 | YouTube Official Blog, "YouTube Shorts deep dive", 2025-01-28 | Creator interview | D | yes | https://blog.youtube/creator-and-artist-stories/youtube-shorts-deep-dive/ |
| 7 | Wals et al. 2026, JAMS, doi:10.1007/s11747-025-01137-x | Eye-tracking study, 42 PSAs | B | yes (full text) | https://link.springer.com/article/10.1007/s11747-025-01137-x |
| 8 | Kang et al. 2009, Psychological Science 20(8) 963-973 | Lab + fMRI | C | yes | https://www.cmu.edu/dietrich/sds/docs/loewenstein/WickCandleLearning.pdf |
| 9 | Brod, Hasselhorn & Bunge 2018, Learning and Instruction 55, 22-31 | Lab experiment | C | yes | https://doi.org/10.1016/j.learninstruc.2018.01.013 |
| 10 | Muller, Bewes, Sharma & Reimann 2008, J. Computer Assisted Learning 24(2) 144-155 | RCT, physics videos | B | via summary only | https://doi.org/10.1111/j.1365-2729.2007.00248.x |
| 11 | Höffler & Leutner 2007, Learning and Instruction 17, 722-738 | Meta-analysis | C | yes | https://doi.org/10.1016/j.learninstruc.2007.09.013 |
| 12 | Szarkowska & Gerber-Morón 2018, PLoS ONE 13(6) e0199331 | Eye-tracking experiment | B | yes | https://doi.org/10.1371/journal.pone.0199331 |
| 13 | Murphy et al. 2022, Applied Cognitive Psychology 36(1) 69-82 | Experiments | C | yes | https://doi.org/10.1002/acp.3899 |
| 14 | Guo, Kim & Rubin 2014, ACM Learning@Scale | Log study, 6.9M sessions | C | yes | https://up.csail.mit.edu/other-pubs/las2014-pguo-engagement.pdf |
| 15 | Schneider, Beege, Nebel & Rey 2018, Educational Research Review (signalling meta-analysis) | Meta-analysis | C | located, not reread | https://bohrium.dp.tech/paper/arxiv/812517839771533313 |
| 16 | Adesope & Nesbit 2012, J. Educational Psychology 104(1) (verbal redundancy meta-analysis) | Meta-analysis | C | located, not reread | https://rex.libraries.wsu.edu/esploro/outputs/journalArticle/Verbal-Redundancy-in-Multimedia-Learning-Environments/99900601157101842 |
| 17 | Gernsbacher 2015, Policy Insights from the Behavioral and Brain Sciences 2(1) | Review | C | located, not reread | https://successforkidswithhearingloss.com/wp-content/uploads/2020/04/Video-Captions-Benefit-Everyone_2015.pdf |
| 18 | Gruber, Gelman & Ranganath 2014, Neuron 84(2) | Lab + fMRI | C | located, not reread | https://pmc.ncbi.nlm.nih.gov/articles/PMC4252494 |
| 19 | Loewenstein 1994, Psychological Bulletin 116(1) (information-gap theory) | Theory review | C | prior knowledge | — |
| 20 | Itti & Baldi 2009, Vision Research 49(10) 1295-1306 | Eye-tracking | C | prior knowledge | — |
| 21 | Lang, Bolls, Potter & Kawahara 1999, J. Broadcasting & Electronic Media; Lang 2000, J. Communication | TV experiments, theory | C | prior knowledge | — |
| 22 | Smith & Henderson 2008, J. Eye Movement Research (edit blindness) | Experiment | C | prior knowledge | — |
| 23 | Brewer & Lichtenstein 1982, J. Pragmatics (structural-affect theory) | Theory + experiments | C | prior knowledge | — |
| 24 | Green & Brock 2000, J. Personality and Social Psychology (transportation) | Experiments | C | prior knowledge | — |
| 25 | Tippett 2010, Int. J. Science and Mathematics Education (refutation text review) | Review | C | prior knowledge | — |
| 26 | Mayer 2021, Multimedia Learning (3rd ed.), Cambridge University Press | Book | C | prior knowledge | — |
| 27 | Counterphysical channel review of @TheUniverseDisagrees, 2026-11-19 | Our observation | D | yes | https://claude.ai/artifact/3ncesKSkAfCWojbV3BTu3W |

### Starting sources from the brief that could not be checked

- doi:10.1007/s40593-025-00481-x and doi:10.1016/j.learninstruc.2024.102077 both redirect to Elsevier
  pages that the research machine could not open, and the first DOI's prefix (Springer, *IJAIED*)
  does not match the Elsevier landing page it redirects to. Their titles and findings are therefore
  **not** used here. Open item: open them in the browser on Caesar's PC and add them in the next revision.

## Limitations of this report

- No study here involved people swiping through a real Shorts feed. The closest (F10) used a lab
  with no option to leave.
- Several classic findings are cited from prior knowledge without rechecking numbers; they are used
  only for direction, never for thresholds.
- Every numeric default above is a starting point that our own analytics must confirm or replace
  within the first 30-50 published videos.
