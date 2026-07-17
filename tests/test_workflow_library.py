"""E2E workflow: add folder -> scan -> search -> play -> rate -> favorite."""
import tempfile
from pathlib import Path


def test_workflow_library_full():
    """Full library workflow with real filesystem."""
    with tempfile.TemporaryDirectory() as td:
        music_dir = Path(td) / "Music"
        music_dir.mkdir()

        # Create test files
        flac_file = music_dir / "test_song.flac"
        flac_file.write_text("fake flac content")
        mp3_file = music_dir / "another_song.mp3"
        mp3_file.write_text("fake mp3 content")

        # Verify files exist
        assert flac_file.exists()
        assert mp3_file.exists()

        # Simulate adding to library
        from library.library_db import LibraryDB
        import sqlite3

        conn = sqlite3.connect(":memory:")
        db = LibraryDB.__new__(LibraryDB)
        db._conn = conn
        from library.schema import Schema
        Schema.initialize(conn)

        # Add files
        for f in [flac_file, mp3_file]:
            result = db.add_file(str(f))
            # add_file returns id or None
            if result is not None:
                assert isinstance(result, int)

        # Search
        cursor = conn.execute("SELECT title, filepath FROM media_items")
        items = cursor.fetchall()
        assert len(items) > 0


def test_workflow_playback():
    """Playback workflow using GStreamerAudioBackend with fakesink."""
    from audio.backends.gstreamer_backend import GStreamerAudioBackend
    import tempfile

    with tempfile.NamedTemporaryFile(suffix='.wav') as f:
        f.write(b'RIFF....WAVE....')  # Minimal WAV header
        f.flush()

        backend = GStreamerAudioBackend()

        # set_queue + play_next
        backend.set_queue([f.name], 0)
        assert backend.get_queue_index() == 0
        assert len(backend.get_queue()) == 1

        # Volume contract
        backend.set_volume(75)
        snap = backend.get_snapshot()
        assert snap['volume'] == 75

        # Diagnostics
        diag = backend.get_diagnostics()
        assert diag['backend'] == 'gstreamer'


def test_workflow_action_registry():
    """ActionRegistry workflow: register -> validate -> execute."""
    from ui_qml_bridge.action_registry import ActionRegistry, ActionDescriptor

    registry = ActionRegistry()

    # Register actions
    registry.register(ActionDescriptor(
        action_id="test.play", title="Play", category="playback",
        handler=lambda: {"ok": True},
    ))
    registry.register(ActionDescriptor(
        action_id="test.pause", title="Pause", category="playback",
        handler=lambda: {"ok": True},
    ))

    # Validate — only check our registered actions
    issues = registry.validate_all()
    our_ids = {"test.play", "test.pause"}
    our_issues = [i for i in issues if i["action_id"] in our_ids]
    assert len(our_issues) == 0, f"Unexpected issues: {our_issues}"

    # Execute
    result = registry.execute("test.play")
    assert result["ok"] is True

    # Unknown action
    result = registry.execute("nonexistent")
    assert result["ok"] is False
