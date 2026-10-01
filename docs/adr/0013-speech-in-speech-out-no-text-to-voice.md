# ADR-0013: Speech in, speech out — never text to voice

**Status:** Accepted
**Date:** 2026-10-01

## Context

echo makes speech in a cloned voice, which is the core capability behind a
deepfake. Most voice-cloning tools take typed text and speak it in the cloned
voice, so anyone holding the voice can make it say anything.

echo never worked that way. The server has no "speak this text" endpoint: the
only route to a cloned voice is `/api/translate`, which takes a recording,
transcribes it, translates it and speaks the translation. That was an
accident of the product idea, but on review it is echo's strongest safeguard,
and nothing so far records it as a rule.

## Decision

The cloned voice only ever speaks **a translation of what was just said into
the microphone**. echo will not offer typed text to cloned voice: no text box,
no "edit before speaking", no API that takes text and returns the owner's voice.
This applies to the prototype and to any mobile app.

## Consequences

- Holding the phone, or the voice, isn't enough to make the owner "say"
  something. The words have to be spoken first, by whoever is speaking, which
  is what ADR-0016 can then check is the owner.
- Misuse is limited to translations of real speech. What echo outputs is
  always tied to something that was actually said.
- **Lost:** correcting a mistranslation by editing the text, or typing when
  speaking is awkward (a noisy room, a quiet one). The fix for a bad
  translation is to say it again. Revisit this only together with a
  replacement safeguard, never on its own.
- The translation step can still rephrase. Claude cleans up disfluency by
  design, so the output isn't word for word, but it stays a translation of
  what was said.
- `pipeline.py` still has a developer-only `speak(text)` used by the
  command-line test. It runs on the developer's own machine and voice and
  isn't exposed by the server. A mobile app must not ship an equivalent.

## Alternatives considered

- **Allow typed text, protected by other checks** (Face ID, watermark):
  those protect the device and mark the output, but whoever holds the
  unlocked phone could still put any words in the owner's mouth.
- **Allow editing the translated text before it's spoken:** a useful feature,
  and it reopens exactly this hole. A one-word edit can turn "I can't come" into
  "I can come". Rejected for the same reason.
