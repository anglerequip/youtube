# Topic intelligence system

Counterphysical research lab, v1, 2026-11-19. How the channel finds, scores, researches and sequences
topics. The initial backlog is `topic_backlog.yaml` (121 ideas, machine-readable) with a ranked view in
`TOPIC_BACKLOG.md`.

## 1. What we know about topic demand

| Finding | Evidence | Tier | Use |
|---|---|---|---|
| Familiar frustrations with a counterintuitive cause can reach very large audiences | The reference channel's traffic-jam Short reached 13.1M views; its traffic long-form 1M; its Braess long-form 10K, 10-20× its non-traffic long-forms (500-1.5K) (channel review, 2026-11-19) | D (one channel, survivorship) | Traffic/roads is the most promising series, not a guarantee |
| The audience that came for traffic argued about tailgating and cut-ins in the comments | Same review, top comments | D | Seeds S005 (lane-change ripple), R004, T011 |
| Misconception-based physics videos teach better | Muller et al. 2008 (R2-F8) | B | Favour topics with a documented misconception |
| Curiosity peaks at moderate uncertainty | Kang et al. 2009 (R2-F6) | C | Favour questions viewers can guess but often get wrong |
| Mass-produced repetitive content is demonetised | YouTube inauthentic-content policy, July 2025 (R2-F4) | A | Similarity gate (section 5) |

Everything else in this document is a hypothesis to test with our own analytics.

## 2. Topic opportunity model

Each idea gets 11 scores (1-5), from the brief's list. Definitions and anchors:

| Key | Criterion | 1 | 5 |
|---|---|---|---|
| familiarity | Immediate familiarity | Specialist object or setting | Everyone has seen or felt it |
| curiosity | Curiosity potential | Answer obvious or irrelevant | Most people guess wrong with some confidence |
| clarity | Clarity of the central question | Needs a paragraph to state | One short question |
| visual | Strength of the visual demonstration | Talking points, no picture | One frame shows the surprise |
| reliability | Scientific reliability | Contested or speculative | Textbook physics or replicated result |
| ease | Ease of explanation | Needs maths or several concepts | One mechanism, no jargon |
| originality | Originality | Heavily covered by big channels | Rarely or never shown as a simulation |
| sources | Availability of trustworthy sources | Blogs only | Peer-reviewed paper or standard text |
| feasibility | Production feasibility | Needs a sim we can't build faithfully | Existing component |
| series | Potential for series development | One-off | Opens several distinct follow-ups |
| breadth | Relevance beyond science fans | Science enthusiasts only | Drivers, cooks, parents, anyone |

Opportunity = weighted mean scaled to 0-100. Weights (in `topic_backlog.yaml`): curiosity and visual
1.5; sources and series 0.5; the rest 1.0. **Gates:** reliability < 4 flags `needs_research` and the
idea cannot move past IDEA until a reliable source is found; originality ≤ 2 flags `low_originality`
and needs a framing that is clearly our own.

**The score ranks exploration, not success.** v1 scores are coarse judgements (many ideas cluster at
90-93). They become useful when the analytics loop calibrates them (section 7).

## 3. Topic record (database schema)

Stored in `topic_backlog.yaml` now; the factory should load it into a `topics` table in SQLite.

| Field | Type | Notes |
|---|---|---|
| id | text | Category letter + number (T traffic, M mechanics, ...) |
| working_title | text | Internal, not the YouTube title |
| topic_family | text | One of the 20 brief categories |
| scientific_question | text | The single question the Short answers |
| explanation | text | 1-2 sentence answer |
| misconception | text | The intuitive wrong model (script SC-17) |
| key_visual_moment | text | The frame that shows the surprise |
| candidate_hooks | list | Hook family keys, best first |
| structure | text | Script structure A-H |
| component | text | Simulation component (section 6) |
| production_complexity | small/medium/large | |
| scores | map | 11 scores |
| opportunity | int | 0-100 |
| sources | list | Primary sources |
| source_check | text | v1: "cited from knowledge; open each source before RESEARCHED" |
| originality_note | text | Overlap with known videos and how we differ |
| flags | list | needs_research, low_originality, source_to_verify |
| status | text | Factory states: IDEA → RESEARCHED → SCRIPTED → ... |
| experiment_tags | list | e.g. hook:prediction_challenge, duration:long |
| performance | map | Filled by analytics: engaged views, stayed-to-watch, APV at 72 h and 7 d |

## 4. Discovery process

Run weekly by a Claude session (the `manual` LLM provider) or on request.

1. **Harvest** candidate questions from:
   - Our own comments (highest value once the channel has an audience).
   - Misconception literature: physics education research (e.g. Force Concept Inventory items,
     Hestenes, Wells & Swackhamer 1992, The Physics Teacher 30, 141; Halloun & Hestenes 1985), refutation-text studies.
   - Classic demonstration collections and *American Journal of Physics* / *Physics Education*
     papers (many backlog items come from these).
   - Engineering case studies (accident reports, design guides).
   - Everyday-experience prompts: commuting, kitchen, sport, weather, queues.
   - Public Q&A on physics (Physics Stack Exchange question titles, "explain like I'm five" style
     forums) for phrasing people actually use. Read for questions only, never copy answers.
   - Search interest where accessible (Google Trends) for seasonal timing (heat in summer, ice in winter).
2. **Screen** each candidate: is there a single question, a counterintuitive answer, a visual, and a
   reliable source? If not, drop it.
3. **Check originality**: search YouTube (in the browser on Caesar's computer) for the question. Record
   the top existing Shorts in `originality_note`. Never use another creator's video as a script
   blueprint; we may cover the same physics with our own question, framing and simulation.
4. **Score** with the model above and add to the backlog.
5. **Research** the top ideas: open every source, extract the claim and its assumptions, write the
   caveats, set `source_check: verified <date>`, move to RESEARCHED.

## 5. Similarity gate (inauthentic-content safeguard)

Before an idea moves to SCRIPTED, compare it with every produced episode:

- Same `scientific_question` (embedding cosine > 0.85) → reject.
- Same `component` + same `hook family` + same `structure` as any of the last 10 episodes → require a
  written reason why the viewer gets a different discovery.
- No more than 3 episodes from one series in any 7 published.
- A parameter sweep of an earlier sim ("now with 30 cars") is not a new episode unless the result is a
  new phenomenon.

## 6. Components and reuse

Grouping ideas by simulation component shows where engineering effort pays off (counts in the v1
backlog):

| Component | Ideas | Notes |
|---|---|---|
| diagram (animated 2D/3D explainer, analytic motion) | 24 | Cheapest; needs the Blueprint look |
| rigid_body | 17 | Rolling, tipping, precession; one engine serves many |
| probability_mc (Monte Carlo + counters) | 14 | Maths series; 2D style may suit better than the diorama |
| projectile / kinematics | 11 | Includes the road-safety cluster |
| agents (crowds, flocks, networks) | 10 | Shared with traffic code |
| traffic_lane + traffic_ring | 11 | Already the pilot; highest series value |
| orbit | 7 | Simple ODEs |
| others (heat_1d, optics_rays, mass_spring, waves, pendulum, fluid_2d, circuit, granular) | 31 | Build on demand |

Recommendation for the pipeline thread: after traffic, build `projectile` (cheap, unlocks the
road-safety cluster T008, R002, Z005, R001) and `rigid_body` next.

## 7. Learning loop

After each published episode, record its performance on the topic record (72 h and 7 d). Every 20
episodes:

- Fit stayed-to-watch and APV against the 11 topic scores (ridge regression). Report which scores
  predict anything; expect noise for a long time.
- Blend new weights 50/50 with old ones, version them, and write what changed and why.
- Report the 5 most over-performing and under-performing topics relative to the score and form
  hypotheses (e.g. "road-safety topics hold better than pure traffic-flow topics").
- Never treat a single viral episode as evidence for a whole family.

**Exploration:** 70% of episodes from the top of the ranking, 30% from under-explored families or
components, so the model sees variety.

## 8. Series

Series are editorial labels for discoverability and sequencing, never templates. Each episode needs its
own discovery. Proposed with seed ideas from the backlog:

| Series | Seed ideas | Why it might work | Risk |
|---|---|---|---|
| The Physics of Traffic | T003, T004, S005, T012, T011, J005, T006, T005, T002 | Proven audience appetite in the niche (Tier D) | Overlap with the reference channel; we must frame differently |
| Speed and You (road safety physics) | T008, R002, Z005, R001, T009 | Practical, shareable, strong numbers | Must not lecture; accuracy of stopping-distance assumptions |
| Why This Happens (everyday mysteries) | C005, H001, D003, D004, Q001, Q002, F006 | High familiarity, low coverage as simulations | Some are hard to simulate faithfully |
| Your Intuition Is Wrong Here (misconceptions) | N001-N005, G003, C002, E001, F007, X002 | Best pedagogical support (R2-F8) | Tone: never mock |
| One Tiny Change | S002, S003, M009, B002, E004 | Causal-chain hooks | Can drift into chaos clichés |
| The Mathematics of Everyday Life | P007, P005, P009, Q002, J001 | Relatable maths, low coverage | Needs a visual style for maths (2D) |

## 9. Recommended first slate

Balanced across series, components and hook families, and each with a genuine discovery. Order is a
suggestion; Caesar decides.

| # | Idea | Why now |
|---|---|---|
| 1 | Falling slinky (existing, revised script in the script spec) | Already built; benchmark for the new rules |
| 2 | T003 The tap that stops car thirty (Pilot A) | Traffic series opener with our own framing |
| 3 | M010/N004-style prediction: horizontal vs dropped ball (Pilot B, script spec 7.3) | Prediction hook test, cheap projectile component |
| 4 | T008 Ten km/h faster, much harder hit | Road-safety cluster, same component as 3 |
| 5 | H001 Metal feels colder than wood | Everyday mystery, mistaken-assumption hook |
| 6 | P007 The bus is always late for you (Pilot C candidate) | Maths surprise with a distinct visual style |
| 7 | W001 The stadium wave rule | Agents component, fun, rarely covered |
| 8 | G003 Astronauts are not weightless | Misconception series, simple orbit sim |
| 9 | S005 The lane-change ripple | Answers the reference audience's top argument |
| 10 | B002 Why spaghetti won't break in two | Kitchen familiarity, strong visual |

## 10. Limitations

- Sources in the v1 backlog are standard references cited from knowledge and were not opened during
  this session; each is checked when its idea moves to RESEARCHED. One (Q003) is explicitly marked
  `source_to_verify`.
- Originality notes are from general knowledge of the niche; the browser-based YouTube check in step 3
  has not yet been run for each idea.
- Scores are single-rater judgements.
