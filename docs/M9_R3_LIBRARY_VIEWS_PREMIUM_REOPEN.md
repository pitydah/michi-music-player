# M9 R3 — Library Views Premium scoped reopen

## Reopen reason

Reproducible interaction and presentation-contract defects, plus the explicit
product requirement to elevate Library Views and View Options without reopening
the global presentation system.

## Scope

- Library header, toolbar, album-view selector, and contextual View Options.
- The six album presentations: Gallery, Album Flow, Listening Wall,
  Chronology, Editorial, and Studio List.
- Per-view preferences and browse-state restoration.
- Canonical album-row parity and structured technical facts at the M6.6
  presentation boundary.
- Truthful select, open, and play semantics.

## M6.6 correction

The domain-to-presentation projection now emits one canonical album-row shape
for every album view. Timeline-specific grouping extends that row rather than
replacing or weakening it. High-resolution filtering consumes structured facts
(`maxBitDepth`, `maxSampleRateHz`, and `containsDsd`) and never parses display
strings.

The factual high-resolution criterion is: at least 24-bit PCM, at least 96 kHz,
or DSD content. It is metadata classification only; it does not claim a
bit-perfect runtime path.

## Non-goals

- Now Playing Bar, queue semantics, audio engine, DSP, DAC, and output routing.
- M7 search ranking.
- A global application redesign.
- Network enrichment or provider-policy changes.

## Refreeze gates

- Domain, projection, settings, and static QML contract tests.
- Strict per-view preference decoding and SQLite restart persistence.
- QML lint and Python lint/format checks.
- Wheel/sdist inclusion of every new QML resource.
- CI-backed Qt runtime, visual, accessibility, and performance validation.

M9 and the narrowly corrected M6.6 presentation contract refreeze when these
gates pass on the pull request targeting `main`.
