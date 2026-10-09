---
name: git-interactive-rebase-cleanup
description: |
  Tidy up local Git history with an interactive rebase: reorder commits, reword
  a commit message that has a typo, and squash/fixup/drop commits before you
  share them. Use this when the user wants to "clean up my git history",
  "reorder these commits", "fix a commit message before pushing", "squash my
  local commits", or asks how to use `git rebase -i`. Applies only to commits
  that have NOT been pushed yet.
metadata:
  version: "0.1.0"
---

# Git interactive rebase: reorder and reword local commits

Use `git rebase -i` to rewrite a run of local commits — fixing the order of
commits and correcting messages — before anyone else has them.

## When to use

- Local (unpushed) commits are in the wrong order.
- A commit message has a typo or is unclear.
- You want to reword, squash, fixup or drop commits into a cleaner series.

## When NOT to use

- Any of the commits are already **pushed/shared**: rebasing rewrites history and
  will desynchronise everyone else. Work on shared history with `git revert`.
- You only need to fix the **latest** commit message: `git commit --amend` is
  simpler.

## Prerequisites

- Git installed, and a text editor configured (`git config core.editor`) — the
  rebase opens it twice: once for the plan, once for any reword.
- The commits to change are local only.

## Procedure

1. Inspect the history in a compact form and locate the problems (a typo, an
   out-of-order commit), then identify the commit **immediately before** the
   earliest one you need to touch:

   ```bash
   git log --oneline
   ```

2. Start the interactive rebase from that prior commit's hash:

   ```bash
   git rebase -i <hash-before-problems>
   ```

   Your editor opens the plan file (`.git/rebase-merge/git-rebase-todo`), one
   line per commit, oldest at the top.

3. Edit the plan:

   - **Reorder** — cut a line and paste it where it belongs; lines are applied
     top to bottom.
   - **Reword** — change `pick` (or `p`) to `reword` (or `r`) on the commit whose
     message you want to change.
   - Other keywords you can use: `edit` (`e`), `squash` (`s`), `fixup` (`f`),
     `drop` (`d`), `exec` (`x`), `break` (`b`).

   Save and quit.

4. Git replays the commits in the new order. When it reaches a `reword` it stops
   and reopens the editor with that commit's message: fix it, save and quit. If
   it stops for another reason, handle it and continue:

   ```bash
   git rebase --continue
   ```

5. If a conflict appears (common when reordering), resolve the files, then:

   ```bash
   git add <resolved-files>
   git rebase --continue
   ```

   To back out completely: `git rebase --abort`.

6. Verify the result:

   ```bash
   git log --oneline
   ```

   The commits should be in the intended order with the corrected messages.

## Gotchas

- **Never rebase shared commits.** If a commit is pushed and others may have it,
  rewriting it breaks their history.
- **Deleting a line drops that commit**, and deleting every line aborts the
  rebase. Use `drop` if you mean it.
- `reword` changes only the message; `edit` stops so you can also change the
  commit's content.
- Reordering can produce conflicts; they are less likely when the commits touch
  different paths, and normal otherwise. Resolve them, do not panic.

## Verification

- `git log --oneline` shows the new order and corrected messages.
- If anything went wrong, `git reflog` still has the pre-rebase HEAD, so you can
  recover: `git reset --hard HEAD@{1}`.

## Source

- Video: *Git Rebase Interactive :: A Practical Example* (AZdev) —
  https://www.youtube.com/watch?v=tukOm3Afd8s
