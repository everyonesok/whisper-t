# ADR-0021: Speak only the owner's part of a message

**Status:** Proposed. Depends on ADR-0016's speaker check, which hasn't been
measured.
**Date:** 2026-10-02

## Context

While the owner was showing echo to a friend, the friend interrupted
mid-recording. echo heard one message:

> "Chuck Roberto Wait, so if I were to say something would it just be your
> voice we can test it"

and spoke all of it, in Spanish, in the owner's cloned voice. The friend's
question ("would it just be your voice?") came out in the owner's voice.

The speech recogniser writes down *what* was said, not *who* said it, so
every voice the microphone picks up becomes one block of text. Interruptions
like this are common in the setting echo is built for: conversations at a
table, with family around.

This is the case ADR-0013 and ADR-0016 exist for: the owner's voice saying
words the owner didn't say. ADR-0016 proposes checking the speaker once per
message. That would reject the whole message here, or, if the owner spoke
most of it, accept the friend's words along with it.

## Decision (proposed)

Check the speaker per piece of a message, not once per message (*speaker
diarisation*). Speak the pieces that match the enrolled voice in that voice.
Show anyone else's pieces as text only, marked as someone else's (for
example "Someone else said: 'Wait…'"), and never voice them.

This is ADR-0016's check at a finer grain, with its fail-safe kept: when
unsure, show text rather than speak.

## What has to be measured before accepting

- **Short interruptions:** "Wait" is about half a second, which is exactly
  the short-input weakness ADR-0016 already lists. Can a piece that short be
  told apart at all?
- **Extra clues:** whether loudness (the owner is usually closest to the
  phone) or a sudden change of voice inside a message helps where the voice
  match alone can't.
- **The owner on a bad day:** the first example was recorded while the owner
  had a cold. A check that splits the owner's own speech into "someone else"
  is worse than no check. Clips recorded while ill are useful test cases.
- **Where to cut:** pieces are currently cut at sentence ends, but an
  interruption can start mid-sentence, as it did here.

## Consequences (if accepted)

- A friend's interruption, a TV in the background or a child talking over
  the owner stays out of the owner's voice.
- What echo shows and what it speaks can differ for one message, so the
  result screen needs a clear way to mark unspoken text.
- More work per message, which has to fit in the time already spent
  transcribing (the same budget as ADR-0016).

## Alternatives considered

- **Do nothing:** interruptions get spoken in the owner's voice. That's
  harmless as a demo, and exactly the misuse the other safeguards are there
  to prevent.
- **Let the owner remove sentences before they're spoken:** quick to build,
  but deleting words can change the meaning ("I can't come. Just kidding."),
  so it partly reopens the editing route ADR-0013 closed.
- **Hold-to-talk instead of tap-to-talk:** reduces how long the microphone is
  open, but doesn't stop someone talking over the owner while it is.
