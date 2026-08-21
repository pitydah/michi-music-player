# Post-1.0 Backlog

Governance authority for deferred scope. Every entry records a feature, capability,
or integration that is excluded from the 1.0 release with its deferral
justification and estimated sizing. No deferred work exists outside this document.

Entries originate from the canonical 1.0 contract (MASTER_ROADMAP_1.0.md) and
from explicit out-of-scope declarations in the roadmap. Items already scheduled
for 1.0 (Required 1.0) are not repeated here.

## Sizing Guide

| Size | Team-weeks | Example                                       |
| ---- | ---------- | --------------------------------------------- |
| S    | 1-2        | Single controller, one persistence table      |
| M    | 3-5        | Multi-screen feature with new domain models   |
| L    | 6-10       | New subsystem with its own ports and adapters |
| XL   | 11+        | Cross-cutting capability touching every layer |

## Deferred Product Features

| #   | Feature                  | Justification                                                                                                                                                                                                                                                                                | Sizing |
| --- | ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| 1   | Playlists                | M4 Queue provides flat track-list ordering; M6 Library provides browsable collection. Named, persisted, user-curated playlists with CRUD, import/export (.m3u, .pls), and sharing exceed the 1.0 core loop. RESCHEDULED (approved scope change 2026-08-16): pre-Beta local work package LOCAL-06 per the reconciled MASTER_ROADMAP_1.0.md — Playlists is a persistent user-curated collection, distinct from Queue and Mix. | L      |
| 2   | Metadata Editor          | Basic metadata display (title/artist/album/duration) is Required for 1.0. A tag editor additionally requires write-capable codec libraries (ID3v2, Vorbis Comments, APEv2), an undo/redo stack, batch operations, and format-specific validation — beyond the 1.0 playback-and-browse scope. | L      |
| 3   | Audio Lab                | Real-time audio effects (EQ, compressor, reverb, pitch shift), effect chaining, preset management, and live preview require a signal-processing graph, DSP library integration, and frame-budget analysis not scoped for 1.0.                                                                | XL     |
| 4   | Disc Lab                 | CD ripping, format transcoding, bit-perfect verification, AccurateRip integration, and cover-art embedding require optical-drive access, multi-format encoder pipelines, and forensic audio tooling deferred past 1.0.                                                                       | XL     |
| 5   | Michi AI                 | Intelligent recommendations, auto-playlists, acoustic fingerprinting, mood detection, and natural-language queries require ML model hosting, training pipelines, and inference infrastructure entirely out of 1.0 scope. Developed in the separate repository `pitydah/michi-ai`; the Player keeps no AI runtime dependency or embedded AI code. | XL     |
| 6   | Sync                     | Multi-device library and playback-position sync requires conflict-free replicated data types (CRDTs), a sync server, authentication, and offline-capable merge resolution — none in 1.0 scope.                                                                                               | XL     |
| 7   | Server Integrations      | Subsonic, Jellyfin, Plex, Navidrome, and DLNA/UPnP streaming require network discovery, remote authentication, streaming protocol adapters, and remote-library indexing far beyond local-first 1.0.                                                                                          | L      |
| 8   | Home Audio               | Chromecast, AirPlay, Sonos, Snapcast, and multi-room synchronized playback require network-streaming pipelines, device discovery, and latency-compensation protocols. 1.0 is local-output only.                                                                                              | L      |
| 9   | Recognition              | AcoustID, MusicBrainz, and Shazam-style fingerprinting for unidentified tracks require external API integration, fingerprint computation, and match-resolution UI deferred past 1.0.                                                                                                         | M      |
| 10  | Radio                    | Internet radio streaming (SHOUTcast, Icecast, HLS), station browsing, and recording require streaming protocol adapters, directory integration, and network buffering not in 1.0.                                                                                                            | M      |
| 11  | Lyrics                   | Timed (LRC) and plain-text lyrics fetching, display, and synchronized highlighting require lyrics-provider API integration, a lyrics overlay widget, and timestamp parsing — deferred past 1.0.                                                                                              | M      |
| 12  | Michi Ecosystem Features | Social sharing, listening stats (last.fm scrobbling), collaborative playlists, and community features require user accounts, APIs, and moderation infrastructure entirely out of 1.0 scope.                                                                                                  | XL     |
| 13  | Video                    | Music video playback, visualizers, and video library management require a separate media pipeline, codec support (H.264, VP9, AV1), and a video playback surface. Video is Not Applicable to the 1.0 product — the product is audio-only.                                                    | N/A    |
| 14  | Windows platform support | 1.0 targets Linux only (AppImage/Flatpak/deb). A Windows build requires installer packaging (MSI/EXE), a Windows test matrix, and platform QA — beyond the Linux-first 1.0 scope.                                                                                                            | L      |
| 15  | macOS platform support   | 1.0 targets Linux only (AppImage/Flatpak/deb). A macOS build requires notarization, .dmg packaging, and a macOS test matrix — beyond the Linux-first 1.0 scope.                                                                                                                              | L      |
| 16  | CoverFlow                | RETIRED product decision: DO NOT implement, restore, or port from Legacy. Successor: PathView (ACTIVE PRODUCT CAPABILITY, pre-Stable local work LOCAL-04, after canonical album model + artwork).                                                                                              | S      |
| 17  | Ecosystem integrations (Michi Link, Michi Mobile, Michi Micro Server, Michi Big Server, Michi Music Stream, Home Audio) | RETAINED product capabilities, AFTER PLAYER STABLE. The current refactor carries no integration code, gateways, or speculative services.                                                                                       | XL     |

## Deferred Capability Decisions (canonical 1.0 contract)

These decisions are recorded in MASTER_ROADMAP_1.0.md. All are Post-1.0 except
as noted. (Gapless playback was promoted to Required-1.0 by the product-owner
realignment of 2026-08-21 — it no longer belongs to this list; see
`docs/MASTER_ROADMAP_1.0.md` and `docs/M11_5_AUDIOPHILE_PLAYBACK_GUARANTEES.md`.)

| Capability                    | Decision | Justification                                                                                                                                     | Sizing |
| ----------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| Crossfade                     | Post-1.0 | Overlapping track transitions require two-buffer mixing; not part of the 1.0 core loop; distinct capability from Gapless.                         | M      |
| Library index DB              | MOVED TO M6.2 (Required 1.0) | A persisted library index requires schema, incremental sync, and migration work; 1.0 scans the filesystem directly each session. RESCHEDULED (M6 original contract reconciliation 2026-08-18): the persistent library index is REQUIRED for 1.0 — M6.2 (LibraryIndexRepository port + versioned SQLite index, filesystem fingerprint size/mtime_ns, no reparse of unchanged) per docs/M6_LIBRARY_MASTER_PLAN.md. | L      |
| Cover art                     | Post-1.0 | Artwork pipeline (extraction, caching, rendering) is outside the 1.0 core loop. Justification update (M6 original contract reconciliation 2026-08-18): embedded artwork extraction + per-album-key cache are delivered (LOCAL-02); folder-art fallback + digest-aware cache invalidation remain M6.5; no premium processing.                                                                                                   | M      |
| Full-text indexed search      | Post-1.0 | Substring filter satisfies 1.0; FTS indexing is a performance enhancement.                                                                        | M      |
| Safe mode                     | Post-1.0 | A `--safe-mode` bypass requires configurable startup paths and degraded-mode contracts deferred past 1.0.                                         | M      |
| Watchdog                      | Post-1.0 | Audio pipeline stall detection requires monitoring infrastructure deferred past 1.0.                                                              | M      |
| Windows platform              | Post-1.0 | 1.0 targets Linux only (AppImage/Flatpak/deb); Windows installer packaging and QA deferred.                                                       | L      |
| macOS platform                | Post-1.0 | 1.0 targets Linux only (AppImage/Flatpak/deb); macOS notarization, .dmg packaging, and QA deferred.                                               | L      |

## Admission Rules

1. A feature on this list MAY be admitted to a post-1.0 phase only after an
   approved scope change with updated justification, sizing, and dependency analysis.
2. A feature NOT on this list SHALL NOT be admitted to any phase without first
   appearing here with deferral rationale.
3. Backlog grooming (M16 exit) assigns t-shirt sizing and rough priority; formal
   sizing requires a dedicated exploration before admission.
