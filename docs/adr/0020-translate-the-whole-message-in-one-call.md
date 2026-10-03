# ADR-0020: Translate the whole message in one call

**Status:** Accepted
**Date:** 2026-10-02

## Context

echo split each message into sentences and translated every sentence in its
own call, all at once. That was fast, and it fed the result screen one row
per sentence. But each call saw only its own sentence.

The first native-speaker review (2026-10-02) found the cost. In the dinner
invitation, "It's been way too long" became «Сколько лет, сколько зим!», a
good idiom placed in the middle. A Russian speaker opens with it, as a
greeting. The translator for that sentence couldn't know an invitation came
before it.

The whole message is always available: echo waits for the speaker to stop
before translating. Splitting threw that context away.

## Decision

A message of two or more sentences goes to the translator in one call, with
the sentences numbered. It may reorder or merge them the way a fluent speaker
would, and answers in structured JSON: rows in spoken order, each listing the
English sentences it covers. The voice speaks the rows in that order, and the
result screen shows them in that order, each paired with its English.

A one-sentence message keeps the plain call, since there is nothing to
reorder.

If the call fails, or the rows don't use every English sentence exactly once,
echo falls back to the old per-sentence method rather than speak a
translation with a hole in it.

## Consequences

- In testing, greetings moved to the front («Сколько лет, сколько зим!»,
  «Мы так давно не виделись!»), and choppy sentences merged naturally:
  "I'll be a bit late. The traffic is terrible." became «Я немного опоздаю —
  ужасные пробки».
- **About a second slower** on multi-sentence messages: translation took
  2.0–3.3 s against 1.1–2.1 s per sentence in parallel (one run each). It
  adds directly to the wait before the voice starts.
- The result screen's rows can now be in a different order from what was
  said, and one row can show two English sentences. That's correct, but may
  surprise a speaker who expects their own order.
- Whether a message counts as several sentences depends on the speech
  recogniser's punctuation. A message spoken without pauses can come through
  as one long sentence; it still goes to the translator whole, just without
  the reordering instructions.
- Reordering doesn't fix everything: the translator kept «Кстати» ("by the
  way") when it moved "Long time no see, by the way" to the front, which
  reads oddly as an opening. Not yet checked by a native speaker.

## Alternatives considered

- **Keep per-sentence calls, but show each one the whole message as context:**
  keeps the speed and the one-to-one rows, but can't move a phrase to the
  front, which is the fix the review asked for.
- **Translate the whole message as plain text and split the result on
  punctuation:** loses the pairing between each Russian row and its English.
- **A fast first draft, corrected a moment later** (as live note-taking apps
  do): solves a different problem, translating before the speaker has
  finished. echo already has the whole message, so one pass is enough.
- **Use the whole-message call for single sentences too:** about a second
  slower with nothing to gain.
