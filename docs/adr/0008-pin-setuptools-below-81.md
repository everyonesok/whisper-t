# ADR-0008: Pin setuptools below 81

**Status:** Accepted
**Date:** 2026-09-03

## Context

Chatterbox failed to load with `TypeError: 'NoneType' object is not callable`, thrown
from a file unrelated to the actual cause.

The real error was `ModuleNotFoundError: No module named 'pkg_resources'`, swallowed
by a `try`/`except` in the `perth` watermarking library which set the class to `None`
on failure. `pkg_resources` ships with setuptools, and setuptools 81 removed it after
a long deprecation. Installing the newest setuptools therefore makes it worse, not
better.

## Decision

Pin `setuptools<81` in `requirements.txt`, with a comment explaining why.

## Consequences

- Chatterbox loads. Without the pin it fails with an error naming neither setuptools
  nor `pkg_resources`.
- The project is held on a deprecated setuptools until `perth` stops using
  `pkg_resources`. Nothing else in the dependency tree currently objects.
- The comment in `requirements.txt` is load-bearing: a future reader tidying
  dependencies would otherwise remove the pin as obviously stale and reintroduce a
  confusing failure.

## Alternatives considered

- **Newest setuptools** — the instinct, and wrong. v84 has no `pkg_resources` at all.
- **Patching `perth`** — a vendored fix to a dependency, which then has to be
  maintained. Disproportionate to a one-line pin.
- **`DummyWatermarker`** — Chatterbox constructs `PerthImplicitWatermarker` directly,
  so this would mean patching Chatterbox too, and it would disable the watermarking
  the README relies on.
