"""Tests: Assistant contextual hints by scope — _contextual_action_hints."""

from core.context.context_service import _contextual_action_hints


class TestAssistantContextHints:

    def _snap(self, scope=None, **overrides):
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
            "can_play_selection": scope in {
                "track", "album", "artist", "genre", "playlist",
                "mix", "folder", "search",
            },
        }
        caps.update(overrides)
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

    def test_track_without_analyze_does_not_suggest_analyze(self):
        hints = _contextual_action_hints(
            self._snap("track", can_analyze_selected_tracks=False))
        assert not any("Analizar" in h for h in hints)

    def test_playlist_without_edit_does_not_suggest_edit(self):
        hints = _contextual_action_hints(
            self._snap("playlist", can_edit_metadata=False))
        assert not any("Editar" in h for h in hints)
        assert any("Reproducir" in h for h in hints)

    def test_none_scope_no_queue_create_edit_analyze(self):
        hints = _contextual_action_hints(
            self._snap(None,
                       can_create_playlist_from_selection=False,
                       can_queue_selection=False,
                       can_edit_metadata=False,
                       can_analyze_selected_tracks=False))
        assert not any("Crear" in h or "Encolar" in h or "Editar" in h or "Analizar" in h for h in hints)
