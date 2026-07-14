from __future__ import annotations

from michi_ai.v2.context.context_assembler import ContextAssembler, ContextPrivacyPolicy
from michi_ai.v2.core.models import ContextSnapshot, PrivacyLevel


class TestContextAssembler:
    def test_assemble_empty(self):
        ca = ContextAssembler()
        snapshot = ca.assemble(session_id="test_session")
        assert snapshot.session_id == "test_session"
        assert snapshot.active_section == ""

    def test_assemble_with_providers(self):
        ca = ContextAssembler()

        def playback_provider():
            return {"now_playing": {"title": "Song"}, "queue_length": 5}

        def library_provider():
            return {"track_count": 100, "album_count": 10}

        ca.register("playback", playback_provider)
        ca.register("library", library_provider)

        snapshot = ca.assemble()
        assert snapshot.playback.get("now_playing", {}).get("title") == "Song"
        assert snapshot.playback.get("queue_length") == 5
        assert snapshot.library.get("track_count") == 100

    def test_provider_failure_does_not_block(self):
        ca = ContextAssembler()

        def failing_provider():
            raise RuntimeError("fail")

        def working_provider():
            return {"key": "value"}

        ca.register("failing", failing_provider)
        ca.register("working", working_provider)

        snapshot = ca.assemble()
        assert snapshot.library == {}

    def test_unregister(self):
        ca = ContextAssembler()

        def provider():
            return {"key": "val"}

        ca.register("test", provider)
        assert len(ca._providers) == 1
        ca.unregister("test")
        assert len(ca._providers) == 0

    def test_clear(self):
        ca = ContextAssembler()

        def provider():
            return {}

        ca.register("a", provider)
        ca.register("b", provider)
        ca.clear()
        assert len(ca._providers) == 0

    def test_assemble_sanitized(self):
        ca = ContextAssembler()

        def playback_provider():
            return {"now_playing": {"title": "Song"}, "token": "secret123"}

        ca.register("playback", playback_provider)
        sanitized = ca.assemble_sanitized(privacy_level=PrivacyLevel.STANDARD)
        assert "token" not in str(sanitized.snapshot.playback)
        assert sanitized.privacy_level == PrivacyLevel.STANDARD


class TestContextPrivacyPolicy:
    def test_minimal_removes_sensitive_sections(self):
        snapshot = ContextSnapshot(
            playback={"now_playing": {"title": "Song"}},
            library={"track_count": 100},
            settings={"volume": 80},
        )
        policy = ContextPrivacyPolicy(PrivacyLevel.MINIMAL)
        sanitized, removed = policy.apply(snapshot)
        assert sanitized.playback == {}
        assert sanitized.settings == {}
        assert sanitized.library.get("track_count") == 100

    def test_standard_strips_sensitive_keys(self):
        snapshot = ContextSnapshot(
            playback={"title": "Song", "api_key": "secret", "token": "abc123"},
            servers={"url": "http://example.com", "password": "hunter2"},
        )
        policy = ContextPrivacyPolicy(PrivacyLevel.STANDARD)
        sanitized, removed = policy.apply(snapshot)

        playback = sanitized.playback
        assert "api_key" not in playback
        assert "token" not in playback
        assert playback.get("title") == "Song"

        servers = sanitized.servers
        assert "password" not in servers

    def test_local_full_keeps_everything(self):
        snapshot = ContextSnapshot(
            playback={"token": "secret", "path": "/home/user/music"},
        )
        policy = ContextPrivacyPolicy(PrivacyLevel.LOCAL_FULL)
        sanitized, removed = policy.apply(snapshot)
        assert sanitized.playback.get("token") == "secret"
        assert not removed

    def test_diagnostic_truncates_paths(self):
        snapshot = ContextSnapshot(
            playback={"path": "/home/user/music/artist/album/song.flac"},
        )
        policy = ContextPrivacyPolicy(PrivacyLevel.DIAGNOSTIC)
        sanitized, removed = policy.apply(snapshot)
        path = sanitized.playback.get("path", "")
        assert "..." in path

    def test_minimal_session_id_masked(self):
        snapshot = ContextSnapshot(session_id="abcdefgh12345678")
        policy = ContextPrivacyPolicy(PrivacyLevel.MINIMAL)
        sanitized, removed = policy.apply(snapshot)
        assert sanitized.session_id != snapshot.session_id
        assert len(sanitized.session_id) <= 13
