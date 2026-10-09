"""video-to-skill: turn a single YouTube video into a well-formed agent skill.

The package has two layers:

* a deterministic *capture* engine (download, transcribe, sample frames, build
  an agent-readable package) exposed through the ``video-to-skill`` CLI; and
* a ``SKILL.md`` that teaches an agent how to read that package and distill a
  reusable skill out of the video.

Nothing here is specific to a particular user, project or domain.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
