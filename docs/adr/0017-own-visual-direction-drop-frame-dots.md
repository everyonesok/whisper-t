# ADR-0017: An own visual direction, starting by dropping the frame dots

**Status:** Accepted
**Date:** 2026-10-01

## Context

ADR-0011's visual language was built from external reference images, taken
as a mood rather than a spec. One borrowed detail was a small white dot
wherever the frame's hairlines meet. The dots showed only on desktop (the
phone layout already hid them), so the two versions looked different, and
they were the most recognisably borrowed element in the design.

The owner's direction: the references were a good starting point, but echo
should move toward its own visual identity over time.

## Decision

Remove the frame dots, in the app and in the Figma designs. The hairline
frame, cells, blurred colour field, type and buttons from ADR-0011 stay as
they are.

More generally, ADR-0011 is now a **starting point** rather than a fixed
spec. Later visual changes should move the design toward its own character,
not further toward the references.

## Consequences

- Desktop and mobile now share one visual vocabulary. The desktop frame is a
  plain hairline border.
- Less markup: six decorative elements and their CSS are gone.
- The remaining elements from ADR-0011 are open to revision in the same
  spirit, one considered change at a time rather than a wholesale restyle.

## Alternatives considered

- **Keep the dots on desktop only:** that keeps the inconsistency the owner
  noticed, and the most borrowed-looking detail.
- **Restyle everything at once:** premature without a defined direction
  of echo's own. Small, deliberate steps are easier to judge.
