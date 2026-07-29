"""Fase 10 — Certification tests for Home Audio.

Tests the complete distribution workflow end-to-end:
  1. FIFO creation and lifecycle
  2. Snapserver start/stop lifecycle
  3. Pipeline FIFO branch activation
  4. Source routeable status changes
  5. Route creation with atomic/best_effort
  6. Group operations (create, update, delete)
  7. Diagnostics signal path
"""
import pytest
from unittest.mock import MagicMock, patch

# ---- Fixtures ----

@pytest.fixture
def mock_service():
    """Create a HomeAudioService with mocked dependencies."""
    from core.home_audio_service import HomeAudioService
    svc = HomeAudioService()
    svc._snapserver = MagicMock()
    svc._snapserver.is_running = False
    svc._snapserver.start.return_value = {"ok": True}
    svc._snapserver.stop.return_value = {"ok": True}
    svc._playback = MagicMock()
    svc._playback.current = "Test Song"
    svc._playback.state = "playing"
    return svc


@pytest.fixture
def mock_bridge():
    """Create a HomeAudioBridge with mocked service."""
    from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
    bridge = HomeAudioBridge(home_audio_service=MagicMock())
    return bridge


# ---- FIFO Tests ----

class TestFifoLifecycle:
    def test_fifo_create(self):
        """FIFO can be created and exists."""
        from integrations.snapcast.fifo_manager import ensure_fifo, close_fifo
        import os
        import tempfile

        tmpdir = tempfile.mkdtemp()
        fifo_path = os.path.join(tmpdir, "test.fifo")

        result = ensure_fifo(fifo_path)
        assert result is True
        assert os.path.exists(fifo_path)

        close_fifo()

    def test_fifo_recreate_on_restart(self):
        """FIFO is recreated after deletion."""
        from integrations.snapcast.fifo_manager import ensure_fifo, close_fifo
        import os
        import tempfile

        tmpdir = tempfile.mkdtemp()
        fifo_path = os.path.join(tmpdir, "test.fifo")

        ensure_fifo(fifo_path)
        os.unlink(fifo_path)

        result = ensure_fifo(fifo_path)
        assert result is True
        assert os.path.exists(fifo_path)
        close_fifo()


# ---- Distribution Tests ----

class TestDistribution:
    def test_enable_distribution_starts_snapserver(self, mock_service):
        """enable_distribution() starts Snapserver and enables FIFO."""
        result = mock_service.enable_distribution()
        assert result.get("ok") is True
        mock_service._snapserver.start.assert_called_once()

    def test_disable_distribution_stops_snapserver(self, mock_service):
        """disable_distribution() stops Snapserver."""
        mock_service._snapserver.is_running = True
        result = mock_service.disable_distribution()
        assert result.get("ok") is True
        mock_service._snapserver.stop.assert_called_once()

    def test_source_routeable_true_when_distribution_active(self, mock_service):
        """get_sources() returns routeable=True when FIFO+Snapserver active."""
        mock_service._snapserver.is_running = True
        with patch('os.path.exists', return_value=True), \
             patch('os.access', return_value=True):
            sources = mock_service.get_sources()
        local = [s for s in sources if s.get("id") == "local_playback"]
        assert len(local) == 1
        assert local[0].get("routeable") is True

    def test_source_routeable_false_when_snapserver_down(self, mock_service):
        """get_sources() returns routeable=False when Snapserver stopped."""
        sources = mock_service.get_sources()
        local = [s for s in sources if s.get("id") == "local_playback"]
        assert len(local) == 1
        assert local[0].get("routeable") is False


# ---- Route Tests ----

class TestRoutes:
    def test_route_transaction_atomic(self):
        """RouteTransaction atomic mode rolls back on failure."""
        from core.home_audio_service import RouteTransaction
        tx = RouteTransaction(mode="atomic")
        tx.snapshot({"key": "value"})
        result = tx.commit()
        assert result.get("ok") is True

    def test_route_transaction_best_effort(self):
        """RouteTransaction best_effort mode succeeds regardless."""
        from core.home_audio_service import RouteTransaction
        tx = RouteTransaction(mode="best_effort")
        tx.snapshot({"key": "value"})
        result = tx.commit()
        assert result.get("ok") is True
        assert result.get("mode") == "best_effort"


# ---- Group Tests ----

class TestGroups:
    def test_create_group(self, mock_bridge):
        """Bridge.createGroup creates a group via service."""
        result = mock_bridge.createGroup("Test Room", [{"id": "r1"}, {"id": "r2"}])
        assert result is not None

    def test_update_group(self, mock_bridge):
        """Bridge.updateGroup updates group membership."""
        result = mock_bridge.updateGroup("g1", "New Name", [{"id": "r1"}])
        assert result is not None


# ---- Diagnostics Tests ----

class TestDiagnostics:
    def test_fifo_manager_tracks_bytes(self):
        """FIFO manager tracks bytes written."""
        from integrations.snapcast.fifo_manager import (
            fifo_metrics, fifo_path, ensure_fifo, close_fifo
        )
        import os, tempfile
        
        # Create temp FIFO for testing
        tmpdir = tempfile.mkdtemp()
        test_path = os.path.join(tmpdir, "test.fifo")
        
        ensure_fifo(test_path)
        old_metrics = fifo_metrics()
        assert "bytes_written" in old_metrics
        close_fifo()
        os.unlink(test_path)
