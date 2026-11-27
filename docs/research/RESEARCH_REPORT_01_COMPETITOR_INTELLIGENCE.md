# Research report 01: competitor intelligence

Counterphysical research lab, v1, 2026-11-19. What public data from science and engineering Shorts
channels can and cannot tell us. Raw data: `dataset/competitor_videos_2026-11-19.tsv` (146 videos).

**Bottom line.** Public view counts are a weak signal. They cannot show retention, they reward
survivorship, and near-identical videos on the same channel differ by 90× in views. The useful,
checkable findings are structural: top Shorts in this niche are mostly 40-62 s, almost all carry
captions, and the reference Short uses long continuous shots (5 cuts in 60 s), not rapid cutting.
Everything below is Tier D (observational) unless marked otherwise.

## 1. Method

- **Channels.** 30 science, maths and engineering channels chosen to span sizes (from roughly 10K
  median views per Short to several million) and styles (presenter, 2D animation, 3D animation, lab
  footage). Plus one reference Short, `jBTahEPAr-I` ("Why Do Phantom Traffic Jams Happen?", 13.1M
  views), which Caesar chose as the style reference. Per Caesar's instruction, no other data from
  that channel is used.
- **Collection.** Public pages read in the built-in browser on Caesar's computer on 2026-11-19
  (YouTube is blocked from the cloud container). For each channel the first page of its Shorts tab
  was loaded and sorted by views. Five videos were sampled per channel: the top 2, the 2 around the
  median and the lowest. For each video: publish date, duration, views, likes, caption tracks, title.
- **Frame analysis** (section 5). The video element was sampled every 0.1 s into a 36×64 canvas.
  A hard cut is flagged when the colour-histogram difference is ≥ 0.25 and the grey-level difference
  is ≥ 18, both well above the local median (2.5× and 2× of a ±1 s window), with 0.35 s between
  cuts. Every detected cut was checked against a thumbnail strip.
- **Not collected.** No retention, impressions, swipe-away or traffic-source data exists publicly.
  No transcripts or scripts were copied. Nothing here is a template for an episode.

## 2. Channel sample

Views are public counts on 2026-11-19 (since 2025-03-31 a Shorts view counts every start, so older
and newer counts are not directly comparable). "Median" is the median of the 5 sampled videos, not of
the whole channel.

| Channel | Top Short (views, length) | Sample median | Lowest sampled |
|---|---|---|---|
| NileRed | 127.1M, 155 s | 8.62M | 1.80M |
| Vsauce | 40.5M, 66 s | 4.12M | 0.92M |
| physicsgirl | 21.4M, 49 s | 0.60M | 0.05M |
| zackdfilms | 20.0M, 35 s | 6.97M | 0.67M |
| ElectroBOOM | 18.8M, 55 s | 1.04M | 0.08M |
| EngineeringMindset | 18.0M, 55 s | 2.21M | 0.02M |
| primalspace | 15.0M, 59 s | 0.09M | 0.02M |
| veritasium | 13.4M, 60 s | 3.10M | 0.39M |
| *reference* jBTahEPAr-I | 13.1M, 61 s | n/a | n/a |
| TheActionLab | 12.9M, 58 s | 0.81M | 0.07M |
| tracing.science | 12.8M, 43 s | 0.16M | 0.02M |
| SciencephiletheAI | 12.2M, 55 s | 0.45M | 0.09M |
| SteveMould | 11.4M, 55 s | 0.42M | 0.02M |
| RealEngineering | 10.6M, 55 s | 0.45M | 0.08M |
| mathmotion97 | 8.9M, 17 s | 0.11M | 0.01M |
| kurzgesagt | 5.3M, 67 s | 1.39M | 0.37M |
| 3blue1brown | 4.4M, 58 s | 0.76M | 0.07M |
| PracticalEngineeringChannel | 3.2M, 58 s | 0.66M | 0.14M |
| scienceasylum | 2.8M, 53 s | 0.05M | 0.01M |
| AsapSCIENCE | 1.8M, 97 s | 0.08M | 0.04M |
| PhysicswithElliot | 1.3M, 83 s | 0.05M | 0.01M |
| Animagraffs | 1.3M, 29 s | 0.27M | 0.05M |
| Physicsandanimation | 1.1M, 15 s | 0.06M | 0.002M |
| BranchEducation | 1.0M, 59 s | 0.29M | 0.06M |
| minutephysics | 1.0M, 32 s | 0.21M | 0.06M |
| Scienceabc | 0.80M, 56 s | 0.25M | 0.08M |
| TEDEd | 0.56M, 30 s | 0.13M | 0.04M |
| numberphile | 0.52M, 84 s | 0.14M | 0.04M |
| DrBecky | 0.37M, 152 s | 0.05M | 0.01M |
| EugeneKhutoryansky | 0.19M, 59 s | 0.02M | 0.01M |

**Observation 1: hits are far above each channel's typical Short.** On most channels the top Short
has 10-150× the views of the sampled median (primalspace 160×, tracing.science 80×, mathmotion 84×).
A single viral Short says little about a channel's format, and nothing about ours.

## 3. Within-channel comparison (top 2 vs median 2)

Comparing videos from the same channel controls for audience size and style. 29 channels with 5
samples each:

| Group | n | Median length | Share 40-62 s | Share > 100 s | Has captions | Median likes/view |
|---|---|---|---|---|---|---|
| Top 2 per channel | 58 | 56.5 s | 57% | 12% | 86% | 3.7% |
| Middle 2 per channel | 58 | 60 s | 31% | 21% | 86% | 3.4% |
| Lowest per channel | 29 | 57 s | 34% | 10% | 83% | 3.7% |

- **Observation 2: the 40-62 s band is over-represented among top Shorts** (57% vs 31%). This fits
  the script spec's default of 35-60 s. It does not show that length causes views: channels may have
  made more Shorts at that length during the periods when they grew, and the YouTube 3-minute limit
  (October 2024) means long Shorts are newer on average.
- **Observation 3: long Shorts can work.** NileRed's top two are 155 s and 170 s (127M, 61M);
  Vsauce's second is 141 s (21.7M); RealEngineering's 166 s P-38 Short has 8.9M. All are stories with
  a process or reveal at the end. Supports keeping the script spec's 45-90 s band for structure G
  (process) as an experiment, not a default.
- **Observation 4: captions do not separate hits from misses.** Most videos in every group have a
  caption track (often auto-generated), so this sample cannot test captions. Burned-in captions were
  not counted here; frame checks showed they are common.
- **Observation 5: likes per view are flat** (3.4-3.7%), so likes are not a useful proxy for what
  made the top videos travel.

## 4. A matched pair: the survivorship lesson

mathmotion97 posted two almost identical Shorts: both 17 s, both a field of metronomes starting at
random and syncing, both with a "Random start." caption and a sync-percentage readout, no cuts.

| Video | Count | Views |
|---|---|---|
| `1xeFy95B8xE` (2026-10-08) | 100 metronomes | 8.9M |
| `T-z1Ejk9duY` (2026-11-01) | 1,000 metronomes | 99K |

A 90× gap with the same format, topic and channel. Possible causes are timing, novelty already spent
on the same audience, or distribution luck; public data cannot separate them. **Consequence for the
factory:** never treat one hit as proof of a format, and never judge a format on one upload. This is
why the topic system's learning loop waits for 20 episodes and blends weights 50/50.

## 5. Frame analysis: the reference Short

`jBTahEPAr-I`, 60.5 s, 3D low-poly traffic world (the style the Visual Blueprint describes).

- **Hard cuts:** 5, at 11.9, 23.5, 30.6, 38.7 and 48.1 s. Shot lengths 11.9, 11.6, 7.1, 8.1, 9.4 and
  12.4 s (median about 10 s).
- **Inside each shot** the camera keeps moving: the first 11.9 s are one eased move from a low chase
  cam up to a top-down view of the ring road. Something changes on screen at least every 1-3 s
  (camera, braking, a wave spreading), so viewers get frequent visual events without cuts.
- **Cuts land on a change of scene or scale** (ring road → highway, day → night, close → wide), not
  on a timer.
- **Captions** are 1-3 words, white, centred low, synced to speech (consistent with the Blueprint).

**Conflict with the Visual Blueprint.** The Blueprint says hard cuts "every 2.5-4 s". The measured
reference has one cut about every 10 s, with continuous camera moves inside shots. The Blueprint is
right about the shot types, captions and look; its cut rate should read "long continuous shots (7-12
s) with eased camera moves; hard cut on a change of scene, scale or time of day". `MOTION_DESIGN_SYSTEM.md`
MD-5 is updated to match. Caesar owns `CLAUDE.md`, so the Blueprint text is left for Caesar to change.

For comparison, mathmotion's metronome Shorts (17 s) have no cuts at all, and the event-gap rule
(MD-1, 3 s) is met by motion inside the shot, not by editing.

## 6. What this means for the factory

| # | Recommendation | Basis | Where |
|---|---|---|---|
| 1 | Default length 35-60 s; allow up to 90 s for process stories as an experiment | Obs. 2, 3 (D) | Script spec duration bands |
| 2 | Long shots with eased camera moves; cut on scene or scale change; keep visual events every ≤ 3 s inside the shot | Section 5 (D, n=1 reference) | MD-1, MD-5 |
| 3 | Judge formats on several uploads and our own retention data, never on one video | Section 4 (D) | Topic learning loop |
| 4 | Don't use competitor view counts to pick topics on their own; use them to check originality | Obs. 1 | Topic system step 3 |
| 5 | Keep captions on every episode (cost is low, and nearly every channel uses them) | Obs. 4 (D) | Caption system |

## 7. Limitations

- **Small, non-random sample.** 146 videos from 30 channels plus one reference, five per channel,
  stratified by rank within the first page of each Shorts tab. The brief asked for 200-300; that would
  sharpen the length comparison but not fix the main gap below.
- **No retention data.** The question that matters (does a viewer stay?) cannot be answered from
  public pages. Our own YouTube Analytics will be the first real evidence.
- **View counting changed on 2025-03-31**, so counts for older Shorts mean something different.
- **Frame analysis covers one reference Short in detail** plus two short mathmotion videos. Cut
  detection on 36×64 frames can miss soft dissolves (none were seen in the thumbnail checks).
- Channel choice was mine and leans to English-language, well-known science channels.

## 8. Next steps (optional)

- Measure cut rate and event gaps on the top and median Shorts of 5-10 more channels to see whether
  long-shot pacing is typical of 3D-animation Shorts or specific to the reference.
- After the first 10 Counterphysical uploads, compare their retention curves with these structural
  features; that will matter more than anything in this report.
