"""Tests: Assistant contextual hints by scope — _contextual_action_hints."""

from core.context.context_service import _contextual_action_hints


class TestAssistantContextHints:

    def _snap(self, scope=None):
        caps = {
            "can_search_library": True,
            "can_create_playlist_from_selection": scope in {
                "track", "album", "artist", "genre", "playlist",
                "mix", "folder", "search",
            },
            "can_queue_selection": scope in {
                "track", "album", "artist", "genre", "playlist",
                "mix", "folder", "search",
            },
            "can_edit_metadata": scope in {"track", "album", "artist", "genre"},
            "can_analyze_selected_tracks": scope in {
                "track", "album", "artist", "genre", "playlist",
                "mix", "search",
            },
        }
        return {"selection_scope": scope, "assistant_capabilities": caps}

    def test_hints_generated_for_all_scopes(self):
        for scope in (None, "track", "album", "artist", "genre",
                      "playlist", "mix", "folder", "search"):
            hints = _contextual_action_hints(self._snap(scope))
            assert isinstance(hints, list), f"scope={scope}"
            assert len(hints) <= 4, f"scope={scope} has {len(hints)} hints"

    def test_hints_not_empty(self):
        for scope in ("track", "album", "artist", "genre",
                      "playlist", "mix", "folder", "search"):
            hints = _contextual_action_hints(self._snap(scope))
            assert len(hints) > 0, f"scope={scope} has no hints"

    def test_none_scope_suggests_scan(self):
        hints = _contextual_action_hints(self._snap(None))
        assert any("Escanear" in h for h in hints)

    def test_no_absolute_paths_in_hints(self):
        hints = _contextual_action_hints(self._snap("track"))
        raw = str(hints)
        assert "/home/" not in raw
        assert "/tmp/" not in raw

    def test_no_empty_snapshot_crash(self):
        hints = _contextual_action_hints({})
        assert isinstance(hints, list)
