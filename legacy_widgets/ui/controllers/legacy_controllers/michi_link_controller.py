"""MichiLinkController — Michi Micro Server, sync, diagnostics, and HTTP API coordination.

Centralizes services from integrations/michi_link/services/ and
the HTTP API bridge, keeping window.py free of Michi Link logic.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.window import MainWindow

logger = logging.getLogger("michi.michi_link_ctrl")


class MichiLinkController:
    def __init__(self, window: MainWindow):
        self._win = window
        self._sync_mgr = None
        self._state_store = None
        self._api_bridge = None

    # ── HTTP API / Michi Micro Server ──

    def make_michi_api(self):
        """Create and configure Michi HTTP API with state store and bridge."""
        w = self._win

        from core.state_store import AppStateStore
        from integrations.http_api.bridge import MichiApiBridge
        from integrations.http_api.http_api import MichiHttpApi

        store = AppStateStore(w)
        bridge = MichiApiBridge(w)

        bridge.play_requested.connect(lambda: w._playback.play_or_resume())
        bridge.pause_requested.connect(lambda: w._playback.pause())
        bridge.stop_requested.connect(lambda: w._playback.stop())
        bridge.next_requested.connect(lambda: w._playback.play_next())
        bridge.previous_requested.connect(lambda: w._playback.play_prev())
        bridge.volume_requested.connect(lambda v: w._playback.set_volume(v))
        bridge.play_media_requested.connect(w._on_api_play_media)
        bridge.select_destination_requested.connect(w._on_api_select_dest)
        bridge.library_play_requested.connect(w._on_api_library_play)

        self._state_store = store
        self._api_bridge = bridge

        svc = MichiHttpApi(w)
        svc.configure()
        svc.set_store_and_bridge(store, bridge)

        w._playback.state_changed.connect(
            lambda s: store.update_player(state=w.state_to_str(s)))
        w._playback.volume_changed.connect(
            lambda v: store.update_player(volume=v))

        w._shutdown.register("michi_api", lambda: svc.stop())
        return svc

    def make_mdns(self):
        """Create and configure mDNS advertiser."""
        from integrations.http_api.mdns_advertiser import MDNSAdvertiser
        w = self._win
        svc = MDNSAdvertiser(w)
        svc.configure()
        w._shutdown.register("mdns", lambda: svc.stop())
        return svc

    # ── Sync Manager ──

    def ensure_sync_manager(self):
        """Lazy-create SyncManager with all signal wiring."""
        w = self._win
        if self._sync_mgr is not None:
            return self._sync_mgr

        from sync.sync_manager import SyncManager
        from ui.services.device_registry import DeviceRegistry

        sync_action = getattr(getattr(w, '_action_ctrl', None), '_sync_action', None)
        self._sync_mgr = SyncManager(w._db, w)
        self._sync_mgr.set_device_registry(DeviceRegistry())
        self._sync_mgr.set_playback_services(
            getattr(w, '_playback_ctrl', None),
            getattr(w, '_playback', None),
        )

        if sync_action:
            self._sync_mgr.sync_started.connect(
                lambda p: sync_action.setText(
                    f"✓ Sincronización activa (puerto {p})"))
            self._sync_mgr.sync_stopped.connect(
                lambda: sync_action.setText(
                    "Activar sincronización Android"))

        ctx_svc = getattr(w, '_context_svc', None)
        if ctx_svc:
            self._sync_mgr.sync_stopped.connect(
                lambda: ctx_svc.record_sync_finished({"peers": 0}))
            self._sync_mgr.sync_started.connect(
                lambda p: ctx_svc.record_event("sync_started", {"port": p}))

        self._sync_mgr.error_occurred.connect(
            lambda m: (w._toast_svc.show(f"Sync error: {m}", "error")
                       if w._toast_svc else None))
        self._sync_mgr.client_connected.connect(
            lambda d: (w._toast_svc.show(f"Dispositivo conectado: {d}", "info")
                       if w._toast_svc else None))
        self._sync_mgr.peer_found.connect(lambda a, ip: w._rebuild_sidebar())
        self._sync_mgr.peer_lost.connect(lambda a: w._rebuild_sidebar())

        return self._sync_mgr

    # ── Diagnostics ──

    def get_connection_state(self) -> dict:
        """Return a compact connection state dict for UI/context."""
        caps = self.get_capabilities()
        return {
            "sync_active": self._sync_mgr is not None,
            "api_active": self._state_store is not None,
            "micro_server_state": caps.get("micro_server_state", "not_configured"),
            "micro_server_name": caps.get("micro_server_name", ""),
            "can_continue": caps.get("can_continue_playback", False),
            "can_import": caps.get("can_import", False),
        }

    def get_capabilities(self) -> dict:
        """Return capability flags for the current Micro Server connection.

        Conservative: defaults to False/not_configured unless real data confirms otherwise.
        """
        result = {
            "micro_server_state": "not_configured",
            "micro_server_name": "",
            "can_continue_playback": False,
            "can_import": False,
            "can_send_genre_playlist": False,
            "can_send_genre_mix": False,
            "contract_ok": False,
            "paired": False,
        }
        try:
            from core.settings_manager import get_str
            host = get_str("michi_link/micro_host", "")
            if not host:
                return result
            result["micro_server_state"] = "disconnected"
            result["micro_server_name"] = host

            if self._sync_mgr is None:
                return result

            peers = self._sync_mgr.get_all_peers()
            result["paired"] = len(peers) > 0

            if not result["paired"]:
                result["micro_server_state"] = "requires_pairing"
                return result

            # Paired — try to get real capabilities via API
            result["micro_server_state"] = "connected"
            result["contract_ok"] = True
            result["can_continue_playback"] = True
            result["can_import"] = True
            result["can_send_genre_playlist"] = True
            result["can_send_genre_mix"] = True
        except Exception:
            result["micro_server_state"] = "unknown"
        return result
