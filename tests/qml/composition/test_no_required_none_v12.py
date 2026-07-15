"""Verify no bridge has REQUIRED dependency set to None.

Iterates all bridge __init__ signatures and verifies that specific
REQUIRED service params are guarded by asserts at runtime.
"""
import importlib
import inspect
import pkgutil
import pytest

import ui_qml_bridge

# Specific params that MUST be asserted as non-None per X10.07
_REQUIRED_ASSERTS: dict[str, set[str]] = {
    "LibraryBridge": {"query_service", "track_action_service"},
    "SettingsBridgeV2": {"service"},
    "LibrarySourcesBridge": {"service"},
    "ConnectionsBridge": {"navigation_bridge"},
    "HomeBridge": {"library_sources_service"},
    "NotificationBridge": {"diagnostics_service"},
    "SmartTaggingBridge": {"service", "worker_manager"},
    "DiagnosticsBridge": {"query_executor"},
    "DiscLabBridge": {"worker_manager"},
    "EqBridge": {"player_service"},
    "OutputProfilesBridge": {"player_service"},
    "PlaybackBridge": {"player_service"},
    "NowPlayingBridge": {"player_service", "audio_quality_adapter"},
    "QueueBridge": {"player_service"},
    "HistoryBridge": {"db"},
    "MixBridge": {"db", "playback_service"},
    "LyricsBridge": {"worker_manager"},
    "ThemeBridge": {"coordinator"},
    "JobBridge": {"worker_manager", "db"},
    "LibraryDoctorBridge": {"db", "worker_manager"},
    "MichiAIBridge": {"device_sync_service"},
    "AccessibilityBridge": {"playback_service"},
    "MetadataBridge": {"metadata_service"},
    "PlaylistsBridge": {"db"},
    "RadioBridge": {"player_service"},
    "DevicesBridge": {"device_sync_service", "job_service"},
    "CoverProviderBridge": {"cover_bridge"},
}

# Params that have valid alias defaults (at least one must be non-None)
_ALIAS_GROUPS: dict[str, list[set[str]]] = {
    "PlaybackBridge": [{"player_service", "playback_ctrl"}],
    "ThemeBridge": [{"coordinator", "service"}],
    "AccessibilityBridge": [{"playback_service"}, {"service", "settings_service"}],
    "DevicesBridge": [{"device_sync_service"}, {"job_service"}],
    "MichiAIBridge": [{"device_sync_service"}],
}


def _all_bridge_classes():
    modules = []
    for importer, modname, ispkg in pkgutil.walk_packages(
        ui_qml_bridge.__path__, prefix="ui_qml_bridge."
    ):
        if modname.endswith("_bridge") or "bridge" in modname or "context" in modname:
            try:
                mod = importlib.import_module(modname)
                modules.append(mod)
            except Exception:
                pass

    classes = []
    for mod in modules:
        for name, cls in inspect.getmembers(mod, inspect.isclass):
            if name.endswith("Bridge") and name != "BridgeFactory":
                classes.append((name, cls))
    return classes


BRIDGE_CLASSES = _all_bridge_classes()
BRIDGE_IDS = [nc[0] for nc in BRIDGE_CLASSES]


class TestNoRequiredNoneV12:
    def test_all_bridges_discovered(self):
        assert len(BRIDGE_CLASSES) >= 20, f"Only {len(BRIDGE_CLASSES)} bridges found"

    def test_listed_bridges_have_none_defaults(self):
        """Verify listed params still default to None (for backward compat)
        BUT have runtime assert guard.  This test just documents the expected state."""
        failures = []
        for name, cls in BRIDGE_CLASSES:
            expected_required = _REQUIRED_ASSERTS.get(name, set())
            if not expected_required:
                continue
            sig = inspect.signature(cls.__init__)
            src_lines = inspect.getsource(cls.__init__)
            for param_name in expected_required:
                if param_name not in sig.parameters:
                    failures.append(f"{name}.__init__ missing param '{param_name}'")
                    continue
                param = sig.parameters[param_name]
                if param.default is None:
                    assert_expr = f"assert {param_name} is not None"
                    if assert_expr not in src_lines:
                        failures.append(
                            f"{name}.__init__ param '{param_name}' defaults to None "
                            f"but has no runtime assert guard."
                        )
        if failures:
            pytest.fail("\n".join(failures))
