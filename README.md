# video-to-skill

[![CI](https://github.com/dariovr1/video-to-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/dariovr1/video-to-skill/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

Turn **one** YouTube video into a **well-formed, reusable agent skill** (`SKILL.md`).

`video-to-skill` gives an agent two things it needs to learn a technique from a
tutorial and turn it into something reusable:

1. a deterministic **capture engine** that downloads a video, gets a transcript,
   samples representative frames and writes an agent-readable package; and
2. a **`SKILL.md`** that teaches the agent how to read that package and distill a
   clean, self-contained skill out of it.

It is agent-agnostic: the same `SKILL.md` works in Claude Code, opencode or any
tool that reads the open skill format. Nothing is tied to a specific user,
project or domain.

## Why

Tutorials are a rich source of reusable procedure, but a video is a poor unit of
reuse. `video-to-skill` converts "a person explaining how to do X on YouTube"
into "a `SKILL.md` an agent can pick up and follow" — with the code, commands and
gotchas pulled from the video, and a quality gate that rejects invented facts.

## How it works

```
YouTube URL ──► capture engine ──► package ──► (agent reads it) ──► SKILL.md
                (download,          (transcript +
                 transcribe,         frame grids +
                 frames)             MANIFEST)
```

The capture engine never requires you to choose how to download: a lightweight
"radar" samples a few frames by remote seek and decides between a full download
(visually dynamic video) and a streaming mode that only pulls the audio and seeks
frames on demand (static talks and slideshows).

## Install

```bash
git clone https://github.com/dariovr1/video-to-skill
cd video-to-skill

python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

# Base install: subtitles + frames (no speech-to-text).
pip install -e .

# If you need speech-to-text fallback for videos without captions:
pip install -e ".[whisper]"
```

ffmpeg is provided automatically by [`imageio-ffmpeg`](https://pypi.org/project/imageio-ffmpeg/) —
you do not need a system ffmpeg.

## Quickstart

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

## Output layout

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

## CLI reference

```
video-to-skill probe <url> [--language LANG]
video-to-skill watch <url|file> [options]
```

Useful `watch` options: `--mode {auto,stream,full,audio}`, `--outdir DIR`,
`--language LANG`, `--glossary "Term One, Term Two"`, `--no-captions`,
`--whisper-model`, `--max-frames`, `--fps-floor`, `--force`.
Run `video-to-skill watch --help` for the full list.

## Using it as a skill

`skills/video-to-skill/SKILL.md` is a self-contained skill. Copy it to your
agent's skills directory:

- Claude Code: `~/.claude/skills/video-to-skill/SKILL.md`
- opencode: `~/.config/opencode/skills/video-to-skill/SKILL.md`

## Scope

- Input: a **single** video. For a series, run it once per episode.
- Everything runs locally; no external API keys. Speech-to-text is local
  (faster-whisper) and frames are extracted with ffmpeg.
- The produced skill is a text artefact. Review it before you trust it: the
  quality gate reduces but cannot eliminate model error.

## Development

```bash
pip install -e ".[dev]"
ruff check .
pytest                      # offline unit tests
VTS_NETWORK_TESTS=1 pytest  # also run the network smoke tests
```

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE). `video-to-skill` downloads content from third-party platforms;
respect the source terms of service and copyright when you use it.
