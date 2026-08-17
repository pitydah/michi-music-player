"""M5 FINAL CORRECTION — RED tests pinning the corrected persistence contract.

Four gaps are encoded here (the TARGET behavior the coordinator must reach):

- P1-A: the coordinator enters an explicit restoring state during
  ``restore()``; while restoring, ``_on_queue_changed``/``_on_playback_changed``
  must NOT checkpoint, so the durable resume snapshot is never degraded by
  restore's own queue notification (tests 1-3, 11). QueueService.restore_session
  keeps emitting its notification — other observers are unaffected (test 11).
- P1-B: volume/muted changes persist DURING runtime — no graceful-shutdown
  dependency. The coordinator observes playback volume/mute changes
  (last-observed detection) and syncs ``playback.snapshot_volume()`` →
  ``settings.set_playback_preferences`` → ``settings.save()`` only when they
  change (tests 4-6). The golden works with ONLY runtime public APIs + abrupt
  kill (test_m5_restart_golden.py).
- P2-A: explicit coordinator lifecycle — subscribe on ``start()``, unsubscribe
  on ``stop()``/``shutdown()``; shutdown = freeze -> final checkpoint ->
  persist volume/mute -> unsubscribe; idempotent; backend teardown must not
  destroy the durable resume state (tests 7-8).
- P2-B: a checkpoint advances the durable position marker ONLY when the save
  actually succeeded (``SessionRepository.save`` returns a success signal).
  The failing-repo stub below pins the marker semantics (tests 9-10).

The lifecycle is expressed explicitly in every test: ``coordinator.start()``
after construction arms the persistence subscriptions, ``coordinator.shutdown()``
freezes them.
"""

import sqlite3
from pathlib import Path

from michi.application.persistence_coordinator import PersistenceCoordinator
from michi.application.playback_service import PlaybackService
from michi.application.queue_service import QueueService
from michi.application.settings_service import SettingsService
from michi.domain.queue import RepeatMode
from michi.infrastructure.session_repository import SqliteSessionRepository
from tests.conftest import FakeAudioPort, FakeSettingsRepo

_A = Path("/m/a.flac")
_B = Path("/m/b.flac")
_C = Path("/m/c.flac")

_SESSION_KEY = "session_snapshot"


def _build(db_path: Path, settings_repo=None, shuffle_seed: int | None = None):
    """Fresh services + coordinator on the same db.

    The coordinator is constructed but NOT started — the target lifecycle is
    explicit in each test: ``coordinator.start()`` arms the persistence
    subscriptions, ``coordinator.shutdown()`` freezes them.
    """
    repo = SqliteSessionRepository(db_path)
    settings = SettingsService(
        settings_repo if settings_repo is not None else FakeSettingsRepo()
    )
    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    queue = QueueService(playback, shuffle_seed=shuffle_seed)
    coordinator = PersistenceCoordinator(repo, queue, playback, settings)
    return repo, settings, audio, playback, queue, coordinator


def _session_row(db_path: Path) -> str | None:
    """Raw persisted session row (None when the row does not exist)."""
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (_SESSION_KEY,)
        ).fetchone()
    return row[0] if row is not None else None


class _FailOnDemandRepo:
    """Delegates to the real repo; save() can be forced to fail.

    Records every attempt. Per the target contract (P2-B) ``save`` returns a
    success signal: ``False`` on failure, ``True`` after a real save.
    """

    def __init__(self, real: SqliteSessionRepository) -> None:
        self._real = real
        self.fail_saves = False
        self.save_calls = 0
        self.failed_saves = 0

    def load(self):
        return self._real.load()

    def save(self, snapshot) -> bool:
        self.save_calls += 1
        if self.fail_saves:
            self.failed_saves += 1
            return False
        self._real.save(snapshot)
        return True


def _build_golden_state(db_path: Path):
    """First graph: build the B@222000 resume state via the real flow and
    checkpoint; destroy WITHOUT shutdown (abrupt restart must not depend on
    graceful stop)."""
    repo, _settings, audio, playback, queue, coordinator = _build(
        db_path, shuffle_seed=424242
    )
    coordinator.start()
    queue.add(_A, "A")
    queue.add(_B, "B")
    queue.add(_C, "C")
    queue.play_index(1)  # B pending
    audio.trigger_media_accepted(_B)  # B committed, current 1
    playback.update_position(222000)
    queue.set_repeat_mode(RepeatMode.ALL)
    queue.set_shuffle_enabled(True)
    coordinator.checkpoint()
    del coordinator, queue, playback, audio, repo


class TestRestoringGuard:
    def test_restore_does_not_overwrite_resume_snapshot(self, tmp_path):
        db = tmp_path / "t1.db"
        _build_golden_state(db)

        # ── Session 2: fresh graph — restore must not degrade the snapshot ──
        repo2, _s2, audio2, _playback2, _queue2, coordinator2 = _build(db)
        coordinator2.start()
        coordinator2.restore()

        # BEFORE any media acceptance, the durable resume snapshot is intact:
        # playback_path B, position 222000 — never null/0.
        snap = repo2.load()
        assert snap.playback_path == "/m/b.flac"
        assert snap.position_ms == 222000
        assert snap.queue_current_index == 1
        assert snap.repeat_mode is RepeatMode.ALL
        assert snap.shuffle_enabled is True
        assert snap.shuffle_seed == 424242

    def test_second_restart_during_prepare_preserves_resume(
        self, tmp_path, monkeypatch
    ):
        db = tmp_path / "t2.db"
        _build_golden_state(db)

        # ── Session 2: restore but do NOT accept; destroy abruptly ──
        _r2, _s2, audio2, playback2, _q2, coordinator2 = _build(db)
        coordinator2.start()
        coordinator2.restore()
        del coordinator2, playback2, audio2  # abrupt during the prepare window

        # ── Session 3: the durable resume is still B@222000, never B@0 ──
        _r3, _s3, audio3, playback3, _q3, coordinator3 = _build(db)
        coordinator3.start()
        prepare_calls = []
        orig_prepare = playback3.prepare_for_resume

        def spy_prepare(path, position_ms):
            prepare_calls.append((path, position_ms))
            orig_prepare(path, position_ms)

        monkeypatch.setattr(playback3, "prepare_for_resume", spy_prepare)
        coordinator3.restore()

        assert prepare_calls == [(_B, 222000)]

    def test_acceptance_during_restore_does_not_destroy_position(self, tmp_path):
        db = tmp_path / "t3.db"
        _build_golden_state(db)

        # ── Session 2: restore; the prepare acceptance fires playback events
        # during the protected period ──
        repo2, _s2, audio2, _playback2, _q2, coordinator2 = _build(db)
        coordinator2.start()
        coordinator2.restore()
        audio2.trigger_media_accepted(_B)

        # The durable snapshot is NOT degraded by the protected-period events:
        # only a later legitimate runtime checkpoint may replace it.
        snap = repo2.load()
        assert snap.playback_path == "/m/b.flac"
        assert snap.position_ms == 222000


class TestRuntimeVolumeMuteSync:
    def test_volume_survives_abrupt_kill_without_manual_settings_save(self, tmp_path):
        db = tmp_path / "t4.db"
        settings_repo = FakeSettingsRepo()  # the persisted settings store
        _r1, settings1, audio1, playback1, _q1, coordinator1 = _build(
            db, settings_repo=settings_repo
        )
        coordinator1.start()
        # ONLY the public runtime setter — no settings.save, no shutdown.
        playback1.set_volume(37)
        assert settings1.state.volume == 37  # runtime sync is immediate
        del coordinator1, playback1, audio1  # abrupt kill

        # Fresh graph on the same store: the PERSISTED truth is volume 37
        # (the bootstrap applies it to the backend on startup — its concern).
        _r2, settings2, _a2, _p2, _q2, _c2 = _build(db, settings_repo=settings_repo)
        assert settings2.state.volume == 37

    def test_mute_survives_abrupt_kill_without_manual_settings_save(self, tmp_path):
        db = tmp_path / "t5.db"
        settings_repo = FakeSettingsRepo()
        _r1, settings1, audio1, playback1, _q1, coordinator1 = _build(
            db, settings_repo=settings_repo
        )
        coordinator1.start()
        playback1.set_muted(True)
        assert settings1.state.muted is True
        del coordinator1, playback1, audio1  # abrupt kill

        _r2, settings2, _a2, _p2, _q2, _c2 = _build(db, settings_repo=settings_repo)
        assert settings2.state.muted is True

    def test_volume_change_does_not_checkpoint_session_unnecessarily(self, tmp_path):
        db = tmp_path / "t6.db"
        repo, settings, audio, playback, queue, coordinator = _build(db)
        coordinator.start()
        before = _session_row(db)  # nothing checkpointed yet
        playback.set_volume(42)
        after = _session_row(db)
        # Volume persistence goes through SettingsState only — no full session
        # rewrite: the session row is untouched.
        assert after == before
        assert settings.state.volume == 42  # the runtime sync persisted it


class TestLifecycleFreeze:
    def test_shutdown_freezes_persistence_before_backend_events(self, tmp_path):
        db = tmp_path / "t7.db"
        repo, _settings, audio, playback, queue, coordinator = _build(db)
        coordinator.start()
        queue.add(_A, "A")
        queue.add(_B, "B")
        queue.play_index(1)
        audio.trigger_media_accepted(_B)
        playback.update_position(222000)
        coordinator.checkpoint()

        coordinator.shutdown()  # freeze FIRST: final checkpoint + unsubscribe
        # Backend teardown events AFTER shutdown must be ignored by the
        # frozen coordinator (playback.stop() -> STOPPED + position 0).
        playback.stop()

        snap = repo.load()
        assert snap.playback_path == "/m/b.flac"
        assert snap.position_ms == 222000  # the final durable checkpoint survived

    def test_coordinator_unsubscribes_on_shutdown(self, tmp_path):
        db = tmp_path / "t8.db"
        _repo, _settings, audio, playback, queue, coordinator = _build(db)
        coordinator.start()
        queue.add(_A, "A")
        baseline = _session_row(db)  # row exists (queue-driven checkpoint)
        coordinator.shutdown()
        frozen = _session_row(db)
        assert frozen == baseline  # shutdown's final save is content-identical

        # Post-shutdown mutations must NOT reach the session row.
        queue.add(_B, "B")  # queue.changed fired
        playback.update_position(6000)  # playback.changed fired
        assert _session_row(db) == frozen  # no new writes


class TestDurableMarkerSemantics:
    def test_failed_checkpoint_does_not_advance_durable_position_marker(self, tmp_path):
        db = tmp_path / "t9.db"
        stub = _FailOnDemandRepo(SqliteSessionRepository(db))
        settings = SettingsService(FakeSettingsRepo())
        audio = FakeAudioPort()
        playback = PlaybackService(audio)
        queue = QueueService(playback)
        coordinator = PersistenceCoordinator(stub, queue, playback, settings)
        coordinator.start()

        queue.add(_A, "A")
        queue.add(_B, "B")
        queue.play_index(1)
        audio.trigger_media_accepted(_B)
        playback.update_position(20000)  # durable marker: 20000
        stub.save_calls = 0  # drain notification-driven saves from the setup
        assert stub.load().position_ms == 20000

        stub.fail_saves = True
        playback.update_position(25000)  # delta 5000 from the durable 20000
        assert stub.save_calls == 1  # the checkpoint attempt happened
        assert stub.failed_saves == 1  # and it failed

        # delta >= 5000 is measured from the DURABLE marker: a failed save
        # must not advance it, so 27000 triggers a retry.
        playback.update_position(27000)
        assert stub.save_calls == 2  # the retry happened
        assert stub.failed_saves == 2
        assert stub.load().position_ms == 20000  # durable marker untouched

    def test_failed_checkpoint_does_not_crash_player(self, tmp_path):
        db = tmp_path / "t10.db"
        stub = _FailOnDemandRepo(SqliteSessionRepository(db))
        settings = SettingsService(FakeSettingsRepo())
        audio = FakeAudioPort()
        playback = PlaybackService(audio)
        queue = QueueService(playback)
        coordinator = PersistenceCoordinator(stub, queue, playback, settings)
        coordinator.start()

        queue.add(_A, "A")
        queue.add(_B, "B")
        queue.play_index(1)
        audio.trigger_media_accepted(_B)
        playback.update_position(20000)
        stub.save_calls = 0

        stub.fail_saves = True
        coordinator.checkpoint()  # explicit failing checkpoint: no raise
        assert stub.failed_saves == 1
        playback.update_position(25000)  # notification-driven failing attempt
        assert stub.failed_saves == 2
        queue.add(_C, "C")  # runtime keeps working
        assert queue.state.count == 3
        assert stub.failed_saves == 3  # queue-driven attempt also tolerated

        stub.fail_saves = False  # recovery: a later successful save works
        playback.update_position(27000)  # delta from durable 20000 -> saves
        assert stub.load().position_ms == 27000


class TestRestoreNotificationContract:
    def test_restore_emits_queue_change_but_persistence_suppresses_write(
        self, tmp_path
    ):
        db = tmp_path / "t11.db"
        _build_golden_state(db)

        repo2, _s2, _audio2, _p2, queue2, coordinator2 = _build(db)
        notifications = []
        queue2.subscribe_changed(lambda: notifications.append(1))  # other observer
        coordinator2.start()
        before = _session_row(db)
        coordinator2.restore()

        # The restore's queue notification is preserved for OTHER observers…
        assert notifications == [1]  # EXACTLY ONE notification
        # …but the coordinator wrote nothing during restore.
        assert _session_row(db) == before
        assert repo2.load().playback_path == "/m/b.flac"
        assert repo2.load().position_ms == 222000
