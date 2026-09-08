# ADR-0001: Chatterbox Multilingual for voice cloning

**Status:** Accepted
**Date:** 2026-09-06

## Context

The voice cloning step is the whole point of the app and the slowest part of it —
about 12 seconds per sentence, roughly 0.5x realtime on an M3. That is slow enough
to be worth revisiting, so six zero-shot cloning models were surveyed against an
independent Apple Silicon benchmark.

Three things have to be true at once: fast on Apple Silicon, multilingual including
Russian, and permissively licensed for both code and weights. No model in September
2026 has all three.

## Decision

Use Chatterbox Multilingual (Resemble AI). MIT licensed, 23 languages including
Russian, and accept ~0.5x realtime.

## Consequences

- Roughly 12 seconds to generate one sentence, which is the dominant cost in the
  pipeline and the main thing a user feels.
- Long inputs degrade: sampling drops from ~15 to ~1 tokens/sec and the model can
  force an early stop on repetition. This is why the app chunks by sentence
  (see ADR-0003) rather than generating one long clip.
- Russian stress placement is guessed, because the optional `russian_text_stresser`
  package is not on PyPI. Audible occasionally — *кофе* can drift toward *кафе*.
  Harmless for conversation; would be disqualifying for a pronunciation-teaching
  use case.
- MIT licensing keeps every future option open, including commercial use.

## Alternatives considered

| Model | Apple Silicon | Russian | Licence | Why not |
|---|---|---|---|---|
| Pocket-TTS | 8.8x | no | CC-BY | 6 languages only |
| OpenVoice v2 | 5.9x | no | MIT | ~6 languages only |
| XTTS-v2 | 2.0x | yes | CPML | **non-commercial** — the closest miss |
| Chatterbox Turbo | 1.1x | no | MIT | English only, so it cannot speak a translation |
| OmniVoice | 0.2x | yes | CC-BY-NC | slower than the incumbent, and garbles words |

Four of the five were eliminated on language coverage or licence, not on speed.
XTTS-v2 is the one to revisit if it is ever relicensed: it is four times faster and
covers Russian, and only the non-commercial terms rule it out.
