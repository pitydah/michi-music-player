"""EcosystemController — orchestrate EcosystemPage with MichiEcosystemDoctor.

Diagnostics run in a worker thread to avoid blocking the UI.
"""

from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject

from integrations.michi_ecosystem.ecosystem_doctor import MichiEcosystemDoctor
from integrations.michi_ecosystem.health_graph import build_health_graph, summarize_health

if TYPE_CHECKING:
    from ui.window import MainWindow

logger = logging.getLogger("michi.ecosystem.controller")


class EcosystemController(QObject):
    """Owns EcosystemPage lifecycle + MichiEcosystemDoctor."""

    def __init__(self, window: MainWindow):
        super().__init__(window)
        self._win = window
        self._page = None
        self._doctor = None

    @property
    def page(self):
        return self._page

    def _ensure_doctor(self) -> MichiEcosystemDoctor:
        if self._doctor is None:
            w = self._win
            from integrations.michi_link.services.diagnostics_service import DiagnosticsService
            from integrations.michi_link.services.micro_server_service import MicroServerService
            ha_client = None
            with contextlib.suppress(Exception):
                from integrations.home_assistant.client import HomeAssistantClient
                ha_client = getattr(w, "_ha_client", None) or HomeAssistantClient()
            self._doctor = MichiEcosystemDoctor(
                diagnostics_service=DiagnosticsService(),
                micro_server_service=MicroServerService(),
                sync_mgr=getattr(w, "_sync_mgr", None),
                device_registry=getattr(w, "_device_registry", None),
                settings_provider=getattr(w, "_settings_mgr", None),
                snapcast_manager=getattr(w, "_snapserver", None),
                ha_client=ha_client,
                michi_link_ctrl=getattr(w, "_michi_link_ctrl", None),
            )
        return self._doctor

    def _ensure_page(self):
        if self._page is None:
            from ui.ecosystem.ecosystem_page import EcosystemPage
            self._page = EcosystemPage()
            self._page.diagnose_requested.connect(self._on_diagnose)
            self._page.plan_requested.connect(self._on_plan)
            self._page.assistant_requested.connect(self._on_open_assistant)
        return self._page

    def show(self):
        page = self._ensure_page()
        w = self._win
        if not w._views.widget("ecosystem_hub"):
            w._views.register("ecosystem_hub", page)
        self.diagnose()
        w._fade_content("ecosystem_hub")

    def diagnose(self):
        page = self._page
        if page is None:
            return
        w = self._win
        workers = getattr(w, "_workers", None)
        if workers is not None and hasattr(workers, "run_task"):
            workers.run_task("ecosystem_diag", self._diagnose_task, on_done=self._on_diagnose_done)
        else:
            try:
                self._on_diagnose_done(self._diagnose_task())
            except Exception:
                logger.exception("Ecosystem diagnosis failed")
                page.set_health_summary({"overall": "error", "total": 0, "ok": 0, "warning": 0, "error": 1})

    def _diagnose_task(self):
        doctor = self._ensure_doctor()
        report = doctor.diagnose_ecosystem()
        return report

    def _on_diagnose_done(self, report):
        page = self._page
        if page is None:
            return
        try:
            graph = build_health_graph(report)
            summary = summarize_health(graph)
            page.set_health_summary(summary)
            nodes = [{"name": node.label, "type": node.type, "status": node.status} for node in graph.nodes]
            page.set_devices(nodes)
            issues = []
            for node in graph.nodes:
                if node.issue_code:
                    from integrations.michi_ecosystem.fix_suggester import suggest_next_steps
                    issues.append(suggest_next_steps(node.issue_code))
            page.set_issues(issues)
        except Exception:
            logger.exception("Ecosystem diagnosis result processing failed")
            page.set_health_summary({"overall": "error", "total": 0, "ok": 0, "warning": 0, "error": 1})

    def _on_diagnose(self):
        self.diagnose()

    def _on_plan(self):
        w = self._win
        w._on_sidebar_navigate("assistant")

    def _on_open_assistant(self, section: str = ""):
        w = self._win
        w._on_sidebar_navigate("assistant")
