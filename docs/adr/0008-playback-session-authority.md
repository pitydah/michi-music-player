# ADR 0008 — Playback Session Authority & Queue Decoupling

## Status

ACCEPTED (M4-R1, 2026-08-23)

## Decision

The application introduces a dedicated **PlaybackSessionService** as the sole
authority over the ACTIVE PLAYBACK CONTEXT (sequence, current position,
Next/Previous, Repeat, Shuffle, EndOfMedia navigation). QueueService owns
TEMPORARY user-created Queue CONTENT ONLY and never commands playback.

The old operational assumption — *"Queue current == universal playback
session current"* — is superseded.

## Authorities

- **PlaybackService** — actual audio truth: STOPPED/PLAYING/PAUSED, accepted
  file_path, position, duration, volume, mute, transport failure state.
- **PlaybackSessionService** — active playback context: context type
  (NONE/SINGLE/ALBUM/PLAYLIST/QUEUE), source id, sequence entries, current
  index, Next/Previous, Repeat, Shuffle, EndOfMedia navigation policy.
- **QueueService** — temporary Queue CONTENT only: entries, ordering,
  add/add_many/remove/move/clear/replace. No PlaybackService import, no
  playback commands.
- **PlaylistService** — persistent Playlist collection (no playback).
- **LibraryService** — library data/metadata/filesystem truth (no Queue).
- **AudioTransportRouter** — unchanged, transport routing only.

## Key rules

- PLAYING something does NOT imply adding it to the Queue. Play track/album/
  playlist never copies content into Queue; Queue changes only after an
  EXPLICIT Queue-related user intent.
- A session request is a transaction: only backend acceptance commits the
  context; rejection/cancellation never fabricate a current.
- Automatic fallback/recovery (M11.3G) and explicit switching (M11.3F)
  remain unchanged — M4-R1 lives ABOVE PlaybackService.
- History is PLAYBACK-COMMIT driven (accepted new playback requests), never
  Queue-driven, never restore-driven.
- Persistence snapshot V2 separates Queue CONTENT from the Playback SESSION
  context; V1 snapshots migrate (old queue becomes queue_entries; valid old
  current_index becomes a QUEUE context).

## Queue entry identity (final seal clarification)

- Queue entry identity is OPAQUE and RUNTIME-STABLE (entry_id).
- file_path is payload, not Queue identity.
- Duplicate file paths are first-class (distinct entry_ids).
- PlaybackSessionService owns its subscriptions explicitly (start/stop).
- entry_id is never persisted (restart creates fresh ids).

## Sequence model

- Playlist is a persistent sequence.
- Queue is an ephemeral sequence.
- PlaybackSession is the ACTIVE playback sequence.
- PlaybackService is the actual audio truth.
