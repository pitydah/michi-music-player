"""Tests for Integration Audit (HW)."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
AUDIT_SCRIPT = REPO / "scripts" / "qml_integration_audit.py"
MANIFEST_YAML = REPO / "docs" / "qml_parallel" / "integration_manifest.yaml"
MODULES_YAML = REPO / "config" / "qml_modules.yaml"


class TestScriptStructure:
    def test_audit_script_exists(self):
        assert AUDIT_SCRIPT.exists()

    def test_manifest_exists(self):
        assert MANIFEST_YAML.exists()

    def test_modules_config_exists(self):
        assert MODULES_YAML.exists()

    def test_audit_imports(self):
        import scripts.qml_integration_audit as mod
        assert mod.CANONICAL_SERVICES
        assert mod.CANONICAL_BRIDGES
        assert mod.CANONICAL_CONTEXTS
        assert mod.CANONICAL_MODELS
        assert mod.CANONICAL_ROUTES


class TestCanonicalServiceCoverage:
    def test_core_services_present(self):
        import scripts.qml_integration_audit as mod
        expected_required = {
            "connection_factory", "worker_manager", "query_executor",
            "job_service", "event_bus", "settings_coordinator",
            "playback_service", "queue_service", "metadata_service",
        }
        for s in expected_required:
            assert s in mod.CANONICAL_SERVICES, f"Missing required service: {s}"

    def test_optional_services_present(self):
        import scripts.qml_integration_audit as mod
        expected_optional = {
            "theme_service", "accessibility_service", "audio_lab_service",
            "smart_tagging_service", "notification_service",
        }
        for s in expected_optional:
            assert s in mod.CANONICAL_SERVICES, f"Missing optional service: {s}"


class TestCanonicalBridgeCoverage:
    def test_core_bridges_present(self):
        import scripts.qml_integration_audit as mod
        core = {"app", "navigation", "theme", "library", "playback",
                "nowplaying", "mix", "michi_ai", "metadata", "settings"}
        for b in core:
            assert b in mod.CANONICAL_BRIDGES, f"Missing core bridge: {b}"

    def test_tool_bridges_present(self):
        import scripts.qml_integration_audit as mod
        tools = {"audio_lab", "output_profiles", "smart_tagging",
                 "library_doctor", "disc_lab", "lyrics", "eq",
                 "global_search", "diagnostics", "runtime_quality"}
        for b in tools:
            assert b in mod.CANONICAL_BRIDGES, f"Missing tool bridge: {b}"


class TestCanonicalContextCoverage:
    def test_context_bindings_present(self):
        import scripts.qml_integration_audit as mod
        core = {"appBridge", "navigationBridge", "themeBridge",
                "libraryBridge", "playbackBridge", "nowplayingBridge"}
        for c in core:
            assert c in mod.CANONICAL_CONTEXTS, f"Missing context: {c}"

    def test_secondary_contexts_present(self):
        import scripts.qml_integration_audit as mod
        secondary = {"settingsBridge", "radioBridge", "connectionsBridge",
                     "queueBridge", "historyBridge", "homeBridge"}
        for c in secondary:
            assert c in mod.CANONICAL_CONTEXTS, f"Missing context: {c}"


class TestCanonicalModelCoverage:
    def test_models_present(self):
        import scripts.qml_integration_audit as mod
        expected = {"BasePagedListModel", "QueueListModel", "TrackListModel",
                    "HistoryListModel", "ArtistListModel", "AlbumPagedListModel",
                    "AlbumListModel", "AlbumDetailModel", "JobListModel",
                    "FolderTreeModel"}
        for m in expected:
            assert m in mod.CANONICAL_MODELS, f"Missing model: {m}"


class TestCanonicalRouteCoverage:
    def test_core_routes_present(self):
        import scripts.qml_integration_audit as mod
        core = {"home", "library", "queue", "playback", "settings", "ai"}
        for r in core:
            assert r in mod.CANONICAL_ROUTES, f"Missing core route: {r}"

    def test_detail_routes_present(self):
        import scripts.qml_integration_audit as mod
        details = {"library.album_detail", "library.artist_detail",
                   "devices.detail", "connections.detail",
                   "playlist_detail", "mix_detail"}
        for r in details:
            assert r in mod.CANONICAL_ROUTES, f"Missing detail route: {r}"


class TestModuleExpectations:
    def test_all_modules_have_expectations(self):
        import scripts.qml_integration_audit as mod
        import yaml
        with open(MODULES_YAML) as f:
            data = yaml.safe_load(f)
        for module_name in data.get("modules", {}):  # noqa: B007
            assert module_name in mod.MODULE_EXPECTATIONS, f"Missing expectations for module: {module_name}"

    def test_expectation_structure(self):
        import scripts.qml_integration_audit as mod
        for exp in mod.MODULE_EXPECTATIONS.values():
            assert "services" in exp
            assert "bridges" in exp
            assert "contexts" in exp
            assert "models" in exp
            assert "routes" in exp

    def test_audio_lab_expectation(self):
        import scripts.qml_integration_audit as mod
        exp = mod.MODULE_EXPECTATIONS.get("library")
        assert exp is not None
        assert "library_query_service" in exp["services"]
        assert "library" in exp["bridges"]
        assert "libraryBridge" in exp["contexts"]

    def test_playback_expectation(self):
        import scripts.qml_integration_audit as mod
        exp = mod.MODULE_EXPECTATIONS.get("playback")
        assert exp is not None
        assert "playback_service" in exp["services"]
        assert "queue_service" in exp["services"]
        assert "QueueListModel" in exp["models"]


class TestAuditResult:
    def test_run_audit_returns_dict(self):
        import scripts.qml_integration_audit as mod
        result = mod.audit()
        assert isinstance(result, dict)
        assert "modules_checked" in result
        assert "total_issues" in result
        assert "modules" in result
        assert "passed" in result

    def test_run_audit_checks_all_modules(self):
        import scripts.qml_integration_audit as mod
        import yaml
        with open(MODULES_YAML) as f:
            data = yaml.safe_load(f)
        module_count = len(data.get("modules", {}))
        result = mod.audit()
        assert result["modules_checked"] == module_count

    def test_run_audit_no_false_positives(self):
        import scripts.qml_integration_audit as mod
        result = mod.audit()
        for mod_res in result["modules"].values():
            if not mod_res.get("ok"):
                for issue in mod_res.get("issues", []):
                    assert "missing" in issue

    def test_audit_json_output(self):
        import scripts.qml_integration_audit as mod
        result = mod.audit()
        json_str = json.dumps(result)
        parsed = json.loads(json_str)
        assert parsed["modules_checked"] >= 0
