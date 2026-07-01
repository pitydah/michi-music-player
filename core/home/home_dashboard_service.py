from __future__ import annotations

import logging
import os
import time

from core.home.home_status import (
    AssistantSuggestion,
    AudioHomeStatus,
    EcosystemHomeStatus,
    HomeAction,
    HomeAlert,
    HomeCardError,
    HomeDashboardSnapshot,
    LibraryHomeStatus,
    PlaybackHomeStatus,
)

logger = logging.getLogger("michi.home.dashboard_service")


class HomeDashboardService:
    """Build a HomeDashboardSnapshot from existing services.

    Tolerates missing services — each card can fail independently
    without breaking the whole dashboard.
    """

    def __init__(
        self,
        db=None,
        playback=None,
        context_svc=None,
        sync_mgr=None,
        audio_output_ctrl=None,
        player_engine=None,
        features=None,
        settings_mgr=None,
        michi_link_ctrl=None,
    ):
        self._db = db
        self._playback = playback
        self._context_svc = context_svc
        self._sync_mgr = sync_mgr
        self._audio_output_ctrl = audio_output_ctrl
        self._player_engine = player_engine
        self._features = features
        self._settings_mgr = settings_mgr
        self._michi_link_ctrl = michi_link_ctrl

    def build_snapshot(self) -> HomeDashboardSnapshot:
        errors: list[HomeCardError] = []

        try:
            library = self._build_library_status()
        except Exception as e:
            logger.exception("Library status failed")
            library = LibraryHomeStatus(is_empty=True, is_healthy=False)
            errors.append(HomeCardError("library", str(e), is_fatal=False))

        try:
            playback = self._build_playback_status()
        except Exception as e:
            logger.exception("Playback status failed")
            playback = PlaybackHomeStatus()
            errors.append(HomeCardError("playback", str(e), is_fatal=False))

        try:
            audio = self._build_audio_status()
        except Exception as e:
            logger.exception("Audio status failed")
            audio = AudioHomeStatus()
            errors.append(HomeCardError("audio", str(e), is_fatal=False))

        try:
            ecosystem = self._build_ecosystem_status()
        except Exception as e:
            logger.exception("Ecosystem status failed")
            ecosystem = EcosystemHomeStatus()
            errors.append(HomeCardError("ecosystem", str(e), is_fatal=False))

        try:
            alerts = self._build_alerts(library, audio, ecosystem)
        except Exception as e:
            logger.exception("Alerts build failed")
            alerts = []
            errors.append(HomeCardError("alerts", str(e), is_fatal=False))

        try:
            suggestions = self._build_assistant_suggestions(library, playback)
        except Exception as e:
            logger.exception("Assistant suggestions failed")
            suggestions = []
            errors.append(HomeCardError("assistant_suggestions", str(e), is_fatal=False))

        overall_state = self._derive_overall_state(library, playback, audio, ecosystem)
        headline = self._format_headline(overall_state)
        subtitle = self._format_subtitle(library, audio, ecosystem)
        actions = self._build_actions(overall_state, library, ecosystem)

        playback.can_continue_remote = bool(
            playback.can_continue
            and ecosystem.micro_server_state == "connected"
            and ecosystem.diagnostics_available
        )

        return HomeDashboardSnapshot(
            overall_state=overall_state,
            headline=headline,
            subtitle=subtitle,
            library=library,
            playback=playback,
            audio=audio,
            ecosystem=ecosystem,
            alerts=alerts,
            assistant_suggestions=suggestions,
            actions=actions,
            errors=errors,
            generated_at=time.time(),
        )

    def _build_library_status(self) -> LibraryHomeStatus:
        ctx = self._context_svc
        db = self._db

        if ctx is not None:
            try:
                snap = ctx.get_home_snapshot()
                if snap and "library_health" in snap:
                    lh = snap["library_health"]
                    return LibraryHomeStatus(
                        track_count=lh.get("track_count", 0),
                        album_count=lh.get("album_count", 0),
                        artist_count=lh.get("artist_count", 0),
                        genre_count=lh.get("genre_count", 0),
                        active_roots_count=lh.get("active_roots_count", 0),
                        last_scan=lh.get("last_scan"),
                        index_error_count=lh.get("index_error_count", 0),
                        missing_file_count=lh.get("missing_file_count", 0),
                        missing_metadata_count=lh.get("missing_metadata_count", 0),
                        missing_cover_count=lh.get("missing_cover_count", 0),
                        tracks_without_audio_features=lh.get(
                            "tracks_without_audio_features", 0
                        ),
                        new_tracks_count=lh.get("new_tracks_count", 0),
                        is_empty=lh.get("track_count", 0) == 0,
                        is_healthy=(
                            lh.get("index_error_count", 0) == 0
                            and lh.get("missing_file_count", 0) == 0
                        ),
                    )
            except Exception:
                logger.debug("ContextService snapshot unavailable, falling back to DB")

        if db is not None:
            try:
                if hasattr(db, "get_dashboard_stats"):
                    ds = db.get_dashboard_stats()
                elif hasattr(db, "get_stats"):
                    ds = db.get_stats()
                else:
                    ds = {}
                tc = ds.get("total_songs", ds.get("total", 0))
                return LibraryHomeStatus(
                    track_count=tc,
                    album_count=ds.get("total_albums", 0),
                    artist_count=ds.get("total_artists", 0),
                    missing_metadata_count=ds.get("missing_metadata", 0),
                    is_empty=tc == 0,
                    is_healthy=True,
                )
            except Exception:
                logger.debug("DB stats unavailable")

        return LibraryHomeStatus(is_empty=True, is_healthy=True)

    @staticmethod
    def _normalize_playback_state(state) -> str:
        if state is None:
            return "stopped"
        if hasattr(state, "name"):
            state = str(state.name)
        value = str(state).lower()
        if "." in value:
            value = value.rsplit(".", 1)[-1]
        if value in ("playing",):
            return "playing"
        if value in ("paused",):
            return "paused"
        return "stopped"

    def _build_playback_status(self) -> PlaybackHomeStatus:
        pb = self._playback
        if pb is None:
            return PlaybackHomeStatus()

        try:
            raw = getattr(pb, "state", "stopped") or "stopped"
        except Exception:
            raw = "unknown"
        state = self._normalize_playback_state(raw)

        has_current = state in ("playing", "paused")
        state_value = state
        title = ""
        artist = ""
        album = ""
        position = 0.0
        duration = 0.0

        if has_current:
            try:
                cur = pb.current if hasattr(pb, "current") else None
                if cur:
                    title = getattr(cur, "title", "") or ""
                    artist = getattr(cur, "artist", "") or ""
                    album = getattr(cur, "album", "") or ""
            except Exception:
                pass
            try:
                if hasattr(pb, "duration"):
                    duration = pb.duration if callable(pb.duration) is False else 0.0
            except Exception:
                pass

        queue_active = False
        queue_count = 0
        try:
            if hasattr(pb, "get_queue_state"):
                qs = pb.get_queue_state()
                if isinstance(qs, tuple) and len(qs) == 2:
                    paths, idx = qs
                    queue_active = len(paths) > 0
                    queue_count = len(paths)
                elif isinstance(qs, dict):
                    queue_active = qs.get("active", False) or qs.get("count", 0) > 0
                    queue_count = qs.get("count", 0)
        except Exception:
            pass

        last_title = ""
        last_artist = ""
        ctx = self._context_svc
        if ctx is not None and not has_current:
            try:
                snap = ctx.get_home_snapshot()
                if snap and "playback" in snap:
                    pb_snap = snap["playback"]
                    np = pb_snap.get("now_playing", {}) or {}
                    last_title = np.get("title", "")
                    last_artist = np.get("artist", "")
            except Exception:
                pass

        can_continue = has_current or bool(last_title)

        return PlaybackHomeStatus(
            has_current_track=has_current,
            current_title=title,
            current_artist=artist,
            current_album=album,
            current_position=position,
            current_duration=duration,
            queue_active=queue_active,
            queue_count=queue_count,
            last_track_title=last_title,
            last_track_artist=last_artist,
            can_continue=can_continue,
            state=state_value,
        )

    def _build_audio_status(self) -> AudioHomeStatus:
        output_device = ""
        output_profile = ""
        replaygain_enabled = False
        eq_enabled = False
        dsp_active = False
        bitperfect_state = "not_available"
        warnings_list: list[str] = []

        try:
            from core.settings_manager import get_str, get_bool

            output_profile = get_str("audio/profile") or ""
            replaygain_enabled = get_bool("audio/replaygain_enabled")
        except Exception:
            pass

        if self._player_engine is not None:
            try:
                eng = self._player_engine
                if hasattr(eng, "dsp_state") and eng.dsp_state is not None:
                    dsp = eng.dsp_state
                    eq_enabled = getattr(dsp, "eq_enabled", False)
                    dsp_active = getattr(dsp, "is_dsp_active", lambda: False)()
                    replaygain_enabled = (
                        replaygain_enabled or getattr(dsp, "replaygain_enabled", False)
                    )

                if hasattr(eng, "current_format"):
                    fmt = eng.current_format
                    if fmt:
                        bitperfect_state = "not_verified"
                        if "bitperfect" in output_profile.lower():
                            bitperfect_state = "verified"
            except Exception:
                pass

        if self._playback is not None:
            try:
                pb = self._playback
                if hasattr(pb, "get_output_device_id"):
                    oid = pb.get_output_device_id()
                    if oid:
                        output_device = str(oid)
                if hasattr(pb, "get_audio_diagnostics"):
                    diag = pb.get_audio_diagnostics()
                    if isinstance(diag, dict) and diag.get("warnings"):
                        warnings_list = diag["warnings"]
                # EQ from PlayerService public API
                if hasattr(pb, "get_eq_state"):
                    eq_state = pb.get_eq_state()
                    if isinstance(eq_state, dict):
                        eq_enabled = not eq_state.get("bypass", True)
                        dsp_active = dsp_active or eq_enabled
            except Exception:
                pass

        if not output_device:
            output_device = "Predeterminado"

        return AudioHomeStatus(
            output_device=output_device,
            output_profile=output_profile,
            replaygain_enabled=replaygain_enabled,
            eq_enabled=eq_enabled,
            dsp_active=dsp_active,
            bitperfect_state=bitperfect_state,
            warnings=warnings_list,
        )

    def _build_ecosystem_status(self) -> EcosystemHomeStatus:
        micro_state = "not_configured"
        micro_name = ""
        micro_issue_code = ""
        micro_host = ""
        remote_music_state = "not_configured"
        remote_music_count = 0
        remote_music_name = ""
        sync_state = "no_device"
        sync_count = 0
        api_state = "unknown"
        ha_state = "disabled"
        last_sync = None
        diag_avail = False

        try:
            from core.settings_manager import get_str
            micro_host = get_str("michi_link/micro_host", "")
            micro_port = 53318
            if micro_host:
                micro_state = "unreachable"
                micro_name = f"{micro_host}:{micro_port}"
        except Exception:
            pass

        # Use Michi Link controller for real Micro Server state
        mlc = self._michi_link_ctrl
        if mlc is not None:
            try:
                conn_state = mlc.get_connection_state()
                if conn_state:
                    ms = conn_state.get("micro_server_state")
                    if ms == "connected":
                        micro_state = "connected"
                        micro_name = conn_state.get("micro_server_name", micro_name)
                    elif ms == "requires_pairing":
                        micro_state = "requires_pairing"
                    elif ms == "contract_error":
                        micro_state = "contract_error"
                    elif ms == "disconnected":
                        micro_state = "disconnected"
            except Exception:
                pass

        try:
            from streaming.subsonic_client import load_servers
            servers = load_servers()
            if servers:
                remote_music_state = "configured"
                remote_music_count = len(servers)
                srv = servers[0]
                remote_music_name = getattr(srv, "name", "") or getattr(srv, "server_type", "Servidor")
        except Exception:
            pass

        if self._sync_mgr is not None:
            try:
                peers = self._sync_mgr.get_all_peers()
                if peers:
                    sync_state = "paired"
                    sync_count = len(peers)
                    if hasattr(self._sync_mgr, "is_syncing") and self._sync_mgr.is_syncing():
                        sync_state = "syncing"
                if hasattr(self._sync_mgr, "last_sync"):
                    ls = self._sync_mgr.last_sync
                    if ls:
                        last_sync = str(ls)
            except Exception:
                sync_state = "error"

        try:
            from core.settings_manager import get_bool
            api_state = "active" if get_bool("home_audio/michi_api_enabled") else "disabled"
        except Exception:
            pass

        try:
            from core.settings_manager import get_bool
            if get_bool("home_audio/ha_base_url"):
                ha_state = "configured"
            if get_bool("home_audio/enabled"):
                ha_state = "active" if ha_state == "configured" else ha_state
        except Exception:
            pass

        diag_avail = bool(micro_host or sync_count > 0 or api_state == "active")

        return EcosystemHomeStatus(
            micro_server_state=micro_state,
            micro_server_name=micro_name,
            micro_server_issue_code=micro_issue_code,
            remote_music_server_state=remote_music_state,
            remote_music_server_count=remote_music_count,
            remote_music_server_name=remote_music_name,
            mobile_sync_state=sync_state,
            mobile_device_count=sync_count,
            api_state=api_state,
            home_audio_state=ha_state,
            last_sync=last_sync,
            diagnostics_available=diag_avail,
        )

    def _build_alerts(
        self,
        library: LibraryHomeStatus,
        audio: AudioHomeStatus,
        ecosystem: EcosystemHomeStatus,
    ) -> list[HomeAlert]:
        alerts: list[HomeAlert] = []

        if library.index_error_count > 0:
            alerts.append(
                HomeAlert(
                    severity="critical",
                    kind="index_errors",
                    title="Errores de indexación",
                    message=f"{library.index_error_count} archivos no pudieron ser indexados",
                    count=library.index_error_count,
                    target_route="audio_lab_diagnostics",
                    action_label="Revisar",
                )
            )

        if library.missing_file_count > 0:
            alerts.append(
                HomeAlert(
                    severity="critical",
                    kind="missing_files",
                    title="Archivos faltantes",
                    message=f"{library.missing_file_count} archivos no encontrados",
                    count=library.missing_file_count,
                    target_route="audio_lab_diagnostics",
                    action_label="Revisar",
                )
            )

        if library.missing_metadata_count > 50:
            alerts.append(
                HomeAlert(
                    severity="warning",
                    kind="metadata",
                    title="Metadatos incompletos",
                    message=f"{library.missing_metadata_count} canciones sin metadatos completos",
                    count=library.missing_metadata_count,
                    target_route="metadata_editor",
                    action_label="Completar",
                )
            )

        if library.missing_cover_count > 50:
            alerts.append(
                HomeAlert(
                    severity="warning",
                    kind="covers",
                    title="Carátulas faltantes",
                    message=f"{library.missing_cover_count} álbumes sin carátula",
                    count=library.missing_cover_count,
                    target_route="audio_lab_artwork",
                    action_label="Buscar",
                )
            )

        if library.tracks_without_audio_features > 50:
            alerts.append(
                HomeAlert(
                    severity="info",
                    kind="audio_features",
                    title="Análisis de audio pendiente",
                    message=f"{library.tracks_without_audio_features} canciones sin perfil acústico",
                    count=library.tracks_without_audio_features,
                    target_route="audio_lab_intelligence",
                    action_label="Analizar",
                )
            )

        if audio.warnings:
            alerts.append(
                HomeAlert(
                    severity="warning",
                    kind="audio_output",
                    title="Advertencias de audio",
                    message=audio.warnings[0][:120],
                    count=len(audio.warnings),
                    target_route="audio_lab_output",
                    action_label="Diagnóstico",
                )
            )

        if ecosystem.micro_server_state == "unreachable" and library.track_count > 0:
            alerts.append(
                HomeAlert(
                    severity="info",
                    kind="micro_server",
                    title="Micro Server no conectado",
                    message="Centraliza tu biblioteca con Michi Micro Server",
                    target_route="connections_hub",
                    action_label="Conectar",
                )
            )

        if ecosystem.micro_server_state == "requires_pairing":
            alerts.append(
                HomeAlert(
                    severity="warning",
                    kind="micro_server",
                    title="Micro Server requiere pairing",
                    message="Acepta la solicitud de pairing en el servidor",
                    target_route="connections_hub",
                    action_label="Pairing",
                )
            )

        if ecosystem.mobile_sync_state == "error":
            alerts.append(
                HomeAlert(
                    severity="warning",
                    kind="sync",
                    title="Error de sincronización",
                    message="La sincronización con dispositivos móviles falló",
                    target_route="devices_page",
                    action_label="Ver",
                )
            )

        safe_mode = os.environ.get("MICHI_SAFE_MODE") == "1"
        if safe_mode:
            alerts.insert(
                0,
                HomeAlert(
                    severity="warning",
                    kind="safe_mode",
                    title="Modo seguro activo",
                    message="Algunas funciones experimentales están desactivadas",
                    target_route="audio_lab_diagnostics",
                    action_label="Ver diagnóstico",
                    dismissible=False,
                ),
            )

        if len(alerts) > 5:
            extra = len(alerts) - 5
            alerts = alerts[:5]
            alerts.append(
                HomeAlert(
                    severity="info",
                    kind="playlists",
                    title="Problemas adicionales",
                    message=f"Hay {extra} problemas adicionales",
                    count=extra,
                )
            )

        return alerts

    def _build_assistant_suggestions(
        self,
        library: LibraryHomeStatus,
        playback: PlaybackHomeStatus,
    ) -> list[AssistantSuggestion]:
        suggestions: list[AssistantSuggestion] = []

        if self._context_svc is not None:
            try:
                snap = self._context_svc.get_assistant_snapshot()
                if snap and "suggested_actions" in snap:
                    for act in snap["suggested_actions"][:3]:
                        suggestions.append(
                            AssistantSuggestion(
                                title=act.get("label", act.get("title", "")),
                                message=act.get("description", ""),
                                target_route=act.get("route", ""),
                                action_kind=act.get("kind", "navigate"),
                                priority=act.get("priority", 0),
                            )
                        )
                    if suggestions:
                        return suggestions
            except Exception:
                logger.debug("Assistant snapshot unavailable")

        if library.missing_metadata_count > 0:
            suggestions.append(
                AssistantSuggestion(
                    title="Limpiar metadatos",
                    message=f"{library.missing_metadata_count} canciones con metadatos incompletos",
                    target_route="metadata_editor",
                    action_kind="navigate",
                    priority=10,
                )
            )

        if library.missing_cover_count > 0:
            suggestions.append(
                AssistantSuggestion(
                    title="Buscar carátulas",
                    message=f"{library.missing_cover_count} álbumes sin carátula",
                    target_route="audio_lab_artwork",
                    action_kind="navigate",
                    priority=8,
                )
            )

        if library.track_count > 0 and not playback.can_continue:
            suggestions.append(
                AssistantSuggestion(
                    title="Explorar biblioteca",
                    message="Descubre nueva música en tu biblioteca",
                    target_route="library_hub",
                    action_kind="navigate",
                    priority=5,
                )
            )

        if not suggestions and library.track_count > 0:
            suggestions.append(
                AssistantSuggestion(
                    title="Crear mix de novedades",
                    message="Genera un mix automático con canciones recién agregadas",
                    target_route="mix_hub",
                    action_kind="navigate",
                    priority=3,
                )
            )

        if not suggestions:
            suggestions.append(
                AssistantSuggestion(
                    title="Añadir música",
                    message="Agrega carpetas o archivos para comenzar",
                    target_route="library_hub",
                    action_kind="navigate",
                    priority=1,
                )
            )

        return suggestions[:3]

    def _derive_overall_state(
        self,
        library: LibraryHomeStatus,
        playback: PlaybackHomeStatus,
        audio: AudioHomeStatus,
        ecosystem: EcosystemHomeStatus,
    ) -> str:
        if os.environ.get("MICHI_SAFE_MODE") == "1":
            return "safe_mode"

        if library.is_empty:
            return "empty_library"

        if playback.state in ("playing",):
            return "playback_active"

        if library.index_error_count > 0 or library.missing_file_count > 0:
            return "needs_attention"

        if not library.is_healthy:
            return "needs_attention"

        if ecosystem.micro_server_state == "requires_pairing":
            return "limited_services"

        return "ready"

    def _format_headline(self, overall_state: str) -> str:
        headlines = {
            "ready": "Michi está listo",
            "needs_attention": "Michi requiere atención",
            "empty_library": "Agrega música para comenzar",
            "safe_mode": "Michi está en modo seguro",
            "playback_active": "Michi está sonando",
            "limited_services": "Servicios limitados",
            "error": "Error al cargar",
            "indexing": "Biblioteca en indexación",
        }
        return headlines.get(overall_state, "Michi está listo")

    def _format_subtitle(
        self,
        library: LibraryHomeStatus,
        audio: AudioHomeStatus,
        ecosystem: EcosystemHomeStatus,
    ) -> str:
        parts: list[str] = []
        if library.track_count > 0:
            parts.append(f"{library.track_count:,} canciones")
        if library.last_scan:
            parts.append(f"Actualizada {library.last_scan}")
        if audio.output_device and audio.output_device != "Predeterminado":
            parts.append(f"Salida: {audio.output_device}")
        if ecosystem.micro_server_state == "connected" and ecosystem.micro_server_name:
            parts.append(f"Micro: {ecosystem.micro_server_name}")
        return " · ".join(parts) if parts else "Todo listo"

    def _build_actions(
        self,
        overall_state: str,
        library: LibraryHomeStatus,
        ecosystem: EcosystemHomeStatus,
    ) -> list[HomeAction]:
        actions: list[HomeAction] = []
        if overall_state == "empty_library":
            actions.append(HomeAction("Añadir carpeta", "library_hub", "folder", 10))
        if library.track_count > 0:
            actions.append(HomeAction("Ver biblioteca", "library_hub", "library", 5))
        if not library.is_healthy:
            actions.append(HomeAction("Diagnóstico", "audio_lab_diagnostics", "diagnostics", 3))
        if ecosystem.micro_server_state == "disconnected":
            actions.append(
                HomeAction("Conectar servidor", "connections_hub", "server", 2)
            )
        if not actions:
            actions.append(HomeAction("Explorar", "library_hub", "explore", 1))
        return actions
