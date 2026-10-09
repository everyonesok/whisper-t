# ADR-0022: On-device voice is feasible on iPhone

**Status:** Accepted, for the mobile plan
**Date:** 2026-10-08

## Context

The mobile version of echo depends on its voice model running on the phone
itself: the owner's voice stays on the device (ADR-0015), and nothing is sent
to a server to be spoken. On the Mac, echo runs Qwen3-TTS under MLX (ADR-0010,
ADR-0012). Whether a phone could run it fast enough had been an open question
since September, and nobody had published a cloning speed on an iPhone.

It was measured on an iPhone 18 Pro, with `mlx-audio-swift` and a small
measuring app. Details and every run's numbers are kept outside this repo, in
the local test folder's notes (`echo-iphone-test/NOTES.md`), since the
results include clips of the owner's voice.

The first measurements said the phone was too slow: 0.6-0.75x real time, with
audible gaps. A run on the Mac found why. The same Swift code ran at 0.53x as
a Debug build and 1.17x as a Release build on the M3. Xcode builds Debug by
default, without compiler optimisation, for the libraries as well as the app.

## Decision

Plan the mobile app around the voice model running on the phone, with:

- **Qwen3-TTS 0.6B Base, 6-bit weights**, through `mlx-audio-swift`;
- **the voice prepared once**, at enrolment, and reused for every message;
- **0.32-second streamed pieces**, as on the Mac;
- **performance judged only on Release builds.**

Measured on the iPhone 18 Pro (Release, three Russian phrases, three rounds):
first sound after **0.27 s**, speed **1.36-1.56x** real time, no head start
needed for gap-free playback, 2.3 GB peak memory.

## Consequences

- The phone starts speaking slightly sooner than echo on the Mac does today
  (0.3 s), and plays without gaps.
- **Accuracy matches the Mac.** Round-trip transcription found the same
  pattern: two phrases near perfect, the train phrase's first word sometimes
  misheard («Поезд»). That's the model, not the phone.
- **Heat slows it down.** Speed drifted from 1.56x to 1.36x over about three
  minutes of nonstop generation. Normal use is short bursts, but a long-session
  test is still owed.
- **iOS rules the Mac didn't have:** no graphics-chip work while the app is in
  the background (MLX stops the app if it tries), so generation must pause or
  finish while echo is on screen; and a per-app memory limit, raised with
  Apple's increased-memory-limit entitlement.
- **Only one phone measured.** Older and cheaper iPhones, and languages other
  than Russian, are untested. The 0.6B model rather than echo's 1.7B: about
  the same voice to Robert's ear, and the 1.7B on a phone is untested.
- Speech recognition and translation on the phone are separate stages, not
  covered here.

## Alternatives considered

- **8-bit weights:** about as fast when cool, 130 MB heavier, and it slipped
  below real time once as the phone warmed. 6-bit is the better phone choice.
- **Bigger streamed pieces (1 second):** no faster, and the first sound came
  1-2 seconds later.
- **A cloud voice service** (for example Microsoft's MAI-Voice): fast, but the
  owner's voice would live on someone else's servers, against ADR-0015. Kept
  under watch, not adopted.
- **Waiting for faster phones or models:** no longer necessary for current
  Pro-class iPhones.
