"""Tests for PersistenceCoordinator — M5.C5 runtime checkpoints + startup restore.

The coordinator subscribes to queue/playback change notifications and
persists a `PlaybackSessionSnapshot` built from PUBLIC state only (pending
candidates are never committed session state, §27), with a position
throttle so tiny position ticks do not produce a SQLite write per event.
Checkpoints make restart independent of graceful shutdown.

`restore()` (startup) rebuilds the queue (C3 — atomic, capacity-guarded)
and, only when the queue current identity matches the backend playback
identity (§4/§22), prepares a non-autoplay resume (C4 — load + seek after
acceptance). A mismatched playback path is never used to fabricate a
PlaybackState.
"""

import sqlite3
from pathlib import Path

from michi.application.persistence_coordinator import PersistenceCoordinator
from michi.application.playback_service import PlaybackService
from michi.application.queue_service import QueueService
from michi.application.settings_service import SettingsService
from michi.domain.playback import PlaybackStatus
from michi.domain.queue import RepeatMode
from michi.domain.session import (
    FORMAT_VERSION,
    PersistedQueueEntry,
    PlaybackSessionSnapshot,
    fresh_snapshot,
)
from michi.infrastructure.session_repository import SqliteSessionRepository
from tests.conftest import FakeAudioPort, FakeSettingsRepo

_A = Path("/m/a.flac")
_B = Path("/m/b.flac")
_C = Path("/m/c.flac")
_X = Path("/m/x.flac")


def _entries(*pairs) -> tuple[PersistedQueueEntry, ...]:
    return tuple(
        PersistedQueueEntry(file_path=path, title=title) for path, title in pairs
    )


def _snapshot(
    entries,
    current_index: int = -1,
    playback_path: str | None = None,
    position_ms: int = 0,
    repeat_mode: RepeatMode = RepeatMode.NONE,
    shuffle_enabled: bool = False,
    shuffle_seed: int = 0,
) -> PlaybackSessionSnapshot:
    return PlaybackSessionSnapshot(
        format_version=FORMAT_VERSION,
        queue_entries=tuple(entries),
        queue_current_index=current_index,
        playback_path=playback_path,
        position_ms=position_ms,
        repeat_mode=repeat_mode,
        shuffle_enabled=shuffle_enabled,
        shuffle_seed=shuffle_seed,
    )


def _build(db_path: Path, settings_repo=None, shuffle_seed: int | None = None):
    """Fresh services + coordinator on the same db (no shutdown)."""
    repo = SqliteSessionRepository(db_path)
    settings = SettingsService(
        settings_repo if settings_repo is not None else FakeSettingsRepo()
    )
    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    queue = QueueService(playback, shuffle_seed=shuffle_seed)
    coordinator = PersistenceCoordinator(repo, queue, playback, settings)
    return repo, settings, audio, playback, queue, coordinator


class TestSnapshotBuilding:
    def test_snapshot_from_public_state(self, tmp_path):
        db = tmp_path / "t1.db"
        _repo, _settings, audio, playback, queue, coordinator = _build(
            db, shuffle_seed=424242
        )
        queue.add(_A, "A")
        queue.add(_B, "B")
        queue.add(_C, "C")
        queue.play_index(1)  # B pending
        audio.trigger_media_accepted(_B)  # committed current = B
        playback.update_position(98765)
        queue.set_repeat_mode(RepeatMode.ALL)
        queue.set_shuffle_enabled(True)

        snap = coordinator._build_snapshot()
        assert snap.format_version == FORMAT_VERSION
        assert snap.queue_entries == _entries(
            ("/m/a.flac", "A"), ("/m/b.flac", "B"), ("/m/c.flac", "C")
        )
        assert snap.queue_current_index == 1
        assert snap.playback_path == "/m/b.flac"
        assert snap.position_ms == 98765
        assert snap.repeat_mode is RepeatMode.ALL
        assert snap.shuffle_enabled is True
        assert snap.shuffle_seed == 424242

    def test_pending_not_persisted(self, tmp_path):
        db = tmp_path / "t2.db"
        _repo, _settings, audio, playback, queue, coordinator = _build(db)
        queue.add(_A, "A")
        queue.add(_B, "B")
        queue.add(_C, "C")
        queue.play_index(0)
        audio.trigger_media_accepted(_A)  # committed index 0
        queue.play_index(2)  # C pending, NOT accepted

        snap = coordinator._build_snapshot()
        # Committed identity, never the pending candidate.
        assert snap.queue_current_index == 0
        assert snap.playback_path == "/m/a.flac"
        assert snap.playback_path != "/m/c.flac"
        assert snap.queue_current_index != 2
        # The queue itself is intact (C is still a queued entry).
        assert snap.queue_entries == _entries(
            ("/m/a.flac", "A"), ("/m/b.flac", "B"), ("/m/c.flac", "C")
        )


class TestCheckpointing:
    def test_checkpoint_saves_session(self, tmp_path):
        db = tmp_path / "t3.db"
        repo, _settings, audio, playback, queue, coordinator = _build(db)
        queue.add(_A, "A")
        queue.play_index(0)
        audio.trigger_media_accepted(_A)
        playback.update_position(1500)

        coordinator.checkpoint()
        assert repo.load() == coordinator._build_snapshot()
        with sqlite3.connect(str(db)) as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = 'session_snapshot'"
            ).fetchone()
        assert row is not None  # the session row exists in the settings table

    def test_queue_change_triggers_checkpoint(self, tmp_path):
        db = tmp_path / "t4.db"
        repo, _settings, _audio, _playback, queue, coordinator = _build(db)
        # No explicit checkpoint call — the coordinator's own subscription saves.
        queue.add(_A, "A")
        snap = repo.load()
        assert snap.queue_entries == _entries(("/m/a.flac", "A"))
        assert snap.queue_current_index == -1

        queue.add(_B, "B")
        snap = repo.load()
        assert snap.queue_entries == _entries(("/m/a.flac", "A"), ("/m/b.flac", "B"))

    def test_position_throttle(self, tmp_path):
        db = tmp_path / "t5.db"
        repo, _settings, audio, playback, queue, coordinator = _build(db)
        queue.add(_A, "A")
        queue.play_index(0)
        audio.trigger_media_accepted(_A)  # baseline checkpoint, position 0

        baseline = repo.load()
        assert baseline.position_ms == 0

        playback.update_position(3000)  # delta 3000 < 5000 -> no save
        assert repo.load() == baseline

        playback.update_position(8000)  # delta 8000 >= 5000 -> save
        assert repo.load().position_ms == 8000

    def test_lifecycle_transition_checkpoints(self, tmp_path):
        db = tmp_path / "t6.db"
        repo, _settings, audio, playback, queue, coordinator = _build(db)
        queue.add(_A, "A")
        queue.play_index(0)
        audio.trigger_media_accepted(_A)
        playback.update_position(100)  # tiny delta — throttled, NOT saved
        assert repo.load().position_ms == 0

        playback.play()
        audio.trigger_playback_state(PlaybackStatus.PLAYING)
        playback.pause()
        audio.trigger_playback_state(PlaybackStatus.PAUSED)  # lifecycle transition
        # The transition checkpoints even with a tiny position delta.
        assert repo.load().position_ms == 100


class TestRestore:
    def test_restore_golden(self, tmp_path, monkeypatch):
        db = tmp_path / "t7.db"

        # ── Session 1: build the golden state and checkpoint ──
        settings_repo = FakeSettingsRepo()
        repo1, settings1, audio1, playback1, queue1, coordinator1 = _build(
            db, settings_repo=settings_repo, shuffle_seed=424242
        )
        settings1.set_playback_preferences(37, True)
        settings1.save()
        queue1.add(_A, "A")
        queue1.add(_B, "B")
        queue1.add(_C, "C")
        queue1.play_index(1)
        audio1.trigger_media_accepted(_B)
        playback1.update_position(222000)
        queue1.set_repeat_mode(RepeatMode.ALL)
        queue1.set_shuffle_enabled(True)
        coordinator1.checkpoint()

        # Destroy WITHOUT shutdown: restart must not depend on graceful stop.
        del coordinator1, queue1, playback1, audio1, repo1

        # ── Session 2: fresh services + coordinator on the SAME db ──
        repo2, settings2, audio2, playback2, queue2, coordinator2 = _build(
            db, settings_repo=settings_repo
        )
        prepare_calls = []
        orig_prepare = playback2.prepare_for_resume

        def spy_prepare(path, position_ms):
            prepare_calls.append((path, position_ms))
            orig_prepare(path, position_ms)

        monkeypatch.setattr(playback2, "prepare_for_resume", spy_prepare)
        play_calls = []
        orig_play = audio2.play

        def spy_play():
            play_calls.append(1)
            orig_play()

        monkeypatch.setattr(audio2, "play", spy_play)

        coordinator2.restore()

        # Queue fully restored.
        assert [t.file_path for t in queue2.state.tracks] == [_A, _B, _C]
        assert queue2.state.current_index == 1
        assert queue2.state.repeat_mode is RepeatMode.ALL
        assert queue2.state.shuffle_enabled is True
        assert queue2.shuffle_seed == 424242
        # Coherent resume requested: load + seek, NEVER autoplay.
        assert prepare_calls == [(_B, 222000)]
        assert play_calls == []
        assert audio2.state != "playing"
        # Playback identity committed only after backend acceptance.
        assert playback2.state.file_path is None
        audio2.trigger_media_accepted(_B)
        assert playback2.state.file_path == _B
        assert playback2.state.status is PlaybackStatus.STOPPED
        assert audio2.seek_calls == [222000]
        # Settings survive (shared FakeSettingsRepo).
        assert settings2.state.volume == 37
        assert settings2.state.muted is True

    def test_restore_no_autoplay(self, tmp_path, monkeypatch):
        db = tmp_path / "t8.db"
        repo, _settings, audio, playback, queue, coordinator = _build(db)
        queue.add(_A, "A")
        queue.add(_B, "B")
        queue.play_index(1)
        audio.trigger_media_accepted(_B)
        playback.update_position(222000)
        coordinator.checkpoint()
        del coordinator, queue, playback, audio, repo

        _repo2, _s2, audio2, playback2, queue2, coordinator2 = _build(db)
        play_calls = []
        orig_play = audio2.play

        def spy_play():
            play_calls.append(1)
            orig_play()

        monkeypatch.setattr(audio2, "play", spy_play)
        coordinator2.restore()
        audio2.trigger_media_accepted(_B)
        assert play_calls == []  # restore + acceptance never autoplay
        assert audio2.state != "playing"
        assert playback2.state.status is PlaybackStatus.STOPPED

        # The user's later play() resumes from the sought position.
        playback2.play()
        assert audio2.state == "playing"

    def test_restore_incoherent_playback_path(self, tmp_path, monkeypatch):
        db = tmp_path / "t9.db"
        repo = SqliteSessionRepository(db)
        repo.save(
            _snapshot(
                _entries(("/m/a.flac", "A"), ("/m/b.flac", "B"), ("/m/c.flac", "C")),
                current_index=1,
                playback_path="/m/c.flac",  # index 1 is B — incoherent
                position_ms=5000,
            )
        )

        _repo2, _s2, audio2, playback2, queue2, coordinator2 = _build(db)
        prepare_calls = []
        orig_prepare = playback2.prepare_for_resume

        def spy_prepare(path, position_ms):
            prepare_calls.append((path, position_ms))
            orig_prepare(path, position_ms)

        monkeypatch.setattr(playback2, "prepare_for_resume", spy_prepare)
        coordinator2.restore()

        # Mismatched path: NEVER prepare with a fabricated playback identity.
        assert prepare_calls == []
        assert [t.file_path for t in queue2.state.tracks] == [_A, _B, _C]
        assert queue2.state.current_index == 1  # queue restored as-is
        assert playback2.state.file_path is None
        assert playback2.state.status is PlaybackStatus.STOPPED
        assert audio2.loaded is None  # backend untouched

    def test_restore_current_index_minus_one(self, tmp_path, monkeypatch):
        db = tmp_path / "t10.db"
        repo = SqliteSessionRepository(db)
        repo.save(
            _snapshot(
                _entries(("/m/a.flac", "A"), ("/m/b.flac", "B")),
                current_index=-1,
                playback_path=None,
            )
        )

        _repo2, _s2, audio2, playback2, queue2, coordinator2 = _build(db)
        prepare_calls = []
        orig_prepare = playback2.prepare_for_resume

        def spy_prepare(path, position_ms):
            prepare_calls.append((path, position_ms))
            orig_prepare(path, position_ms)

        monkeypatch.setattr(playback2, "prepare_for_resume", spy_prepare)
        coordinator2.restore()

        assert queue2.state.count == 2  # queue only
        assert queue2.state.current_index == -1
        assert prepare_calls == []
        assert playback2.state.file_path is None
        assert playback2.state.status is PlaybackStatus.STOPPED
        assert audio2.loaded is None

    def test_restore_rejection_safe(self, tmp_path):
        db = tmp_path / "t11.db"
        repo = SqliteSessionRepository(db)
        repo.save(
            _snapshot(
                _entries(("/m/a.flac", "A"), ("/m/b.flac", "B")),
                current_index=1,
                playback_path="/m/b.flac",
                position_ms=222000,
            )
        )

        _repo2, _s2, audio2, playback2, queue2, coordinator2 = _build(db)
        coordinator2.restore()  # coherent -> prepare_for_resume(B, 222000)
        audio2.trigger_media_rejected(_B, "gone")

        # No crash; rejection is safe; queue stays restored.
        assert playback2.state.status is PlaybackStatus.STOPPED
        assert playback2.state.file_path is None  # never committed
        assert playback2.state.error_message == "gone"
        assert queue2.state.count == 2
        assert queue2.state.current_index == 1

    def test_abrupt_termination_checkpoint(self, tmp_path):
        db = tmp_path / "t12.db"
        repo, _settings, audio, playback, queue, coordinator = _build(db)
        queue.add(_A, "A")
        queue.add(_B, "B")
        queue.play_index(1)
        audio.trigger_media_accepted(_B)
        playback.update_position(42424)
        coordinator.checkpoint()  # NO shutdown
        del coordinator, queue, playback, audio, repo

        _repo2, _s2, audio2, playback2, queue2, coordinator2 = _build(db)
        coordinator2.restore()
        assert [t.file_path for t in queue2.state.tracks] == [_A, _B]
        assert queue2.state.current_index == 1
        audio2.trigger_media_accepted(_B)
        assert audio2.seek_calls == [42424]  # restored position sought

    def test_duplicate_paths_golden(self, tmp_path):
        db = tmp_path / "t13.db"
        repo, _settings, audio, playback, queue, coordinator = _build(db)
        queue.add(_X, "X1")
        queue.add(_A, "A")
        queue.add(_X, "X2")
        queue.play_index(2)
        audio.trigger_media_accepted(_X)  # committed current = X2
        coordinator.checkpoint()
        del coordinator, queue, playback, audio, repo

        _repo2, _s2, audio2, playback2, queue2, coordinator2 = _build(db)
        coordinator2.restore()
        tracks = queue2.state.tracks
        assert len(tracks) == 3  # duplicates survive as distinct entries
        assert tracks[0] is not tracks[2]
        assert tracks[0].file_path == tracks[2].file_path == _X
        assert queue2.state.current_index == 2
        assert playback2.state.file_path is None
        audio2.trigger_media_accepted(_X)
        assert playback2.state.file_path == _X
        assert playback2.state.status is PlaybackStatus.STOPPED


class TestLifecycle:
    def test_shutdown_checkpoints(self, tmp_path):
        db = tmp_path / "t14.db"
        repo, settings, audio, playback, queue, coordinator = _build(db)
        queue.add(_A, "A")
        queue.play_index(0)
        audio.trigger_media_accepted(_A)
        playback.update_position(777)
        playback.set_volume(63)
        playback.set_muted(True)

        coordinator.shutdown()

        snap = repo.load()
        assert snap.queue_entries == _entries(("/m/a.flac", "A"))
        assert snap.playback_path == "/m/a.flac"
        assert snap.position_ms == 777  # final save captures the position
        # Volume/mute persisted through the settings service public API.
        assert settings.state.volume == 63
        assert settings.state.muted is True

    def test_coordinator_never_raises(self, tmp_path):
        class RaisingRepo:
            def load(self):
                return fresh_snapshot()

            def save(self, snapshot):
                raise RuntimeError("simulated sqlite failure")

        repo = RaisingRepo()
        settings = SettingsService(FakeSettingsRepo())
        audio = FakeAudioPort()
        playback = PlaybackService(audio)
        queue = QueueService(playback)
        coordinator = PersistenceCoordinator(repo, queue, playback, settings)

        # Direct checkpoint is best-effort.
        coordinator.checkpoint()
        # Queue-driven checkpoint (subscription) is best-effort.
        queue.add(_A, "A")
        # Playback-driven (position) checkpoint is best-effort.
        playback.update_position(6000)
        # Shutdown checkpoint is best-effort.
        coordinator.shutdown()
