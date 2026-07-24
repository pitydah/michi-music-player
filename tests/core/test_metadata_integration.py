"""Integration tests for MetadataService and ConfirmationService.

Alineado con el contrato canónico real de MetadataService:

    load(filepath)
    edit_field(filepath, field, value)
    validate(filepath)
    preview_changes(filepath)
    request_confirmation(filepath, message="")
    confirm_and_apply(filepath, confirmation_token)
    undo(filepath)
    load_batch(...)
    edit_batch(...)
    cancel_operation(...)
    refresh_model(...)
    diff(...)
    has_conflicts(...)

Los resultados se expresan como dict, no como objetos con .ok / .code.
"""

import tempfile
import os

from core.metadata_service import MetadataService
from core.confirmation_service import ConfirmationService


# ── MetadataService ────────────────────────────────────────────────────


class TestMetadataServiceLoad:
    """Cobertura del contrato load()."""

    def test_load_nonexistent(self):
        svc = MetadataService()
        result = svc.load("/nonexistent/file.mp3")
        assert result["ok"] is False
        assert result["error"] == "FILE_NOT_FOUND"

    def test_load_empty_path(self):
        svc = MetadataService()
        result = svc.load("")
        assert result["ok"] is False
        assert result["error"] == "FILE_NOT_FOUND"

    def test_load_with_injected_reader(self):
        """load() con tag_reader inyectado para evitar dependencia externa."""
        svc = MetadataService(tag_reader=lambda fp: {
            "title": "Test",
            "artist": "Artist",
            "album": "Album",
        })
        fd, path = tempfile.mkstemp(suffix=".flac")
        os.close(fd)
        try:
            result = svc.load(path)
            assert result["ok"] is True
            assert result["tags"]["title"] == "Test"
            assert result["tags"]["artist"] == "Artist"
        finally:
            os.unlink(path)


class TestMetadataServiceEditFlow:
    """Flujo completo: load → edit → validate → preview → confirm → apply."""

    def test_edit_and_validate(self):
        svc = MetadataService(tag_reader=lambda fp: {
            "title": "Original",
            "artist": "Artist",
        })
        fd, path = tempfile.mkstemp(suffix=".flac")
        os.close(fd)
        try:
            svc.load(path)
            r = svc.edit_field(path, "title", "Updated")
            assert r["ok"] is True
            assert r["field"] == "title"
            assert r["old_value"] == "Original"
            assert r["new_value"] == "Updated"

            vr = svc.validate(path)
            assert vr["ok"] is True
            assert vr["valid"] is True

            pr = svc.preview_changes(path)
            assert pr["ok"] is True
            assert len(pr["changes"]) == 1
        finally:
            os.unlink(path)


class TestMetadataServiceConfirmation:
    """Confirmación vía request_confirmation / confirm_and_apply."""

    def test_request_confirmation(self):
        svc = MetadataService()
        result = svc.request_confirmation("/music/song.flac")
        assert result["ok"] is True
        token = result["confirmation_token"]
        assert token in svc._confirmation_tokens

    def test_confirm_and_apply_invalid_token(self):
        svc = MetadataService()
        result = svc.confirm_and_apply("/music/song.flac", "invalid")
        assert result["ok"] is False
        assert result["error"] == "INVALID_CONFIRMATION_TOKEN"

    def test_confirm_and_apply_single_use(self):
        svc = MetadataService()
        fd, path = tempfile.mkstemp(suffix=".flac")
        os.close(fd)
        try:
            # Inyectar tag_reader para que load funcione
            svc._tag_reader = lambda fp: {
                "title": "Test", "artist": "Artist",
            }
            svc.load(path)

            # Mock _apply_changes para que retorne éxito sin tocar disco
            original_apply = svc._apply_changes
            svc._apply_changes = lambda fp: {"ok": True}

            result = svc.request_confirmation(path)
            assert result["ok"] is True
            token = result["confirmation_token"]

            # Primer uso → ok
            r1 = svc.confirm_and_apply(path, token)
            assert r1["ok"] is True

            # Segundo uso con mismo token → inválido
            r2 = svc.confirm_and_apply(path, token)
            assert r2["ok"] is False
            assert r2["error"] == "INVALID_CONFIRMATION_TOKEN"

            svc._apply_changes = original_apply
        finally:
            os.unlink(path)


# ── ConfirmationService ────────────────────────────────────────────────


class TestConfirmationService:
    """Tests contra ConfirmationService real — alineado con API actual."""

    def test_request_and_approve(self):
        cs = ConfirmationService()
        req = cs.request("op-1", "/music/song.flac", field_count=3)
        assert req.token is not None
        assert not req.resolved
        approved = cs.approve(req.token)
        assert approved is not None
        assert approved.approved is True

    def test_reject(self):
        cs = ConfirmationService()
        req = cs.request("op-1", "/music/song.flac")
        assert cs.reject(req.token) is True
        assert cs.approve(req.token) is None

    def test_expired_token(self):
        cs = ConfirmationService()
        from core.confirmation_service import ConfirmationRequest
        req = ConfirmationRequest("op-1", "/music/song.flac", "test", expiry_s=0)
        cs._pending[req.token] = req
        import time
        time.sleep(0.01)
        assert cs.approve(req.token) is None

    def test_revoke(self):
        cs = ConfirmationService()
        req = cs.request("op-1", "/music/song.flac")
        cs.revoke("op-1")
        assert cs.approve(req.token) is None

    def test_shutdown(self):
        cs = ConfirmationService()
        req = cs.request("op-1", "/music/song.flac")
        assert req.token in cs._pending
        cs.shutdown()
        assert len(cs._pending) == 0


# ── ServiceContainer integration ────────────────────────────────────────
# Verifica que MetadataService se construya correctamente via container
# sin depender del sistema gi/GStreamer (import lazy)


class TestMetadataServiceContainer:
    def test_service_constructable(self):
        svc = MetadataService()
        assert svc is not None
        # Verifica que load funcione sin gi/GStreamer
        result = svc.load("/nonexistent/file.mp3")
        assert result["ok"] is False
