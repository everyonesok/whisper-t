# ADR-0004: NDJSON streaming over WebSockets

**Status:** Accepted
**Date:** 2026-09-05

## Context

Sentences finish generating at different times and should reach the browser as they
complete, so playback can start on the first while the rest are still queued. The
obvious mechanism is a WebSocket, and a rewrite was planned.

Re-reading the existing code showed the transport already streamed multiple events —
it had been built that way for the three-stage progress display. What needed to
change was what the server *emitted*, not how it connected.

## Decision

Keep the existing `POST /api/translate` returning a streaming NDJSON response, one
JSON object per line. Emit a `chunk` event per sentence as each finishes.

## Consequences

- The change came in far smaller than planned: one function rewritten rather than a
  new transport plus a new client.
- No connection lifecycle to manage — no reconnect logic, no heartbeat, no
  distinction between a closed socket and a finished response.
- Progress is reported from real events rather than a timer, so the times shown are
  measured. A timer would be wrong in exactly the situation where feedback matters
  most: when a stage runs long.
- Upload is still a single request, so this cannot stream audio *while* the user is
  still speaking. That is not currently a limitation, because Whisper processes
  audio in 30-second windows and cannot transcribe progressively below that anyway.

## Alternatives considered

- **WebSockets** — genuinely needed only for utterances over 30 seconds, where
  incremental transcription would become possible. The interface actively
  discourages those, and the 30s recording cap makes them impossible. Deferred
  rather than rejected; revisit if long-form input is ever wanted.
- **Polling a job endpoint** — more requests, more state on the server, and worse
  latency than a response that is already streaming.
