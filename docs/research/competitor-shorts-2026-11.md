# Competitor Shorts study and retention plan (November 2026)

Prepared 2026-11-19 for the Counterphysical channel. Covers deliverables A (competitor research),
B (techniques library), C (gap analysis of our chain-fountain video) and F (roadmap). Deliverable D (code)
is described in `docs/RETENTION.md`; E (demo) is `content/episodes/chain-fountain-hud`.

**Evidence labels.** `OBSERVED` = read from a frame, the measured audio, or the platform's metadata.
`INFERRED` = our interpretation of what we observed. `HYPOTHESIS` = an idea worth testing that the data
does not prove. Nothing in this document claims that a technique produces a given number of views.

---

## 0. Method and limits

- **Data collection** ran on the owner's PC (cloud IPs are blocked by YouTube/TikTok) with yt-dlp, ffmpeg
  and a measuring script. Every video, frame sheet, transcript, `measure.json` and per-video
  `breakdown.md` is in `D:\CounterPhysical\research\competitors\` (private analysis copies, never
  committed or re-published). Metrics were checked at **2026-11-19 17:39 UTC**.
- **Selection.** Each channel's full Shorts/video listing was sorted by views; we took the top 3 and two
  "ordinary" videos at the channel median (recent, to show what a typical upload does now). 25 videos.
- **Measures.** Hard cuts = ffmpeg scene score > 0.30; soft cuts = a lower threshold. Words per minute
  from platform auto-captions (Hindi for ProfessorOfHow). Loudness in LUFS (momentary), silences, and
  "loud accents" (sudden level jumps). Frames sampled every 0.5 s for 0-10 s and every 2 s for the rest.
- **Known limits.**
  - The hard-cut detector **under-counts**: it misses dissolves, flashes and fast camera moves (several
    breakdowns list scene changes with no detected cut). Treat cut counts as a lower bound.
  - We could not listen to the audio, so **music presence and style are not determinable**; only loudness.
  - TikTok "What if?" (@man_ia_c) and Simply Simulated have **no narration transcript** (no captions
    track, and no speech-to-text was run), so their spoken words and WPM are unknown; their story is
    carried by on-screen text, which we read from frames.
  - Timed story notes at 5/15/30/45/60 s come from transcripts/frames at 2 s resolution (±1 s).
  - YouTube listing view counts are rounded; the exact counts below come from each video's own page.
    TikTok listings may be incomplete, so "top 3" on TikTok means top 3 of what the listing returned.
  - Ordinary videos are confounded: ProfessorOfHow's recent median videos are a different format
    (talking head, satire), so "top vs ordinary" there compares formats, not techniques.

---

## A. Competitor research report

### A.1 Channel overview (OBSERVED)

| Channel | Platform | Videos listed | Median views | Top video views |
|---|---|---|---|---|
| Zack D. Films (@zackdfilms) | YouTube | 4,203 Shorts | about 14 M | 255.8 M |
| Professor Of How (@ProfessorOfHow) | YouTube | 544 Shorts | about 8.9 M | 195.5 M |
| Low Poly Shorts (@lowpolyshorts) | TikTok | 96 | about 1.95 M | 86.6 M |
| What if? (@man_ia_c) | TikTok | 25 | about 694 k | 19.5 M |
| Simply Simulated (@simplysimulated) | TikTok | 36 | about 66.5 k | 24.9 M |

### A.2 The 25 videos (OBSERVED; views checked 2026-11-19 17:39 UTC)

Hard cuts = detected (lower bound). WPM = metrics.json; "-" = no transcript.

| # | Channel / rank | Title (as published, emoji dropped) | Published | Views | Length | Hard cuts (first 10 s) | Median shot | WPM |
|---|---|---|---|---|---|---|---|---|
| 1 | zackdfilms top1 | [How Stitches Work](https://www.youtube.com/shorts/ttuKeS5k4Uo) | 2024-02-24 | 255,764,054 | 31.0 s | 0 (0) | 31.0 s | 150 |
| 2 | zackdfilms top2 | [How Splinters Get Unstuck](https://www.youtube.com/shorts/yGw0nhlUtkQ) | 2024-03-05 | 216,865,296 | 30.4 s | 0 (0) | 30.4 s | 161 |
| 3 | zackdfilms top3 | [McFlurry spoon](https://www.youtube.com/shorts/rRAmNz6G3Tk) | 2022-12-19 | 167,191,975 | 23.4 s | 0 (0) | 23.4 s | 182 |
| 4 | zackdfilms ordinary | [Bug Man inside the purple guy](https://www.youtube.com/shorts/GIIA1d0059o) | 2026-11-04 | 14,904,449 | 51.7 s | 2 (1) | 18.4 s | 145 |
| 5 | zackdfilms ordinary | [Hoover Dam made of humans](https://www.youtube.com/shorts/orbNiULu_t0) | 2026-11-02 | 14,301,408 | 37.9 s | 13 (2) | 0.35 s | 163 |
| 6 | ProfessorOfHow top1 | [The science behind hurting testicles](https://www.youtube.com/shorts/EGI_YvF7S3w) | 2022-12-11 | 195,535,814 | 59.9 s | 9 (1) | 5.5 s | 238 (Hindi) |
| 7 | ProfessorOfHow top2 | [How a bulletproof jacket works](https://www.youtube.com/shorts/M9XhqdwSAGI) | 2022-04-10 | 190,391,610 | 59.1 s | 5 (1) | 6.1 s | 231 (Hindi) |
| 8 | ProfessorOfHow top3 | [Brain-eating amoeba](https://www.youtube.com/shorts/fRdF8yFt84g) | 2022-09-26 | 168,764,350 | 57.5 s | 19 (3) | 2.4 s | 249 (Hindi) |
| 9 | ProfessorOfHow ordinary | [Life lesson, talking head](https://www.youtube.com/shorts/27VO-PURFWs) | 2026-01-03 | 8,981,869 | 77.1 s | 14 (2) | 4.1 s | 279 (Hindi) |
| 10 | ProfessorOfHow ordinary | [Delhi CM on pollution (satire)](https://www.youtube.com/shorts/Fv22OYokztE) | 2025-12-14 | 8,973,911 | 85.9 s | 15 (2) | 4.5 s | 250 (Hindi) |
| 11 | lowpolyshorts top1 | [Touch: atoms aligning](https://www.tiktok.com/@lowpolyshorts/video/7606648171032317197) | 2026-02-14 | 86.6 M | 38.8 s | 19 (6) | 1.5 s | 208 |
| 12 | lowpolyshorts top2 | [Cannulated cow](https://www.tiktok.com/@lowpolyshorts/video/7581258548244434190) | 2025-12-07 | 29.6 M | 24.4 s | 7 (2) | 3.0 s | 210 |
| 13 | lowpolyshorts top3 | [Bamboo torture](https://www.tiktok.com/@lowpolyshorts/video/7602408465008577805) | 2026-02-02 | 23.4 M | 33.6 s | 12 (5) | 2.5 s | 210 |
| 14 | lowpolyshorts ordinary | [Perpetual liver transplant](https://www.tiktok.com/@lowpolyshorts/video/7688464833146096910) | 2026-09-22 | 2.0 M | 60.9 s | 13 (1) | 2.7 s | 195 |
| 15 | lowpolyshorts ordinary | [Red paperclip trades](https://www.tiktok.com/@lowpolyshorts/video/7579011741665758478) | 2025-12-01 | 2.0 M | 48.7 s | 22 (5) | 2.0 s | 201 |
| 16 | man_ia_c top1 | [What if electrons disappeared for 5 seconds?](https://www.tiktok.com/@man_ia_c/video/7693494009494342945) | 2026-10-06 | 19.5 M | 80.0 s | 3 (2*) | 12.0 s | - |
| 17 | man_ia_c top2 | [What if oxygen disappeared for 5 seconds?](https://www.tiktok.com/@man_ia_c/video/7693305573487562016) | 2026-10-05 | 14.4 M | 80.0 s | 3 (0) | 12.4 s | - |
| 18 | man_ia_c top3 | [What if a pop star was 100 times taller?](https://www.tiktok.com/@man_ia_c/video/7694025665993100576) | 2026-10-07 | 10.2 M | 80.0 s | 3 (0) | 23.5 s | - |
| 19 | man_ia_c ordinary | [What if Earth left the universe for 5 seconds?](https://www.tiktok.com/@man_ia_c/video/7698033834897509664) | 2026-10-18 | 694,000 | 80.0 s | 5 (1) | 6.3 s | - |
| 20 | man_ia_c ordinary | [What if Earth fell into a black hole?](https://www.tiktok.com/@man_ia_c/video/7693428628633193760) | 2026-10-06 | 702,700 | 80.0 s | 3 (0) | 23.2 s | - |
| 21 | simplysimulated top1 | [What if all women disappeared?](https://www.tiktok.com/@simplysimulated/video/7695199069089631502) | 2026-10-11 | 24.9 M | 76.0 s | 14 (0) | 4.0 s | - |
| 22 | simplysimulated top2 | [What if all men disappeared?](https://www.tiktok.com/@simplysimulated/video/7695317174335868173) | 2026-10-11 | 11.6 M | 76.0 s | 12 (0) | 4.0 s | - |
| 23 | simplysimulated top3 | [What if every adult on earth disappeared?](https://www.tiktok.com/@simplysimulated/video/7696246675815353614) | 2026-10-13 | 2.2 M | 80.0 s | 30 (5) | 2.6 s | - |
| 24 | simplysimulated ordinary | [What if you got 2x faster every second?](https://www.tiktok.com/@simplysimulated/video/7695879633828318478) | 2026-10-12 | 67,300 | 93.5 s | 5 (0) | 9.1 s | - |
| 25 | simplysimulated ordinary | [What if the Tower of Babel happened today?](https://www.tiktok.com/@simplysimulated/video/7694909727515397389) | 2026-10-10 | 65,800 | 73.5 s | 12 (1) | 5.0 s | - |

\* 8.000 and 8.033 are one event.

### A.3 Per-video notes (what grabs attention, hook, signature element, editing, sound, text, ending)

Short form; the full second-by-second breakdowns (shot lists with times, every overlay with
position/colour/size, captions, loudness, ending) are in each video's `breakdown.md` on the PC.

**1. Stitches (Zack, 255.8 M).** Photoreal CG calf; the wound is being stitched **from frame 0** (OBSERVED:
1 stitch at 0.5 s, about 9 by 3 s) while the narration explains the same action. One continuous take with
a slow push-in, no cuts, no captions, no graphics. Payoff object (scissors) enters at about 5.5 s.
Ends on the healed leg in a composition that echoes the opening (before/after; partial loop, INFERRED).
Why it works (INFERRED): a universal, slightly uncomfortable everyday experience shown up close, with the
explanation and the picture perfectly in sync.

**2. Splinters (Zack, 216.9 M).** Opening scene change at 0.5 s (wood surface to fingertip, undetected by
the cut detector). Tweezers at 2.5 s. White word-by-word captions near 78 % height. **Pressure arrows**
pointing at the splinter 17-23 s while the body pushes it out (OBSERVED). Glowing pus particles 13-21 s.
No loop.

**3. McFlurry spoon (Zack, 167.2 M).** Live-action-style object held toward the lens while a question is
asked ("have you ever noticed...", paraphrase). Mystery reveal: the spoon's design reason. Ends in the
same setting as the opening (partial loop).

**4. Bug Man (Zack ordinary, 14.9 M).** Hypothetical "what if X shrank inside Y" question that runs
0-11.8 s; the answer (the figure bursting into particles) is **shown at 9.5 s while the question is still
being asked** (OBSERVED). Force arrows: blue outward from the ribcage at ~27 s, red inward at ~29 s.
Ring marker that follows the character's position between shots.

**5. Hoover Dam of humans (Zack ordinary, 14.3 M).** Hypothetical with a counter **in the 3D scene**: a
digital sign counts 0 to 185 lbs (9-11 s), then a big number, then gold 3D text "70 Million" on the wall
at 18.9 s. Fastest editing in the set (13 cuts, median shot 0.35 s in a montage). Compression-like
smearing in many frames (cause unknown). No loop.

**6. Testicle pain (ProfessorOfHow, 195.5 M; Hindi).** Event happens in the first half second; title bar
"3D ANIMATION / The Science Behind..." 0.5-4.5 s; Instagram handle top-left from 5 s; a tag **pinned to the
organ with a leader line** ("4000+ NERVES", 39-43 s) that moves with the camera; a "Pain" bar at 31 s;
end card with a course link. Channel self-promotion takes the last 3-6 s.

**7. Bulletproof jacket (ProfessorOfHow, 190.4 M).** The camera **follows the bullet** from the muzzle
(0-5.5 s, the bullet stays centred while the world slides past). Layer labels added one by one and
tilting with the 3D plates (10-15 s). Subscribe end card (53.8-59.1 s).

**8. Brain-eating amoeba (ProfessorOfHow, 168.8 M).** Names the threat in the first words with a pinned
red tag on the amoeba (1.5-3.5 s). A "double-tap" like prompt with a 3D phone at 6.5-8.5 s. Cross-section
labels at 13-15 s. **Draining green "life bar"** 30-34 s. **Numbered symptom list** builds up 37-44 s.

**9-10. ProfessorOfHow ordinary (9.0 M each).** A talking-head life lesson and a political satire with
pinned tags ("AQI = TEMPERATURE"), source credits and a link to a long video. Different format from the
top 3, so not comparable on technique.

**11. "Touch" (Low Poly Shorts, 86.6 M).** Spoken premise from 0.02 s ("if you touch something and your
atoms align..."). **Six cuts in the first 10 s** (first at 1.2 s, median shot 1.53 s). Yellow lowercase
2-4 word captions at about 67 % height. A red number string "1 in 1,000,000,000..." running off the right
edge (7.5-9.4 s) as the one big-number beat. 3D channel logo placed in the scene at 9.5 s. About 208 WPM,
no silences. **The last sentence is cut off mid-phrase**, so a replay completes it with the opening
line (INFERRED designed loop).

**12. Cannulated cow (Low Poly Shorts, 29.6 M).** Shock premise in the first words, the act already in
progress at frame 0. 7 cuts in 24 s, push-ins, logo in scene. Complete final sentence, no loop.

**13. Bamboo (Low Poly Shorts, 23.4 M).** Growth label "3.97 / 4 feet" at about 4.5 s; cutaway
(inside view) 23-31.9 s.

**14-15. Low Poly Shorts ordinary (2.0 M each).** Liver: first cut only at 9.3 s (one continuous push into
a see-through torso), a red-orange number overlay at about 33 s. Paperclip: one scene per trade with a
**"n/14" progress counter** under the captions from 8.7 s to the end; 22 cuts.

**16. Electrons disappear (What if?, 19.5 M).** Frame 0 already has the moving 3D park, a serif question
title with the key word coloured, an animated atom icon and a **countdown "ELECTRONS DISAPPEAR IN
0:07.766" running in real time** (0-8 s). At 8.0 s the world changes and the timer becomes **"RETURN IN
0:04.979 / TIME SLOWED DOWN 11x"**, counting slowly to 62 s. Italic one-sentence captions at ~67 %.
Only 3 real scene changes (8.0, a whiteout at 41.6, 64.0); everything else is one continuous camera.
Loud accents at 8.3 and 41.6 sit on the two big transitions. End card repeats the title plus one real
fact line.

**17. Oxygen disappears (What if?, 14.4 M).** Same template. The HUD pairs the timer with a **physical
reading that changes** (air pressure 14.7 then 11.6 PSI, -21 %), later "THE GROUND HAS DROPPED 47 FT",
then a **distance counter** to an approaching fireball (644, 445, 205 ft at 56-60 s) that ends as
**"THE FIRE HERE"** (62.5 s). First hard cut at 55.3 s; a whip pan at about 4.5 s.

**18. Pop star 100x taller (What if?, 10.2 M).** A **height/distance counter falls continuously** (2,034 ft
at 0 s, about 650 at 30 s, 20 ft at 60 s), relabelled at the cut at 33 s ("HER HIPS ... LEVEL WITH FLOOR
23"), and ends as **"HER HIPS HERE"** at 62.2 s. Comment CTA on the end card.

**19-20. What if? ordinary (about 0.7 M each).** Same template and production level as the top 3: chained
counters (distance in miles then light-years, universe age, sky temperature; tide height, "Earth's grip"
97 % to 32 %, event-horizon distance then "HERE"). #19 has a designed loop: it "rewinds" to the opening
scene at 69.5 s with the same cracked-glass overlay that frame 0 shows. Since the top 3 and the ordinary
videos share the template, **the template does not explain the 15-30x difference**; topic and premise
relatability are the likely variables (INFERRED).

**21-22. All women / all men disappeared (Simply Simulated, 24.9 M and 11.6 M).** Same countdown opener
("WOMEN VANISH IN 0:07.767"), a white flash at 7.9 s with an accent at 8.3 s, then an **elapsed-time
HUD** ("SECOND 0", "+10 SEC" ... "+116 YEARS") stepping every 4.0 s, big coloured percentages for a few
facts (16-42 s), a births counter (48-52 s). Published the same day as a pair; the first ends with a
"PART 2" teaser for the second (INFERRED series hook).

**23. Every adult disappeared (Simply Simulated, 2.2 M).** No numbers, a chapter header ("1 HOUR LATER /
THE FIRST HOUR"...), cuts every 1.2 s in the first 10 s aligned with people vanishing, a rising pulse of
accents about 0.7 s apart from 68 s to the end.

**24-25. Simply Simulated ordinary (about 66 k each).** The **richest HUDs in the whole set**: a doubling
speed readout, timer, slow-motion factor, milestone labels, light-speed progress bar, a graph (#24); a
5-part progress bar, part labels, time tag and scripture line (#25). Captions are long (up to 20 words).

### A.4 Story position at 5 / 15 / 30 / 45 / 60 s (paraphrased; times ±1 s)

| Video | ~5 s | ~15 s | ~30 s | ~45 s | ~60 s |
|---|---|---|---|---|---|
| Stitches | needle exits, scissors cut the thread (5.5 s) | macro: inflamed halo, fluid in the wound | stitches gone, scar, pull-out to wide (ends 31 s) | - | - |
| Splinters | cut to a skin cutaway with the splinter in the dermis (5.0 s) | swelling, pus particles, pressure arrows (to 21 s) | bump pushes the splinter out, tweezers (ends 30.4 s) | - | - |
| "Touch" | man's head through a wall "like a ghost" | finger pressing a wall, atoms as dot patterns | atom/particle close-ups, fast cuts | (ended 38.8 s, last sentence cut off) | - |
| Electrons (What if?) | countdown under 3 s, park | dark sky, you see stars through your hands | hands turn solid white, glow rising | Earth breaking apart, timer under 2 s | timer about 0.1 s; "ELECTRONS BACK" at 64 s |
| Pop star (What if?) | counter about 1,700 ft | counter about 1,300 ft, star larger | about 650 ft; cut to floor 23 at 33 s | hips about 600-300 ft | 20 ft; "HER HIPS HERE" at 62.2 s |
| All women (Simply) | countdown about 3 s | +10 SEC driverless car, then 90 % nurses | +1 HOUR, 94 % preschool teachers | +1 MONTH, chaos at night | +100 YEARS |

Common thread (INFERRED): in the hits, by ~5 s the viewer knows **what will happen and roughly when**
(a countdown, a falling distance, an action already under way), and by 60 s the promised moment arrives.

---

## B. Techniques library (ranked)

Scoring 1-5 (5 = best): **Ret** = strength of retention evidence in this sample, **Rel** = relevance to
counterintuitive physics simulations, **Cx** = implementation complexity (5 = easy), **Auto** = how
fully the factory can automate it, **Cost** = render/production cost (5 = cheap). Rank = sum.

| Rank | Technique | Ret | Rel | Cx | Auto | Cost | Status in repo |
|---|---|---|---|---|---|---|---|
| 1 | Phenomenon already happening at frame 0, big, camera moving | 5 | 5 | 4 | 4 | 5 | demo shot override; rule in RETENTION.md |
| 2 | Live simulation-driven counter toward a moment ("... HERE") | 4 | 5 | 4 | 5 | 5 | `counter`, `meter` widgets |
| 3 | Countdown to the event, then an explicitly slowed clock | 4 | 4 | 4 | 5 | 5 | `timer` widget (down/up), existing speed badge |
| 4 | Labels pinned to the 3D object (leader line / measuring line) | 4 | 5 | 3 | 4 | 5 | `callout`, `dimension` + projected QA |
| 5 | Spoken question in the first 1-3 s, answer delayed (open loop) | 4 | 5 | 5 | 3 | 5 | `question` widget + `story.loop_*` QA |
| 6 | Force / pressure arrows at the moment of the explanation | 3 | 5 | 4 | 4 | 5 | `arrow` widget |
| 7 | Show the counterfactual on screen ("without X, no Y") | 3 (HYP) | 5 | 3 | 3 | 4 | demo no-push experiment |
| 8 | Dense narration with no dead air (~145-210 WPM) | 3 | 4 | 5 | 5 | 5 | we are at ~202 WPM already |
| 9 | New visual information every ~2-4 s (cut or in-shot change) | 3 | 4 | 4 | 4 | 4 | pacing QA (attention events now count HUD) |
| 10 | One big-number beat (number shown once, large) | 3 | 4 | 5 | 4 | 5 | label cards (existing) |
| 11 | Sound accent on the transition / the number landing | 2 | 4 | 5 | 5 | 5 | cues: `lock`, `blip`, `thud`, risers |
| 12 | Ending that loops into the opening (visual or cut-off sentence) | 2 (HYP) | 4 | 3 | 3 | 5 | existing loop ending |
| 13 | Elapsed-time / chapter / progress HUD | 2 | 3 | 5 | 5 | 5 | `progress` widget |
| 14 | Cutaway / x-ray / macro view of the mechanism | 3 | 5 | 2 | 2 | 3 | manual per episode (existing macro shots) |
| 15 | Short captions (1-4 words) in the lower middle, no colour highlight | 2 | 5 | 5 | 5 | 5 | existing (Blueprint 6) |
| 16 | Camera follows the moving object (bullet-follow) | 2 | 4 | 3 | 3 | 4 | roadmap: `follow` camera type |
| 17 | Paired/series videos, end card teasing the next | 1 (HYP) | 3 | 5 | 4 | 5 | roadmap (needs publishing plan) |

### B.1 Technique cards (evidence first)

**1. Frame-0 phenomenon.** *Function:* removes the "what is this?" scroll moment. *Examples:* Stitches,
stitching visible at 0.0-0.5 s; "Touch" arm reaching at 0.5 s; What if? / Simply Simulated open on a moving
camera with the countdown running. *Placement:* subject in the middle third. *Animation:* slow push-in or
drift, never static. *Problem solved:* the first second is the most-skipped part of any Short.
*Our version:* override the first shot so the chain arch fills the middle of the frame and the camera
is already moving (done in the demo: shot keys 0.15-0.29 m out instead of a wide grassy frame).

**2. Live counter toward a moment.** *Examples:* pop-star height 2,034 ft falling to "HER HIPS HERE"
(0-62 s); oxygen fire distance 644 to 205 ft then "THE FIRE HERE" (56-62.5 s); Zack's in-scene
0 to 185 lbs sign (9-11 s). *Placement:* left middle (TikTok) or in the scene (Zack). *Animation:* digits
change continuously; relabel at a cut. *Problem solved:* turns a long explanation into a visible
progress bar toward a promised moment. *Our version:* `counter`/`meter` widgets read their values from the
simulation series (never typed in), and QA blocks any number not backed by a claim.

**3. Countdown then slowed clock.** *Examples:* "ELECTRONS DISAPPEAR IN 0:07.766" counting in real time
(0-8 s), then "RETURN IN ... TIME SLOWED DOWN 11x" (8-62 s); Simply Simulated's "VANISH IN 0:07.767".
*Problem solved:* tells the viewer exactly when the event happens, and makes slow motion legible as
slow motion. *Our version:* `timer` widget (down to a story event, or up at a rate) next to the existing
"SLOWED 4x" badge. *Caution:* the 0:07.7xx countdown opener is these channels' signature; we use a timer
only when our physics has a real moment to count to, styled as our own label card.

**4. Labels pinned to the object.** *Examples:* "4000+ NERVES" tag following the organ (39-43 s);
bulletproof-jacket layer tags tilting with the plates (10-15 s); Zack's green ring marker. *Our version:*
`callout` (ring + leader + label tracking a 3D anchor) and `dimension` (white measuring line with end caps,
e.g. the arch height growing from 14 to 27 cm). Pre-render QA projects the anchor with the plan's own
camera and flags off-screen, tiny or caption-band labels before anything renders.

**5. Open question.** *Examples:* Zack's "if you..." and "have you ever noticed..." (first words); What if?
titles as questions on screen from frame 0. *Our version:* narration asks; `question` widget pins a "?"
chip until the narration answers, then flips to a short answer chip. QA flags loops answered in under 4 s
or left open over 45 s.

**6. Force arrows.** *Examples:* splinter pressure arrows 17-23 s; Bug Man blue outward / red inward
arrows ~27-29 s. *Our version:* `arrow` widget anchored to a 3D point (red, Blueprint accent), shown only
while the narration names the force.

**7. Counterfactual on screen.** No competitor did exactly this (HYPOTHESIS, from physics-explainer
practice). It is the strongest proof format for a counterintuitive claim: switch the cause off and let
the viewer watch the effect vanish. *Our version:* demo's "no push" experiment: meter 12 % to 0 %, arch
collapses to a drape, then comes back for the loop.

**8-9. Density and visual change.** The data does **not** support "more cuts = more views": Zack's top 3
have zero detected cuts and the fastest-cut video in the set (Hoover Dam, median shot 0.35 s) is an
ordinary one; What if?'s hits run 12-23 s median shots. What the hits share is that **something changes
on screen every few seconds** (a counter, a push-in, a new label, a cut). Narration has almost no dead air
(Low Poly 195-210 WPM, no silences). *Our version:* pacing QA now counts HUD events (appear, settle,
cross, answer) as attention events, so a long shot with a live counter is not flagged as dead.

**10. Big-number beat.** "1 in 1,000,000,000..." (7.5-9.4 s); "70 Million" gold text (18.9 s); Simply's
big percentages. *Our version:* existing off-white label card, once per episode, for the number that
matters (Blueprint 7).

**11. Sound accents.** Loud accents land on the main transitions in What if? (8.3 s after the switch at
8.0; 41.6 on the whiteout) and Simply Simulated (8.3 after the vanish flash; end-card sting at 72.4).
Most accents in the set do **not** sit on hard cuts. *Our version:* story-bound cues (`at:
"hud:drop.settle"`, `"catch@no"`) with license-free synthesised `lock`/`blip`; the sound QA rejects
metronomes and click trains.

**12. Loop ending.** Partial loops in about 4 of 25 (Stitches, McFlurry, the "Touch" cut-off sentence, the Earth-leaves
rewind; Bug Man ends on the opening pair); most hits do not loop. HYPOTHESIS only; our episodes already loop visually.

**13-17.** Progress/elapsed HUDs appear in both the best and the worst Simply Simulated videos, so they
are not the cause of a hit. Cutaways and object-follow cameras are high value but per-episode work.
Series pairing is a publishing tactic to test, not a template to copy.

### B.2 Not supported by this data

- "More cuts = more views" (counter-examples above).
- "A rich HUD makes a hit" (Simply Simulated's 66 k-view videos have the richest HUDs; topic differs).
- "Colour-highlighted caption words help": no video in the set highlights caption words; only titles
  colour one key word.
- Music choice: not measurable from our data.

### B.3 Unsuitable for Counterphysical

- Shock, gore, body-horror and political satire topics (ProfessorOfHow, Low Poly), and talking-head
  formats: off-brand for a calm physics channel.
- Social handles and subscribe/course end cards over the picture (ProfessorOfHow): clutter, and Blueprint
  forbids HUD clutter.
- Real brands as props (McDonald's): legal risk.
- The exact "What if X disappeared for 5 seconds" template, the 0:07.7xx countdown opener, their serif
  title look or "... HERE" wording verbatim: that is copying another channel's concept and branding.
  We adopt the principle (count toward a real physical moment) in our own design.
- Compression smear / AI-video artefacts, unreadable tiny sub-labels, and long 20-word captions.

---

## C. Gap analysis: `final.mp4` (chain fountain, 69.8 s overnight render)

The file analysed is the overnight render (69.8 s). Beat times are from the regression timeline
(`tests/fixtures/regression/chain-fountain.timeline.json`); main has had later chain-fountain rounds since.

| Time | What happens now (OBSERVED) | Gap vs the hits | Recommendation (toolkit) | Priority |
|---|---|---|---|---|
| 0.0-3.4 (hook) | Arch visible at frame 0 but small in a mostly grassy frame | Hits put the phenomenon big in the middle third at frame 0 | Tighter, moving first shot (demo override) | High |
| 3.7-10.6 (setup, wrong guess) | Cuts cluster at 7.2-7.9 s | Fine pace; no visible "what to watch for" | Pin the question when narration asks it later (rehook 27.3 s) | Medium |
| 10.8-14.0 (reality) | Rope-to-arch morph at ~11.2 s with a riser | Good reveal | Keep; a riser that **ends** on the reveal (`riser` cue) | Low |
| 14.2-20.1 (payoff) | Card "≈ 14 cm" only at ~17.4 s, after the narration said it | Number arrives late and static | Live measuring line inside the arch from payoff+0.3 s (`dimension`) | High |
| 20.3-22.5 (double the drop) | No live measure of the drop while "double" is said | Hits show the quantity changing | Drop counter 1.0 → 2.0 m from the simulation (`counter`), punch-in on "doubles" | High |
| 22.8-27.1 (speed) | Card "≈ 4.7 m/s" | OK; one big-number beat | Keep the card; lock accent when it lands | Low |
| 27.3-30.8 (rehook) | Question asked in words only | Open loop not visible | `question` chip "What pushes it up?" until 36.9 s | Medium |
| 31.0-40.7 (links, push) | Macro shots, good | Force not shown where it acts | `arrow` at the pile contact point while "pushes" is said | Medium |
| 41.0-46.4 (rope) | Comparison label "WHITE: A ROPE" in the top badge, far from the object | Hits pin labels to the object | Pinned `callout` on the rope | Low |
| 56.1-63.2 (catch) | Picture nearly static while the narration says "no push, no fountain" | Longest dead stretch; claim not shown | Counterfactual: meter 12 % → 0 %, arch collapses, music drops | High |
| 63.5-67.6 (outro) | Loops to the opening | Good | Keep; meter returns to 12 % for the loop | Low |
| whole | ~202 WPM, 0.25 s gaps between lines | Already at Low Poly density | Keep | - |

Everything in the "High" rows is implemented in `content/episodes/chain-fountain-hud` and verified on
pre-render stills (tight hook, 14 cm measuring line inside the arch, drop counter 1.0 → 1.4 m, arch line
19 → 27 cm, question chip → "the pile", meter 12 % → 3 % → 0 % with the arch collapsing to a drape).

---

## D/E. Implementation and demo (summary)

See `docs/RETENTION.md`. Episodes opt in with a `retention:` block; nothing changes for episodes
without one (tested). All on-screen numbers are driven by the simulation and bound to claims; HUD
layout, overlap, safe area, clutter and open loops are checked before rendering.

---

## F. Roadmap and A/B tests

### F.1 Next build steps (ordered by value / effort)

1. **Word-level timing from the TTS / forced alignment** (e.g. Whisper alignment of the Kokoro audio)
   so `beat@word` cues and captions hit the exact syllable instead of the syllable-weighted estimate.
2. **Follow camera** (`type: follow`) that keeps a moving 3D anchor centred, for bullet-follow-style
   shots of falling or launched objects.
3. **Speed-ramp helper**: ease the simulation clock into slow motion on a story event, with the badge
   and `timer` updating automatically.
4. **Music intensity control**: per-beat intensity levels (not only drop/swell) driven by cues.
5. **Auto camera-change rule**: when no attention event (cut, HUD event, reveal) happens for N seconds,
   suggest a push-in or angle change in the QA report.
6. **Cutaway/x-ray material preset** (semi-transparent outer object) for mechanism shots.
7. **Frame-0 premise title** (a short question on screen for the first 2-3 s): needs a Blueprint
   decision, because the current style forbids title cards. Test before adopting.

### F.2 A/B tests (one variable at a time, same topic, measure in YouTube Studio / TikTok analytics)

Metrics: 3-second hold (viewed vs swiped away), average view duration, % viewed to end, rewatches.
Platforms do not offer true split tests for Shorts; use pairs of comparable episodes, or re-uploads to a
test account, and treat any single result as a hint, not proof.

| Test | Variant A | Variant B | Primary metric |
|---|---|---|---|
| Hook framing | standard opening shot | tight, moving frame-0 phenomenon | 3-s hold |
| Live HUD | static label cards | sim-driven counter / measuring line | average view duration |
| Counterfactual | narration only | on-screen "switch it off" experiment | % viewed to end |
| Open-loop chip | question in words only | pinned question chip | retention dip at the rehook |
| Accents | `auto_accents: false` | `auto_accents: true` | average view duration |
| Caption emphasis | `caption_emphasis: none` | `weight` | average view duration |
| Premise title (if allowed) | no title | 2-3 s question title | 3-s hold |

Record each test (episode, variant, dates, metrics at 48 h and 7 days) in project memory so later
episodes learn from it.
