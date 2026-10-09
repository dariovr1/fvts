# Security policy

## Reporting a vulnerability

Please do not open a public issue for a security problem. Instead, report it
privately, for example through GitHub's "Report a vulnerability" button under the
repository's **Security** tab. Include:

- what the problem is and its impact;
- steps to reproduce (redact any private URLs);
- the `video-to-skill --version` and your OS/Python version.

You will get an acknowledgement as soon as possible, and credit in the fix if you
want it.

## Scope

`video-to-skill` runs entirely on your machine. It performs network requests only
when fetching a video and its captions from the platform you point it at, and it
shells out to a bundled ffmpeg binary. Things worth reporting include:

- command or path injection through input (URLs, file names, options);
- a network request that can be steered to an unintended host or scheme;
- unsafe handling of downloaded files.

## Notes for users

- Downloaded video, audio and transcripts are written under `runs/` (or your
  `--outdir`) and can contain third-party copyrighted content. That folder is
  git-ignored by default; do not publish it.
- Only process content you are allowed to use, and respect the source platform's
  terms of service.
