# Examples

Each folder is a skill produced by `video-to-skill` from one video, included as a
worked demonstration. They are ordinary skills — copy one into your agent's
skills directory to use it.

## git-interactive-rebase-cleanup

Produced from *Git Rebase Interactive :: A Practical Example* (AZdev).
It captures the procedure for reordering and rewording local commits with
`git rebase -i`, with the commands and gotchas read from the video's frames.

To reproduce the capture (network required):

```bash
video-to-skill watch "https://www.youtube.com/watch?v=tukOm3Afd8s" --language en --mode full
```

Then have your agent follow `skills/video-to-skill/SKILL.md` on the run folder.
