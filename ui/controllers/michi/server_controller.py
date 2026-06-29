"""MichiServerController — manages Player as server lifecycle.

Future: controls pairing, token management, device listing, and server
configuration from the UI. Do not connect to window.py yet.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.controller.server")


class MichiServerController:
    """Manages the Michi Link server lifecycle: start, stop, pairing, devices."""
    def __init__(self, sync_manager=None, account_manager=None, device_registry=None):
        self._sync_mgr = sync_manager
        self._account_mgr = account_manager
        self._registry = device_registry

    @property
    def is_active(self) -> bool:
        return bool(self._sync_mgr and self._sync_mgr.is_active)

    @property
    def paired_devices(self) -> list:
        if self._registry:
            return self._registry.list_all()
        return []

    @property
    def has_local_account(self) -> bool:
        return bool(self._account_mgr and self._account_mgr.exists())

    def toggle_server(self):
        if self._sync_mgr:
            self._sync_mgr.toggle()

    def revoke_device(self, device_id: str):
        if self._registry:
            self._registry.revoke(device_id)
