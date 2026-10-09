# fvts: from video to skill

[![CI](https://github.com/dariovr1/fvts/actions/workflows/ci.yml/badge.svg)](https://github.com/dariovr1/fvts/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

## You understood the tutorial. You'll forget it anyway. Now you can turn it into a skill

We all know the ritual. You find the perfect YouTube video, the one that explains exactly the thing you need right now. You watch it, nod along, and feel smarter for twenty minutes. Three months later you're back, dragging the progress bar to minute 12, because all that's left in your head of the whole procedure is the name of the tool.

It's not your fault. A video is a poor container for a procedure. A tutorial is great to watch once and useless to rewatch three times. What you actually need isn't the video, it's the method inside it, written down in a format you can reuse.

That's the problem `fvts` goes after. It takes a single YouTube video and turns it into an agent skill: a text file your assistant can read and follow whenever it's needed, even if you closed the video months ago. It isn't tied to one agent either. It works in Claude Code, in opencode, or in any tool that reads the open skill format.

## Two pieces, not one

There's more here than a downloader. Two halves do different jobs.

The first is the capture engine: it downloads the video, fetches the transcript, samples representative frames and writes a package an agent can read. The second is the skill itself, a `SKILL.md` that tells the agent how to read that package and distill a clean, self-sufficient skill out of it.

The split makes sense. Downloading and frame extraction are pure determinism, and we don't want the model adding its own ideas there. Understanding and writing stay the agent's job.

```
YouTube URL ──► capture engine ──► package ──► (agent reads it) ──► SKILL.md
                (download,          (transcript +
                 transcribe,         frame grids +
                 frames)             MANIFEST)
```

## The radar: understanding a video without downloading it

Before downloading anything there's `probe`, a diagnosis that never touches the video. It tells you the title, the duration, whether subtitles exist, and an estimate of the size for the video version and for the audio track alone. So far that's just good service. The interesting part is the verdict.

The way the project picks how to capture a video is a small piece of common sense. It samples five low-resolution frames at fixed fractions of the duration (12%, 30%, 50%, 70%, 88%), compares them pairwise using the Hamming distance between their average hashes, and looks at how much they change. If the mean difference stays under a threshold of 6, the video is almost motionless: a talking head, a slide, a fixed webcam. In that case the streaming mode is the right choice: it grabs only the audio and seeks frames on demand. If the difference climbs, the video is dynamic (frequent cuts, heavy editing), and downloading the whole thing is worth it.

Five frames of a few KB each to decide whether to download hundreds of megabytes. These lazy heuristics beat plenty of elaborate pipelines: they do 80% of the work with 2% of the effort. There's also a courtesy built in: under 5 minutes the radar steps back, because streaming isn't worth the trouble.

There are four modes, each with its reason: `auto` lets the radar decide, `stream` never saves the video, `full` always downloads, and `audio` ignores frames, which suits content where only the words exist.

## The part that counts: actually watching the video

This is what sets the tool apart from a "summarize this video" prompt.

The skill forces the agent to really watch the video. It reads the `MANIFEST` first, then the timestamped transcript, then the frame grids in order. And when a grid cell holds dense text (code, a terminal, a README, a table, a diagram with small labels), the agent must open the full-resolution frame before quoting or relying on that content. Building the skill from the transcript alone is forbidden, and so is trusting the thumbnail for the details that matter: repository names, commands, URLs, numbers.

That rule saves the result. A model working only from what it heard tends to invent the flag that doesn't exist, the parameter that "should" be there. Making it look at the pixels before writing a command is a different level of honesty.

Then there's the final quality gate, the one I like most: no invented facts. Every command, flag, version and number must trace back to the transcript or to a high-resolution frame. If something couldn't be confirmed, it gets flagged as unverified, never presented as fact just because it's plausible. Precision comes before fluency.

## What comes out

At the end you have a folder for each captured video:

```
runs/<video_id>/
├── MANIFEST.txt      # what this run produced + how to "watch" it
├── transcript.txt    # timestamped transcript [mm:ss - mm:ss]
├── transcript.json   # same, structured
├── info.json         # title, channel, duration, chapters, heatmap
├── grids/grid_NNN.jpg    # contact sheets, labelled '#index @ timestamp'
├── frames/frame_NNN.jpg  # individual frames (for high-res details)
└── frames.json       # frame index with timestamps
```

From that material comes the distilled skill, which has to stand on its own: whoever reads it shouldn't need the video in front of them.

A real example is already in the repo: [git-interactive-rebase-cleanup](examples/git-interactive-rebase-cleanup), produced from a [tutorial on interactive rebase](https://www.youtube.com/watch?v=tukOm3Afd8s). The skill contains the commands to reorder and rewrite local commits, taken from the video's frames, plus the places where people go wrong. You don't need to have seen a single second of the original video.

## Install

```bash
git clone https://github.com/dariovr1/fvts
cd fvts

python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

# Base install: subtitles + frames (no speech-to-text).
pip install -e .

# If you need speech-to-text fallback for videos without captions:
pip install -e ".[whisper]"
```

ffmpeg is provided automatically by [`imageio-ffmpeg`](https://pypi.org/project/imageio-ffmpeg/), so you don't need a system ffmpeg. Python 3.10 or later is required.

## Quickstart

The command-line tool is called `video-to-skill`.

```bash
# 1. Get a download-free diagnosis and a mode recommendation.
video-to-skill probe "https://www.youtube.com/watch?v=XXXXXXXXXXX"

# 2. Capture the video into ./runs/<video_id>/.
video-to-skill watch "https://www.youtube.com/watch?v=XXXXXXXXXXX"

# Force a full download (e.g. to reuse the file or maximise scene precision):
video-to-skill watch "<url>" --mode full

# Or, for talking-head content where only the words matter:
video-to-skill watch "<url>" --mode audio
```

Then point your agent at the skill:

```
Read skills/video-to-skill/SKILL.md and follow it on ./runs/<video_id>.
```

### CLI reference

```
video-to-skill probe <url> [--language LANG]
video-to-skill watch <url|file> [options]
```

Useful `watch` options: `--mode {auto,stream,full,audio}`, `--outdir DIR`,
`--language LANG`, `--glossary "Term One, Term Two"`, `--no-captions`,
`--whisper-model`, `--max-frames`, `--fps-floor`, `--force`.
Run `video-to-skill watch --help` for the full list.

### Using it as a skill

`skills/video-to-skill/SKILL.md` is a self-contained skill. Copy it to your
agent's skills directory:

- Claude Code: `~/.claude/skills/video-to-skill/SKILL.md`
- opencode: `~/.config/opencode/skills/video-to-skill/SKILL.md`

## Everything runs locally, with a caveat

The project runs on your computer and nowhere else. No external API keys: speech-to-text is local with faster-whisper, and frames are extracted with ffmpeg. The input is a **single** video; for a series, run it once per episode. The license is MIT and the version is still 0.1.0, so this is alpha territory.

Which brings the usual honest warning. The produced skill is a text artefact, and the quality gate reduces the model's errors but doesn't eliminate them. If the tutorial teaches a procedure you'll actually rely on, reread the result before trusting it. The tool saves you the work of synthesis, not the need for judgment.

## Development

```bash
pip install -e ".[dev]"
ruff check .
pytest                      # offline unit tests
VTS_NETWORK_TESTS=1 pytest  # also run the network smoke tests
```

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE). `fvts` downloads content from third-party platforms; respect the
source terms of service and copyright when you use it.
