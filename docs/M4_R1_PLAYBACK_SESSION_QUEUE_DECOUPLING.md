# M4-R1 — Playback Session Authority & Queue Decoupling

## Scope

Separate PLAYBACK SESSION / SEQUENCE AUTHORITY from QUEUE CONTENT. Playing
something never implies adding it to the Queue. M4-R1 lives ABOVE
PlaybackService: no engine, router, adapter or transport changes.

## Authorities

| Component | Owns |
| --- | --- |
| PlaybackService | PlaybackState truth (status, accepted path, position, duration, volume, mute) |
| PlaybackSessionService | active playback context, sequence, current index, Next/Previous, Repeat, Shuffle, EndOfMedia navigation |
| QueueService | temporary user-created Queue CONTENT only (add/remove/move/clear/replace) |
| PlaylistService | persistent Playlist collection |
| LibraryService | library data/metadata/filesystem truth, favorites/history/recent |
| AudioTransportRouter | stable transport facade (unchanged) |

## Context types

NONE / SINGLE / ALBUM / PLAYLIST / QUEUE — exactly ONE active context.
Generic track clicks are SINGLE; Album Detail track clicks are ALBUM at the
clicked index; Playlist Detail track clicks are PLAYLIST at the clicked
index; Queue entry clicks are QUEUE (LIVE source sequence).

## Queue semantics

- Play track/album/playlist → session context, NEVER Queue mutation.
- Queue add/remove/move/clear/replace → explicit Queue intents only.
- QUEUE context is LIVE: future navigation follows the current Queue
  ordering; the current entry identity is preserved even if its index moves;
  removing the current Queue entry converges the session to SINGLE (playback
  continues); removing a PENDING Queue candidate cancels the request.
- QueueService NEVER commands playback (no PlaybackService import).

## History ownership

History is PLAYBACK-COMMIT driven: PlaybackHistoryCoordinator records a
Library history entry only after a NEW playback request is ACCEPTED.
Queue mutations and startup restore never record History.

## Persistence migration

Snapshot V2 (FORMAT_VERSION=2): queue_entries (Queue CONTENT) + context
(type/source_id/entries/current_index — PlaybackSession) + playback
(path/position) + navigation (repeat/shuffle/seed). V1→V2: old queue becomes
queue_entries; valid old current_index becomes a QUEUE context; current_index
-1 becomes NONE; an incoherent legacy playback path is never fabricated.
Restore rebuilds Queue content + Session logical context with session-entry
coherence; no autoplay; no History event.

## Tests

- PlaybackSessionService matrix (SINGLE/ALBUM/PLAYLIST/QUEUE contexts,
  pending transaction, request epoch, live Queue sync, navigation, repeat,
  shuffle, EOM).
- QueueService content-only authority (add/remove/move/clear/capacity/
  duplicates/notifications; zero PlaybackService calls).
- Session codec V2 + V1→V2 migration matrix.
- Persistence restart (SINGLE/ALBUM/PLAYLIST/QUEUE logical restore, no
  autoplay, resume coherence via Session current entry).
- Architecture gates (AR01-AR10): QueueService source-level independence,
  Library/Playlist no Queue import, QML navigation via playbackSession, no
  private _queue access, zero Queue mutations for SINGLE/ALBUM/PLAYLIST.

## Final convergence seal (M4-R1 FINAL, 2026-08-23)

- Queue entries carry an opaque RUNTIME entry_id (uuid4 hex): unique per
  insertion, immutable, preserved by move, removed by remove/clear; two
  entries with the same file_path always differ. file_path is payload,
  never Queue identity. entry_id is runtime-only (never persisted; restart
  creates fresh ids — Snapshot V2 contract unchanged).
- PlaybackSessionService tracks the exact active/pending Queue entry ids;
  duplicate move/remove/add and pending cancellation are identity-exact;
  shuffle navigator distinguishes duplicate paths.
- Library playback routing: LibraryBridge.activate → LibraryPlaybackCoordinator
  (SINGLE); every Library-origin intent validates TD-013 through
  LibraryService before any session request; Album clicks stay ALBUM.
- Playlist row activation: PlaylistTrackList.playTrackRequested(index) →
  PlaylistsBridge → PLAYLIST context at the exact index; Queue unchanged.
- Explicit lifecycle: PlaybackSessionService.start()/stop() own the EOM and
  the ONE Queue→Session delivery; PersistenceCoordinator never redispatches;
  PlaybackHistoryCoordinator.stop() and PlaybackSessionBridge.dispose() run
  before audio teardown.
- QueueService constructor sealed: keyword-only max_tracks — the legacy
  positional PlaybackService shim is removed (QueueService(playback) fails
  at signature level).
- P0=0, P1=0. Full suite 2536 passed at CODE_VALIDATED_HEAD 1ed36f5.

## Non-goals

- NO Play-Next overlay / interruption stack (future).
- NO ARTIST/FOLDER/SEARCH contexts yet.
- NO Queue redesign (visual or semantic).
- NO engine/transport changes.

## Boundaries

- **M11.3** (frozen): engines, switching, fallback, runtime convergence —
  unchanged. M4-R1 lives above PlaybackService.
- **M11.4** (next global WP): DAC/output device management — not touched.
- **M11.5**: gapless conformance. Ownership correction recorded:
  PlaybackSessionService owns WHICH track is next; PlaybackService owns
  transition orchestration; AudioPort/engine owns prepare-next/preload
  capability; QueueService owns temporary Queue content only.

## Status

DONE / TESTED / FROZEN (M4-R1 final convergence seal).
