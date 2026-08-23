# M6.9-BACKEND-R1.2 — Final Request Correlation + Real Tag Compatibility Seal

Status: implemented. R1.2 closes the backend concurrency/correlation
defects found after R1.1 (which is therefore SUPERSEDED by this final
correlation seal). NO UI/QML/EnrichmentBridge; NO M11.3D; NO audio;
NO canonical metadata; NO tag writes; NO new providers.

## Generation authority (P1-02/03/05/06/07)

Per (entity_kind, local_key) a MONOTONIC generation exists in
`EnrichmentService` (runtime state, never persisted). Every operation
carries its generation inside its `EnrichmentRequest`. Identity
transitions, request registration and final deliveries re-validate the
generation INSIDE the authority commit gate (`threading.RLock`): an old
worker may physically finish its computation but can never cross an
authority gate again — zero identity mutation, zero request
replacement, zero knowledge mutation. `IdentityResolutionStatus.SUPERSEDED`
marks the stale gate; the coordinator converges it to CANCELLED.
Legacy direct service calls (generation 0, no recorded authority) keep
standalone semantics.

## Exact request invalidation (P1-01/08)

`EnrichmentRequestLedger.invalidate_if_current(entity_kind, key,
request_id, generation) -> bool`: a stale worker can NEVER cancel a
newer generation's request. The coordinator's terminal failure paths
invalidate EXACTLY the worker's own request (when one exists) and its
own generation — an old failure never kills the new request.

## Authority transactions (P1-09)

Manual identity operations (confirm/reset/clear) and deliveries are
serialized by the SAME authority lock: no logical window exists where
an old request stays valid after a newer identity transition. No
provider/network work under the lock.

## Correlated state events (P1-10/11)

`EnrichmentOperationEvent` (operation_id, generation, entity_kind,
local_entity_key, state) — every callback carries full correlation;
events belonging to an older generation are distinguishable by
construction. Policy notices (DISABLED / shutdown rejection) carry
operation_id "" and generation 0. Future Presentation filters by
generation (documented; callbacks arrive on the backend worker thread —
the future bridge marshals to the Qt owner thread).

## Executor admission (P1-12)

`EnrichmentExecutorPort.submit(work) -> bool` under a lifecycle lock:
False after shutdown, never a leaked RuntimeError. `enrich_artist`,
`enrich_album` and the manual searches use the controlled submission
boundary; a rejected submission cancels exactly that generation,
removes the token and publishes CANCELLED with zero work.

## Response limit semantics (P1-13/14/15/16)

Oversized provider responses raise `EnrichmentResponseLimitError`
(non-transient, never retried, never stale-eligible, never OFFLINE,
exactly ONE attempt). The transport closes the response on EVERY exit
path via a single try/finally.

## Real MusicBrainz tag compatibility (P1-17..22)

- Vorbis/FLAC/Ogg/Opus: `MUSICBRAINZ_TRACKID` → recording role
  (the real Picard key), `MUSICBRAINZ_RELEASETRACKID` stays separate;
  every recording key is probed in isolation in tests.
- ID3/MP3/WAV: TXXX MusicBrainz descriptions + UFID (owner
  `http://musicbrainz.org`) for the recording id.
- MP4/M4A: freeform atoms `----:com.apple.iTunes:MusicBrainz ...`
  (bytes values).
- ASF/WMA: `MusicBrainz/...` keys with REAL Mutagen attribute values
  (`ASFUnicodeAttribute` and any attribute exposing `.value`) via a
  strict recursive extractor — no generic `str()` coercion.
- Same-role conflicts preserved everywhere; never first-wins;
  READ-ONLY (never breaks the scan).

## Linearization points (documented)

- BEGIN OPERATION: coordinator registry + service generation record.
- CANCEL/SUPERSEDE: coordinator token cancel + service
  cancel_operation(current generation only).
- IDENTITY COMMIT / REQUEST REGISTER / REQUEST INVALIDATE / KNOWLEDGE
  DELIVERY / MANUAL IDENTITY CHANGE / RESET: inside the service
  authority lock with generation re-validation.
- SHUTDOWN ADMISSION CLOSE: executor lifecycle lock.

## Bounded cache (P2)

Maintenance streams each shard with os.scandir (never materialized);
iteration stops at `max_entries_per_run` examined entries.

## Firewalls

metadata_extractor / application/ports / domain/library /
library_index: zero R1.2 diff (blob-compared against SYNCED_BASE).
Audio and Presentation: zero R1.2-owned diff. No tag writes; no
startup/scan network; provider set unchanged.

## Final status

M6.9A FOUNDATION: DONE / TESTED / FROZEN
M6.9 BACKEND: DONE / TESTED / FROZEN
M6.9 PRESENTATION: NOT IMPLEMENTED
M6.9 TOTAL: IN PROGRESS
NEXT AUTHORIZED WP: M6.9 PRESENTATION INTEGRATION
