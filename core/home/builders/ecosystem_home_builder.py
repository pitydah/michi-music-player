"""EcosystemHomeBuilder — maps the canonical ContextService ecosystem section.

The section is produced by ``EcosystemSectionProvider`` (real sync/connection
services); live controllers (MichiLinkController / sync manager) still supply
the micro-server contract details that the snapshot section does not carry.
"""

from __future__ import annotations

from typing import Any

from core.home.home_status import EcosystemHomeStatus


def build_ecosystem_status_from_section(
    section: dict,
    context_svc: Any = None,
    sync_mgr: Any = None,
    michi_link_ctrl: Any = None,
) -> EcosystemHomeStatus:
    if not isinstance(section, dict):
        return EcosystemHomeStatus()

    mobile = section.get("mobile_sync") or {}
    link = section.get("michi_link") or {}
    remote = section.get("remote_music") or {}

    micro_state = "not_configured"
    micro_name = ""
    micro_issue_code = ""
    contract_ok = False
    can_continue = False

    if link.get("available"):
        state = str(link.get("state", "unknown") or "unknown")
        if state == "connected":
            micro_state = "connected"
        elif state in ("requires_pairing", "contract_error", "disconnected", "unreachable"):
            micro_state = state
        elif state == "not_configured":
            micro_state = "not_configured"

    if michi_link_ctrl is not None:
        try:
            conn_state = michi_link_ctrl.get_connection_state()
            if conn_state:
                ms = conn_state.get("micro_server_state")
                if ms in ("connected", "requires_pairing", "contract_error",
                          "disconnected", "unreachable", "not_configured"):
                    micro_state = ms
                micro_name = conn_state.get("micro_server_name", micro_name) or micro_name
            caps = michi_link_ctrl.get_capabilities()
            if caps:
                contract_ok = bool(caps.get("contract_ok", False))
                can_continue = bool(caps.get("can_continue_playback", False))
        except Exception:
            pass

    sync_state = "no_device"
    sync_count = 0
    if mobile.get("available"):
        sync_count = int(mobile.get("peers", 0) or 0)
        sync_state = "syncing" if mobile.get("syncing") else ("paired" if sync_count else "no_device")

    api_state = "unknown"
    ha_state = "disabled"
    try:
        from core.settings_manager import get_bool
        api_state = "active" if get_bool("home_audio/michi_api_enabled") else "disabled"
        if get_bool("home_audio/ha_base_url"):
            ha_state = "configured"
        if get_bool("home_audio/enabled"):
            ha_state = "active" if ha_state == "configured" else ha_state
    except Exception:
        pass

    remote_count = int(remote.get("servers", 0) or 0)
    remote_state = "configured" if remote.get("configured") else "not_configured"

    diag_avail = bool(
        micro_state in ("connected", "unreachable", "requires_pairing")
        or sync_count > 0
        or api_state == "active"
    )

    return EcosystemHomeStatus(
        micro_server_state=micro_state,
        micro_server_name=micro_name,
        micro_server_issue_code=micro_issue_code,
        micro_server_contract_ok=contract_ok,
        micro_server_can_continue=can_continue,
        remote_music_server_state=remote_state,
        remote_music_server_count=remote_count,
        mobile_sync_state=sync_state,
        mobile_device_count=sync_count,
        api_state=api_state,
        home_audio_state=ha_state,
        diagnostics_available=diag_avail,
    )
