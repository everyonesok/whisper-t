# Architecture Decision Records

Short records of decisions that were genuinely decisions — where there was a real
alternative and a reason one was chosen. Not documentation of how the code works;
the code already does that.

## Why these exist, and why they aren't a single file

A `decisions.md` that you keep editing drifts. You change your mind, edit the line,
and the reasoning that led to the original choice is gone — so six months later you
reverse a decision without knowing why it was made.

**ADRs are append-only.** You never edit an accepted one. When something changes you
write a new record that supersedes it, and the old one stays, marked. That makes the
history explicit instead of overwritten, and it makes contradiction impossible by
construction rather than by discipline.

They live in the repo so they version with the code. A decision and the code it
explains move together, which is the one thing a separate notes file can never do.

## Format

Adapted from Michael Nygard's original. Four sections, kept short:

- **Context** — what was true that forced a choice
- **Decision** — what was chosen
- **Consequences** — what this costs, including the bad parts
- **Alternatives** — what else was considered and why it lost

## Adding one

Copy `template.md`, number it next in sequence, and don't renumber anything.
Numbers are identifiers, not an ordering you maintain.

If you're changing a decision, don't edit the old record. Write a new one, and add
`**Superseded by:** ADR-00XX` to the old one's status line. That single line is the
whole mechanism.

## Index

| # | Decision | Status |
|---|---|---|
| [0001](0001-chatterbox-multilingual-for-voice-cloning.md) | Chatterbox Multilingual for voice cloning | Superseded by 0010 |
| [0002](0002-small-en-for-speech-recognition.md) | `small.en` for speech recognition | Accepted |
| [0003](0003-punctuation-not-silence-for-sentence-boundaries.md) | Punctuation, not silence, for sentence boundaries | Accepted |
| [0004](0004-ndjson-streaming-over-websockets.md) | NDJSON streaming over WebSockets | Accepted |
| [0005](0005-serialise-voice-generation.md) | Serialise voice generation, parallelise translation | Accepted |
| [0006](0006-tap-to-toggle-over-hold-to-talk.md) | Tap to toggle over hold to talk | Accepted |
| [0007](0007-server-side-clip-history.md) | Server-side clip history | Accepted |
| [0008](0008-pin-setuptools-below-81.md) | Pin setuptools below 81 | Accepted |
| [0009](0009-crossfade-sentence-chunks.md) | Crossfade sentence chunks when joining | Superseded by 0012 |
| [0010](0010-qwen3-tts-on-mlx-for-voice-cloning.md) | Qwen3-TTS on MLX for voice cloning | Accepted |
| [0011](0011-gradient-visual-language-and-system-type.md) | Gradient visual language and system type | Partly superseded by 0017 |
| [0012](0012-stream-one-generation-per-message.md) | Stream one generation per message | Accepted |
| [0013](0013-speech-in-speech-out-no-text-to-voice.md) | Speech in, speech out — never text to voice | Accepted |
| [0014](0014-live-voice-enrolment-no-imported-audio.md) | Live voice enrolment, no imported audio | Accepted (mobile) |
| [0015](0015-one-voice-per-device.md) | One voice per device, locked to it | Accepted (mobile) |
| [0016](0016-verify-the-speaker-on-every-translation.md) | Verify the speaker on every translation | Proposed |
| [0017](0017-own-visual-direction-drop-frame-dots.md) | An own visual direction, starting by dropping the frame dots | Accepted |
| [0018](0018-thumb-zone-layout.md) | Thumb-zone layout | Accepted |
| [0019](0019-translate-for-the-ear-numbers-as-words.md) | Translate for the ear: numbers as words | Accepted |
