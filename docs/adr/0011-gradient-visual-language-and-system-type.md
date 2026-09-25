# ADR-0011: Gradient visual language and system type

**Status:** Accepted (on the `qwen-streaming` branch)
**Date:** 2026-09-25

## Context

The interface was a dark, warm-grey theme with an orange accent, set in two
Google Fonts (Space Grotesk and IBM Plex Mono). The owner wanted a redesign
built around a different direction: a softly blurred, colourful background,
black primary buttons and Helvetica-style type. The direction was a mood,
not a spec to reproduce.

Two constraints shaped it. White text on a mid-tone gradient doesn't have
enough contrast for anything smaller than a headline. And nothing about how
the page behaves should change: the recording, streaming playback and save
logic had been tested and were working.

## Decision

- **Background:** a full-screen field of large blurred colour blobs (slate
  blue, mauve, peach) drifting slowly, with film grain over it. The drift
  stops for anyone who has asked their system for reduced motion.
- **Frame:** the app sits in thin white hairlines with small dots where they
  meet. Header and footer split into two cells.
- **Type:** Helvetica Neue, which macOS already has, instead of web fonts.
  Big headings set tight in white on the gradient.
- **Surfaces:** anything read at length (sentences, history, progress,
  errors) sits on an off-white card in near-black text.
- **Buttons:** black pills for the main action, white pills for the rest.
- **One accent:** a lime-to-pink gradient, only for things that are live.
  That means the sentence playing now, the stage in progress, the timing bars
  and the hover ring on the mic.
- **Tokens, two scopes.** The same variable names (`--text`, `--muted`,
  `--faint` and so on) mean white-on-gradient at the top level and
  dark-on-light inside `.card` and `.srow`. Colours that JavaScript sets
  therefore come out right wherever they land, without touching the logic.

## Consequences

- **No request to Google Fonts on page load.** The page now makes no
  third-party request at all until you translate something.
- Helvetica Neue exists only on Apple devices. Elsewhere it falls back to
  Helvetica, then Arial. That's acceptable for an app that already needs
  Apple Silicon.
- `backdrop`-style blur is done with `filter: blur()` on one fixed layer,
  not per element, so it costs little. The drift animation is 38 seconds long
  and uses `transform` only.
- Every element ID and all behaviour are unchanged. Two existing JavaScript
  colours were moved onto tokens, and one stale Chatterbox estimate (`~10s`)
  was corrected along the way.
- A layout bug came with it and was fixed: rows gained `overflow: hidden`
  so the gradient strip stays inside the rounded corners, which let a
  scrolling flex list squash and clip them. Rows are now `flex-shrink: 0`.
- **The design canvas (`*.dc.html`, `canvas.json`) still shows the old
  theme.** It is a design source, not the running app, and hasn't been
  redrawn.

## Alternatives considered

- **White body text on the gradient throughout.** Closer to a pure poster
  look, but small text fails contrast on the lighter peach areas. Reserved
  for headings and short labels.
- **Frosted translucent cards (backdrop blur).** Fashionable, but readable
  only when the colour behind happens to be dark. Opaque off-white cards are
  predictable.
- **A self-hosted Helvetica-like web font.** Unnecessary on the only platform
  the app runs on, and it would be a file to license and ship.
- **Keeping the dark theme and only swapping the font.** Doesn't reach the
  direction asked for.
