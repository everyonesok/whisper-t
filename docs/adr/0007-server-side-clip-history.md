# ADR-0007: Server-side clip history

**Status:** Accepted
**Date:** 2026-09-06

## Context

Comparing the same sentence across languages — Russian against Japanese — is only
possible if both are still around. That means keeping every translation, and keeping
it automatically: the value comes from clips you did not know you would want to
compare until after you had made both.

A browser can write files, but reading a folder back requires a directory handle
granted through a picker, stashed in IndexedDB, and re-permissioned when the browser
decides to ask again. It does not survive sessions reliably.

## Decision

The server writes every finished translation to a local `history/` folder — audio
plus a JSON sidecar — and serves an index of it. The browser just asks for the list.

## Consequences

- No permission flow, and it survives restarts, because the server is an ordinary
  local process with ordinary file access.
- The clips are real files, openable in Finder or droppable into a deck.
- One JSON sidecar per clip rather than a shared index file, so a partial write
  cannot corrupt the whole history.
- **Recordings of the user's voice and transcripts of everything they said now
  persist to disk by default**, where previously nothing was kept unless explicitly
  saved. `history/` is gitignored, including the `.json` sidecars, which are text and
  would otherwise slip past the audio rules.
- Disk grows unbounded. There is a delete button per clip but no cap or expiry.

## Alternatives considered

- **File System Access API in the browser** — the permission dance above. Fragile
  across sessions for no benefit here, since a local server already exists.
- **Save-on-demand only** — defeats the purpose. It requires deciding a clip is worth
  keeping before hearing what you would compare it against.
- **The existing Save button** — kept, and deliberately separate. It exports one clip
  to a folder the user picks, which is a different job from browsing what exists.
