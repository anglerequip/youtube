# Prompt audit, 2026-11-27

Procedure: Anthropic's `prompt-audit.md` from the official `anthropics/skills` repo (`skills/claude-api/shared/prompt-audit.md`).
It looks for instructions that no longer fit the model, the project or each other. Shorter text is not the goal.
Line numbers below refer to `anglerequip/youtube` at `1916b0b` (main) and `anglerequip/anglermind` at `37e903b` (master),
before any of the proposed edits.

## Assumptions

- **Scope.** Every file that reaches a Claude model as text in both repos:
  - youtube: `CLAUDE.md`, `docs/ARCHITECTURE.md` (CLAUDE.md says to read it first), `docs/QA.md`, `docs/styles/DUO.md`,
    `docs/styles/BUILD.md`, and the two reviewer briefs that the pipeline writes for the independent Claude reviewers:
    `INSTRUCTIONS` in `factory/qa/critic.py` (picture) and in `factory/qa/sound.py` (sound).
  - anglermind: `CLAUDE.md`, `AGENTS.md`, `CLAUDE-old.md`, and the Ask AnglerMind assistant prompt (`src/lib/assistant/`).
  - Not read: `.claude/settings*.json` and `.mcp.json` (they can hold secrets), user-level config outside the repos,
    project memory (not in either repo).
- **Target model.** The instruction files and reviewer briefs are read by Claude Code sessions, so they are audited
  against Claude Opus 5.5, the model running this audit. The Ask AnglerMind assistant runs on
  `@cf/meta/llama-3.3-70b-instruct-fp8-fast` on Cloudflare Workers AI (`src/lib/assistant/provider.ts:77`), not a Claude
  model. This procedure's model-behaviour rules are about Claude, so they don't apply there and that prompt was not audited.

## Summary

The biggest problems are stale facts and one broken file, not dated prompting style. The Claude-facing text is mostly
written the way current models want: plain rules with their reasons, little shouting, and no "think step by step"
leftovers.

1. **anglermind `CLAUDE.md` is cut off, and its key business rules are missing.** The file Claude Code loads ends inside an
   unclosed code block (line 141). The affiliate-link rules (never an untagged Amazon link, never guess an ASIN), the gear
   rules (spin and casting compatibility, wire leaders for pike), the design direction, and the safe way to launch the dev
   server are now only in `CLAUDE-old.md`, which Claude Code never loads. The diff closes the code block. Bringing the rules
   back is your decision (finding A2).
2. **youtube `CLAUDE.md` sends the repeat check to the wrong place.** It says to check `content/episodes/` for repeats, but
   that folder holds 6 episodes while the topic ledger holds 51 topics. The ledger is the real repeat check.
3. **The Sound Reviewer is told the video is 60-75 s long**, but the length rule is 15-60 s. `docs/ARCHITECTURE.md` also
   still describes the first version: Matplotlib visuals, Kokoro as the main voice, publishing "not started".

Counts: Group 1 (dated prompt text): 3 findings. Group 2 (instruction files): 10. Group 3 (tool descriptions): not
applicable, because no Claude-facing tool definitions are in scope. Group 4 (request config): not applicable, because
neither repo calls the Claude API (youtube uses `LLM_PROVIDER` manual, and the anglermind assistant is Llama).

## Findings

### High confidence

**Y1. The repeat check points at the wrong source**
- Location: youtube `CLAUDE.md:9-10`
- Evidence: "Check `content/episodes/` so you don't repeat one."
- Pattern: Group 2, volatile specifics.
- Why it's stale: `content/episodes/` has 6 folders on main. The topic ledger `content/ledger/topics.jsonl` has 51 entries,
  and `factory/autopilot/ledger.py:1-11` describes itself as the check that runs "right before scripting". A session that
  follows CLAUDE.md as written can repeat a topic that was already posted.
- Action: rewrite. Point to `python -m factory.autopilot ledger check "<core claim>"` and the ledger file. Commit `f0fb3d1`.

**Y3. The Sound Reviewer is given the wrong video length**
- Location: youtube `factory/qa/sound.py:230`
- Evidence: "You are the sound team for a 60-75 s vertical science Short."
- Pattern: Group 2, volatile specifics (in a prompt).
- Why it's stale: the length rule is 15-60 s (`CLAUDE.md:15-16`, `factory/configuration.py:44-45`). Telling a reviewer to
  expect a longer video skews how it judges density and fatigue.
- Action: rewrite to "15-60 s". Commit `a3dd131`. Only the prompt string changes, no logic.

**A1. anglermind `CLAUDE.md` ends in the middle of a code block**
- Location: anglermind `CLAUDE.md:138-141`
- Evidence: the file ends with the `curl ... http://localhost:3000/` line. There is no closing fence and no instruction
  for what to do with the result.
- Pattern: Group 2, volatile specifics (the repository itself shows the defect).
- Why it matters: the dev-server safety rule says to check before starting, then stops. The model is left to guess what
  comes next, and the unclosed block can swallow anything added later.
- Action: rewrite. Close the block and add the reuse rule from `CLAUDE-old.md:82` ("reuse it rather than spawning a second
  copy that fights the first for the port"). This adds no new command. Commit `efd010d` on the anglermind branch.

**A2. Business and safety rules that only live in a file Claude Code never loads (flagged, your decision)**
- Location: anglermind `CLAUDE-old.md:49-84` (dev-server launch), `:86-91` (design direction), `:139-148` (affiliate link
  rules), `:150-163` (gear recommendation rules), `:99-137` (reference docs index). None of these are in `CLAUDE.md`, and
  `CLAUDE.md` does not import `CLAUDE-old.md` (its only import is `@AGENTS.md`).
- Evidence (examples): "Never emit an untagged Amazon link; it earns nothing." "An ASIN must be real ... Never guess one:
  a wrong product link can get the Associates account pulled." "A spinning rod never gets a baitcasting reel." "never answer
  a pike question without wire in it." "`NEXT_CPUS=2` is the setting that actually matters."
- Pattern: Group 2, instruction files that disagree, and keep-list item 1 (context is never cruft).
- Why it's flagged and not fixed: these are prohibitions and launch commands, and the procedure says to flag rather than
  move those. Git history can't settle it either: both files were last edited in `df77c14` (2026-09-13).
- What you have to decide: copy these sections back into `CLAUDE.md` (recommended: the affiliate and gear rules protect
  revenue and safety), or say they were dropped on purpose and delete `CLAUDE-old.md` so nobody follows it by mistake.

### Medium confidence

**Y2. CLAUDE.md describes only the 2D episode route**
- Location: youtube `CLAUDE.md:13`, `:23-25`
- Evidence: "copy the structure of `falling-slinky`" and "Create `sim.py` with `class Sim(Scene)`".
- Pattern: Group 2, volatile specifics.
- Why it's stale: most episodes are 3D. They use `plan.py` with `SCENE = "<name>"` and `build_plan(tl, ...)`, drawn by
  `renderer/scenes/<name>.js` (`factory/production.py:121-155`, `content/episodes/falling-slinky-3d/plan.py:15,112`).
  Step 5 already mentions `plan.py`, but steps 3-4 never explain it.
- Action: rewrite steps 3-4 to cover both routes. The y=0.25-0.90 rule is kept for 2D only. Commit `17ef36a`.

**Y4. The Sound Reviewer brief assumes a female narrator**
- Location: youtube `factory/qa/sound.py:245`
- Evidence: "effects or music loud while she speaks."
- Pattern: Group 2, volatile specifics.
- Why it's stale: the narrator voice changed (`CLAUDE.md:47-48`), and DUO episodes have a male presenter (`CLAUDE.md:49`).
- Action: rewrite to "while someone is speaking". Commit `4872a00`. The same phrase in the finding message at
  `sound.py:15,214` is report text, not prompt text, and is left alone.

**Y5. Section 13 is worded as a change from an older version**
- Location: youtube `CLAUDE.md:246`, `:270`, `:271-272`
- Evidence: "Every 3D render now goes through", "Depth of field and ground cover now make this read", "(AO shows it now;
  a floating object looks worse than before)".
- Pattern: Group 1d, migration-relative phrasing. The model never saw the "before".
- Action: rewrite as plain present-tense rules. Commit `5c6e584`. Caesar's planned visual rework may rewrite section 13
  anyway. If so, drop this commit.

**Y6. The style modules don't point at section 13**
- Location: youtube `CLAUDE.md:180`, `docs/styles/DUO.md:4`, `docs/styles/BUILD.md:4`
- Evidence: "sit on top of sections 1-11".
- Pattern: Group 2, two files that disagree. Section 13 (Look v3 and shot craft) was added after these lines. It applies to
  "every 3D render", which includes DUO and BUILD, but the module docs list only 1-11.
- Action: rewrite to "sections 1-11 and 13". Commit `550dea2`.

**Y7. DUO.md still lists the replaced voice ids**
- Location: youtube `docs/styles/DUO.md:83`
- Evidence: "(... replaced `zYcjlYFOd3taleS0gkk3`)", "(... replaced `0ggs85h7hrWz8ExXnsBc`)".
- Pattern: Group 2, history narrative. The retired ids add nothing to the current rule, and a model can copy the wrong id.
- Action: remove the "replaced" notes and keep the current ids. Commit `76036fd`.

**Y8. ARCHITECTURE.md describes the first version of the factory** (CLAUDE.md says to read this file first, so every
session gets these facts)
- `docs/ARCHITECTURE.md:56`: "Visuals | numpy simulations drawn with Matplotlib". But most episodes use the three.js renderer
  in headless Chromium (`renderer/`, `factory/production.py:121`). Rewrite, commit `7516fb0`.
- `:57`: "Voice | Kokoro-82M ... ElevenLabs is a drop-in". But `CLAUDE.md:47-48` (newer, 2026-11-20) makes ElevenLabs the
  narrator and Kokoro the fallback. Rewrite to match CLAUDE.md, commit `b3120a8`.
- `:91-95`: "About **1 minute per Short**". But `docs/QA.md:43` says a full render takes 1.5-2.5 hours. Rewrite to say the
  1-minute figure is the 2D route, commit `a084302`.
- `:3-4`, `:105`: "Status as of 2026-11-19" and Phase 5 (YouTube upload and scheduling) "not started". But
  `factory/autopilot/cloud_post.py` and `.github/workflows/publish.yml` do exactly that. Drop the dated status line and
  update the Phase 5 row, commit `ea8034b`. Phases 3, 6 and 7 are left alone because I couldn't confirm their state from the repo.
- Pattern: Group 2, volatile specifics.

### Flagged (no edit proposed)

**F1. "Approval in Telegram" (safety rule, your wording)**
- Location: youtube `CLAUDE.md:40`, `docs/ARCHITECTURE.md:23,61,70,104`, `docs/QA.md:7,78,127`, `factory/qa/gate.py:8,79,107`.
- Evidence: "Nothing is ever published without the human's approval in Telegram."
- Why it's flagged: approvals happen in the project chat and the cloud queue posts what is queued. No Telegram bot exists in
  the repo, and Phase 4 is "not started". The rule is a safety rule, so the procedure says to flag it and not reword it.
- Suggested wording if you agree: "Nothing is ever published without Caesar's approval in the project chat. Only
  approved videos go into `autopilot_queue/`. Do not add code paths that upload from the production workflow."

**F2. The AnglerMind rebrand isn't in this CLAUDE.md**
- youtube `CLAUDE.md:1` ("Counterphysical Shorts factory") and `:241` ("Animated with real physics by Counterphysical") still
  describe the old channel, while the project now makes AnglerMind marketing videos.
- That change belongs to the open rebrand PR (#16, `docs/BRAND.md`), so this audit leaves it to that PR to avoid a conflict.

**F3. Dated attributions (low)**
- Lines such as "(Caesar, 2026-11-20)" are the history-narrative idiom.
- They're kept because they tell a session that the rule is the owner's own decision.

**F4. The em-dash rule's long list of places (low)**
- anglermind `CLAUDE.md:41-76` lists twenty places the character is banned. That matches the "kitchen-sink" padding
  pattern, but the rule is a real constraint enforced by `npm run no-em-dash`, so it's kept as is.

### Checked and clean

- Picture reviewer brief (`factory/qa/critic.py:42-85`). The numbered steps stay because order matters: the blind first
  impression must come before reading the intent. The "Do not accept..." lines are the reviewer's stated stance, each with
  its reason. The one capitalised "do NOT open the first critique" comes with its reason (an independent second review).
- Sound reviewer brief, apart from Y3 and Y4.
- `docs/QA.md`. Its history ("Built 2026-11-19 after Caesar rejected three videos") is the reason for the rules, which counts
  as context.
- anglermind `AGENTS.md`. It's the Next.js 16 vendor block. Its warning about training data is real context: the repo runs a
  newer Next.js with its own docs in `node_modules/next/dist/docs/`.

## Verification

- Every path and command named in the edits was checked against the repository (`ledger check` was run and returned a verdict).
- youtube `python -m pytest -q`: 105 passed and 6 failed. The 6 are renderer regression tests that call `node renderer/render.mjs`
  and fail because this container has no renderer npm packages. None of the edits touch `renderer/` or any code path.
- No em dashes were added in either repo.
