# September closeout quality hold — 2026-09-10

## Status

This audit file supersedes the temporary September closeout / recovery publishing attempts created on 2026-09-09 and 2026-09-10.

Publishing remains frozen for Walk to Earn chapters 131-185 until the rebuilt text passes the full repository quality gates and a separate explicit publishing audit authorizes the exact upload range.

## Confirmed platform state

The following chapters were confirmed by publisher logs as successfully created/scheduled on Fanqie before the quality hold:

- 111-115: scheduled for 2026-09-16 00:00
- 116-120: scheduled for 2026-09-17 00:00
- 121-125: scheduled for 2026-09-18 00:00
- 126-130: scheduled for 2026-09-19 00:00

The following chapters are not approved for publication:

- 131-185: not published by the last confirmed run; chapter 131 was rejected by Fanqie duplicate-content detection and the batch stopped before 132-185.

## Root cause

The rejected chapters were not duplicate because the automation submitted the same chapter twice. They were rejected because the generated local text reused a highly visible paragraph frame across multiple chapters, including phrases like:

- `这条记录只落在第X章第Y段`
- repeated explanation paragraphs about money, routes, rain, bus choices, and not forcing extra steps
- repeated chapter-title insertion at the end of nearly every paragraph

This violated the novel quality standard even when each chapter had a different number, title, step count, location, or small object. Platform duplicate detection correctly treated the prose as large-scale repeated content.

## Rebuild status

As of commit `118808228c201c5b1f0b9c5a45adbb08aca26fa0`, chapters 131-185 have been replaced in the repository with scene-based prose instead of the rejected template-generated text.

The template-marker searches for `这条记录只落在`, `旁边写着`, and the artificial `第X章第Y段` pattern return no matches on the current repository text.

This rebuild is not a publishing approval. The content still needs the full automated gate results plus a cold-read audit before any Fanqie mutation is allowed.

## Safety rollback completed

The temporary September publishing / recovery workflows and direct upload helper scripts have been removed.

The Fanqie mutation safety cap has been restored from `90` to `30` in `novels/walk-to-earn/platform-sync/config.json` after the failed closeout flow left it elevated.

## Hard rule going forward

No remaining chapter may be published merely because it passes character-count checks or platform upload tests.

Before any new platform mutation for chapters 131-185:

1. The chapter must be rewritten as a complete scene with its own conflict, objects, dialogue, rhythm, and ending turn.
2. The chapter must not contain template markers such as `第X章第Y段`, `这条记录只落在`, or repeated section wrappers.
3. The chapter must pass the repository length gate.
4. The chapter must pass narrative, dialogue, humanizer, prose, and meta-narrative review.
5. A cold-read audit must explicitly state that the text does not read as batch-generated filler.
6. Only after the above can a new queue operation be created and authorized.

## Publishing rule

Do not use the deleted temporary recovery workflows or scripts as precedent. Future upload workflows for this book must be created only after a quality audit file marks the exact chapter range as passed.
