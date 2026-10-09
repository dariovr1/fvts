# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-10-09

### Added
- Capture engine: `video-to-skill watch` downloads a video, obtains a transcript
  (platform captions or local faster-whisper), samples frames and writes an
  agent-readable package.
- `video-to-skill probe`: download-free diagnosis with a static/dynamic radar and
  size estimates.
- Capture modes: `auto`, `stream` (no full download), `full`, `audio`.
- `skills/video-to-skill/SKILL.md`: agent-agnostic methodology to distill a
  reusable skill from the captured package.
- Offline unit tests and an opt-in network smoke test.
