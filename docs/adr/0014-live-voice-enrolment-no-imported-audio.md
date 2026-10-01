# ADR-0014: Live voice enrolment, no imported audio

**Status:** Accepted — for the mobile app. The prototype still accepts a
reference file; see Consequences.
**Date:** 2026-10-01

## Context

Zero-shot cloning needs only ~15 seconds of someone's speech, and plenty of
people have that much of themselves online: a video, a voicemail, a podcast.
Any app that clones from an uploaded file can clone anyone whose recording
the user can find. echo's prototype works exactly that way: `reference.wav` is
whatever file you give it (`use_recording.sh` converts any audio).

The established services solved this by proving the voice belongs to the
person present, using speech that can only be produced live:

- **ElevenLabs** ("voice captcha") shows a random sentence that must be read
  aloud within 10 seconds, and compares that voice with the uploaded samples.
- **Microsoft Azure** requires a recorded consent statement, checked by
  speaker recognition against the training audio.
- **Apple Personal Voice** has the user read randomly chosen phrases on the
  device, with no import route.

## Decision

The owner's voice is enrolled **only inside the app, live**, by reading
sentences chosen at random at that moment, in their own language. There is no
way to import, pick or upload an audio file as the voice. The first prompt is
a consent statement in the owner's language (for example, "This is my voice,
and I'm creating it for my own use in echo").

## Consequences

- Cloning someone from an existing recording becomes impractical: an old
  clip can't contain sentences that were picked seconds ago. Replaying a
  recording through the speaker fails for the same reason.
- An attacker who *already* has a convincing clone of the person could
  speak the prompts with it. That needs a voice clone from somewhere else
  first, which puts echo outside the attack.
- The enrolment recording also gives Qwen3-TTS its reference **and** its
  transcript for free: the sentences are known in advance, so no Whisper pass
  is needed for `reference.txt`.
- Random sentences must exist in every input language, and they should be
  natural and phonetically varied, since they double as the voice reference.
  That's real content work per language.
- **The prototype doesn't do this yet.** `record_voice.sh` and
  `use_recording.sh` accept any audio. That suits a developer prototype on
  their own Mac, and the README says to clone only your own voice. The
  planned in-app "record your voice" step for the any-language version should
  be built this way, so the prototype practises the rule before the mobile app
  depends on it.

## Alternatives considered

- **Upload a file, plus a consent checkbox:** a checkbox stops nobody.
- **Upload plus a live verification read** (the ElevenLabs model): it allows
  higher-quality studio recordings, but echo needs only ~15 seconds, so a
  live read can *be* the reference. One step instead of two, and nothing to
  upload.
- **Compare against Apple Personal Voice:** proposed, and impossible. Apps
  allowed to use Personal Voice can't capture its audio, and it's
  English-only, with 15 minutes of setup.
