# ADR-0016: Verify the speaker on every translation

**Status:** Proposed — needs measuring before it can be accepted
**Date:** 2026-10-01

## Context

Because of ADR-0013, every translation starts with a fresh recording of
whoever is speaking, which is a voice sample collected at no extra cost. Comparing it
with the enrolled voice (ADR-0014) would mean the cloned voice only speaks
when its owner is the one talking. Every use becomes a check, with no extra
step for the user.

This is speaker verification, which is a weaker idea than it sounds as a
*password*: banks' voice ID was beaten with AI clones (see ADR-0015). Here,
though, it isn't the only lock. It sits behind Face ID, and its job is
narrower: stopping someone else's voice driving the owner's clone on an
already-unlocked phone.

## Decision (proposed)

Before generating any speech, compare the input recording against the
enrolled voice with an on-device speaker-verification model. If it doesn't
match, don't speak in the owner's voice. Show the text translation, with a
message that the speaker wasn't recognised.

## What has to be measured before accepting

- **False rejections:** the owner turned away when tired, ill, in a
  noisy room or speaking quietly. For a family app this is the bigger risk:
  being refused by your own translator at dinner is a product failure.
- **Short inputs:** "Sorry, I can't come" is about a second of speech. How
  reliable is verification on that?
- **Speed:** it has to fit inside the time already spent transcribing,
  without adding to the wait.
- **Which model:** on-device speaker-embedding models exist (ECAPA-style),
  and Apple's frameworks may offer something. Neither has been evaluated.

## Consequences (if accepted)

- Someone holding the unlocked phone can't make the owner's voice speak
  their words.
- A fallback is needed for borderline matches. Text-only output fails safe:
  the meaning still gets through, just not in the owner's voice.
- A recording of the owner played into the microphone would pass. But
  because of ADR-0013 it could only produce a translation of what the owner
  had actually said, which is low value to an attacker.

## Alternatives considered

- **Rely on Face ID alone:** protects opening the app, not each use. An
  unlocked phone handed across a table bypasses it.
- **Verify only at enrolment:** stops cloning someone else at setup
  (ADR-0014), but not someone else using the owner's set-up voice afterwards.
