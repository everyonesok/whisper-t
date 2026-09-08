# ADR-0005: Serialise voice generation, parallelise translation

**Status:** Accepted
**Date:** 2026-09-05

## Context

With the recording split into sentences, the obvious optimisation is to run all
three stages concurrently. Attempting that deadlocked: three voice generations
called from parallel threads against one Chatterbox model hung permanently, CPU flat
at 0%, requiring the process to be killed.

Translation has no such problem — it is a network call holding nothing locally.

## Decision

Translations run concurrently in a thread pool. Voice generation strictly queues,
one sentence at a time.

## Consequences

- No deadlock, and the speed-up survives: the win was never parallel generation, it
  was that sentence one becomes playable early while later ones are queued.
- Total time also improved — three short generations beat one long one, because long
  inputs degrade (see ADR-0001). 51s against 89.6s for the same content.
- The asymmetry is invisible from the outside: both stages look like ordinary
  function calls. It is stated explicitly in a comment in `server.py` for that
  reason.
- Whether the deadlock is specific to this model, to PyTorch's MPS backend, or
  general to single-GPU inference under threading is untested. Only one model was
  tried.

## Alternatives considered

- **Parallel voice generation** — the thing that deadlocked. Not viable with one
  model on one GPU regardless of how the calling code is written.
- **A single worker thread consuming a queue** — would likely behave identically to
  serialising inline, with more machinery. Not tried, and worth considering if the
  server ever needs to handle concurrent users.
