# M6.9 — Library Enrichment (Implementation Record)

Status: **COMPLETE — M6.9A FOUNDATION DONE/TESTED/FROZEN; M6.9 BACKEND
DONE/TESTED/MERGED/FROZEN; M6.9 PRESENTATION DONE/TESTED**. This
document records the implemented runtime truth of the full user-facing
feature.

## Architecture

Five bounded contexts preserved (permanent firewall):

```
LOCAL AUDIO FILES → CANONICAL LOCAL LIBRARY → LOCAL IDENTITY EVIDENCE
    → RESOLVED EXTERNAL IDENTITY → EXTERNAL KNOWLEDGE
    → enrichment.db / enrichment-assets/
    → EnrichmentBridge (owner-thread projection)
    → QML
```

Never reversed: external knowledge can never write canonical metadata,
library_index, audio tags, favorites, history or playlists.

## Backend (frozen — see M6_9_BACKEND_R1_3_2_FINAL_TERMINAL_PENDING_MAIN_SEAL.md)

EnrichmentService = identity/generation/request/knowledge authority;
EnrichmentCoordinator = async workflow owner; MANUAL > EMBEDDED_HINT >
AUTO; old generations never commit; startup network ZERO; scan network
ZERO. No authority change was made by the Presentation WP.

## Presentation (M6.9-PRESENTATION-COMPLETE)

- **EnrichmentBridge** (`src/michi/presentation/enrichment_bridge.py`) —
  the ONLY Presentation adapter. QML intent → coordinator/service →
  Qt owner-thread projection → QML. No provider/repository/SQLite/HTTP
  access from QML.
- **Owner-thread contract (P0)**: every worker callback is marshaled
  through an explicit relay (`Qt.QueuedConnection`); the projection
  mutates only on the GUI thread (proven by deterministic tests with a
  real thread pool).
- **Double anti-stale filter**: presentation intent epoch (action
  closure) + backend generation (events older than the last observed
  generation are dropped) + active-entity check. A late
  CANCELLED/FAILED/READY from a previous artist can never change the
  current UI.
- **Activation semantics**: cached knowledge projects immediately and
  network-free; network starts ONLY on explicit Artist/Album detail
  with Online Library Enrichment ON and no cached knowledge (exactly
  once). Lists, search, scan, startup: never.
- **Artist UX**: external portrait (fallback: local artwork), About the
  artist glass card (biography plain text with Show more/less, factual
  fields only when the backend really provides them), status bar with
  sober semantics (CANCELLED is not an error; DISABLED is a policy
  state), contextual actions (Fetch/Refresh, Review match, Clear
  online info, Reset match).
- **Album UX**: About this album knowledge card — complementary to
  canonical local metadata (album title/artist/year/genres stay
  authoritative); local artwork outranks external (Cover Art Archive is
  a visual fallback); same status/actions.
- **Manual Review (ReviewMatchesDialog)**: artist
  (displayName/disambiguation/provider) and album
  (displayTitle/artistCredit/year) candidates, async search with epoch
  correlation (a stale search can never fill another entity's dialog),
  loading/empty/error states, full keyboard (Up/Down/Enter/Escape),
  Accessible names. Manual confirm keeps MANUAL authority; a late
  automatic operation can never replace it.
- **Provenance/Attribution**: truthful rows (provider, sourceUrl,
  license, licenseUrl, attribution, retrievedAt, isStale) — only fields
  the backend provided; external links open only on https:// (fail
  closed); remote biography is plain text, never rendered HTML.
- **Settings**: `Online Library Enrichment` switch in the Library panel
  (DEFAULT OFF; persisted with transactional rollback; restart
  restores). OFF cancels live enrichment via the coordinator and blocks
  any new network work; cached data stays viewable. Cached
  Artist/Album knowledge remains visible offline (OFF ≠ hide data).
- **Clear vs Reset**: CLEAR keeps identity and removes knowledge;
  RESET removes identity and knowledge with no automatic re-enrich.
- **Lifecycle**: `EnrichmentBridge.dispose()` is idempotent, drops all
  pending presentation callbacks and is called by the container BEFORE
  the coordinator shutdown.
- **Composition**: bootstrap builds ONE EnrichmentBridge over the SAME
  production EnrichmentGraph (coordinator/service/asset store),
  registers the `enrichment` context property and wires
  SettingsBridge → EnrichmentBridge policy (composition root only).

## Privacy gates (deterministic tests, fake providers)

startup = 0 network · scan = 0 · lists = 0 · search = 0 · detail OFF =
0 · detail ON + cached = 0 · detail ON + no cache = allowed · refresh
ON = allowed · review OFF = 0.

## Validation (real numbers)

- Focused presentation: 41 passed
- All M6.9 suites: 647 passed
- Full suite: **2543 passed, 1 skipped, 13 warnings** (baseline 2502)
- Ruff check + format: PASS · qmllint (full QML tree): PASS ·
  `python -m build`: PASS · `git diff --check`: PASS
- Firewalls vs BASE_MAIN (86a16cc): Queue/M4-R1 ZERO · audio ZERO ·
  canonical metadata ZERO · Antigravity UNTOUCHED

## Known limitations (documented truth)

- No live-network tests in CI (fixtures only).
- `album_artist_ids` matching is not implemented (deferred).
- Provider-specific UUID syntax validation belongs to provider boundary
  (deferred).
