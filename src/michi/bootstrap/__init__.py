"""Composition root — wires dependencies, owns lifecycle. No business logic.

M6-PRODUCTION-INTEGRATION-AND-ASYNC-CORRECTION: ``_build_services`` is the
single production-graph construction path shared by the application
container AND the tests — TEST GRAPH == PRODUCTION GRAPH. The container
additionally wires the QML engine, settings/coordinators and owns the
shutdown lifecycle.
"""

import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from michi.application.audio_engine_registry import AudioEngineRegistry
from michi.application.audio_engine_service import AudioEngineService
from michi.application.audio_transport_router import AudioTransportRouter
from michi.application.coordinator import PlaybackCoordinator
from michi.application.library_preferences_coordinator import (
    LibraryPreferencesCoordinator,
)
from michi.application.library_service import LibraryService
from michi.application.navigation_service import NavigationService
from michi.application.persistence_coordinator import PersistenceCoordinator
from michi.application.playback_service import PlaybackService
from michi.application.playlist_navigation_coordinator import (
    PlaylistNavigationCoordinator,
)
from michi.application.playlist_service import PlaylistService
from michi.application.queue_service import QueueService
from michi.application.settings_service import SettingsService
from michi.domain.audio_engine import AudioEngineId
from michi.infrastructure.artwork import ArtworkCache, MutagenArtworkProvider
from michi.infrastructure.audio_engines.providers import (
    GStreamerEngineProvider,
    MpdEngineProvider,
    QtEngineProvider,
)
from michi.infrastructure.filesystem_scanner import FilesystemLibraryScanner
from michi.infrastructure.library_index import SqliteLibraryIndexRepository
from michi.infrastructure.library_prefs import SqliteLibraryPrefsRepository
from michi.infrastructure.metadata_extractor import InfrastructureMetadataExtractor
from michi.infrastructure.playlists import SqlitePlaylistsRepository
from michi.infrastructure.qt_backend import (
    QtMultimediaBackend as QtMultimediaBackend,  # noqa: F401 — re-export histórico para tests
)
from michi.infrastructure.scan_dispatcher import LibraryScanDispatcher
from michi.infrastructure.scan_runner import ScanRelay, ThreadScanRunner
from michi.infrastructure.session_repository import SqliteSessionRepository
from michi.infrastructure.sqlite_settings import SQLiteSettingsRepository
from michi.presentation.library_bridge import LibraryBridge
from michi.presentation.navigation_bridge import NavigationBridge
from michi.presentation.playback_bridge import PlaybackBridge
from michi.presentation.playlists_bridge import PlaylistsBridge
from michi.presentation.queue_bridge import QueueBridge
from michi.presentation.settings_bridge import SettingsBridge

_MISSING = object()  # sentinel: production default vs explicit None override


def _data_dir() -> Path:
    base = QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)
    path = Path(base)
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class ServiceGraph:
    """The production library graph — the same wiring for app and tests."""

    db_path: Path
    library: LibraryService
    bridge: LibraryBridge
    runner: ThreadScanRunner
    dispatcher: LibraryScanDispatcher
    playlist_service: PlaylistService
    library_index: SqliteLibraryIndexRepository
    library_prefs_repo: SqliteLibraryPrefsRepository
    playlists_repo: SqlitePlaylistsRepository
    relay: ScanRelay
    queue: QueueService
    playback: PlaybackService
    # NON-AUTHORITY / OBSERVABILITY ONLY: the concrete port bound inside the
    # router (test handle / introspection). Ownership lives in the provider.
    bound_audio_port: object
    audio_router: AudioTransportRouter
    audio_engine_registry: AudioEngineRegistry
    audio_engine_service: AudioEngineService
    qt_engine_provider: QtEngineProvider
    scanner: object
    metadata_extractor: object
    artwork_provider: object
    artwork_cache: object


def _initialize_reference_audio_runtime(
    qt_provider,
    registry,
    engine_service,
    router,
    *,
    injected_backend=None,
):
    """Canonical reference-engine startup transaction (M11.3B-R1).

    PROBE → CAN_ACTIVATE → INITIALIZING → OPEN → ROUTER BIND → VALIDATE →
    READY. Pre-init blockers converge to UNAVAILABLE; post-init failures
    clean up (router unbind + provider close best effort) and converge to
    FAILED, then re-raise the ORIGINAL error (first-error-wins).

    ``injected_backend`` is the TEST seam: a fake AudioPort bound through
    the SAME router (topology parity) but NOT owned by the provider (its
    ownership stays with the test). Returns the bound concrete port.
    """
    descriptor = registry.descriptor(AudioEngineId.QT_MULTIMEDIA)
    if not descriptor.can_activate:
        engine_service.mark_unavailable(
            AudioEngineId.QT_MULTIMEDIA, descriptor.activation_blocker
        )
        raise RuntimeError(
            f"Qt reference engine no activable: {descriptor.activation_blocker}"
        )

    engine_service.mark_initializing(AudioEngineId.QT_MULTIMEDIA)
    provider_owned = injected_backend is None
    try:
        backend = qt_provider.open() if provider_owned else injected_backend
        router.bind(AudioEngineId.QT_MULTIMEDIA, backend)
        # validate transport: bound identity + concrete target
        if router.bound_engine_id != AudioEngineId.QT_MULTIMEDIA:
            raise RuntimeError("router bind validation failed")
    except Exception as original:
        # M11.3B-R2 FIRST-ERROR-WINS: every cleanup step is best effort —
        # a secondary cleanup failure (e.g. router.unbind raising) must
        # NEVER replace the primary startup failure, must NEVER skip the
        # FAILED state, and the primary exception is always re-raised
        # (bare raise preserves the original traceback).
        from contextlib import suppress

        with suppress(Exception):
            router.unbind()
        if provider_owned:
            with suppress(Exception):
                qt_provider.close()
        engine_service.mark_failed(AudioEngineId.QT_MULTIMEDIA, str(original))
        raise
    engine_service.mark_ready(AudioEngineId.QT_MULTIMEDIA)
    return backend


def _build_services(
    db_path,
    *,
    backend=None,
    scanner=None,
    metadata_extractor=None,
    artwork_provider=_MISSING,
    artwork_cache=_MISSING,
) -> ServiceGraph:
    """Build the PRODUCTION library service graph (composition root core).

    The application container and the production-composition tests share
    this exact construction path. ``backend`` defaults to the real Qt
    backend (tests inject the fake audio port); ``scanner``/
    ``metadata_extractor`` default to the real infrastructure (tests inject
    spies); ``artwork_provider``/``artwork_cache`` default to the real
    Mutagen implementations (passing None disables artwork in headless
    tests). All library persistence is real: SqliteLibraryIndexRepository,
    SqliteLibraryPrefsRepository, SqlitePlaylistsRepository.
    """
    # M11.3B-R1: ONE canonical Qt provider instance — the SAME object is
    # registered in the registry AND used as the productive provider
    # (registry.provider(QT) is qt_provider). The reference engine startup
    # runs the canonical lifecycle transaction (probe → can_activate →
    # INITIALIZING → open → bind → validate → READY) with honest failure
    # convergence (UNAVAILABLE pre-init / FAILED post-init + cleanup).
    qt_provider = QtEngineProvider()
    gstreamer_provider = GStreamerEngineProvider()
    mpd_provider = MpdEngineProvider()
    registry = AudioEngineRegistry([qt_provider, gstreamer_provider, mpd_provider])
    engine_service = AudioEngineService(registry)
    router = AudioTransportRouter()
    backend = _initialize_reference_audio_runtime(
        qt_provider,
        registry,
        engine_service,
        router,
        injected_backend=backend,
    )
    if scanner is None:
        scanner = FilesystemLibraryScanner()
    if metadata_extractor is None:
        metadata_extractor = InfrastructureMetadataExtractor()
    if artwork_provider is _MISSING:
        artwork_provider = MutagenArtworkProvider()
    if artwork_cache is _MISSING:
        artwork_cache = ArtworkCache(Path.home() / ".cache" / "michi" / "artwork")

    playback = PlaybackService(router)
    queue = QueueService(playback)

    library_index = SqliteLibraryIndexRepository(db_path)
    library_prefs_repo = SqliteLibraryPrefsRepository(db_path)
    playlists_repo = SqlitePlaylistsRepository(db_path)
    playlist_service = PlaylistService(queue, playlists_repo)

    scan_relay = ScanRelay()
    scan_runner = ThreadScanRunner(scan_relay)

    library = LibraryService(
        scanner,
        queue,
        metadata_extractor,
        artwork_provider,
        artwork_cache,
        library_prefs=library_prefs_repo,
        library_index=library_index,
        scan_pipeline=scan_runner,
    )

    # Owner-thread async dispatch (M6-PRODUCTION-INTEGRATION): the runner
    # emits on the worker thread; the EXPLICIT QueuedConnection delivers
    # progress/done to the owner (GUI) thread where the dispatcher delegates
    # to the service. The service never touches Qt.
    scan_dispatcher = LibraryScanDispatcher(library)
    scan_relay.done.connect(scan_dispatcher.on_done, Qt.QueuedConnection)
    scan_relay.progress.connect(scan_dispatcher.on_progress, Qt.QueuedConnection)

    lb = LibraryBridge(library)

    return ServiceGraph(
        db_path=db_path,
        library=library,
        bridge=lb,
        runner=scan_runner,
        dispatcher=scan_dispatcher,
        playlist_service=playlist_service,
        library_index=library_index,
        library_prefs_repo=library_prefs_repo,
        playlists_repo=playlists_repo,
        relay=scan_relay,
        queue=queue,
        playback=playback,
        bound_audio_port=backend,
        audio_router=router,
        audio_engine_registry=registry,
        audio_engine_service=engine_service,
        qt_engine_provider=qt_provider,
        scanner=scanner,
        metadata_extractor=metadata_extractor,
        artwork_provider=artwork_provider,
        artwork_cache=artwork_cache,
    )


class ApplicationContainer:
    """Creates and owns all long-lived components. Explicit wiring only."""

    def __init__(self) -> None:
        self._app: QGuiApplication | None = None
        self._engine: QQmlApplicationEngine | None = None
        self._audio_router: AudioTransportRouter | None = None
        self._qt_engine_provider: QtEngineProvider | None = None
        self._settings: SettingsService | None = None
        self._playback: PlaybackService | None = None
        self._queue: QueueService | None = None
        self._library: LibraryService | None = None
        self._library_prefs: LibraryPreferencesCoordinator | None = None
        self._navigation: NavigationService | None = None
        self._coordinator: PlaybackCoordinator | None = None
        self._persistence: PersistenceCoordinator | None = None
        self._playlist_service: PlaylistService | None = None
        self._scan_runner: ThreadScanRunner | None = None
        self._scan_dispatcher: LibraryScanDispatcher | None = None
        self._pb: PlaybackBridge | None = None
        self._qb: QueueBridge | None = None
        self._lb: LibraryBridge | None = None
        self._plb: PlaylistsBridge | None = None
        self._nb: NavigationBridge | None = None
        self._sb: SettingsBridge | None = None

    def initialize(self) -> None:
        QGuiApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QGuiApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        self._app = QGuiApplication.instance() or QGuiApplication(sys.argv)
        self._app.setApplicationName("Michi Music Player")
        self._app.setApplicationVersion("0.1.0")
        self._app.setOrganizationName("Michi")

        db_path = _data_dir() / "michi.db"
        repo = SQLiteSettingsRepository.open_for_startup(db_path)
        graph = _build_services(db_path)
        self._audio_router = graph.audio_router
        self._qt_engine_provider = graph.qt_engine_provider
        settings = SettingsService(repo)

        playback = graph.playback
        queue = graph.queue
        library = graph.library
        scan_runner = graph.runner
        scan_dispatcher = graph.dispatcher
        playlist_service = graph.playlist_service

        navigation = NavigationService()

        # M8-R1 delete convergence: deleting the playlist that is the active
        # navigation target converges to PLAYLISTS / All Playlists. The
        # navigation service stays the sole NavigationState authority; the
        # hook only forwards the deleted id.
        playlist_service.set_on_playlist_deleted(navigation.forget_playlist)

        # Load persisted preferences once
        s = settings.load()
        playback.restore_volume(s.volume, s.muted)

        # Library/settings coordination: restore last_directory, sync on scan
        lib_prefs = LibraryPreferencesCoordinator(library, settings)
        lib_prefs.start()

        # M11.3B: PlaybackCoordinator subscribes to the SAME router instance
        # as PlaybackService — one transport identity for both consumers.
        coordinator = PlaybackCoordinator(graph.audio_router, queue, playback)
        coordinator.start()

        # Session persistence (M5.C5): runtime checkpoints + startup restore.
        # Shares the settings database; restores the queue and, when the
        # queue current identity matches the persisted playback identity,
        # prepares a non-autoplay resume — before the UI is shown, never
        # blocking autoplay. The coordinator lifecycle is explicit, in the
        # CANONICAL production order (M5-PRODUCTION-LIFECYCLE-GATE):
        # start() arms the runtime subscriptions (queue/playback/
        # resume_prepared) BEFORE restore() so a FAST backend's
        # resume_prepared is never lost; _restoring suppresses the
        # restore-generated checkpoints.
        session_repo = SqliteSessionRepository(db_path)
        persistence = PersistenceCoordinator(session_repo, queue, playback, settings)
        persistence.start()
        persistence.restore()

        pb = PlaybackBridge(playback, library)
        qb = QueueBridge(queue, library)
        lb = graph.bridge
        # M8-R1F: application-level coordination for the OPEN PLAYLIST
        # product intent (validate → recent → navigate). Not a state
        # authority: it only orchestrates PlaylistService + NavigationService.
        playlist_nav = PlaylistNavigationCoordinator(playlist_service, navigation)
        nb = NavigationBridge(navigation, playlist_navigation=playlist_nav)
        # M9-R1: first-class Playlists presentation bridge — canonical
        # playlist projection lives here, not in LibraryBridge.
        plb = PlaylistsBridge(
            playlist_service,
            playlist_navigation=playlist_nav,
            navigation_service=navigation,
            library=library,
        )
        sb = SettingsBridge(settings)

        engine = QQmlApplicationEngine()
        engine.quit.connect(self._app.quit)
        ctx = engine.rootContext()
        ctx.setContextProperty("playback", pb)
        ctx.setContextProperty("queue", qb)
        ctx.setContextProperty("library", lb)
        ctx.setContextProperty("navigation", nb)
        ctx.setContextProperty("playlists", plb)
        ctx.setContextProperty("settingsBridge", sb)

        self._settings = settings
        self._playback = playback
        self._queue = queue
        self._library = library
        self._playlist_service = playlist_service
        self._scan_runner = scan_runner
        self._scan_dispatcher = scan_dispatcher
        self._library_prefs = lib_prefs
        self._navigation = navigation
        self._coordinator = coordinator
        self._persistence = persistence
        self._pb = pb
        self._qb = qb
        self._lb = lb
        self._plb = plb
        self._nb = nb
        self._sb = sb
        self._engine = engine

    def run(self) -> int:
        qml_dir = Path(__file__).parent.parent / "presentation"
        main_qml = qml_dir / "main.qml"
        if not main_qml.exists():
            print(f"FATAL: QML entry not found at {main_qml}", file=sys.stderr)
            return 1
        self._engine.load(QUrl.fromLocalFile(str(main_qml)))
        if not self._engine.rootObjects():
            print("FATAL: QML engine failed to load any root object", file=sys.stderr)
            return 1
        return self._app.exec()

    def shutdown(self) -> None:
        error: Exception | None = None

        # The persistence coordinator owns the durable session + prefs
        # policy: freeze, final checkpoint and volume/mute persistence all
        # happen FIRST, before any runtime teardown, so the final durable
        # checkpoint always precedes the backend teardown events. The
        # container only calls lifecycle; when no coordinator is wired
        # (partial startup / tests), it falls back to persisting the prefs
        # directly so volume/mute are never silently dropped at shutdown.
        try:
            if self._persistence:
                self._persistence.shutdown()
            elif self._playback and self._settings:
                vol, muted = self._playback.snapshot_volume()
                self._settings.set_playback_preferences(vol, muted)
                self._settings.save()
        except Exception as exc:
            error = error or exc

        # Async scan lifecycle (M6-PRODUCTION-INTEGRATION): freeze the
        # runner (reject new submits + cancel active generations) and close
        # the dispatcher (drop late callbacks) BEFORE any bridge/coordinator
        # teardown — a worker finishing late can never mutate LibraryState
        # or reach the QML bridge.
        try:
            if self._scan_runner:
                self._scan_runner.shutdown()
            if self._scan_dispatcher:
                self._scan_dispatcher.shutdown()
            if self._scan_runner and self._scan_runner._relay is not None:
                try:
                    self._scan_runner._relay.done.disconnect()
                    self._scan_runner._relay.progress.disconnect()
                except (TypeError, RuntimeError):
                    pass  # no live connections
        except Exception as exc:
            error = error or exc

        try:
            if self._coordinator:
                self._coordinator.stop()
        except Exception as exc:
            error = error or exc

        try:
            if self._library_prefs:
                self._library_prefs.stop()
        except Exception as exc:
            error = error or exc

        for bridge in (self._pb, self._qb, self._lb, self._plb, self._nb):
            try:
                if bridge:
                    bridge.dispose()
            except Exception as exc:
                error = error or exc

        # M11.3B SWITCH ORDER: the router detaches BEFORE the provider
        # closes. The provider owns the backend lifecycle (stop + release);
        # the container never stops the backend directly anymore.
        try:
            if self._audio_router:
                self._audio_router.unbind()
        except Exception as exc:
            error = error or exc

        try:
            if self._qt_engine_provider:
                self._qt_engine_provider.close()
        except Exception as exc:
            error = error or exc

        try:
            if self._engine:
                self._engine.deleteLater()
        except Exception as exc:
            error = error or exc

        self._engine = None
        self._audio_router = None
        self._qt_engine_provider = None
        self._lb = None
        self._plb = None
        self._qb = None
        self._pb = None
        self._nb = None
        self._sb = None
        self._coordinator = None
        self._persistence = None
        self._library_prefs = None
        self._playlist_service = None
        self._scan_runner = None
        self._scan_dispatcher = None
        self._navigation = None
        self._library = None
        self._queue = None
        self._playback = None
        self._settings = None
        self._app = None

        if error is not None:
            raise error
