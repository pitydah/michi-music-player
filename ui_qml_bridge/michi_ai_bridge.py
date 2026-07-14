from __future__ import annotations

import logging
import uuid
from typing import Any

from PySide6.QtCore import QObject, Property, Signal, Slot

from michi_ai.v2.core.assistant_core import AssistantCoreService
from michi_ai.v2.core.models import (
    AssistantRequest, AssistantResponse, AssistantResponseType,
)

logger = logging.getLogger("michi.ai.bridge")

_VALID_STATES = frozenset({
    "idle", "building_context", "routing", "planning",
    "awaiting_confirmation", "executing", "cancelling",
    "cancelled", "completed", "partial", "failed",
})

_RESPONSE_TYPE_MAP = {
    AssistantResponseType.ANSWER: "answer",
    AssistantResponseType.CLARIFICATION: "clarification",
    AssistantResponseType.PLAN_PREVIEW: "plan_preview",
    AssistantResponseType.CONFIRMATION_REQUEST: "confirmation",
    AssistantResponseType.EXECUTION_PROGRESS: "progress",
    AssistantResponseType.EXECUTION_RESULT: "result",
    AssistantResponseType.ERROR: "error",
    AssistantResponseType.SUGGESTION: "suggestion",
}


class MichiAIBridge(QObject):
    responseChanged = Signal()
    statusChanged = Signal(str)
    progressChanged = Signal()
    confirmationRequested = Signal(str, str, str)
    suggestionsChanged = Signal()
    errorOccurred = Signal(str)
    sessionChanged = Signal()

    def __init__(self, assistant_service: AssistantCoreService | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._assistant = assistant_service
        self._session_id: str = ""
        self._current_response: AssistantResponse | None = None
        self._status = "idle"
        self._progress: dict[str, Any] = {}
        self._pending_confirmation: dict[str, Any] = {}
        self._last_error = ""
        self._suggestions: list[dict[str, Any]] = []

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    def _set_status(self, new: str) -> None:
        if new in _VALID_STATES and new != self._status:
            self._status = new
            self.statusChanged.emit(new)

    @Property(str, notify=responseChanged)
    def lastError(self) -> str:
        return self._last_error

    @Property(str, notify=responseChanged)
    def currentResponse(self) -> str:
        if self._current_response:
            return self._current_response.message
        return ""

    @Property(str, notify=responseChanged)
    def responseType(self) -> str:
        if self._current_response:
            return _RESPONSE_TYPE_MAP.get(self._current_response.type, "unknown")
        return ""

    @Property(str, notify=responseChanged)
    def responseTitle(self) -> str:
        if self._current_response:
            return self._current_response.title
        return ""

    @Property(str, notify=responseChanged)
    def responseDetails(self) -> str:
        if self._current_response:
            return self._current_response.details
        return ""

    @Property("QVariantList", notify=responseChanged)
    def responseActions(self) -> list[dict[str, Any]]:
        if self._current_response:
            return list(self._current_response.actions)
        return []

    @Property(bool, notify=statusChanged)
    def isBusy(self) -> bool:
        return self._status in ("building_context", "routing", "planning", "executing")

    @Property("QVariantMap", notify=progressChanged)
    def progress(self) -> dict[str, Any]:
        return self._progress

    @Property("QVariantMap", notify=suggestionsChanged)
    def pendingConfirmation(self) -> dict[str, Any]:
        return self._pending_confirmation

    @Property("QVariantList", notify=suggestionsChanged)
    def suggestions(self) -> list[dict[str, Any]]:
        return self._suggestions

    @Property(str, notify=sessionChanged)
    def sessionId(self) -> str:
        return self._session_id

    @Slot()
    def startNewSession(self) -> None:
        if self._assistant:
            result = self._assistant.create_session()
            if result.ok and result.data:
                self._session_id = result.data.session_id
                self.sessionChanged.emit()

    @Slot(str)
    def sendMessage(self, text: str) -> None:
        if not self._assistant:
            self._last_error = "Assistant service not available"
            self._set_status("failed")
            self.errorOccurred.emit(self._last_error)
            return

        if not self._session_id:
            self.startNewSession()

        self._set_status("routing")
        request = AssistantRequest(
            text=text,
            session_id=self._session_id,
            correlation_id=uuid.uuid4().hex[:12],
        )

        response = self._assistant.process_message(request)
        self._current_response = response
        self._map_response_to_bridge(response)

    def _map_response_to_bridge(self, response: AssistantResponse) -> None:
        rtype = response.type

        if rtype == AssistantResponseType.ANSWER:
            self._set_status("completed")

        elif rtype == AssistantResponseType.CLARIFICATION:
            self._set_status("idle")

        elif rtype == AssistantResponseType.PLAN_PREVIEW:
            self._set_status("awaiting_confirmation")
            if response.plan:
                plan_id = getattr(response.plan, "plan_id", "")
                summary = response.message
                self._pending_confirmation = {
                    "plan_id": plan_id,
                    "summary": summary,
                    "title": response.title,
                    "details": response.details,
                }
                self.confirmationRequested.emit(plan_id, summary, response.details)

        elif rtype == AssistantResponseType.CONFIRMATION_REQUEST:
            self._set_status("awaiting_confirmation")
            plan = response.plan
            plan_id = getattr(plan, "plan_id", "") if plan else ""
            summary = response.message
            self._pending_confirmation = {
                "plan_id": plan_id,
                "summary": summary,
                "title": response.title,
                "details": response.details,
            }
            self.confirmationRequested.emit(plan_id, summary, response.details)

        elif rtype == AssistantResponseType.EXECUTION_PROGRESS:
            self._set_status("executing")
            if response.progress:
                self._progress = response.progress
                self.progressChanged.emit()

        elif rtype == AssistantResponseType.EXECUTION_RESULT:
            self._set_status("completed")
            self._pending_confirmation = {}

        elif rtype == AssistantResponseType.ERROR:
            self._set_status("failed")
            self._last_error = response.message
            self.errorOccurred.emit(self._last_error)

        elif rtype == AssistantResponseType.SUGGESTION:
            self._set_status("idle")

        self.responseChanged.emit()

    @Slot(str)
    def confirmAction(self, confirmation_id: str) -> None:
        if not self._assistant or not self._session_id:
            return
        self._set_status("executing")
        response = self._assistant.confirm_plan(confirmation_id, self._session_id)
        self._current_response = response
        self._pending_confirmation = {}
        self._map_response_to_bridge(response)

    @Slot()
    def rejectAction(self) -> None:
        if not self._assistant or not self._session_id:
            return
        response = self._assistant.cancel_plan(self._session_id)
        self._current_response = response
        self._pending_confirmation = {}
        self._map_response_to_bridge(response)

    @Slot()
    def cancelCurrentRequest(self) -> None:
        if not self._assistant:
            return
        if self._pending_confirmation:
            plan_id = self._pending_confirmation.get("plan_id", "")
            if plan_id:
                self._assistant.cancel_execution(plan_id)
        self._set_status("cancelled")
        self._pending_confirmation = {}

    @Slot()
    def requestSuggestions(self) -> None:
        if not self._assistant:
            return
        suggestions = self._assistant.get_suggestions(self._session_id)
        self._suggestions = [
            {"id": s.id, "title": s.title, "description": s.description,
             "action": s.action, "priority": s.priority}
            for s in suggestions
        ]
        self.suggestionsChanged.emit()

    @Slot()
    def clearConversation(self) -> None:
        if self._assistant and self._session_id:
            self._assistant.clear_history(self._session_id)
        self._current_response = None
        self._last_error = ""
        self._pending_confirmation = {}
        self._set_status("idle")
        self.responseChanged.emit()

    @Slot(str)
    def dismissSuggestion(self, suggestion_id: str) -> None:
        if self._assistant:
            self._assistant.dismiss_suggestion(suggestion_id)
        self.requestSuggestions()
