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
        ecosystem_doctor=None,
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
        self._ecosystem_doctor = ecosystem_doctor

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
            and ecosystem.micro_server_contract_ok
            and ecosystem.micro_server_can_continue
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
        from core.home.builders.library_home_builder import build_library_status
        return build_library_status(db=self._db, context_svc=self._context_svc)

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
        from core.home.builders.playback_home_builder import build_playback_status
        return build_playback_status(playback=self._playback, context_svc=self._context_svc)

    def _build_audio_status(self) -> AudioHomeStatus:
        output_device = ""
        output_profile = ""
        replaygain_enabled = False
        eq_enabled = False
        dsp_active = False
        bitperfect_state = "not_available"
        bitperfect_intended = False
        warnings_list: list[str] = []

        try:
            from core.settings_manager import get_str, get_bool
            output_profile = get_str("audio/profile") or ""
            replaygain_enabled = get_bool("audio/replaygain_enabled")
        except Exception:
            pass

        # Leer desde PlayerService (high-level API)
        pb = self._playback
        if pb is not None:
            try:
                if hasattr(pb, "get_output_device_id"):
                    oid = pb.get_output_device_id()
                    if oid:
                        output_device = str(oid)
                if hasattr(pb, "get_audio_diagnostics"):
                    diag = pb.get_audio_diagnostics()
                    if isinstance(diag, dict):
                        warnings_list = diag.get("warnings", [])
                if hasattr(pb, "get_eq_state"):
                    eq_state = pb.get_eq_state()
                    if isinstance(eq_state, dict):
                        eq_enabled = not eq_state.get("bypass", True)
                        dsp_active = dsp_active or eq_enabled
            except Exception:
                pass

        # PlayerEngine como fuente adicional de DSP/EQ
        eng = self._player_engine
        if eng is not None:
            try:
                if hasattr(eng, "dsp_state") and eng.dsp_state is not None:
                    dsp = eng.dsp_state
                    eq_enabled = eq_enabled or getattr(dsp, "eq_enabled", False)
                    dsp_active = dsp_active or getattr(dsp, "is_dsp_active", lambda: False)()
                    replaygain_enabled = replaygain_enabled or getattr(dsp, "replaygain_enabled", False)
            except Exception:
                pass

        if not output_device:
            output_device = "Predeterminado"

        # DAC activo: dispositivo no predeterminado con nombre DAC
        dac_active = False
        dev_lower = output_device.lower()
        dac_keywords = ("dac", "usb audio", "hi-fi", "hifi", "audioquest", "ifi",
                        "topping", "schiit", "smsl", "rme", "focusrite",
                        "scarlett", "motu", "benchmark", "apogee",
                        "minidsp", "cmedia", "xmos")
        if output_device != "Predeterminado":
            for kw in dac_keywords:
                if kw in dev_lower:
                    dac_active = True
                    break

        # Semantica de Bit-Perfect honesta
        is_bitperfect_profile = "bitperfect" in output_profile.lower()
        if is_bitperfect_profile:
            bitperfect_intended = True
            if eq_enabled or dsp_active or replaygain_enabled:
                bitperfect_state = "disabled"
            elif dac_active:
                bitperfect_state = "intended"
            else:
                bitperfect_state = "not_verified"
        elif output_device != "Predeterminado":
            bitperfect_state = "disabled" if (eq_enabled or dsp_active) else "not_verified"
        else:
            bitperfect_state = "not_available"

        return AudioHomeStatus(
            output_device=output_device,
            output_profile=output_profile,
            dac_active=dac_active,
            replaygain_enabled=replaygain_enabled,
            eq_enabled=eq_enabled,
            dsp_active=dsp_active,
            bitperfect_state=bitperfect_state,
            bitperfect_intended=bitperfect_intended,
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

        contract_ok = False
        can_continue = False

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
                    elif ms == "unreachable":
                        micro_state = "unreachable"
                caps = mlc.get_capabilities()
                if caps:
                    contract_ok = caps.get("contract_ok", False)
                    can_continue = caps.get("can_continue_playback", False)
            except Exception:
                pass

        # Use Ecosystem Doctor if available
        ed = self._ecosystem_doctor
        if ed is not None:
            try:
                diag = ed.diagnose_micro_server(host=micro_host)
                if diag:
                    micro_state = diag.get("state", micro_state)
                    micro_issue_code = diag.get("issue_code", "")
                    if micro_state == "connected":
                        micro_name = diag.get("host", micro_name)
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
            micro_server_contract_ok=contract_ok,
            micro_server_can_continue=can_continue,
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

        MAX_HOME_ALERTS = 5

        if len(alerts) > MAX_HOME_ALERTS:
            extra = len(alerts) - (MAX_HOME_ALERTS - 1)
            alerts = alerts[:MAX_HOME_ALERTS - 1] + [
                HomeAlert(
                    severity="info",
                    kind="additional",
                    title="Problemas adicionales",
                    message=f"Hay {extra} problemas adicionales",
                    count=extra,
                    target_route="audio_lab_diagnostics",
                    action_label="Ver todo",
                )
            ]

        return alerts

    def _build_assistant_suggestions(
        self,
        library: LibraryHomeStatus,
        playback: PlaybackHomeStatus,
    ) -> list[AssistantSuggestion]:
        from core.home.builders.assistant_suggestions_home_builder import build_assistant_suggestions
        return build_assistant_suggestions(
            library=library,
            playback=playback,
            context_svc=self._context_svc,
        )

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
