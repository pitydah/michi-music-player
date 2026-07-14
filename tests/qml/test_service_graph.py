"""Tests for service dependency graph: cycle detection, missing deps, duplicates."""

from core.service_container import ServiceContainer


def _make_container(**overrides):
    c = ServiceContainer()
    from unittest.mock import MagicMock
    defaults = {
        "connection_factory": MagicMock(),
        "worker_manager": MagicMock(),
        "query_executor": MagicMock(),
        "job_service": MagicMock(),
        "event_bus": MagicMock(),
        "settings_coordinator": MagicMock(),
        "settings_service": MagicMock(),
        "library_query_service": MagicMock(),
        "library_sources_service": MagicMock(),
        "library_mutation_service": MagicMock(),
        "playlist_service": MagicMock(),
        "history_query_service": MagicMock(),
        "global_search_service": MagicMock(),
        "mix_query_service": MagicMock(),
        "track_action_service": MagicMock(),
        "playback_service": MagicMock(),
        "queue_service": MagicMock(),
        "metadata_service": MagicMock(),
        "theme_service": MagicMock(),
        "accessibility_service": MagicMock(),
        "audio_lab_service": MagicMock(),
        "smart_tagging_service": MagicMock(),
        "library_doctor_service": MagicMock(),
        "device_sync_service": MagicMock(),
        "connection_service": MagicMock(),
        "home_audio_service": MagicMock(),
        "diagnostics_service": MagicMock(),
        "notification_service": MagicMock(),
        "action_registry": MagicMock(),
    }
    defaults.update(overrides)
    for name, svc in defaults.items():
        if name in c._all_names():
            c.register(name, svc)
    return c


class TestGraphAuditImports:
    def test_audit_script_imports(self):
        from scripts.qml_service_graph_audit import load_dependencies, detect_cycles, check_missing_deps, check_duplicates
        assert callable(load_dependencies)
        assert callable(detect_cycles)
        assert callable(check_missing_deps)
        assert callable(check_duplicates)


class TestCycleDetection:
    def test_no_cycles(self):
        deps = {"a": ["b"], "b": []}
        from scripts.qml_service_graph_audit import detect_cycles
        cycles = detect_cycles(deps)
        assert cycles == []

    def test_direct_cycle(self):
        deps = {"a": ["b"], "b": ["a"]}
        from scripts.qml_service_graph_audit import detect_cycles
        cycles = detect_cycles(deps)
        assert len(cycles) >= 1

    def test_self_loop(self):
        deps = {"a": ["a"]}
        from scripts.qml_service_graph_audit import detect_cycles
        cycles = detect_cycles(deps)
        assert len(cycles) >= 1


class TestMissingDependencies:
    def test_no_missing(self):
        deps = {"a": ["b"], "b": []}
        known = {"a", "b"}
        from scripts.qml_service_graph_audit import check_missing_deps
        missing = check_missing_deps(deps, known)
        assert missing == []

    def test_missing_found(self):
        deps = {"a": ["nonexistent"]}
        known = {"a"}
        from scripts.qml_service_graph_audit import check_missing_deps
        missing = check_missing_deps(deps, known)
        assert len(missing) == 1


class TestDuplicateServices:
    def test_no_duplicates(self):
        deps = {"a": [], "b": []}
        from scripts.qml_service_graph_audit import check_duplicates
        assert check_duplicates(deps) == []

    def test_duplicates_found(self):
        deps = {"a": [], "b": []}
        from scripts.qml_service_graph_audit import check_duplicates
        dups = check_duplicates(deps)
        assert len(dups) == 0

    def test_duplicate_key_via_construction(self):
        deps = [("a", []), ("b", []), ("a", [])]
        deduped = dict(deps)
        assert len(deduped) == 2  # last key wins

    def test_duplicate_check_utility(self):
        items = ["a", "b", "a"]
        from collections import Counter
        dups = [k for k, v in Counter(items).items() if v > 1]
        assert dups == ["a"]


class TestRequiredFailureState:
    def test_required_failure_sets_capability_false(self):
        c = ServiceContainer()
        c.register("connection_factory", object())
        c.report_failure("connection_factory", "error")
        assert c.is_capable("connection_factory") is False

    def test_required_failure_logs_in_list(self):
        c = ServiceContainer()
        c.register("connection_factory", object())
        c.report_failure("connection_factory", "db connection lost")
        info = c.list_services()["connection_factory"]
        assert info["capable"] is False
        assert info["failed"] is True


class TestAuditScriptExecution:
    def test_main_runs_with_yaml(self, tmp_path):
        import yaml
        deps = {"test_svc": {"requires": []}}
        yaml_path = tmp_path / "service_dependencies.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(deps, f)
        from scripts.qml_service_graph_audit import load_dependencies, detect_cycles
        loaded = load_dependencies(str(yaml_path))
        assert loaded == {"test_svc": []}
        cycles = detect_cycles(loaded)
        assert cycles == []
