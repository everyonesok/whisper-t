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
| [0001](0001-chatterbox-multilingual-for-voice-cloning.md) | Chatterbox Multilingual for voice cloning | Accepted |
| [0002](0002-small-en-for-speech-recognition.md) | `small.en` for speech recognition | Accepted |
| [0003](0003-punctuation-not-silence-for-sentence-boundaries.md) | Punctuation, not silence, for sentence boundaries | Accepted |
| [0004](0004-ndjson-streaming-over-websockets.md) | NDJSON streaming over WebSockets | Accepted |
| [0005](0005-serialise-voice-generation.md) | Serialise voice generation, parallelise translation | Accepted |
| [0006](0006-tap-to-toggle-over-hold-to-talk.md) | Tap to toggle over hold to talk | Accepted |
| [0007](0007-server-side-clip-history.md) | Server-side clip history | Accepted |
| [0008](0008-pin-setuptools-below-81.md) | Pin setuptools below 81 | Accepted |
