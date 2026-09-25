# ADR-0010: Qwen3-TTS on MLX for voice cloning

**Status:** Accepted (on the `qwen-streaming` branch)
**Date:** 2026-09-25

## Context

ADR-0001 chose Chatterbox Multilingual because it was the only model that was
both multilingual and permissively licensed, and accepted its speed (~0.5x
realtime, ~12 seconds per sentence) as the price. It named the trigger for
revisiting: a model that is fast on Apple Silicon, speaks Russian, and is
permissively licensed for code and weights.

Qwen3-TTS had been rejected on speed: 0.2x on an M4 under PyTorch. A monthly
watch routine found an Apple-native MLX port (`mlx-audio`) claiming 1.67x. On
reading, that figure was for the CustomVoice variant (preset voices), not
Base (the one that clones), so it was measured here instead, on an M3:

| Model (6-bit, MLX) | First sound | Streaming | Whole clip |
|---|---|---|---|
| Qwen3-TTS 1.7B Base | 0.55s | 1.4x | 0.8x |
| Qwen3-TTS 0.6B Base | 0.3s | 1.9x | 0.8x |

Russian word accuracy, checked by transcribing the output back with a
multilingual Whisper: 6% of words not heard as intended for 1.7B, against 5%
for Chatterbox on the same check. The owner judged both sizes to sound like
him, 1.7B slightly better. Apache-2.0 for code and weights.

End to end in echo, a three-sentence Russian recording played its first
sentence at 9.9s, against ~21s with Chatterbox. Each sentence took ~4s for
~6s of speech.

## Decision

Use **Qwen3-TTS 1.7B Base, 6-bit, via `mlx-audio`** for voice generation,
with **stream=True** internally (twice as fast as whole-clip mode in this
library), joining the pieces into one WAV per sentence so the server and page
are unchanged.

Apply the **Perth watermark** to every generated clip ourselves. Chatterbox
did this internally and the README promises it; Qwen3-TTS doesn't.

## Consequences

- **Languages drop from 22 to 9.** Kept: Chinese, French, German, Italian,
  Japanese, Korean, Portuguese, Russian, Spanish. Lost: Arabic, Danish, Dutch,
  Finnish, Greek, Hebrew, Hindi, Malay, Norwegian, Polish, Swahili, Swedish,
  Turkish. They remain available on `main`.
- **A second environment.** Chatterbox pins `transformers==5.2.0`; `mlx-audio`
  needs `>=5.14`. The two cannot share an install, so this branch runs from
  `.venv-mlx`. `main` and its `.venv` are untouched and still work.
- **Qwen needs a transcript of the reference clip.** Whisper makes it once and
  saves `reference.txt` (gitignored: it is the owner's own words). It is
  regenerated whenever `reference.wav` is newer, so re-recording the voice
  can't silently leave a stale transcript behind.
- **Perth's dependencies are undeclared.** Its package metadata lists none,
  but it imports torch, librosa, soundfile, pydub, pyrubberband and audioread,
  and hides a missing one as `'NoneType' object is not callable` — the same
  failure as ADR-0008. `librosa` was found missing exactly that way. All are
  pinned by hand in `requirements.txt`. The watermark was verified with
  Perth's own detector (0.00 before, 1.00 after), not just by running.
- **Occasional nonsense.** One whole-clip generation in the test set slid into
  English-sounding syllables. None of the streaming ones did. The sample is
  small: three sentences, one speaker, one language.
- **Streaming is still internal.** The page receives whole sentences as before.
  Sending audio to the browser as it is generated is the next step and a
  separate decision.
- **Startup is faster:** ~10s to load instead of ~50s, after a one-time
  ~2.7 GB download.

## Alternatives considered

- **Stay on Chatterbox** — keeps 22 languages and its built-in watermark, at
  four to five times the wait. Remains the choice on `main`.
- **Qwen3-TTS 0.6B** — faster (1.9x, first sound 0.3s) but made more word
  errors in Russian (10% vs 6%) and sounded slightly less like the owner. Both
  are already faster than realtime, so the extra speed buys little.
- **Qwen for its 9 languages, Chatterbox for the other 13** — impossible in one
  process because of the `transformers` conflict. Workable as two servers, at
  the cost of twice the moving parts and the 13 languages staying slow.
  Deferred until a missing language actually matters; the family use case
  needs one language per family, not 22.
- **Chatterbox under MLX or CoreML** — two ports appeared in September 2026.
  The CoreML one lacks Russian and cloning; the MLX one publishes no speed
  figure. Would keep all 22 languages if one proves fast. Being watched.
- **Drop the watermark and say so in the README** — honest, but walks back a
  public promise for no real saving.
