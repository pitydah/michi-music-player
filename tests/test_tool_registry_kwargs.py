"""Tests: ToolRegistry filters kwargs by function signature."""

from unittest.mock import MagicMock
from integrations.ai_assistant.tool_registry import ToolRegistry


def tool_accepts_db(db, query=""):
    return {"result": "ok", "query": query}


def tool_accepts_playback(db, playback=None):
    return {"result": "ok", "has_playback": playback is not None}


def tool_accepts_kwargs(db, **kwargs):
    return {"result": "ok", "received": list(kwargs.keys())}


class TestToolRegistryKwargs:
    def setup_method(self):
        self.reg = ToolRegistry()
        # Register tools with controlled permissions
        import integrations.ai_assistant.permissions as perms
        self._saved = {}
        for name in ("tool_a", "tool_b", "tool_c"):
            self._saved[name] = perms.TOOL_PERMISSIONS.get(name)
        perms.TOOL_PERMISSIONS["tool_a"] = perms.PermissionLevel.READ_ONLY
        perms.TOOL_PERMISSIONS["tool_b"] = perms.PermissionLevel.READ_ONLY
        perms.TOOL_PERMISSIONS["tool_c"] = perms.PermissionLevel.READ_ONLY
        self._perms = perms

    def teardown_method(self):
        for name, level in self._saved.items():
            if level is None:
                self._perms.TOOL_PERMISSIONS.pop(name, None)
            else:
                self._perms.TOOL_PERMISSIONS[name] = level

    def test_ignores_unknown_kwargs(self):
        self.reg.register("tool_a", tool_accepts_db)
        result = self.reg.execute("tool_a", db=MagicMock(), query="test", playback=MagicMock())
        assert result.success

    def test_passes_known_kwargs(self):
        self.reg.register("tool_b", tool_accepts_playback)
        pb = MagicMock()
        result = self.reg.execute("tool_b", db=MagicMock(), playback=pb)
        assert result.success

    def test_passes_all_to_kwargs_func(self):
        self.reg.register("tool_c", tool_accepts_kwargs)
        result = self.reg.execute("tool_c", db=MagicMock(), extra="val", playback=MagicMock())
        assert result.success
        assert "extra" in result.data["received"]
