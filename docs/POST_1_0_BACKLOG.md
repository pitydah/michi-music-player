# Post-1.0 Backlog

Governance authority for deferred scope. Every entry records a feature, capability,
or integration that is excluded from the 1.0 release with its deferral
justification and estimated sizing. No deferred work exists outside this document.

Entries originate from the M0 Foundation exclusion list (22 items routed here per
INVARIANTS.md feature-freeze policy) and from explicit out-of-scope declarations in
individual M-phase sections of MASTER_ROADMAP_1.0.md. Items already covered by
M1-M16 phases are not repeated here.

## Sizing Guide

| Size | Team-weeks | Example                                       |
| ---- | ---------- | --------------------------------------------- |
| S    | 1-2        | Single controller, one persistence table      |
| M    | 3-5        | Multi-screen feature with new domain models   |
| L    | 6-10       | New subsystem with its own ports and adapters |
| XL   | 11+        | Cross-cutting capability touching every layer |

## Deferred Features

| #   | Feature                  | Justification                                                                                                                                                                                                                                         | Sizing |
| --- | ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| 1   | Playlists                | M4 Queue provides flat track-list ordering; M6 Library provides browsable collection. Named, persisted, user-curated playlists with CRUD, import/export (.m3u, .pls), and sharing exceed the 1.0 core loop.                                           | L      |
| 2   | Metadata Editor          | M3 extracts read-only metadata for display. A tag editor requires write-capable codec libraries (ID3v2, Vorbis Comments, APEv2), an undo/redo stack, batch operations, and format-specific validation — all beyond the 1.0 playback-and-browse scope. | L      |
| 3   | Audio Lab                | Real-time audio effects (EQ, compressor, reverb, pitch shift), effect chaining, preset management, and live preview require a signal-processing graph, DSP library integration, and frame-budget analysis not scoped for 1.0.                         | XL     |
| 4   | Disc Lab                 | CD ripping, format transcoding, bit-perfect verification, AccurateRip integration, and cover-art embedding require optical-drive access, multi-format encoder pipelines, and forensic audio tooling deferred past 1.0.                                | XL     |
| 5   | Michi AI                 | Intelligent recommendations, auto-playlists, acoustic fingerprinting, mood detection, and natural-language queries require ML model hosting, training pipelines, and inference infrastructure entirely out of 1.0 scope.                              | XL     |
| 6   | Sync                     | Multi-device library and playback-position sync requires conflict-free replicated data types (CRDTs), a sync server, authentication, and offline-capable merge resolution — none in 1.0 scope.                                                        | XL     |
| 7   | Server Integrations      | Subsonic, Jellyfin, Plex, Navidrome, and DLNA/UPnP streaming require network discovery, remote authentication, streaming protocol adapters, and remote-library indexing far beyond local-first 1.0.                                                   | L      |
| 8   | Home Audio               | Chromecast, AirPlay, Sonos, Snapcast, and multi-room synchronized playback require network-streaming pipelines, device discovery, and latency-compensation protocols. 1.0 is local-output only.                                                       | L      |
| 9   | Recognition              | AcoustID, MusicBrainz, and Shazam-style fingerprinting for unidentified tracks require external API integration, fingerprint computation, and match-resolution UI deferred past 1.0.                                                                  | M      |
| 10  | Radio                    | Internet radio streaming (SHOUTcast, Icecast, HLS), station browsing, and recording require streaming protocol adapters, directory integration, and network buffering not in 1.0.                                                                     | M      |
| 11  | Lyrics                   | Timed (LRC) and plain-text lyrics fetching, display, and synchronized highlighting require lyrics-provider API integration, a lyrics overlay widget, and timestamp parsing — deferred past 1.0.                                                       | M      |
| 12  | Michi Ecosystem Features | Social sharing, listening stats (last.fm scrobbling), collaborative playlists, and community features require user accounts, APIs, and moderation infrastructure entirely out of 1.0 scope.                                                           | XL     |
| 13  | Video                    | Music video playback, visualizers, and video library management require a separate media pipeline, codec support (H.264, VP9, AV1), and a video playback surface — 1.0 is audio-only.                                                                 | L      |

## Admission Rules

1. A feature on this list MAY be admitted to a post-1.0 phase only after an
   approved scope change with updated justification, sizing, and dependency analysis.
2. A feature NOT on this list SHALL NOT be admitted to any phase without first
   appearing here with deferral rationale.
3. Backlog grooming (M16 exit) assigns t-shirt sizing and rough priority; formal
   sizing requires a dedicated exploration before admission.
