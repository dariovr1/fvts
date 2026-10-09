---
name: video-to-skill
description: |
  Turn a single YouTube tutorial into a well-formed, reusable agent skill
  (SKILL.md). Use this when the user wants to capture the technique, workflow or
  procedure taught in a video and get back a clean, self-contained skill that can
  be reused later: "make a skill from this video", "turn this tutorial into a
  skill", "extract the method from this video", "we can learn this from that
  talk". It covers both the capture step (download / transcribe / frame sampling
  through the `video-to-skill` command) and the distillation step (authoring the
  output SKILL.md with verified code, commands and gotchas).
metadata:
  version: "0.1.0"
---

# video-to-skill — from one video to one reusable skill

This skill produces a **new, self-contained skill** that captures a technique
demonstrated in a video. You are the one who reads the video (transcript +
frames) and writes the skill; the `video-to-skill` command only prepares an
agent-readable package. Do not treat the package as a summary — read it and
build understanding from it.

It works on **one video at a time**. For a series, repeat the whole flow per
episode and merge only if the episodes are genuinely one procedure.

## Prerequisites

The `video-to-skill` command must be available (see the project README to
install it, typically `pip install "video-to-skill[whisper]"`). Verify with:

```
video-to-skill --version
```

If it is not installed, stop and tell the user what to install before
continuing.

## Step 0 — Scope contract

If it is not already clear, ask the user (one short question, not a
questionnaire):

- **What should the produced skill cover?** "The whole workflow shown" vs "only
  part X of it". A skill with one clear purpose beats a skill that tries to
  capture an entire 40-minute video.
- **Does the skill need runnable code?** If yes, the produced skill should ship
  the code/manifest the video used, not just describe it. If the video shows a
  UI-only tool, say so and write a UI-driven skill instead.
- **Target runtime**: the skill is agent-agnostic by default (a `SKILL.md` with
  `name`/`description` frontmatter). Confirm if the user wants it tailored to a
  specific tool.

Write the answers down; they are the acceptance criteria at Step 6.

## Step 1 — Probe before downloading

For a URL, run a download-free diagnosis first and show the numbers to the user:

```
video-to-skill probe "<URL>"
```

It prints title, duration, subtitle availability and — crucially — the radar
verdict (static vs dynamic) plus estimated sizes for the video versus audio
only. Use it to pick the capture mode, and ask the user if the trade-off is not
obvious (a long static talk: streaming is much lighter; a dynamic editing
tutorial: full download is worth it). If the user already stated a preference,
skip the question and pass the matching `--mode`.

## Step 2 — Capture the video

```
video-to-skill watch "<URL_OR_LOCAL_FILE>" --mode <auto|stream|full|audio>
```

- default `--mode auto` lets the radar choose; force `stream` (no video stored),
  `full` (always download) or `audio` (no frames — only for purely verbal
  content).
- Use `--language <code>` to pin the caption/transcription language and
  `--glossary "Term One, Term Two"` when the video is about a specialised
  domain: it biases the transcriber toward the correct spelling of product names
  and jargon.
- Output goes to `runs/<video_id>/` (override with `--outdir`). If a run already
  exists, the command skips it; use `--force` to redo.

For anything longer than a couple of minutes this can take a while (network for
the download, CPU for transcription). Run it in the background and wait for the
notification rather than blocking.

## Step 3 — Actually watch the video

Read the package **in this order**:

1. `MANIFEST.txt` — structure of the run, and whether frames exist (in `audio`
   mode there are none).
2. `transcript.txt` — the spoken track with `[mm:ss - mm:ss]` timestamps.
3. `grids/grid_000.jpg`, `grid_001.jpg`, ... **in order**, using the image
   reader. Each cell is labelled `#index @ timestamp`. Read all of them; this is
   how you build the visual understanding.
4. For any detail finer than a grid cell, open the matching high-resolution
   `frames/frame_NNN.jpg` (index/timestamp from `frames.json`).

**For technical content this step is mandatory.** Whenever a grid cell shows
dense text — code, a README, a terminal, a table, a dashboard, a diagram with
small labels — open the full-resolution frame before you quote or rely on it.
Do not build the skill from the transcript alone and do not trust a thumbnail
for specifics (repository names, commands, URLs, numbers). If the question
depends on something visual and the run is in `audio` mode, say so and offer to
re-run with `--mode stream` or `full`.

## Step 4 — Distill

Separate **what the video shows** from **how to reproduce it**. Extract:

- the goal and when the technique applies;
- prerequisites (accounts, versions, files, prior steps);
- the ordered procedure, with the exact commands, code, flags and settings as
  they appear in the video (from Step 3's high-resolution frames);
- the gotchas, defaults and "don't do this" moments the author mentions;
- a way to verify the result — a command, an observable state, a check.

Discard the presenter's asides, sponsor reads and anecdotes unless they carry a
decision-relevant fact.

## Step 5 — Author the output skill

Write a new `SKILL.md` in the run folder (e.g. `runs/<video_id>/skill/SKILL.md`).
It must be self-contained — a reader must not need the video.

Required frontmatter:

```yaml
---
name: <short-kebab-case-name>
description: |
  <One paragraph: what the skill does AND when to use it, with concrete trigger
  phrases a reader would actually say. This is what makes the skill discoverable.>
metadata:
  version: "0.1.0"
---
```

Body, at minimum:

- **When to use / when not to** (so the skill is not applied blindly).
- **Prerequisites**.
- **Procedure** — numbered, with commands and code in fenced blocks, exactly as
  usable by a reader who never saw the video.
- **Gotchas** — the pitfalls the video exposes.
- **Verification** — how to confirm it worked.

If the skill needs code or files, add them under `skill/scripts/` and
`skill/assets/` and reference them by relative path. Keep one skill to one
purpose.

## Step 6 — Quality gate (do not skip)

Before delivering, verify every item:

1. **Frontmatter valid**: `name` is kebab-case, `description` states both what
   and when, with real trigger phrases.
2. **No invented facts**: every command, flag, version and number traces back to
   the transcript or a high-resolution frame. If you could not confirm
   something, mark it explicitly as unverified — never present a plausible guess
   as fact.
3. **Self-contained**: the skill reads correctly with the video deleted.
4. **Single purpose**: it does not smuggle in unrelated side-quests.
5. **Runnable**: if the video shows steps you can execute here, run them and fix
   the skill until they work; if you cannot, say which step is unverified.
6. **Prose clean**: run the text through a style/humanizer pass if one is
   available; at minimum, remove filler and marketing tone.

If any item fails, fix the skill rather than shipping a caveat around it.

## Step 7 — Deliver and (optionally) install

1. Present the produced `SKILL.md` (and any scripts) to the user, with the
   video's title/channel/URL as the source.
2. Append a pointer to the run log the project keeps (if the repository has one,
   e.g. `INDEX.md`): skill name, source video, run folder, date.
3. Offer to install it into the user's skills directory:
   - Claude Code: `~/.claude/skills/<name>/SKILL.md`
   - opencode: `~/.config/opencode/skills/<name>/SKILL.md`
   Do not install silently; ask first.

## Notes

- Everything runs locally. The only network access is fetching the video and any
  embedded captions from the platform.
- Captions, when present, are taken as-is; auto-generated ones can carry their
  own recognition errors. When a term matters and looks wrong, re-check it
  against the frames or run with `--no-captions` to force speech-to-text.
- The produced skill is a draft until a human verifies it against the video.
