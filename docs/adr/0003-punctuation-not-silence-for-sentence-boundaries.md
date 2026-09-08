# ADR-0003: Punctuation, not silence, for sentence boundaries

**Status:** Accepted
**Date:** 2026-09-05

## Context

Generating one long clip for a multi-sentence recording is slow and degrades
(see ADR-0001). Splitting the transcript into sentences lets each one be translated
and spoken separately, so the first becomes playable while the rest are still
generating — 21.6s to first audio instead of 89.6s on a three-sentence recording.

That requires knowing where sentences end. Two obvious sources were tested and both
failed:

- **Voice-activity detection pauses** split mid-sentence: "watch the street" and
  "wake up." came back as separate chunks.
- **Whisper's own segment timestamps** produced identical boundaries with VAD
  disabled entirely, which showed VAD was never the cause. Whisper breaks roughly
  every 5 seconds regardless of grammar.

Neither is a sentence boundary. Both are timing artefacts.

## Decision

Ignore all timing-based boundaries. Buffer the transcript text and cut only when
the accumulated text ends in `.`, `?` or `!` — using the punctuation Whisper already
transcribes reliably. Implemented as `SentenceBuffer` in `pipeline.py`.

## Consequences

- Chunks are complete, self-contained sentences, which translate correctly and
  sound natural spoken alone.
- A run-on with no full stop would buffer forever, so there is a safety valve: past
  25 words, cut at the last comma; past 40 with no comma, cut mid-clause. The gap
  between the two limits is deliberate grace so a long-but-real sentence finishes
  naturally.
- When the valve fires you get an audible seam, because each chunk is generated with
  its own intonation contour. Accepted as the price of a bounded wait.
- VAD stays enabled regardless — it is what stops Whisper hallucinating words from
  silence (see the README), it is just not the chunking mechanism.

## Alternatives considered

- **Commas as a routine boundary** — tested. Fragments translate acceptably but
  drift in register without surrounding context, and one Russian fragment came back
  with a stray Chinese character. Joined audio ran 8.5s against 6.6s for the same
  sentence and sounded like separate statements. Kept only as the emergency cut.
- **`...` and em dashes as boundaries** — Whisper never emits either. Tested on a
  trailing-off sentence and a parenthetical aside; both came back with plain commas.
