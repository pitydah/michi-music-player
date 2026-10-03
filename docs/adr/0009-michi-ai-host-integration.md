# ADR 0009 — Optional Michi AI Host Integration Baseline

- **Status:** Accepted
- **Date:** 2026-10-03

## Context

Michi AI is an independent governed-assistant package. The Player continues to
evolve, so requiring exhaustive adapters would leave integration permanently
unfinished. At the same time, embedding AI internals or publishing speculative
capabilities would violate Player ownership and the existing layer model.

The earlier roadmap deferred every AI dependency until Player Stable. The
product owner has now authorized a narrower pre-Stable baseline: establish and
test the host boundary while keeping intelligent recommendations, local model
hosting, remote providers, and further ecosystem capabilities outside the
Player.

## Decision

Add an optional `integrations/michi_ai` layer with these rules:

1. Dependency direction is always `michi-music-player → michi-ai`.
2. The dependency is an optional extra pinned to an immutable Michi AI commit.
3. The first vertical slice is read-only library search/status/track lookup.
4. The adapter reads canonical `LibraryService` state and pure M7 search
   projections; it never mutates the visible Player search query.
5. Returned dictionaries contain stable track IDs and safe metadata, never
   paths, media IDs, source IDs, credentials, Qt objects, or Player internals.
6. Only `library.search` and `library.read` are published. Every other gateway
   fails closed with `CAPABILITY_UNAVAILABLE`.
7. `ApplicationContainer` owns the optional runtime and tears it down before
   service shutdown. No QML surface or background model/provider call is added
   by this baseline.
8. Cross-repository contract tests pin Michi AI's host API and library schema
   versions.

## Consequences

- The Player can prove a real governed vertical slice before Stable without
  importing Michi AI into domain, application, infrastructure, or presentation.
- Base installs remain free of the optional dependency.
- Player compatibility becomes an ongoing maintenance track; new adapters do
  not reopen this baseline or block later Michi AI phases.
- Playback remains unpublished until asynchronous acceptance can be reported
  truthfully. Metadata, diagnostics, Michi Link, settings, and Audio Lab remain
  out of this slice.
- Any future QML bridge needs an explicit worker/owner-thread policy; synchronous
  provider calls must never block the GUI thread.
