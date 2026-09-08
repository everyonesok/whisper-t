# ADR-0002: `small.en` for speech recognition

**Status:** Accepted
**Date:** 2026-09-05

## Context

Transcription was taking 9.7 seconds for a 4-second clip — a third of the total
wait, on the least valuable stage. Benchmarking on this machine showed the beam
size was irrelevant and the model size was everything:

| Model | Time on a 4s clip | Transcript |
|---|---|---|
| large-v3-turbo, beam 5 | 9.61s | identical |
| large-v3-turbo, beam 1 | 9.85s | identical |
| **small.en, beam 1** | **1.14s** | **identical** |

Byte-identical output at one eighth the time, on clean dictation from a good
microphone.

## Decision

Use `small.en`, set as `WHISPER_MODEL` at the top of `pipeline.py` so it is a
one-line change.

## Consequences

- Total pipeline time dropped from ~23s to ~15s for a single sentence.
- **English input only.** The `.en` models are monolingual, so the app can only
  transcribe English being spoken. This is fine while English is always the source
  language, and would need reverting for any use case where the user speaks the
  target language — pronunciation practice, for instance.
- Accuracy may suffer on heavy accents, background noise, or unusual vocabulary.
  Not observed in use, but not stress-tested either.

## Alternatives considered

- **`large-v3-turbo`** — 8x slower for identical output on this audio. Correct
  choice if multilingual input is ever needed, and the swap is one line.
- **Reducing beam size** — measured, made no difference. The bottleneck was model
  size, not search width.
- **Groq's hosted Whisper** — free tier, very fast, but adds a network dependency
  and a second account to a pipeline that otherwise runs locally.
