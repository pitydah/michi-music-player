"""M6.9-PRESENTATION — EnrichmentBridge.

The ONLY Presentation adapter of the Library Enrichment subsystem.

QML intent
    ↓
EnrichmentBridge
    ↓
EnrichmentCoordinator / EnrichmentService
    ↓
Qt owner-thread projection (relay)
    ↓
QML

QML NEVER reaches providers, repositories, SQLite, HTTP or the resolver
directly. The backend (EnrichmentService = identity/generation/request/
knowledge authority; EnrichmentCoordinator = async workflow owner) is
FROZEN and untouched by this module.

THREADING (P0): coordinator callbacks arrive from executor worker
threads. Every callback is marshaled through ``_EnrichmentRelay`` with an
explicit ``Qt.QueuedConnection`` — the projection is ONLY ever mutated
on the bridge owner thread (the GUI thread).

DOUBLE ANTI-STALE FILTER: (A) each Presentation action bumps
``_presentation_intent_id``; the callback closure captures it and late
callbacks are dropped. (B) backend generation: an event whose generation
is older than the last observed generation for that entity is dropped.
A late CANCELLED/FAILED/READY from a previous artist can never change
the UI of the currently selected artist.
"""

from PySide6.QtCore import Property, QObject, Qt, Signal, Slot

from michi.application.enrichment_coordinator import (
    EnrichmentCoordinator,
    EnrichmentOperationEvent,
    EnrichmentOperationState,
)
from michi.application.enrichment_ports import EnrichmentAssetStorePort
from michi.application.enrichment_service import EnrichmentService
from michi.application.library_service import LibraryService


class _EnrichmentRelay(QObject):
    """Marshals worker-thread callbacks to the bridge owner thread."""

    event_received = Signal(object, int)  # (EnrichmentOperationEvent, intent_id)
    candidates_received = Signal(
        object, object, object, int, object
    )  # (kind, key, session, epoch, candidates)
    search_error = Signal(
        object, object, object, int, object
    )  # (kind, key, session, epoch, error)
    portrait_event_received = Signal(object)


_STATE_MESSAGES = {
    "DISABLED": "Online info is disabled",
    "RESOLVING_IDENTITY": "Finding {kind}…",
    "FETCHING_KNOWLEDGE": "Loading {kind} information…",
    "PARTIAL": "Some information could not be updated",
    "OFFLINE": "Offline — showing saved information",
    "FAILED": "Could not update {kind} information",
    "AMBIGUOUS": "{kind} match needs review",
    "NOT_FOUND": "No confident match found",
    "CANCELLED": "Operation cancelled",
}

_KIND_LABEL = {"artist": "artist", "album": "album"}

_TERMINAL_STATES = {
    EnrichmentOperationState.READY,
    EnrichmentOperationState.PARTIAL,
    EnrichmentOperationState.OFFLINE,
    EnrichmentOperationState.FAILED,
    EnrichmentOperationState.CANCELLED,
    EnrichmentOperationState.AMBIGUOUS,
    EnrichmentOperationState.NOT_FOUND,
    EnrichmentOperationState.DISABLED,
}

_MAX_PORTRAIT_PREFETCH_INFLIGHT = 2
_MAX_PORTRAIT_PREFETCH_QUEUE = 12


class EnrichmentBridge(QObject):
    """One production bridge exposing a stable QML projection.

    Detail activation semantics (never trigger network from search/scan):
    - activate_artist/activate_album: cached knowledge is projected
      immediately; network starts ONLY when Online Library Enrichment is
      ON and no cached knowledge exists (exactly once per activation).
    - Artist gallery delegates may request a missing portrait through the
      separate bounded prefetch slot. That workflow never activates an entity.
    - Manual review, clear and reset are explicit user actions.
    """

    changed = Signal()
    onlineEnabledChanged = Signal()

    def __init__(
        self,
        coordinator: EnrichmentCoordinator,
        service: EnrichmentService,
        library: LibraryService,
        asset_store: EnrichmentAssetStorePort,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._coordinator = coordinator
        self._service = service
        self._library = library
        self._asset_store = asset_store

        self._relay = _EnrichmentRelay()
        self._relay.event_received.connect(self._apply_event, Qt.QueuedConnection)
        self._relay.candidates_received.connect(
            self._apply_candidates, Qt.QueuedConnection
        )
        self._relay.search_error.connect(self._apply_search_error, Qt.QueuedConnection)
        self._relay.portrait_event_received.connect(
            self._apply_portrait_event, Qt.QueuedConnection
        )

        self._disposed = False
        self._presentation_intent_id = 0
        self._manual_search_epoch = 0
        self._review_session_id = 0
        self._candidates_session_id = -1
        self._last_generation: dict[tuple[str, str], int] = {}

        # policy
        self._online_enabled = False

        # active entity
        self._active_kind = ""
        self._active_key = ""
        self._state = "IDLE"
        self._state_message = ""
        self._knowledge_stale = False

        # projections
        self._artist_knowledge: dict = {}
        self._artist_has_knowledge = False
        self._artist_artwork_path = ""
        self._artist_attributions: list = []
        self._album_knowledge: dict = {}
        self._album_has_knowledge = False
        self._album_artwork_path = ""
        self._album_attributions: list = []
        self._artist_portraits: dict[str, str] = {}
        self._portrait_prefetch_queue: list[str] = []
        self._portrait_prefetch_inflight: set[str] = set()
        self._portrait_prefetch_attempted: set[str] = set()

        # manual review
        self._review_open = False
        self._review_kind = ""
        self._review_loading = False
        self._review_error = ""
        self._artist_candidates: list = []
        self._album_candidates: list = []

    # ------------------------------------------------------------------
    # QML properties
    # ------------------------------------------------------------------

    onlineEnabled = Property(
        bool, lambda self: self._online_enabled, notify=onlineEnabledChanged
    )
    busy = Property(
        bool,
        lambda self: self._state in ("RESOLVING_IDENTITY", "FETCHING_KNOWLEDGE"),
        notify=changed,
    )
    activeKind = Property(str, lambda self: self._active_kind, notify=changed)
    activeKey = Property(str, lambda self: self._active_key, notify=changed)
    state = Property(str, lambda self: self._state, notify=changed)
    stateMessage = Property(str, lambda self: self._state_message, notify=changed)

    artistKnowledge = Property(
        "QVariantMap", lambda self: self._artist_knowledge, notify=changed
    )
    artistHasKnowledge = Property(
        bool, lambda self: self._artist_has_knowledge, notify=changed
    )
    artistArtworkPath = Property(
        str, lambda self: self._artist_artwork_path, notify=changed
    )
    artistAttributions = Property(
        "QVariantList", lambda self: self._artist_attributions, notify=changed
    )

    albumKnowledge = Property(
        "QVariantMap", lambda self: self._album_knowledge, notify=changed
    )
    albumHasKnowledge = Property(
        bool, lambda self: self._album_has_knowledge, notify=changed
    )
    albumArtworkPath = Property(
        str, lambda self: self._album_artwork_path, notify=changed
    )
    albumAttributions = Property(
        "QVariantList", lambda self: self._album_attributions, notify=changed
    )
    artistPortraits = Property(
        "QVariantMap", lambda self: self._artist_portraits, notify=changed
    )

    reviewOpen = Property(bool, lambda self: self._review_open, notify=changed)
    reviewKind = Property(str, lambda self: self._review_kind, notify=changed)
    reviewLoading = Property(bool, lambda self: self._review_loading, notify=changed)
    reviewError = Property(str, lambda self: self._review_error, notify=changed)
    artistCandidates = Property(
        "QVariantList", lambda self: self._artist_candidates, notify=changed
    )
    albumCandidates = Property(
        "QVariantList", lambda self: self._album_candidates, notify=changed
    )

    # ------------------------------------------------------------------
    # activation (explicit detail only — never lists/scan/search)
    # ------------------------------------------------------------------

    @Slot(str)
    def prefetch_artist_portrait(self, local_artist_key: str) -> None:
        """Cache-first, bounded portrait intent for one instantiated tile.

        GridView delegate creation supplies the viewport bound; this bridge
        owns dedupe, network policy and concurrency. Detail activation state
        is never changed by this workflow.
        """
        if self._disposed or not local_artist_key:
            return
        profile = self._service.get_artist_knowledge(local_artist_key)
        if profile is not None:
            path = self._artwork_path_for(profile.artwork_asset_id)
            if path:
                self._set_artist_portrait(local_artist_key, path)
                return
        if (
            not self._online_enabled
            or (self._active_kind == "artist" and self._active_key == local_artist_key)
            or local_artist_key in self._portrait_prefetch_attempted
            or local_artist_key in self._portrait_prefetch_inflight
            or local_artist_key in self._portrait_prefetch_queue
        ):
            return
        if len(self._portrait_prefetch_queue) >= _MAX_PORTRAIT_PREFETCH_QUEUE:
            return
        self._portrait_prefetch_queue.append(local_artist_key)
        self._pump_portrait_prefetch()

    @Slot(str)
    def activate_artist(self, local_artist_key: str) -> None:
        if self._disposed or not local_artist_key:
            return
        self._invalidate_review_session()
        self._presentation_intent_id += 1
        if (
            self._active_kind == "artist"
            and self._active_key
            and self._active_key != local_artist_key
        ):
            self._coordinator.cancel_artist(self._active_key)
        self._active_kind = "artist"
        self._active_key = local_artist_key
        self._reset_transient()
        self._load_cached_artist()
        if not self._online_enabled:
            self._state = "READY" if self._artist_has_knowledge else "DISABLED"
            self._state_message = (
                "" if self._artist_has_knowledge else "Online info is disabled"
            )
            self.changed.emit()
            return
        if self._artist_has_knowledge:
            self._state = "PARTIAL" if self._knowledge_stale else "READY"
            self._state_message = (
                "Saved information may be outdated" if self._knowledge_stale else ""
            )
            self.changed.emit()
            return
        self._start_artist_operation(local_artist_key)

    @Slot(str)
    def activate_album(self, local_album_key: str) -> None:
        if self._disposed or not local_album_key:
            return
        self._invalidate_review_session()
        self._presentation_intent_id += 1
        if (
            self._active_kind == "album"
            and self._active_key
            and self._active_key != local_album_key
        ):
            self._coordinator.cancel_album(self._active_key)
        self._active_kind = "album"
        self._active_key = local_album_key
        self._reset_transient()
        self._load_cached_album()
        if not self._online_enabled:
            self._state = "READY" if self._album_has_knowledge else "DISABLED"
            self._state_message = (
                "" if self._album_has_knowledge else "Online info is disabled"
            )
            self.changed.emit()
            return
        if self._album_has_knowledge:
            self._state = "PARTIAL" if self._knowledge_stale else "READY"
            self._state_message = (
                "Saved information may be outdated" if self._knowledge_stale else ""
            )
            self.changed.emit()
            return
        self._start_album_operation(local_album_key)

    @Slot()
    def refresh_artist(self) -> None:
        if self._disposed or self._active_kind != "artist" or not self._active_key:
            return
        if not self._online_enabled:
            return  # network action: not available while OFF
        self._invalidate_review_session()
        self._presentation_intent_id += 1
        self._start_artist_operation(self._active_key, refresh=True)

    @Slot()
    def refresh_album(self) -> None:
        if self._disposed or self._active_kind != "album" or not self._active_key:
            return
        if not self._online_enabled:
            return
        self._invalidate_review_session()
        self._presentation_intent_id += 1
        self._start_album_operation(self._active_key, refresh=True)

    # ------------------------------------------------------------------
    # manual review
    # ------------------------------------------------------------------

    @Slot(str)
    def open_review(self, kind: str) -> None:
        if self._disposed or kind not in ("artist", "album"):
            return
        self._review_session_id += 1  # fresh review session
        self._review_kind = kind
        self._review_open = True
        self._review_loading = False
        self._review_error = ""
        self._artist_candidates = []
        self._album_candidates = []
        self._candidates_session_id = -1
        self.changed.emit()

    @Slot()
    def close_review(self) -> None:
        if not self._review_open:
            return
        self._invalidate_review_session()
        self._review_open = False
        self._review_loading = False
        self._review_error = ""
        self._artist_candidates = []
        self._album_candidates = []
        self.changed.emit()

    @Slot(str)
    def search_artist(self, name: str) -> None:
        if self._disposed or not self._review_open or self._review_kind != "artist":
            return
        name = name.strip()
        if not name:
            return
        if not self._online_enabled:
            self._review_error = "Online info is disabled"
            self.changed.emit()
            return
        self._manual_search_epoch += 1
        epoch = self._manual_search_epoch
        session = self._review_session_id
        kind = "artist"
        key = self._active_key
        self._review_loading = True
        self._review_error = ""
        self._artist_candidates = []

        def on_result(candidates):
            self._relay.candidates_received.emit(kind, key, session, epoch, candidates)

        def on_error(error):
            self._relay.search_error.emit(kind, key, session, epoch, error)

        self._coordinator.search_artist_candidates_async(name, on_result, on_error)
        self.changed.emit()

    @Slot(str, str)
    def search_album(self, title: str, artist_name: str) -> None:
        if self._disposed or not self._review_open or self._review_kind != "album":
            return
        title = title.strip()
        if not title:
            return
        if not self._online_enabled:
            self._review_error = "Online info is disabled"
            self.changed.emit()
            return
        self._manual_search_epoch += 1
        epoch = self._manual_search_epoch
        session = self._review_session_id
        kind = "album"
        key = self._active_key
        self._review_loading = True
        self._review_error = ""
        self._album_candidates = []

        def on_result(candidates):
            self._relay.candidates_received.emit(kind, key, session, epoch, candidates)

        def on_error(error):
            self._relay.search_error.emit(kind, key, session, epoch, error)

        self._coordinator.search_album_candidates_async(
            title, artist_name.strip(), on_result, on_error
        )
        self.changed.emit()

    @Slot(str)
    def confirm_artist_candidate(self, external_artist_id: str) -> None:
        if self._disposed or self._active_kind != "artist" or not self._active_key:
            return
        if not self._review_is_current():
            return  # no valid review session: never confirm stale candidates
        external_artist_id = external_artist_id.strip()
        if not external_artist_id:
            return
        self._coordinator.confirm_artist_identity(self._active_key, external_artist_id)
        self.close_review()
        self._presentation_intent_id += 1
        self._reset_transient()
        self._load_cached_artist()
        self._start_artist_operation(self._active_key, refresh=True)

    @Slot(str)
    def confirm_album_candidate(self, release_group_id: str) -> None:
        if self._disposed or self._active_kind != "album" or not self._active_key:
            return
        if not self._review_is_current():
            return  # no valid review session: never confirm stale candidates
        release_group_id = release_group_id.strip()
        if not release_group_id:
            return
        self._coordinator.confirm_album_identity(self._active_key, release_group_id)
        self.close_review()
        self._presentation_intent_id += 1
        self._reset_transient()
        self._load_cached_album()
        self._start_album_operation(self._active_key, refresh=True)

    # ------------------------------------------------------------------
    # clear knowledge vs reset match (distinct actions)
    # ------------------------------------------------------------------

    @Slot()
    def clear_knowledge(self) -> None:
        """CLEAR ONLINE INFO: identity stays, knowledge disappears.
        The active entity operation is CANCELLED first (generation
        retired), so a late worker delivery can never resurrect the
        deleted profile; the presentation intent bump makes every event
        of that operation stale."""
        if self._disposed or not self._active_key:
            return
        self._invalidate_review_session()
        self._presentation_intent_id += 1
        if self._active_kind == "artist":
            self._coordinator.cancel_artist(self._active_key)
            self._coordinator.clear_artist_knowledge(self._active_key)
        elif self._active_kind == "album":
            self._coordinator.cancel_album(self._active_key)
            self._coordinator.clear_album_knowledge(self._active_key)
        else:
            return
        self._clear_projection()
        self._state = "IDLE"
        self._state_message = ""
        self.changed.emit()

    @Slot()
    def reset_identity(self) -> None:
        """RESET MATCH: identity disappears, no automatic re-enrich.
        The backend reset is a generation barrier; the intent bump makes
        every late event of the previous operation stale for the UI."""
        if self._disposed or not self._active_key:
            return
        self._invalidate_review_session()
        self._presentation_intent_id += 1
        if self._active_kind == "artist":
            self._coordinator.reset_artist_identity(self._active_key)
        elif self._active_kind == "album":
            self._coordinator.reset_album_identity(self._active_key)
        else:
            return
        self._clear_projection()
        self._state = "IDLE"
        self._state_message = ""
        self.changed.emit()

    # ------------------------------------------------------------------
    # policy (composition root wires SettingsBridge -> here)
    # ------------------------------------------------------------------

    @Slot(bool)
    def on_online_enrichment_changed(self, enabled: bool) -> None:
        if self._disposed:
            return
        if not enabled:
            self._invalidate_review_session()
            # P1 residual: bump the presentation intent BEFORE cancel_all —
            # the worker's late CANCELLED/FAILED/READY carries the OLD
            # intent and becomes stale; the UI stays READY/DISABLED.
            self._presentation_intent_id += 1
        was_enabled = self._online_enabled
        self._online_enabled = enabled
        if enabled and not was_enabled:
            self._portrait_prefetch_attempted.clear()
        if enabled != was_enabled:
            self.onlineEnabledChanged.emit()
        if not enabled:
            # Persist OFF, cancel live operations: workers lose authority;
            # the UI converges to cached data (READY) or DISABLED.
            self._coordinator.cancel_all()
            self._portrait_prefetch_queue.clear()
            self._portrait_prefetch_inflight.clear()
            if self._active_kind == "artist":
                self._load_cached_artist()
                self._state = "READY" if self._artist_has_knowledge else "DISABLED"
                self._state_message = (
                    "" if self._artist_has_knowledge else "Online info is disabled"
                )
            elif self._active_kind == "album":
                self._load_cached_album()
                self._state = "READY" if self._album_has_knowledge else "DISABLED"
                self._state_message = (
                    "" if self._album_has_knowledge else "Online info is disabled"
                )
        self.changed.emit()

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------

    def dispose(self) -> None:
        """Idempotent: stops accepting QML events and drops all pending
        presentation callbacks. Never touches the coordinator here — the
        container calls this BEFORE enrichment.coordinator.shutdown()."""
        if self._disposed:
            return
        self._disposed = True
        self._portrait_prefetch_queue.clear()
        self._portrait_prefetch_inflight.clear()
        self._presentation_intent_id += 1
        self._manual_search_epoch += 1
        self._review_session_id += 1
        try:
            self._relay.event_received.disconnect(self._apply_event)
            self._relay.candidates_received.disconnect(self._apply_candidates)
            self._relay.search_error.disconnect(self._apply_search_error)
            self._relay.portrait_event_received.disconnect(self._apply_portrait_event)
        except RuntimeError:
            pass  # already disconnected

    # ------------------------------------------------------------------
    # relay slots (owner thread only)
    # ------------------------------------------------------------------

    def _apply_event(self, event: EnrichmentOperationEvent, intent: int) -> None:
        if self._disposed or intent != self._presentation_intent_id:
            return  # stale presentation intent
        kind = event.entity_kind.name.lower()
        if kind != self._active_kind or event.local_entity_key != self._active_key:
            return  # event belongs to another entity
        gen_key = (kind, event.local_entity_key)
        if event.generation < self._last_generation.get(gen_key, 0):
            return  # stale backend generation (0 = policy/unknown, always
            # older than any observed operation generation)
        if event.generation:
            self._last_generation[gen_key] = max(
                self._last_generation.get(gen_key, 0), event.generation
            )
        if (
            event.state is EnrichmentOperationState.READY
            or event.state is EnrichmentOperationState.PARTIAL
        ):
            self._reload_active_cached()
        elif event.state is EnrichmentOperationState.CANCELLED:
            self._state = "CANCELLED"
            self._state_message = "Operation cancelled"
            self.changed.emit()
            return
        self._state = event.state.name
        self._state_message = self._message_for(kind, event.state)
        self.changed.emit()

    def _apply_candidates(
        self, kind: str, key: str, session: int, epoch: int, candidates
    ) -> None:
        """Accept ONLY results bound to the exact review context: epoch +
        review session + entity kind + entity key + open review. A stale
        search from another entity (or an older review session) can never
        fill this dialog."""
        if (
            self._disposed
            or epoch != self._manual_search_epoch
            or session != self._review_session_id
            or kind != self._review_kind
            or key != self._active_key
            or not self._review_open
        ):
            return  # stale manual search
        if kind == "artist":
            self._artist_candidates = [
                {
                    "externalArtistId": c.external_artist_id,
                    "displayName": c.display_name,
                    "disambiguation": c.disambiguation,
                    "provider": c.provider,
                }
                for c in candidates
            ]
        else:
            self._album_candidates = [
                {
                    "externalReleaseGroupId": c.external_release_group_id,
                    "displayTitle": c.display_title,
                    "artistCredit": c.artist_credit,
                    "year": c.year,
                    "provider": c.provider,
                }
                for c in candidates
            ]
        # Bind the visible candidates to this exact review session so a
        # confirmation can never reuse candidates from another session.
        self._candidates_session_id = session
        self._review_loading = False
        self._review_error = ""
        self.changed.emit()

    def _apply_search_error(
        self, kind: str, key: str, session: int, epoch: int, error
    ) -> None:
        if (
            self._disposed
            or epoch != self._manual_search_epoch
            or session != self._review_session_id
            or kind != self._review_kind
            or key != self._active_key
            or not self._review_open
        ):
            return
        self._review_loading = False
        self._review_error = "Could not search — please try again later"
        self.changed.emit()

    def _apply_portrait_event(self, event: EnrichmentOperationEvent) -> None:
        """Owner-thread completion for gallery prefetch only.

        It deliberately does not touch activeKind, activeKey, detail state,
        review state or the active knowledge projections.
        """
        if self._disposed:
            return
        key = event.local_entity_key
        if key not in self._portrait_prefetch_inflight:
            return
        if event.state not in _TERMINAL_STATES:
            return
        self._portrait_prefetch_inflight.discard(key)
        if event.state in (
            EnrichmentOperationState.READY,
            EnrichmentOperationState.PARTIAL,
        ):
            profile = self._service.get_artist_knowledge(key)
            if profile is not None:
                self._set_artist_portrait(
                    key, self._artwork_path_for(profile.artwork_asset_id)
                )
        self._pump_portrait_prefetch()

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _invalidate_review_session(self) -> None:
        """P0-01: any navigation/policy/confirmation action invalidates
        the manual-search authority — old results can never be applied."""
        self._review_session_id += 1
        self._candidates_session_id = -1

    def _review_is_current(self) -> bool:
        """Confirmation safety: visible candidates must belong to the
        exact current review session of the exact active entity."""
        return (
            self._review_open
            and self._candidates_session_id == self._review_session_id
            and self._review_kind == self._active_kind
        )

    def _reset_transient(self) -> None:
        self._state = "IDLE"
        self._state_message = ""
        self._knowledge_stale = False

    def _set_artist_portrait(self, key: str, path: str) -> None:
        if not path or self._artist_portraits.get(key) == path:
            return
        self._artist_portraits = {**self._artist_portraits, key: path}
        self.changed.emit()

    def _pump_portrait_prefetch(self) -> None:
        while (
            not self._disposed
            and self._online_enabled
            and self._portrait_prefetch_queue
            and len(self._portrait_prefetch_inflight) < _MAX_PORTRAIT_PREFETCH_INFLIGHT
        ):
            key = self._portrait_prefetch_queue.pop(0)
            profile = self._service.get_artist_knowledge(key)
            if profile is not None:
                path = self._artwork_path_for(profile.artwork_asset_id)
                if path:
                    self._set_artist_portrait(key, path)
                    continue
            if self._active_kind == "artist" and self._active_key == key:
                continue
            artist, albums, tracks = self._artist_refs(key)
            self._portrait_prefetch_attempted.add(key)
            if artist is None:
                continue
            self._portrait_prefetch_inflight.add(key)

            def on_state(event):
                self._relay.portrait_event_received.emit(event)

            self._coordinator.enrich_artist(artist, albums, tracks, on_state)

    def _clear_projection(self) -> None:
        self._artist_knowledge = {}
        self._artist_has_knowledge = False
        self._artist_artwork_path = ""
        self._artist_attributions = []
        self._album_knowledge = {}
        self._album_has_knowledge = False
        self._album_artwork_path = ""
        self._album_attributions = []
        self._knowledge_stale = False

    def _load_cached_artist(self) -> None:
        profile = self._service.get_artist_knowledge(self._active_key)
        self._project_artist(profile)

    def _load_cached_album(self) -> None:
        profile = self._service.get_album_knowledge(self._active_key)
        self._project_album(profile)

    def _reload_active_cached(self) -> None:
        if self._active_kind == "artist":
            self._load_cached_artist()
        elif self._active_kind == "album":
            self._load_cached_album()

    def _project_artist(self, profile) -> None:
        if profile is None:
            self._artist_knowledge = {}
            self._artist_has_knowledge = False
            self._artist_artwork_path = ""
            self._artist_attributions = []
            self._knowledge_stale = False
            return
        knowledge = {
            "biography": profile.biography,
            "genres": list(profile.external_genres),
            "beginYear": profile.begin_year or profile.wikidata_begin_year,
            "endYear": profile.end_year or profile.wikidata_end_year,
            "area": profile.area,
            "country": profile.country_label or profile.country_qid,
            "artistType": profile.artist_type,
            "website": profile.official_website,
            "sortName": profile.sort_name,
            "wikipediaPageTitle": profile.wikipedia_page_title,
            "wikipediaLanguage": profile.wikipedia_language,
        }
        self._artist_knowledge = {k: v for k, v in knowledge.items() if v}
        self._artist_has_knowledge = bool(profile.biography or self._artist_knowledge)
        self._artist_artwork_path = self._artwork_path_for(profile.artwork_asset_id)
        self._artist_attributions = [
            self._attribution_map(p)
            for p in (
                profile.provenance,
                profile.biography_provenance,
                profile.wikidata_provenance,
            )
            if p.provider
        ]
        self._merge_asset_attribution(
            self._artist_attributions, profile.artwork_asset_id
        )
        self._knowledge_stale = any(
            p.is_stale
            for p in (
                profile.provenance,
                profile.biography_provenance,
                profile.wikidata_provenance,
            )
        )

    def _project_album(self, profile) -> None:
        if profile is None:
            self._album_knowledge = {}
            self._album_has_knowledge = False
            self._album_artwork_path = ""
            self._album_attributions = []
            self._knowledge_stale = False
            return
        knowledge = {
            "releaseGroupId": profile.release_group_id,
            "releaseId": profile.release_id,
            "genres": list(profile.external_genres),
            "firstReleaseYear": profile.first_release_year,
            "releaseYear": profile.release_year,
            "label": profile.label,
        }
        self._album_knowledge = {k: v for k, v in knowledge.items() if v}
        self._album_has_knowledge = bool(self._album_knowledge)
        self._album_artwork_path = self._artwork_path_for(profile.artwork_asset_id)
        self._album_attributions = (
            [self._attribution_map(profile.provenance)]
            if profile.provenance.provider
            else []
        )
        self._merge_asset_attribution(
            self._album_attributions, profile.artwork_asset_id
        )
        self._knowledge_stale = profile.provenance.is_stale

    @staticmethod
    def _attribution_map(prov) -> dict:
        entry = {
            "provider": prov.provider,
            "sourceUrl": prov.source_url,
            "language": prov.language,
            "license": prov.license,
            "licenseUrl": prov.license_url,
            "attribution": prov.attribution,
            "retrievedAt": prov.retrieved_at,
            "isStale": prov.is_stale,
        }
        # never invent fields: only truthy values are projected (isStale
        # is a boolean flag and is always included).
        return {k: v for k, v in entry.items() if v or k == "isStale"}

    def _artwork_path_for(self, asset_id: str) -> str:
        if not asset_id:
            return ""
        path = self._asset_store.path_for(asset_id)
        return str(path) if path is not None else ""

    def _merge_asset_attribution(self, attributions: list, asset_id: str) -> None:
        """P1-04: project the asset record's own truthful provenance
        (creator/license/licenseUrl/attribution/sourceUrl) next to the
        profile provenance. Never invent fields; skip a row that is
        semantically identical to an existing profile row."""
        if not asset_id:
            return
        record = self._asset_store.record_for(asset_id)
        if record is None:
            return
        entry = {
            "provider": record.provider or "",
            "sourceUrl": record.source_url or "",
            "creator": record.creator or "",
            "license": record.license or "",
            "licenseUrl": record.license_url or "",
            "attribution": record.attribution or "",
            "isStale": False,
        }
        entry = {k: v for k, v in entry.items() if v or k == "isStale"}
        for existing in attributions:
            if existing.get("provider") == entry.get("provider") and existing.get(
                "sourceUrl"
            ) == entry.get("sourceUrl"):
                return  # semantically identical row — avoid duplicates
        attributions.append(entry)

    def _message_for(self, kind: str, state: EnrichmentOperationState) -> str:
        template = _STATE_MESSAGES.get(state.name, "")
        if not template:
            return ""
        return template.format(kind=_KIND_LABEL.get(kind, "entity"))

    def _artist_refs(self, key: str):
        artist = self._library.artist_by_key(key)
        if artist is None:
            return None, (), ()
        return (
            artist,
            self._library.albums_for_artist(key),
            self._library.tracks_for_artist(key),
        )

    def _album_refs(self, key: str):
        return self._library.album_by_key(key)

    def _start_artist_operation(self, key: str, refresh: bool = False) -> None:
        artist, albums, tracks = self._artist_refs(key)
        if artist is None:
            self._state = "NOT_FOUND"
            self._state_message = "No confident match found"
            self.changed.emit()
            return
        intent = self._presentation_intent_id

        def on_state(event):
            self._relay.event_received.emit(event, intent)

        if refresh:
            self._coordinator.refresh_artist_enrichment(
                artist, albums, tracks, on_state
            )
        else:
            self._coordinator.enrich_artist(artist, albums, tracks, on_state)

    def _start_album_operation(self, key: str, refresh: bool = False) -> None:
        album = self._album_refs(key)
        if album is None:
            self._state = "NOT_FOUND"
            self._state_message = "No confident match found"
            self.changed.emit()
            return
        intent = self._presentation_intent_id

        def on_state(event):
            self._relay.event_received.emit(event, intent)

        if refresh:
            self._coordinator.refresh_album_enrichment(album, on_state=on_state)
        else:
            self._coordinator.enrich_album(album, on_state=on_state)
