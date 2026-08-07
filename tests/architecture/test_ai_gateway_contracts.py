"""Gateway contract: every Production* method is real or honestly unavailable.

Rules guarded here (ADR-006):

1. With NO backing services, every gateway method must return an explicit
   CAPABILITY_UNAVAILABLE (never a hardcoded "operational" / fake success).
2. With services present, the method must actually invoke the service
   (spot-checked with controlled fakes).
3. No gateway method may fabricate ``{"ok": True, "status": "operational"}``.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from core.assistant_gateways import (
    ProductionAudioLabGateway,
    ProductionDeviceGateway,
    ProductionDiagnosticsGateway,
    ProductionJobGateway,
    ProductionLibraryDoctorGateway,
    ProductionLibraryGateway,
    ProductionMixGateway,
    ProductionNavigationGateway,
    ProductionPlaybackGateway,
    ProductionPlaylistGateway,
    ProductionQueueGateway,
    ProductionSettingsGateway,
)

GATEWAY_CALLS = [
    # (gateway_factory, method, args)
    (ProductionPlaybackGateway, "play_track", ("1",)),
    (ProductionPlaybackGateway, "play_album", ("album-1",)),
    (ProductionPlaybackGateway, "play_artist", ("Genesis",)),
    (ProductionPlaybackGateway, "play_playlist", ("1",)),
    (ProductionPlaybackGateway, "pause", ()),
    (ProductionPlaybackGateway, "resume", ()),
    (ProductionPlaybackGateway, "stop", ()),
    (ProductionPlaybackGateway, "next", ()),
    (ProductionPlaybackGateway, "previous", ()),
    (ProductionPlaybackGateway, "seek", (30.0,)),
    (ProductionPlaybackGateway, "set_volume", (50,)),
    (ProductionPlaybackGateway, "set_repeat", ("all",)),
    (ProductionPlaybackGateway, "set_shuffle", (True,)),
    (ProductionPlaybackGateway, "get_state", ()),
    (ProductionLibraryGateway, "search", ("jazz",)),
    (ProductionLibraryGateway, "get_track", ("1",)),
    (ProductionLibraryGateway, "get_album", ("album-1",)),
    (ProductionLibraryGateway, "get_artist", ("Genesis",)),
    (ProductionLibraryGateway, "list_recent", (5,)),
    (ProductionLibraryGateway, "list_unplayed", (5,)),
    (ProductionLibraryGateway, "list_favorites", (5,)),
    (ProductionLibraryGateway, "find_metadata_gaps", (5,)),
    (ProductionQueueGateway, "get_queue", ()),
    (ProductionQueueGateway, "add_to_queue", (["1"],)),
    (ProductionQueueGateway, "play_next", (["1"],)),
    (ProductionQueueGateway, "replace_queue", (["1"],)),
    (ProductionQueueGateway, "remove_from_queue", (0,)),
    (ProductionQueueGateway, "clear_queue", ()),
    (ProductionQueueGateway, "reorder_queue", (0, 1)),
    (ProductionPlaylistGateway, "list_playlists", ()),
    (ProductionPlaylistGateway, "get_playlist", ("1",)),
    (ProductionPlaylistGateway, "create_playlist", ("Mi Lista",)),
    (ProductionPlaylistGateway, "add_to_playlist", ("1", ["1"])),
    (ProductionPlaylistGateway, "remove_from_playlist", ("1", 0)),
    (ProductionPlaylistGateway, "reorder_playlist", ("1", 0, 1)),
    (ProductionPlaylistGateway, "delete_playlist", ("1",)),
    (ProductionSettingsGateway, "get_setting", ("key",)),
    (ProductionSettingsGateway, "suggest_change", ("key", "v")),
    (ProductionSettingsGateway, "preview_change", ("key", "v")),
    (ProductionSettingsGateway, "apply_change", ("key", "v")),
    (ProductionSettingsGateway, "list_settings", ()),
    (ProductionAudioLabGateway, "probe_audio", ("1",)),
    (ProductionAudioLabGateway, "analyze_audio", (["1"],)),
    (ProductionAudioLabGateway, "recommend_conversion", (["1"],)),
    (ProductionAudioLabGateway, "preview_conversion", ("p",)),
    (ProductionAudioLabGateway, "start_conversion", ("p",)),
    (ProductionAudioLabGateway, "cancel_conversion", ("j",)),
    (ProductionAudioLabGateway, "analyze_replaygain", (["1"],)),
    (ProductionAudioLabGateway, "check_integrity", (["1"],)),
    (ProductionAudioLabGateway, "compare_audio", ("a", "b")),
    (ProductionAudioLabGateway, "get_status", ()),
    (ProductionDeviceGateway, "list_devices", ()),
    (ProductionDeviceGateway, "get_device_details", ("d",)),
    (ProductionDeviceGateway, "diagnose_ecosystem", ()),
    (ProductionDeviceGateway, "diagnose_server", ()),
    (ProductionDeviceGateway, "diagnose_home_audio", ()),
    (ProductionDeviceGateway, "diagnose_pairing", ()),
    (ProductionDeviceGateway, "plan_sync", ("pl-1", "dev-1")),
    (ProductionDeviceGateway, "start_sync", ("dev-1",)),
    (ProductionDeviceGateway, "cancel_sync", ("j",)),
    (ProductionDeviceGateway, "get_sync_status", ()),
    (ProductionDiagnosticsGateway, "get_diagnostics", ()),
    (ProductionDiagnosticsGateway, "get_audio_diagnostics", ()),
    (ProductionDiagnosticsGateway, "get_network_diagnostics", ()),
    (ProductionDiagnosticsGateway, "open_diagnostics", ("audio",)),
    (ProductionMixGateway, "create_mix", ("daily",)),
    (ProductionMixGateway, "explain_mix", ("m",)),
    (ProductionMixGateway, "save_mix_as_playlist", ("m", "name")),
    (ProductionMixGateway, "cancel_mix", ("j",)),
    (ProductionJobGateway, "list_jobs", ()),
    (ProductionJobGateway, "cancel_job", ("j",)),
    (ProductionJobGateway, "get_job_status", ("j",)),
    (ProductionNavigationGateway, "request_navigation", ("library",)),
    (ProductionLibraryDoctorGateway, "scan", ()),
    (ProductionLibraryDoctorGateway, "preview_repair", ("s",)),
    (ProductionLibraryDoctorGateway, "repair", ("r",)),
    (ProductionLibraryDoctorGateway, "rollback", ("r",)),
]


def _construct(factory, **kwargs):
    defaults = {
        ProductionPlaybackGateway: lambda: factory(None),
        ProductionLibraryGateway: lambda: factory(None),
        ProductionQueueGateway: lambda: factory(None),
        ProductionPlaylistGateway: lambda: factory(None),
        ProductionSettingsGateway: lambda: factory(None),
        ProductionAudioLabGateway: lambda: factory(None),
        ProductionDeviceGateway: lambda: factory(None),
        ProductionDiagnosticsGateway: lambda: factory(None),
        ProductionMixGateway: lambda: factory(None),
        ProductionJobGateway: lambda: factory(None),
        ProductionNavigationGateway: lambda: factory(None),
        ProductionLibraryDoctorGateway: lambda: factory(None),
    }
    return defaults[factory]()


def test_unbacked_gateway_methods_are_honestly_unavailable() -> None:
    for factory, method, args in GATEWAY_CALLS:
        gateway = _construct(factory)
        result = getattr(gateway, method)(*args)
        assert isinstance(result, dict), f"{factory.__name__}.{method} returned {type(result)}"
        assert result.get("ok") is False, (
            f"{factory.__name__}.{method} returned ok=True with no services: {result}"
        )
        assert result.get("code") == "CAPABILITY_UNAVAILABLE", (
            f"{factory.__name__}.{method} returned {result.get('code')} "
            f"instead of CAPABILITY_UNAVAILABLE: {result}"
        )


def test_no_hardcoded_operational_status_in_source() -> None:
    source = Path(__file__).resolve().parent.parent.parent / "core" / "assistant_gateways.py"
    text = source.read_text(encoding="utf-8")
    assert '"status": "operational"' not in text, (
        "Static 'operational' success payload found in assistant_gateways.py"
    )
    assert '"status": "operational"' not in (
        Path(__file__).resolve().parent.parent.parent / "core" / "assistant_metadata_gateway.py"
    ).read_text(encoding="utf-8")


def test_real_paths_invoke_backing_services() -> None:
    """Spot-check that real paths call the service, not fabricate results."""
    player = MagicMock()
    player.state = "playing"
    gateway = ProductionPlaybackGateway(player)
    result = gateway.pause()
    assert result["ok"] is True
    player.pause.assert_called_once()

    queue = MagicMock()
    queue.get_state.return_value = {"items": [{"id": 1}], "current_index": 0,
                                    "repeat": "none", "shuffle": False, "revision": 1}
    result = ProductionQueueGateway(queue).get_queue()
    assert result["ok"] is True
    assert result["count"] == 1

    playlist_svc = MagicMock()
    playlist_svc.create_playlist.return_value = {"ok": True, "id": 7, "name": "X"}
    playlist_svc.batch_add.return_value = {"ok": True, "count": 2}
    result = ProductionPlaylistGateway(None, playlist_svc).create_playlist("X", ["1", "2"])
    assert result["ok"] is True
    playlist_svc.create_playlist.assert_called_once_with("X")
    playlist_svc.batch_add.assert_called_once_with(7, [1, 2])

    diagnostics = MagicMock()
    diagnostics.check_all.return_value = {"service_health": {"status": "ok"}}
    result = ProductionDiagnosticsGateway(diagnostics).get_diagnostics()
    assert result["ok"] is True
    diagnostics.check_all.assert_called_once()
    assert result["checks"] == {"service_health": {"status": "ok"}}


def test_diagnostics_gateway_never_claims_operational_without_service() -> None:
    gateway = ProductionDiagnosticsGateway(None)
    for method, args in (
        ("get_diagnostics", ()),
        ("get_audio_diagnostics", ()),
        ("get_network_diagnostics", ()),
        ("open_diagnostics", ("audio",)),
    ):
        result = getattr(gateway, method)(*args)
        assert result["code"] == "CAPABILITY_UNAVAILABLE", method
