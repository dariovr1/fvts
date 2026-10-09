# Contributing

Thanks for considering a contribution.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

The `whisper` extra (heavier, pulls in the speech-to-text stack) is only needed
if you want to exercise the transcription fallback:

```bash
pip install -e ".[whisper,dev]"
```

## Checks

```bash
ruff check .
pytest                            # offline tests
VTS_NETWORK_TESTS=1 pytest        # also run network smoke tests
```

CI runs `ruff` and the offline tests on Python 3.10–3.12. Keep them green.

## Guidelines

- Keep the capture engine deterministic and dependency-light.
- No user-, project- or domain-specific values in code or defaults. Anything
  domain-specific (a glossary, a language) belongs in a CLI flag.
- Add a test for every behaviour change. Network-dependent tests must carry the
  `network` marker.
- One skill, one purpose: the output `SKILL.md` should stay self-contained.

## Reporting bugs

Include the output of `video-to-skill --version`, your OS/Python version, and the
exact command you ran (redact private URLs).
