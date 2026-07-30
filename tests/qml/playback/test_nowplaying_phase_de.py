"""Phase D/E Now Playing architecture and responsive UI contracts."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge


ROOT = Path(__file__).resolve().parents[3]


class _TaskHandle:
    def __init__(self) -> None:
        self.cancelled = False
        self.state = "running"
        self.error_code = ""
        self.message = ""

    def cancel(self) -> bool:
        self.cancelled = True
        return True


class _ControlledWorkerManager:
    def __init__(self) -> None:
        self.jobs: list[dict] = []

    def run_task(self, task_id, fn, *args, **kwargs):
        handle = _TaskHandle()
        self.jobs.append(
            {
                "task_id": task_id,
                "fn": fn,
                "args": args,
                "handle": handle,
                "on_done": kwargs["on_done"],
                "on_error": kwargs["on_error"],
                "on_cancelled": kwargs["on_cancelled"],
            }
        )
        return handle


class _RejectingWorkerManager:
    def run_task(self, *_args, **_kwargs):
        handle = _TaskHandle()
        handle.state = "failed"
        handle.error_code = "TASK_REJECTED"
        handle.message = "Worker unavailable"
        return handle


def _player(filepath: str = "/music/first.flac") -> MagicMock:
    player = MagicMock()
    player.current = None
    player.current_filepath = filepath
    player.current_path = ""
    player.state = "paused"
    player.duration = 180
    for signal_name in (
        "track_changed",
        "state_changed",
        "position_changed",
        "duration_changed",
        "volume_changed",
        "error_occurred",
    ):
        setattr(player, signal_name, MagicMock())
    return player


def test_quality_probe_runs_as_worker_job_and_reports_loading() -> None:
    worker_manager = _ControlledWorkerManager()
    adapter = MagicMock()
    bridge = NowPlayingBridge(
        player_service=_player(),
        audio_quality_adapter=adapter,
        worker_manager=worker_manager,
    )

    bridge._on_track("First", "Artist", "Album")

    assert bridge.qualityLoading is True
    assert len(worker_manager.jobs) == 1
    assert worker_manager.jobs[0]["task_id"].startswith("nowplaying-quality-probe-")


def test_new_quality_probe_cancels_previous_and_ignores_stale_result() -> None:
    worker_manager = _ControlledWorkerManager()
    adapter = MagicMock()
    player = _player()
    bridge = NowPlayingBridge(
        player_service=player,
        audio_quality_adapter=adapter,
        worker_manager=worker_manager,
    )
    emissions: list[bool] = []
    bridge.qualityChanged.connect(lambda: emissions.append(True))

    bridge._on_track("First", "Artist", "Album")
    first_job = worker_manager.jobs[0]
    player.current_filepath = "/music/second.flac"
    bridge._on_track("Second", "Artist", "Album")
    second_job = worker_manager.jobs[1]
    first_job["on_done"]({"ok": True, "format_label": "MP3"})
    second_job["on_done"]({"ok": True, "format_label": "FLAC", "sample_rate": "96 kHz"})

    assert first_job["handle"].cancelled is True
    assert bridge.formatLabel == "FLAC"
    assert bridge.sampleRate == "96 kHz"
    assert bridge.qualityLoading is False
    assert emissions


def test_quality_probe_failure_sets_error_state() -> None:
    worker_manager = _ControlledWorkerManager()
    bridge = NowPlayingBridge(
        player_service=_player(),
        audio_quality_adapter=MagicMock(),
        worker_manager=worker_manager,
    )

    bridge._on_track("First", "Artist", "Album")
    worker_manager.jobs[0]["on_error"]("TASK_FAILED", "Probe exploded")

    assert bridge.qualityLoading is False
    assert bridge.qualityInfoAvailable is False
    assert bridge.qualityError == "Probe exploded"


def test_rejected_quality_probe_job_sets_error_state() -> None:
    bridge = NowPlayingBridge(
        player_service=_player(),
        audio_quality_adapter=MagicMock(),
        worker_manager=_RejectingWorkerManager(),
    )

    bridge._on_track("First", "Artist", "Album")

    assert bridge.qualityLoading is False
    assert bridge.qualityInfoAvailable is False
    assert bridge.qualityError == "Worker unavailable"


def test_transport_command_stays_pending_until_backend_confirmation() -> None:
    bridge = NowPlayingBridge(player_service=_player())

    result = bridge.togglePlay()

    assert result["ok"] is True
    assert bridge.commandState == "pending"
    assert bridge.commandPending is True
    assert bridge.lastCommandOk is False

    bridge._on_state("playing")

    assert bridge.commandState == "confirmed"
    assert bridge.commandPending is False
    assert bridge.lastCommandOk is True


def test_failed_command_uses_failed_state() -> None:
    bridge = NowPlayingBridge(player_service=None)

    result = bridge.togglePlay()

    assert result["ok"] is False
    assert bridge.commandState == "failed"
    assert bridge.commandPending is False
    assert bridge.lastCommandOk is False


def test_central_error_handler_deduplicates_code_and_operation() -> None:
    bridge = NowPlayingBridge(player_service=_player())
    emissions: list[bool] = []
    bridge.errorChanged.connect(lambda: emissions.append(True))

    bridge._handle_error("seek", "PLAYBACK_ERROR", "Seek failed")
    bridge._handle_error("seek", "PLAYBACK_ERROR", "Seek failed again")
    bridge._handle_error("togglePlay", "PLAYBACK_ERROR", "Playback failed")
    bridge._handle_error("seek", "PLAYBACK_ERROR", "Seek failed once more")

    assert len(emissions) == 2
    assert bridge.errorMessage == "Playback failed"


def test_queue_preview_uses_queue_bridge_only() -> None:
    page = (ROOT / "ui_qml/pages/nowplaying/NowPlayingPage.qml").read_text(encoding="utf-8")
    preview = (ROOT / "ui_qml/pages/nowplaying/NowPlayingQueuePreview.qml").read_text(
        encoding="utf-8"
    )

    assert "property var qb:" in page
    assert "qb: root.qb" in page
    assert "ps: root.ps" not in preview
    assert "nowplayingBridge.queue" not in page + preview


def test_nowplaying_bar_declares_three_density_heights() -> None:
    content = (ROOT / "ui_qml/components/NowPlayingBar.qml").read_text(encoding="utf-8")

    # The bar has two height modes: compact (72) and full (154)
    assert "compactLayout ? 72 : 154" in content
    assert '!compactLayout' in content
    assert 'compactLayout' in content


def test_compact_overflow_exposes_all_secondary_actions() -> None:
    content = (ROOT / "ui_qml/components/NowPlayingBar.qml").read_text(encoding="utf-8")

    # Compact layout uses PlaybackTransport with full transport controls
    assert "compact: true" in content
    assert 'objectName: "playbackTransport"' in content or "PlaybackTransport" in content
    assert "isPlaying" in content
    assert "shuffleEnabled" in content
    assert "repeatMode" in content
