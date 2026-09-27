# ADR-0012: Stream one generation per message

**Status:** Accepted (on the `qwen-streaming` branch)
**Date:** 2026-09-26

## Context

Since ADR-0003, speech has been split into sentences, and each sentence was
translated, voiced and played separately. That split existed for speed: with
Chatterbox, one long clip meant a 90-second wait, while sentence 1 could play
while sentence 3 was still being generated.

Two things changed.

**The joins sounded like different people.** Every generation re-guesses the
voice. Measured on the owner's own test recordings, pitch jumped 2–7 semitones
between neighbouring sentences, with a change in brightness on top, which is
roughly the gap between two different speakers. A test of fixes on the same
passage, three runs each (average / worst jump at a join, in semitones):

| Approach | Average | Worst |
|---|---|---|
| Separate sentences (as it was) | 5.2 | 10.9 |
| Lower sampling temperature | 3.6 | 7.5 |
| Same random seed per sentence | 4.3 | 6.4 |
| One generation for the whole message | 3.1 | 5.0 |

Part of the remaining jump is natural (a question rising at the end). A fixed
seed produced identical audio every run: consistent, but no more matched.
In a blind-ish A/B listen of two pairs, the owner's verdict on one generation
was "much better".

**Streaming removed the reason for the split.** Qwen3-TTS (ADR-0010) streams:
the first 0.3 seconds of audio arrive about 0.5 s after generation starts,
however long the message. One generation no longer means one long wait.

## Decision

Voice the whole message in **one streamed generation** and play it as it
arrives.

- **Server:** transcribe and split into sentences as before (ADR-0003), and
  translate each in parallel, but voice the joined translation once. Send it
  as NDJSON `audio` events, each ~0.3 s of raw 32-bit float PCM
  (little-endian, base64), already watermarked. `translate/done` carries the
  per-sentence `{source, text}` pairs so the page can still show rows. The
  history file is exactly the audio that was streamed.
- **Watermark each piece with `StreamWatermarker`:** each piece is marked
  together with the 0.32 s of audio before it, and 20 ms is held back and
  crossfaded into the next pass.
- **Browser: `StreamPlayer`** schedules each piece on the Web Audio clock to
  start at the exact sample where the previous one ends. The audio context runs
  at 24 kHz, the model's own rate, so pieces are never resampled one by one.
  Playback starts once 0.6 s is buffered; if it ever runs dry it shows
  "buffering…" and resumes after 0.5 s more.
- **Result screen:** one play/pause, a progress bar and time, and one row per
  sentence with the one being spoken highlighted. Tapping a row plays from
  there.
- **Leaving mid-stream aborts the request,** and the server stops generating
  when the connection closes. A `VOICE_LOCK` stops two requests (two tabs)
  from ever running the model at once (ADR-0005).

## Consequences

- **First sound ~4 s sooner, and no joins.** On the same 17-second reference
  recording: heard at ~6.0 s against 9.9 s, with generation finished at
  16.4 s against 17.8 s. On a short three-sentence clip, first sound was
  measured in the page at 4.8–5.2 s.
- **Playback is sample-exact.** Rendered offline, the player's output differed
  from the source by ~2×10⁻¹², floating-point rounding, across 11 irregular
  pieces. Seeking lands on the exact sample. A stream fed at half realtime
  started after 1.28 s, stalled exactly where the audio ran out, and recovered
  three times, with the position never moving backwards.
- **The highlight is an estimate.** A single stream has no sentence markers,
  so each sentence's start is worked out from its share of the translated
  text (13 characters a second, plus a pause per sentence), and rescaled to
  the real duration once the stream ends. It's usually right, but can be off
  by a fraction of a second on unevenly paced speech.
- **No per-sentence audio.** You can no longer replay "just sentence 2" as a
  separate clip; tapping it plays from there onwards.
- **Watermark: detected at 1.00, and no clicks.** Watermarking each piece
  naively (without context) made the sample jumps at joins 4× larger, and the
  largest jump in the whole signal, a faint tick three times a second. With
  context and crossfade, the jumps at joins are identical to watermarking
  the whole clip at once. Cost: ~11 ms per 0.3 s piece.
- **The live audio is watermarked too,** not just the saved file. Played out
  loud is how echo's output actually leaves the machine.
- **Bandwidth is irrelevant on localhost** (~130 KB/s of base64 float32). A
  remote deployment would want 16-bit PCM or a compressed codec.
- **Long messages generate only just faster than realtime** (1.12× measured on
  a 27-second message; 1.42× on the reference clip). The start buffer and
  rebuffer path exist for the case where a busy, fanless laptop falls behind.
- **Frame callbacks aren't reliable for UI state.** Browsers slow or pause
  `requestAnimationFrame` in tabs that aren't visible (measured: ~18 frames a
  second in the hidden test pane). The transport redraws immediately on every
  action and state change, and uses frames only for smooth motion.
- **ADR-0009 (crossfade at joins) no longer applies to new clips:** there are
  no joins. `join_wavs()` still runs, on a single file.

## Alternatives considered

- **Keep separate sentences, stream each one:** fast, but it keeps the change
  of speaker at every join, the problem that prompted this.
- **Lower temperature or a fixed seed:** tested; see the table above.
  Neither removes the joins.
- **Watermark only the saved file:** simpler, but the audio people actually
  hear, which is what can be recorded, would be unmarked, and the README's
  "everything generated here is watermarked" would stop being true.
- **Watermark each piece without context:** measured clicks; see above.
- **`<audio>` elements, one per piece:** each start has scheduling jitter,
  and the gaps are audible. Media Source Extensions don't accept raw PCM or
  WAV in Chrome without an encoder.
- **WebSocket instead of NDJSON:** same reasoning as ADR-0004; a one-way
  stream per request is all this needs.
- **16-bit PCM to halve the payload:** unnecessary on localhost; float32 goes
  straight into Web Audio with no conversion.
- **Exact sentence timings from a forced aligner:** accurate highlighting at
  the cost of another model and more latency. Not worth it for a highlight.
