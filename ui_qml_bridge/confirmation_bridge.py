from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot


class ConfirmationBridge(QObject):
    confirmationRequested = Signal(str, str, dict)
    confirmationResolved = Signal(str, bool)

    def __init__(self, confirmation_service=None, action_registry=None, parent=None):
        super().__init__(parent)
        self._svc = confirmation_service
        self._action_registry = action_registry
        self._pending: dict[str, dict] = {}

    @Slot(str, str, "QVariant", result=bool)
    def requestConfirmation(self, confirmation_id: str, title: str, details: dict = None):
        if details is None:
            details = {}
        self._pending[confirmation_id] = {"title": title, "details": details}
        self.confirmationRequested.emit(confirmation_id, title, details)
        return True

    @Slot(str, bool, result=dict)
    def resolveConfirmation(self, confirmation_id: str, accepted: bool):
        self._pending.pop(confirmation_id, None)
        self.confirmationResolved.emit(confirmation_id, accepted)
        if accepted and self._action_registry:
            action_id = self._action_registry.get(confirmation_id)
            if action_id:
                return self._action_registry.execute(confirmation_id)
        return {"ok": accepted, "confirmation_id": confirmation_id}

    @Slot(str, result=bool)
    def hasPending(self, confirmation_id: str = "") -> bool:
        if confirmation_id:
            return confirmation_id in self._pending
        return len(self._pending) > 0

    @Property("QVariantList", notify=confirmationRequested)
    def pendingConfirmations(self):
        return [{"id": k, **v} for k, v in self._pending.items()]

    @Slot(result=dict)
    def confirmationScore(self) -> dict:
        score = 0
        if self._svc:
            score += 30
        if self._action_registry:
            score += 20
        score += min(25, len(self._pending) * 5)
        return {
            "score": min(100, score),
            "pending_count": len(self._pending),
            "has_service": self._svc is not None,
            "has_action_registry": self._action_registry is not None,
        }
