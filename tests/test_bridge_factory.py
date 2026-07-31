# -*- coding: utf-8 -*-
"""Tests for BridgeFactory graph validation (Parche 4).

Covers validate_all_bridges() report classification and the bridgeReport property.
"""
from unittest.mock import Mock

from core.service_container import ServiceContainer
from ui_qml_bridge.bridge_factory import BridgeFactory


def _full_container() -> ServiceContainer:
    """Container with every service mocked so no bridge is degraded."""
    c = ServiceContainer()
    services = {
        "action_registry": Mock(),
        "audio_lab_service": Mock(),
        "confirmation_service": Mock(),
        "connection_factory": Mock(),
        "connection_service": Mock(),
        "database": Mock(),
        "device_sync_service": Mock(),
        "diagnostics_service": Mock(),
        "folder_service": Mock(),
        "global_search_service": Mock(),
        "history_query_service": Mock(),
        "home_audio_service": Mock(),
        "job_service": Mock(),
        "library_doctor_service": Mock(),
        "library_query_service": Mock(),
        "library_service": Mock(),
        "library_sources_service": Mock(),
        "metadata_service": Mock(),
        "michi_ai_service": Mock(),
        "mix_service": Mock(),
        "mobile_sync_service": Mock(),
        "navigation_service": Mock(),
        "notification_service": Mock(),
        "playback_service": Mock(),
        "playlist_service": Mock(),
        "process_controller": Mock(),
        "query_executor": Mock(),
        "queue_service": Mock(),
        "radio_service": Mock(),
        "settings_coordinator": Mock(),
        "settings_service": Mock(),
        "smart_tagging_service": Mock(),
        "track_action_service": Mock(),
        "worker_manager": Mock(),
        "cd_ripper_service": Mock(),
    }
    for k, v in services.items():
        c.register(k, v)
    # QueueListModel reads len(queue_service.get_state()["items"]) at construction.
    qs = c.get("queue_service")
    if isinstance(qs, Mock):
        qs.get_state.return_value = {"items": [], "current_index": -1}
    return c


class TestValidateAllBridgesReport:
    def test_report_has_bridges_and_summary(self):
        f = BridgeFactory(_full_container())
        f.create_all()
        report = f.validate_all_bridges()
        assert "bridges" in report
        assert "summary" in report
        summary = report["summary"]
        assert summary["total"] == len(report["bridges"])
        assert (
            summary["ok"]
            + summary["missing_required"]
            + summary["degraded"]
            + summary["created"]
            == summary["total"]
        )

    def test_full_container_yields_no_degraded_no_missing(self):
        f = BridgeFactory(_full_container())
        f.create_all()
        summary = f.validate_all_bridges()["summary"]
        assert summary["degraded"] == 0
        assert summary["missing_required"] == 0
        assert summary["ok"] > 0

    def test_created_bridge_classified_ok(self):
        f = BridgeFactory(_full_container())
        f.create_all()
        report = f.validate_all_bridges()
        assert report["bridges"]["navigation"]["status"] == "ok"
        assert report["bridges"]["library"]["status"] == "ok"

    def test_degraded_bridge_classified_degraded(self):
        f = BridgeFactory(ServiceContainer())  # empty -> navigation skipped
        f.create_all()
        report = f.validate_all_bridges()
        assert report["bridges"]["navigation"]["status"] == "degraded"
        assert "reason" in report["bridges"]["navigation"]
        assert report["summary"]["degraded"] > 0

    def test_query_executor_has_created_status_no_binding(self):
        f = BridgeFactory(_full_container())
        f.create_all()
        report = f.validate_all_bridges()
        # query_executor is created but has no ContextBinding entry.
        assert report["bridges"]["query_executor"]["status"] == "created"

    def test_missing_required_detected_when_dep_becomes_none(self):
        f = BridgeFactory(_full_container())
        f.create_all()  # all bridges ok
        # Simulate navigation_service becoming None after creation.
        f._container._services["navigation_service"] = None
        report = f.validate_all_bridges()
        nav = report["bridges"]["navigation"]
        assert nav["status"] == "missing_required"
        assert "navigation_service" in nav["missing"]


class TestBridgeReportProperty:
    def test_bridge_report_empty_before_validation(self):
        f = BridgeFactory(_full_container())
        assert f.bridgeReport == {}

    def test_bridge_report_populated_after_create_all(self):
        f = BridgeFactory(_full_container())
        f.create_all()
        assert "summary" in f.bridgeReport
        assert f.bridgeReport["summary"]["total"] > 0

    def test_validate_emits_bridge_report_changed(self):
        f = BridgeFactory(_full_container())
        f.create_all()
        emissions = []
        f.bridgeReportChanged.connect(lambda: emissions.append(1))
        before = len(emissions)
        f.validate_all_bridges()
        assert len(emissions) == before + 1

    def test_create_all_emits_bridge_report_changed(self):
        f = BridgeFactory(_full_container())
        emissions = []
        f.bridgeReportChanged.connect(lambda: emissions.append(1))
        f.create_all()
        assert len(emissions) >= 1


class TestCreateAllIntegration:
    def test_create_all_invokes_validation(self):
        f = BridgeFactory(_full_container())
        f.create_all()
        assert f.bridgeReport["summary"]["total"] > 0

    def test_validation_does_not_mutate_degraded_list(self):
        f = BridgeFactory(_full_container())
        f.create_all()
        degraded_before = f.degraded_bridges
        f.validate_all_bridges()
        assert f.degraded_bridges == degraded_before
