from __future__ import annotations

from michi_ai.v2.conversation.conversation_service import (
    ConversationService, ConversationTurn, PersistenceMode,
)
from michi_ai.v2.core.models import ErrorCode


class TestConversationService:
    def setup_method(self):
        self.service = ConversationService(
            persistence_mode=PersistenceMode.MEMORY_ONLY,
        )

    def test_create_session(self):
        result = self.service.create_session()
        assert result.ok is True
        assert result.data is not None
        assert result.data.session_id != ""

    def test_get_session_found(self):
        created = self.service.create_session()
        session_id = created.data.session_id
        result = self.service.get_session(session_id)
        assert result.ok is True
        assert result.data.session_id == session_id

    def test_get_session_not_found(self):
        result = self.service.get_session("nonexistent")
        assert result.ok is False
        assert result.code == ErrorCode.SESSION_NOT_FOUND

    def test_add_turn(self):
        created = self.service.create_session()
        session_id = created.data.session_id
        turn = ConversationTurn(role="user", content="hello")
        result = self.service.add_turn(session_id, turn)
        assert result.ok is True

    def test_get_history(self):
        created = self.service.create_session()
        session_id = created.data.session_id
        self.service.add_turn(session_id, ConversationTurn(role="user", content="hello"))
        self.service.add_turn(session_id, ConversationTurn(role="assistant", content="hi"))

        result = self.service.get_history(session_id)
        assert result.ok is True
        assert len(result.data) == 2

    def test_get_history_limit(self):
        created = self.service.create_session()
        session_id = created.data.session_id
        for i in range(5):
            self.service.add_turn(session_id, ConversationTurn(role="user", content=f"msg{i}"))

        result = self.service.get_history(session_id, limit=3)
        assert len(result.data) == 3

    def test_clear_history(self):
        created = self.service.create_session()
        session_id = created.data.session_id
        self.service.add_turn(session_id, ConversationTurn(role="user", content="hello"))
        self.service.clear_history(session_id)
        result = self.service.get_history(session_id)
        assert len(result.data) == 0

    def test_delete_session(self):
        created = self.service.create_session()
        session_id = created.data.session_id
        self.service.delete_session(session_id)
        result = self.service.get_session(session_id)
        assert result.ok is False

    def test_get_context_messages(self):
        created = self.service.create_session()
        session_id = created.data.session_id
        self.service.add_turn(session_id, ConversationTurn(role="user", content="hello"))
        self.service.add_turn(session_id, ConversationTurn(role="assistant", content="hi"))

        messages = self.service.get_context_messages(session_id)
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"

    def test_pending_plan_flow(self):
        created = self.service.create_session()
        session_id = created.data.session_id
        assert self.service.get_pending_plan(session_id) is None

        self.service.set_pending_plan(session_id, {"id": "plan_1"})
        pending = self.service.get_pending_plan(session_id)
        assert pending is not None

        self.service.clear_pending_plan(session_id)
        assert self.service.get_pending_plan(session_id) is None

    def test_max_turns_enforced(self):
        service = ConversationService(
            persistence_mode=PersistenceMode.MEMORY_ONLY,
            max_turns=5,
        )
        created = service.create_session()
        session_id = created.data.session_id
        for i in range(10):
            service.add_turn(session_id, ConversationTurn(role="user", content=f"msg{i}"))

        history = service.get_history(session_id)
        assert len(history.data) <= 5

    def test_list_sessions(self):
        self.service.create_session()
        self.service.create_session()
        sessions = self.service.list_sessions()
        assert len(sessions) >= 2
