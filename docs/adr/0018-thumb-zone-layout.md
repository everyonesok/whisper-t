# ADR-0018: Thumb-zone layout

**Status:** Accepted
**Date:** 2026-10-01

## Context

On a phone, the bottom third of the screen is the easiest to reach with the
thumb holding the device, and the top is the hardest. echo's layout put
things the other way round: the language choice sat in the top bar, the
history button in the footer, and the "English → Russian" readout at the
bottom, so the control you change most often was the one furthest from your
thumb.

## Decision

Split the screen by what you *do* with each element:

- **Top bar: things you read.** The brand, a one-line status (with a dot that
  shows the state) and the history button. The status shortens with an
  ellipsis rather than pushing the history button off screen.
- **Bottom: things you tap.** On the idle screen, the microphone sits low,
  with the language choice directly under it as a pill
  ("English → Russian"). That makes the readout and the control one thing.
  On the recording screen, Cancel and "Stop and translate" sit at the bottom.
- **The footer is gone.** Its jobs moved to the top bar (status, history) and
  to the language pill (target language).
- **Exception on the result screen:** "Misheard? Say it again" stays at the
  top, beside the player. The owner's reasoning: you've just pressed play up
  there, and you only find out it was misheard by listening, so the retry
  belongs next to that action. The main next steps ("Say something else",
  Save) are already at the bottom.

## Consequences

- One-handed use on a phone: speaking, picking a language and stopping a
  recording no longer need a reach to the top.
- History is still at the top. It's used less often, and keeping it out of
  the bottom avoids crowding the main action.
- On desktop the same layout simply has more empty space between the top bar
  and the controls; nothing breaks.
- At narrow widths, the two recording buttons aren't equal halves, because
  the "Stop and translate" label can't shrink further. That was accepted.
- The Figma screens should follow the same split (the Idle, Recording and
  Result proposals already do).

## Alternatives considered

- **Move everything to the bottom, including history:** too many targets
  competing with the microphone.
- **Move the retry link to the bottom too:** it would be consistent with
  the rule, but cut it off from the play button it relates to (see the
  exception above).
