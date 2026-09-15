# ADR-0009: Crossfade sentence chunks when joining

**Status:** Accepted
**Date:** 2026-09-14

## Context

ADR-0003 chunks speech by sentence and generates each one separately. Each
clip carries its own intonation contour — a rise at the start, a fall at the
end — so butted together they sound like separate statements rather than one
utterance. ADR-0003 recorded this as an accepted cost.

Voicebox (jamiepine/voicebox), which independently arrived at the same
chunking approach, solves it with a user-adjustable 0–200ms crossfade between
clips. That prompted revisiting whether the cost was actually necessary.

## Decision

Overlap the last 50ms of each clip with the first 50ms of the next, fading one
out as the other fades in, wherever clips are joined into one file.

Do this **once, server-side**, in `join_wavs()`. The browser's Save button now
fetches the server's already-joined history file rather than joining
client-side; the client joiner stays only as a fallback if history saving
failed.

## Consequences

- Measured on a real three-sentence clip: the seams became the *smoothest*
  points in the file — sample-to-sample jumps of 0.015 and 0.005 at the two
  seams, against 0.345 for ordinary speech transients elsewhere.
- The joined file is 50ms shorter per seam. Negligible.
- Only the joined files (history, Save) get the crossfade. Live playback still
  plays each sentence as a separate audio element, so the seam is still
  audible *while listening in real time*. Fixing that means overlapping
  separate audio elements on the client, which is a different and harder
  change.
- One joiner instead of two means the crossfade logic exists in exactly one
  place. The client-side joiner is now legacy fallback code and could be
  removed once history saving is trusted.

## Alternatives considered

- **No crossfade** — the incumbent. The seam was a documented, accepted cost.
  It turned out to be cheap to fix, which changes the calculus.
- **Crossfade in both joiners** — would mean decoding samples in two formats
  (int16 and float32) in JavaScript, duplicating logic that would drift from
  the Python. Rejected in favour of one joiner and a fetch.
- **A user-adjustable duration** as Voicebox has — sensible for a general
  voice workstation with many models and voices; unnecessary here, where
  every clip comes from the same model at the same sample rate. A constant
  is enough, and it's one line to change.
- **Equal-power (sqrt) fade** instead of linear — marginally better in theory
  for uncorrelated signals. At 50ms the difference is inaudible and linear
  is simpler.
