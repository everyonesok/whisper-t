# ADR-0015: One voice per device, locked to it

**Status:** Accepted — for the mobile app
**Date:** 2026-10-01

## Context

The app model is one owner, one voice, one install (clarified 2026-09-26):
each person installs their own copy and enrols their own voice. Each voice
then needs to stay attached to its owner and device. A voice that can be
exported, synced or added alongside others is a voice that can be moved to
someone who shouldn't have it.

## Decision

- **One voice per install.** Enrolling again **replaces** the previous voice
  (after confirmation). There is never a second profile.
- **The voice is stored encrypted and can't be exported.** It's kept with iOS
  data protection, tied to the device's keychain, and excluded from backups
  and iCloud sync. There's no share or export option.
- **Opening echo requires Face ID** (or the device passcode), through iOS's
  standard local authentication.
- **Output is watermarked** (Perth, as in ADR-0010 and ADR-0012). That's a
  separate safeguard, recorded here as part of the set.

## Consequences

- A new phone means enrolling again: about a minute of reading. That's the
  intended cost of not being able to move the voice.
- Lending an unlocked phone doesn't hand over the voice: Face ID protects the
  app, and ADR-0016 can protect each use.
- Losing or wiping the phone loses the voice. Since enrolment is quick, that
  is acceptable, and arguably correct.
- Device binding protects the *app*. It can't stop someone cloning a voice
  with other tools. The underlying model is open source, so the honest goal
  is that echo shouldn't be the easiest way to fake someone's voice, not that
  faking a voice becomes impossible.

## Alternatives considered

- **Several voices per device** (a shared family tablet): rejected with the
  app model. Several voices on one device is the shape of a
  voice-impersonation tool.
- **A voice password** ("my voice is my password"): banks did this, and in
  2023 journalists got into their own Lloyds, Santander and Halifax accounts
  with AI clones of their voices. Face ID is far stronger and costs nothing.
- **Account-based cloud storage of the voice:** convenient across devices,
  but it creates a server full of voice references, the most valuable thing
  to steal, and it breaks the promise that the voice stays on the device.
