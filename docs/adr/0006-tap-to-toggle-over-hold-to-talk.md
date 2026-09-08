# ADR-0006: Tap to toggle over hold to talk

**Status:** Accepted
**Date:** 2026-09-06

## Context

The original interaction was hold-to-talk: press and hold the mic, release to
translate. That suited the app's first shape — one short sentence at a time — because
an unambiguous start and end meant the app never had to guess when speech finished.

Chunking changed the job. Multi-sentence input is now the point, and holding a button
for twenty-plus seconds while speaking several sentences is physically uncomfortable
and fights the feature it gates.

## Decision

Tap the mic to start, tap "Stop and translate" to finish. Tapping anywhere on the
recording screen also stops.

## Consequences

- Comfortable for the multi-sentence case the app is now built around.
- Loses hold-to-talk's accident-proofing, so the safeguards matter more: a 30-second
  cap, Escape to abort, and stop on window blur — the last of which matters
  specifically because an unattended tab would otherwise hold the microphone open.
- A `holding` flag is still needed to cover a second tap arriving while the browser's
  permission prompt is open, which would otherwise leave a recording with nothing to
  stop it.

## Alternatives considered

- **Hold to talk** — the incumbent. Right for one short sentence, wrong once
  multi-sentence input became the purpose.
- **Tap to start, automatic stop on silence** — what Google and Apple do, and the
  nicest to use. Needs live silence detection running on the audio stream while the
  user speaks, which is real new machinery rather than a rewiring. Deferred.
