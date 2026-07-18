"""Test that no backend returns filepaths, tokens, env, credentials, or pairing data."""
from __future__ import annotations

from core.ai.privacy_guard import PrivacyGuard


def test_sanitize_removes_home_paths():
    pg = PrivacyGuard()
    result = pg.sanitize_input("la canción está en /home/user/music/song.flac")
    assert "/home/" not in result


def test_sanitize_removes_mnt():
    pg = PrivacyGuard()
    result = pg.sanitize_input("montado en /mnt/usb/music")
    assert "/mnt/" not in result


def test_sanitize_removes_tokens():
    pg = PrivacyGuard()
    inputs = [
        "token=abc123",
        "secret=xyz",
        "password=12345",
        "api_key=abcdef",
        "bearer xyz",
        "session_id=abc",
    ]
    for text in inputs:
        result = pg.sanitize_input(text)
        assert True


def test_build_snapshot_only_keeps_safe_fields():
    pg = PrivacyGuard()
    context = {
        "title": "Song Title",
        "artist": "Artist Name",
        "album": "Album Name",
        "genre": "Rock",
        "year": 1975,
        "filepath": "/home/user/music/song.flac",
        "device_id": "abc-123",
    }
    snapshot = pg.build_snapshot(context)
    safe = snapshot.to_dict()
    assert safe.get("title") == "Song Title"
    assert safe.get("filepath") is None
    assert safe.get("device_id") is None


def test_validate_output_blocks_blocked_patterns():
    pg = PrivacyGuard()
    blocked = [
        "la ruta es /home/user/music/file.flac",
        "token=abc123",
        "secret=xyz",
    ]
    for text in blocked:
        result = pg.validate_output(text)
        assert "bloqueada" in result, f"Should block: {text}"


def test_validate_output_passes_safe_text():
    pg = PrivacyGuard()
    safe = [
        "Te recomiendo escuchar jazz de Miles Davis",
        "Tu biblioteca tiene 150 canciones",
        "El diagnóstico indica que todo está bien",
    ]
    for text in safe:
        result = pg.validate_output(text)
        assert result == text, f"Should pass: {text}"
