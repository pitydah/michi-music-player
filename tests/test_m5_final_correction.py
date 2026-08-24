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
- M5-LAST-GATE-2 (TestLastGate2): the restore window is TWO-PHASE and the
  durable snapshot during it is a HYBRID. Media acceptance alone does NOT
  release the restore authority — a backend position confirmation does
  (position 0 is a valid confirmation; the first post-acceptance position
  update confirms, clamped or not). During the window, the queue portion of
  every checkpoint reflects the LIVE runtime queue (user mutations are never
  lost) while the playback portion keeps the restored truth WHILE coherent;
  a broken coherence (e.g. removing the current) writes playback_path None
  and releases the authority. Rejection/supersession release it too. The
  resume completes through PlaybackService's public ``resume_prepared``
  event (TestResumePreparedEvent in tests/test_playback_service.py).

The lifecycle is expressed explicitly in every test: ``coordinator.start()``
after construction arms the persistence subscriptions, ``coordinator.shutdown()``
freezes them.
"""

import sqlite3
from pathlib import Path

from michi.application.coordinator import PlaybackCoordinator
from michi.application.persistence_coordinator import PersistenceCoordinator
from michi.application.playback_service import PlaybackService
from michi.application.playback_session_service import PlaybackSessionService
from michi.application.queue_service import QueueService
from michi.application.settings_service import SettingsService
from michi.domain.playback import PlaybackStatus
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
    queue = QueueService()

    session = PlaybackSessionService(playback, queue, shuffle_seed=shuffle_seed)
    coordinator = PersistenceCoordinator(repo, queue, session, playback, settings)
    return repo, settings, audio, playback, queue, session, coordinator


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


def _build_golden_state(
    db_path: Path,
    *,
    repeat_mode: RepeatMode = RepeatMode.ALL,
    shuffle_enabled: bool = True,
    position_ms: int = 222000,
    shuffle_seed: int = 424242,
) -> None:
    """First graph: build the B@222000 resume state via the real flow and
    checkpoint; destroy WITHOUT shutdown (abrupt restart must not depend on
    graceful stop).

    Keyword variants build a golden with a different repeat/shuffle/position
    profile for the M5-LAST-GATE-2 RED tests (repeat NONE, shuffle OFF,
    position 0, a clamped 999999). The shuffle seed always travels with the
    snapshot so a later shuffle enable reconstructs the same navigator.
    """
    repo, _settings, audio, playback, queue, session, coordinator = _build(
        db_path, shuffle_seed=shuffle_seed
    )
    coordinator.start()
    queue.add(_A, "A")
    queue.add(_B, "B")
    queue.add(_C, "C")
    session.play_queue_index(1)  # B pending
    audio.trigger_media_accepted(_B)  # B committed, current 1
    playback.update_position(position_ms)
    session.set_repeat_mode(repeat_mode)
    session.set_shuffle_enabled(shuffle_enabled)
    coordinator.checkpoint()
    del coordinator, queue, playback, audio, repo


class TestRestoringGuard:
    def test_restore_does_not_overwrite_resume_snapshot(self, tmp_path):
        db = tmp_path / "t1.db"
        _build_golden_state(db)

        # ── Session 2: fresh graph — restore must not degrade the snapshot ──
        repo2, _s2, audio2, _playback2, _queue2, session2, coordinator2 = _build(db)
        coordinator2.start()
        coordinator2.restore()

        # BEFORE any media acceptance, the durable resume snapshot is intact:
        # playback_path B, position 222000 — never null/0.
        snap = repo2.load()
        assert snap.playback_path == "/m/b.flac"
        assert snap.position_ms == 222000
        assert snap.context.current_index == 1
        assert snap.repeat_mode is RepeatMode.ALL
        assert snap.shuffle_enabled is True
        assert snap.shuffle_seed == 424242

    def test_second_restart_during_prepare_preserves_resume(
        self, tmp_path, monkeypatch
    ):
        db = tmp_path / "t2.db"
        _build_golden_state(db)

        # ── Session 2: restore but do NOT accept; destroy abruptly ──
        _r2, _s2, audio2, playback2, _q2, session2, coordinator2 = _build(db)
        coordinator2.start()
        coordinator2.restore()
        del coordinator2, playback2, audio2  # abrupt during the prepare window

        # ── Session 3: the durable resume is still B@222000, never B@0 ──
        _r3, _s3, audio3, playback3, _q3, session3, coordinator3 = _build(db)
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
        repo2, _s2, audio2, _playback2, _q2, session2, coordinator2 = _build(db)
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
        _r1, settings1, audio1, playback1, _q1, session1, coordinator1 = _build(
            db, settings_repo=settings_repo
        )
        coordinator1.start()
        # ONLY the public runtime setter — no settings.save, no shutdown.
        playback1.set_volume(37)
        assert settings1.state.volume == 37  # runtime sync is immediate
        del coordinator1, playback1, audio1  # abrupt kill

        # Fresh graph on the same store: the PERSISTED truth is volume 37
        # (the bootstrap applies it to the backend on startup — its concern).
        _r2, settings2, _a2, _p2, _q2, session2, _c2 = _build(
            db, settings_repo=settings_repo
        )
        assert settings2.state.volume == 37

    def test_mute_survives_abrupt_kill_without_manual_settings_save(self, tmp_path):
        db = tmp_path / "t5.db"
        settings_repo = FakeSettingsRepo()
        _r1, settings1, audio1, playback1, _q1, session1, coordinator1 = _build(
            db, settings_repo=settings_repo
        )
        coordinator1.start()
        playback1.set_muted(True)
        assert settings1.state.muted is True
        del coordinator1, playback1, audio1  # abrupt kill

        _r2, settings2, _a2, _p2, _q2, session2, _c2 = _build(
            db, settings_repo=settings_repo
        )
        assert settings2.state.muted is True

    def test_volume_change_does_not_checkpoint_session_unnecessarily(self, tmp_path):
        db = tmp_path / "t6.db"
        repo, settings, audio, playback, queue, session, coordinator = _build(db)
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
        repo, _settings, audio, playback, queue, session, coordinator = _build(db)
        coordinator.start()
        queue.add(_A, "A")
        queue.add(_B, "B")
        session.play_queue_index(1)
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
        _repo, _settings, audio, playback, queue, session, coordinator = _build(db)
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
        queue = QueueService()
        session = PlaybackSessionService(playback, queue)
        coordinator = PersistenceCoordinator(stub, queue, session, playback, settings)
        coordinator.start()

        queue.add(_A, "A")
        queue.add(_B, "B")
        session.play_queue_index(1)
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
        queue = QueueService()
        session = PlaybackSessionService(playback, queue)
        coordinator = PersistenceCoordinator(stub, queue, session, playback, settings)
        coordinator.start()

        queue.add(_A, "A")
        queue.add(_B, "B")
        session.play_queue_index(1)
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

        repo2, _s2, _audio2, _p2, queue2, session2, coordinator2 = _build(db)
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


class TestPendingResumeShutdown:
    """M5-LAST-GATE — WHILE the resume prepare is unresolved, the RESTORED
    playback truth is the last valid durable truth; runtime must not overwrite
    it with the incomplete Playback (still None@0); a second kill must not
    lose the position.

    M5-LAST-GATE-2 hybrid refinement: during the restore window the durable
    snapshot is a HYBRID. The PLAYBACK portion keeps the restored
    playback_path/position_ms while coherent (queue current identity ==
    restored path) — never the incomplete runtime None@0. The QUEUE portion
    reflects the LIVE runtime queue, so user mutations during startup are
    never lost (test 13 now persists queue.add(D) instead of suppressing it).
    A shutdown inside any phase keeps the restored truth (test 12); the
    durable authority returns to runtime only when the backend position
    confirms the resume (test 14).
    """

    def test_shutdown_during_prepare_preserves_restored_snapshot(
        self, tmp_path, monkeypatch
    ):
        db = tmp_path / "t12.db"
        _build_golden_state(db)

        # ── Session 2: restore; NO media acceptance — the prepare is still
        # pending — then a graceful shutdown ──
        _r2, _s2, audio2, _p2, _q2, session2, coordinator2 = _build(db)
        coordinator2.start()
        coordinator2.restore()
        coordinator2.shutdown()  # must SKIP the degraded final checkpoint
        del coordinator2, audio2

        # ── Session 3: the durable B@222000 survived the shutdown during the
        # pending window — the resume is requested again (never B@0/null) ──
        _r3, _s3, audio3, playback3, _q3, session3, coordinator3 = _build(db)
        coordinator3.start()
        prepare_calls = []
        orig_prepare = playback3.prepare_for_resume

        def spy_prepare(path, position_ms):
            prepare_calls.append((path, position_ms))
            orig_prepare(path, position_ms)

        monkeypatch.setattr(playback3, "prepare_for_resume", spy_prepare)
        coordinator3.restore()

        assert prepare_calls == [(_B, 222000)]

    def test_queue_change_during_pending_window_does_not_degrade_snapshot(
        self, tmp_path
    ):
        db = tmp_path / "t13.db"
        _build_golden_state(db)

        # ── Session 2: restore; the resume is still pending (WAITING_MEDIA) ──
        repo2, _s2, _a2, playback2, queue2, session2, coordinator2 = _build(db)
        coordinator2.start()
        coordinator2.restore()
        before = _session_row(db)

        # A queue mutation DURING the restore window is a USER mutation: the
        # hybrid contract persists the LIVE queue alongside the RESTORED
        # playback truth. The session row CHANGES to include D, but the
        # playback portion is still the restored "/m/b.flac"@222000 — the
        # incomplete runtime Playback (None@0) never leaks into it.
        queue2.add(Path("/m/d.flac"), "D")
        after_row = _session_row(db)
        assert after_row != before  # the row CHANGES (hybrid persists the add)
        assert '"/m/d.flac"' in after_row  # D is durable
        hybrid = repo2.load()
        assert hybrid.playback_path == "/m/b.flac"
        assert hybrid.position_ms == 222000  # never B@0 / null
        assert [e.file_path for e in hybrid.queue_entries] == [
            "/m/a.flac",
            "/m/b.flac",
            "/m/c.flac",
            "/m/d.flac",
        ]

        # The restore completes in TWO phases: the media acceptance moves the
        # window to WAITING_POSITION (still no checkpoint), and the backend
        # position update CONFIRMS the resume — the durable authority returns
        # to runtime; a subsequent legit change checkpoints the NEW runtime
        # truth (B@230000 with the live queue preserved).
        _a2.trigger_media_accepted(_B)
        playback2.update_position(230000)
        resolved = repo2.load()
        assert resolved.playback_path == "/m/b.flac"
        assert resolved.position_ms == 230000  # durable authority is runtime again
        assert [e.file_path for e in resolved.queue_entries] == [
            "/m/a.flac",
            "/m/b.flac",
            "/m/c.flac",
            "/m/d.flac",
        ]

    def test_shutdown_during_pending_then_resume_resolves(self, tmp_path):
        db = tmp_path / "t14.db"
        _build_golden_state(db)

        # ── Session 2: restore (pending) + shutdown — the final checkpoint
        # must be skipped so the durable B@222000 survives ──
        _r2, _s2, _a2, _p2, _q2, session2, coordinator2 = _build(db)
        coordinator2.start()
        coordinator2.restore()
        coordinator2.shutdown()
        del coordinator2

        # ── Session 3: resume resolves normally — prepare, accept (STOPPED +
        # seek to the persisted position), then a legit checkpoint persists
        # the NEW runtime truth ──
        repo3, _s3, audio3, playback3, _q3, session3, coordinator3 = _build(db)
        coordinator3.start()
        coordinator3.restore()
        audio3.trigger_media_accepted(_B)

        # The prepare committed and sought; status stayed STOPPED (no autoplay).
        assert playback3.state.status is PlaybackStatus.STOPPED
        assert playback3.state.file_path == _B
        assert audio3.seek_calls == [222000]

        # The pending window closed with the acceptance: a legit position
        # change now checkpoints the runtime truth (B@240000, not B@222000).
        playback3.update_position(240000)
        snap = repo3.load()
        assert snap.playback_path == "/m/b.flac"
        assert snap.position_ms == 240000


class TestLastGate2:
    """M5-LAST-GATE-2 — TWO-PHASE resume + HYBRID snapshot during the window.

    The restore authority is released ONLY by a backend position
    confirmation, never by media acceptance alone. Explicit phases:
    WAITING_MEDIA (file_path not confirmed) -> media accepted ->
    WAITING_POSITION (file_path committed, position not confirmed) ->
    backend position update -> NONE (runtime authoritative). Position 0 is
    a valid confirmation (never position>0 as the signal); the FIRST
    post-acceptance position update confirms, whatever its value (backend
    clamp tolerated).

    While any phase is open, every checkpoint is a HYBRID: the queue portion
    is the LIVE runtime QueueState (user mutations during startup are never
    lost), the playback portion is the restored snapshot's
    playback_path/position_ms WHILE coherent (current_index valid AND
    queue[current_index].file_path == restored playback_path). A broken
    coherence (e.g. removing the current) writes playback_path None /
    position 0 and releases the authority. Rejection/supersession release it
    too — the restored truth is never retained indefinitely; the next
    checkpoint is a coherent session.
    """

    # ── 1: WAITING_POSITION shutdown preserves the restored position ──────
    def test_shutdown_after_accept_before_position_confirm_preserves_position(
        self, tmp_path, monkeypatch
    ):
        db = tmp_path / "t15.db"
        _build_golden_state(db)

        # ── Session 2: restore; media accepted (WAITING_POSITION — file_path
        # committed, position NOT confirmed); then a graceful shutdown. The
        # position confirmation never arrived, so the restored truth is the
        # durable authority: B@222000, NEVER the runtime's B@0. ──
        _r2, _s2, audio2, playback2, _q2, session2, coordinator2 = _build(db)
        coordinator2.start()
        coordinator2.restore()
        audio2.trigger_media_accepted(_B)  # WAITING_MEDIA -> WAITING_POSITION
        coordinator2.shutdown()
        del coordinator2, audio2, playback2

        # ── Session 3: the durable B@222000 survived — never B@0 ──
        _r3, _s3, _a3, playback3, _q3, session3, coordinator3 = _build(db)
        coordinator3.start()
        prepare_calls = []
        orig_prepare = playback3.prepare_for_resume

        def spy_prepare(path, position_ms):
            prepare_calls.append((path, position_ms))
            orig_prepare(path, position_ms)

        monkeypatch.setattr(playback3, "prepare_for_resume", spy_prepare)
        coordinator3.restore()

        assert prepare_calls == [(_B, 222000)]

    # ── 2: queue.add during the window survives an abrupt kill ────────────
    def test_queue_add_during_restore_survives_abrupt_kill(self, tmp_path, monkeypatch):
        db = tmp_path / "t16.db"
        _build_golden_state(db)

        # ── Session 2: restore (pending); a user queue.add DURING the window.
        # M4-R1 production topology: the Session is STARTED (it owns the one
        # Queue→Session delivery) so the live Queue mutation re-projects the
        # Session BEFORE persistence checkpoints — the hybrid snapshot then
        # carries a STRICTLY coherent context (A,B,C,D). Destroy abruptly. ──
        _r2, _s2, _a2, _p2, queue2, session2, coordinator2 = _build(db)
        session2.start()  # M4-R1 final seal: session live-sync armed
        coordinator2.start()
        coordinator2.restore()
        queue2.add(Path("/m/d.flac"), "D")
        del coordinator2, queue2  # abrupt kill during the window

        # ── Session 3: the hybrid survived — queue A,B,C,D; current still B
        # (index 1); the restore is requested at the restored position. ──
        _r3, _s3, _a3, playback3, queue3, session3, coordinator3 = _build(db)
        coordinator3.start()
        prepare_calls = []
        orig_prepare = playback3.prepare_for_resume

        def spy_prepare(path, position_ms):
            prepare_calls.append((path, position_ms))
            orig_prepare(path, position_ms)

        monkeypatch.setattr(playback3, "prepare_for_resume", spy_prepare)
        coordinator3.restore()

        assert [t.file_path for t in queue3.state.tracks] == [
            _A,
            _B,
            _C,
            Path("/m/d.flac"),
        ]
        assert session3.state.current_index == 1
        assert prepare_calls == [(_B, 222000)]

    # ── 3: queue.move during the window preserves current + position ──────
    def test_queue_move_during_restore_preserves_current_and_position(
        self, tmp_path, monkeypatch
    ):
        db = tmp_path / "t17.db"
        _build_golden_state(db)

        # ── Session 2: restore (pending); move B (index 1) to index 2 ->
        # [A,C,B] with the committed current identity (B) following to index
        # 2; kill abruptly. ──
        _r2, _s2, _a2, _p2, queue2, session2, coordinator2 = _build(db)
        session2.start()  # M4-R1 final seal: session live-sync armed
        coordinator2.start()
        coordinator2.restore()
        queue2.move(1, 2)
        assert [t.file_path for t in queue2.state.tracks] == [_A, _C, _B]
        assert session2.state.current_index == 2
        del coordinator2, queue2  # abrupt kill during the window

        # ── Session 3: order A,C,B with current B at index 2 and the restored
        # position intact — coherence (queue[2] == B) keeps the resume. ──
        _r3, _s3, _a3, playback3, queue3, session3, coordinator3 = _build(db)
        coordinator3.start()
        prepare_calls = []
        orig_prepare = playback3.prepare_for_resume

        def spy_prepare(path, position_ms):
            prepare_calls.append((path, position_ms))
            orig_prepare(path, position_ms)

        monkeypatch.setattr(playback3, "prepare_for_resume", spy_prepare)
        coordinator3.restore()

        assert [t.file_path for t in queue3.state.tracks] == [_A, _C, _B]
        assert session3.state.current_index == 2
        assert prepare_calls == [(_B, 222000)]

    # ── 4: removing the restored current clears the resume truth ──────────
    def test_remove_restored_current_clears_resume_truth(self, tmp_path, monkeypatch):
        db = tmp_path / "t18.db"
        _build_golden_state(db)

        # ── Session 2: restore (pending); the user REMOVES the restored
        # current (B). The queue drops to A,C with current -1 (no fictitious
        # identity) and the pending resume is superseded/cancelled through the
        # queue/playback public machinery; kill abruptly. ──
        _r2, _s2, _a2, _p2, queue2, session2, coordinator2 = _build(db)
        session2.start()  # M4-R1 final seal: session live-sync armed
        coordinator2.start()
        coordinator2.restore()
        queue2.remove(1)  # removes the restored current B
        assert [t.file_path for t in queue2.state.tracks] == [_A, _C]
        # M4-R1 §27: session converges to SINGLE for the accepted path
        # (playback continues; Queue no longer owns the current identity).
        assert session2.state.context_type.name == "SINGLE"
        assert session2.state.current_entry.file_path == _B
        del coordinator2, queue2  # abrupt kill during the window

        # ── Session 3: NO fabricated resume — no prepare is requested at all;
        # the queue restores as A,C with no current; no autoplay. ──
        _r3, _s3, _a3, playback3, queue3, session3, coordinator3 = _build(db)
        coordinator3.start()
        prepare_calls = []
        orig_prepare = playback3.prepare_for_resume

        def spy_prepare(path, position_ms):
            prepare_calls.append((path, position_ms))
            orig_prepare(path, position_ms)

        monkeypatch.setattr(playback3, "prepare_for_resume", spy_prepare)
        coordinator3.restore()

        assert [t.file_path for t in queue3.state.tracks] == [_A, _C]
        # M4-R1: the persisted session is the SINGLE/B convergence (no
        # fabricated Queue current) — restored logically; the resume is
        # COHERENT with the session current (B), never fabricated from a
        # deleted Queue identity.
        assert session3.state.context_type.name == "SINGLE"
        assert session3.state.current_entry.file_path == _B
        assert prepare_calls == [(_B, 222000)]  # coherent session resume
        assert playback3.state.file_path is None  # committed only on acceptance

    # ── 5: repeat change during the window is durable ─────────────────────
    def test_repeat_change_during_restore_is_durable(self, tmp_path, monkeypatch):
        db = tmp_path / "t19.db"
        _build_golden_state(db, repeat_mode=RepeatMode.NONE)

        # ── Session 2: restore (pending); repeat -> ALL DURING the window;
        # kill abruptly. ──
        _r2, _s2, _a2, _p2, queue2, session2, coordinator2 = _build(db)
        coordinator2.start()
        coordinator2.restore()
        session2.set_repeat_mode(RepeatMode.ALL)
        del coordinator2, queue2  # abrupt kill during the window

        # ── Session 3: the repeat change survived — repeat ALL AND the
        # restored position intact. ──
        _r3, _s3, _a3, playback3, queue3, session3, coordinator3 = _build(db)
        coordinator3.start()
        prepare_calls = []
        orig_prepare = playback3.prepare_for_resume

        def spy_prepare(path, position_ms):
            prepare_calls.append((path, position_ms))
            orig_prepare(path, position_ms)

        monkeypatch.setattr(playback3, "prepare_for_resume", spy_prepare)
        coordinator3.restore()

        assert session3.state.repeat_mode is RepeatMode.ALL
        assert prepare_calls == [(_B, 222000)]

    # ── 6: shuffle change during the window is durable ────────────────────
    def test_shuffle_change_during_restore_is_durable(self, tmp_path, monkeypatch):
        db = tmp_path / "t20.db"
        _build_golden_state(db, shuffle_enabled=False)  # seed 424242 travels

        # ── Session 2: restore (pending); shuffle ON during the window (the
        # restored RNG, seeded 424242, drives the navigator reset); kill. ──
        _r2, _s2, _a2, _p2, queue2, session2, coordinator2 = _build(db)
        coordinator2.start()
        coordinator2.restore()
        session2.set_shuffle_enabled(True)
        del coordinator2, queue2  # abrupt kill during the window

        # ── Session 3: shuffle True + seed 424242 AND the restored position
        # intact. ──
        _r3, _s3, _a3, playback3, queue3, session3, coordinator3 = _build(db)
        coordinator3.start()
        prepare_calls = []
        orig_prepare = playback3.prepare_for_resume

        def spy_prepare(path, position_ms):
            prepare_calls.append((path, position_ms))
            orig_prepare(path, position_ms)

        monkeypatch.setattr(playback3, "prepare_for_resume", spy_prepare)
        coordinator3.restore()

        assert session3.state.shuffle_enabled is True
        assert session3.shuffle_seed == 424242
        assert prepare_calls == [(_B, 222000)]

    # ── 7: position 0 is a valid confirmation ─────────────────────────────
    def test_zero_position_resume_can_complete(self, tmp_path, monkeypatch):
        db = tmp_path / "t21.db"
        _build_golden_state(db, position_ms=0)

        # ── Session 2: restore (pending); media accepted -> WAITING_POSITION;
        # update_position(0) CONFIRMS the resume — position 0 is a valid
        # confirmation (never position>0 as the signal); shutdown then writes
        # the runtime truth (B@0): the restore COMPLETED, not eternally
        # pending. ──
        repo2, _s2, audio2, playback2, _q2, session2, coordinator2 = _build(db)
        coordinator2.start()
        coordinator2.restore()
        audio2.trigger_media_accepted(_B)
        playback2.update_position(0)  # position 0 CONFIRMED
        coordinator2.shutdown()

        snap = repo2.load()
        assert snap.playback_path == "/m/b.flac"
        assert snap.position_ms == 0

        # ── Session 3: the completed zero-position restore is durable —
        # prepare(B, 0). ──
        _r3, _s3, _a3, playback3, _q3, session3, coordinator3 = _build(db)
        coordinator3.start()
        prepare_calls = []
        orig_prepare = playback3.prepare_for_resume

        def spy_prepare(path, position_ms):
            prepare_calls.append((path, position_ms))
            orig_prepare(path, position_ms)

        monkeypatch.setattr(playback3, "prepare_for_resume", spy_prepare)
        coordinator3.restore()

        assert prepare_calls == [(_B, 0)]

    # ── 8: the first post-acceptance position update confirms (clamp) ─────
    def test_clamped_position_confirmation_releases_restore_authority(
        self, tmp_path, monkeypatch
    ):
        db = tmp_path / "t22.db"
        _build_golden_state(db, position_ms=999999)

        # ── Session 2: restore (pending); accept B (WAITING_POSITION); the
        # backend CLAMPS the seek to 300000 — the FIRST post-acceptance
        # position update confirms, whatever its value; shutdown persists the
        # confirmed clamp as the durable truth. ──
        _r2, _s2, audio2, playback2, _q2, session2, coordinator2 = _build(db)
        coordinator2.start()
        coordinator2.restore()
        audio2.trigger_media_accepted(_B)
        playback2.update_position(300000)  # backend clamp -> confirmation
        coordinator2.shutdown()

        # ── Session 3: prepare(B, 300000) — the clamp became the durable
        # truth, NOT the golden 999999. ──
        _r3, _s3, _a3, playback3, _q3, session3, coordinator3 = _build(db)
        coordinator3.start()
        prepare_calls = []
        orig_prepare = playback3.prepare_for_resume

        def spy_prepare(path, position_ms):
            prepare_calls.append((path, position_ms))
            orig_prepare(path, position_ms)

        monkeypatch.setattr(playback3, "prepare_for_resume", spy_prepare)
        coordinator3.restore()

        assert prepare_calls == [(_B, 300000)]

    # ── 9: rejection releases the restore authority ───────────────────────
    def test_rejection_releases_restore_authority(self, tmp_path, monkeypatch):
        db = tmp_path / "t23.db"
        _build_golden_state(db)

        # ── Session 2: restore (pending); the resume is REJECTED by the
        # backend -> the restore authority is released (phase NONE); the NEXT
        # legitimate checkpoint writes a COHERENT session: queue restored,
        # playback_path None (no fabricated B), STOPPED. ──
        _r2, _s2, audio2, _p2, queue2, session2, coordinator2 = _build(db)
        session2.start()  # M4-R1 final seal: session live-sync armed
        coordinator2.start()
        coordinator2.restore()
        audio2.trigger_media_rejected(_B, "gone")
        queue2.add(Path("/m/d.flac"), "D")  # legit checkpoint after release
        coordinator2.shutdown()

        snap = _r2.load()
        assert snap.playback_path is None  # no fabricated B
        assert snap.position_ms == 0
        assert snap.context.current_index == 1
        assert [e.file_path for e in snap.queue_entries] == [
            "/m/a.flac",
            "/m/b.flac",
            "/m/c.flac",
            "/m/d.flac",
        ]

        # ── Session 3: queue restored; NO resume requested — the rejected
        # truth is never retained indefinitely. ──
        _r3, _s3, _a3, playback3, queue3, session3, coordinator3 = _build(db)
        coordinator3.start()
        prepare_calls = []
        orig_prepare = playback3.prepare_for_resume

        def spy_prepare(path, position_ms):
            prepare_calls.append((path, position_ms))
            orig_prepare(path, position_ms)

        monkeypatch.setattr(playback3, "prepare_for_resume", spy_prepare)
        coordinator3.restore()

        assert [t.file_path for t in queue3.state.tracks] == [
            _A,
            _B,
            _C,
            Path("/m/d.flac"),
        ]
        assert session3.state.current_index == 1
        assert prepare_calls == []

    # ── 10: supersession releases the OLD restore authority ───────────────
    def test_supersession_releases_old_restore_authority(self, tmp_path, monkeypatch):
        db = tmp_path / "t24.db"
        _build_golden_state(db)

        # ── Session 2: restore (prepare B pending); the user selects C via
        # the queue — C's request supersedes B's prepare; a LATE B acceptance
        # is dropped by the identity guards (never restores authority); C's
        # acceptance commits C at index 2 (the queue current); shutdown
        # persists the C session. ──
        _r2, _s2, audio2, playback2, queue2, session2, coordinator2 = _build(db)
        coordinator2.start()
        coordinator2.restore()
        session2.play_queue_index(2)  # user selects C; C supersedes B's prepare
        audio2.trigger_media_accepted(_B)  # LATE stale B acceptance: ignored
        audio2.trigger_media_accepted(_C)  # C commits -> queue current 2
        coordinator2.shutdown()

        snap = _r2.load()
        assert snap.context.current_index == 2
        assert snap.playback_path == "/m/c.flac"
        assert snap.position_ms == 0  # C's runtime position (no seek/update)

        # ── Session 3: the C session is durable — prepare(C, 0); NEVER a
        # prepare for the superseded B. ──
        _r3, _s3, _a3, playback3, _q3, session3, coordinator3 = _build(db)
        coordinator3.start()
        prepare_calls = []
        orig_prepare = playback3.prepare_for_resume

        def spy_prepare(path, position_ms):
            prepare_calls.append((path, position_ms))
            orig_prepare(path, position_ms)

        monkeypatch.setattr(playback3, "prepare_for_resume", spy_prepare)
        coordinator3.restore()

        assert prepare_calls == [(_C, 0)]


class TestProductionLifecycle:
    """M5-PRODUCTION-LIFECYCLE-GATE — CANONICAL LIFECYCLE (§7, §29-B/C).

    Bootstrap's canonical order is construct -> start() -> restore() — the
    subscriptions (queue/playback/resume_prepared) are armed BEFORE the
    restore, so a FAST backend's resume_prepared is never lost. restore()
    runs UNDER _restoring (its queue.changed/playback.changed notifications
    never checkpoint a degraded snapshot); _on_resume_prepared processes
    whenever started — even during _restoring, it is the completion signal:
    the state IS complete at that point and must never be dropped by an
    ``if _restoring: return`` guard.
    """

    def _wire_audio_path(self, audio, queue, playback):
        """(playback param kept for call-site compatibility; the coordinator
        only needs the audio port + playback service.)"""
        _ = (queue, playback)
        """Production position wiring: PlaybackCoordinator forwards the
        backend position channel into PlaybackService.update_position."""
        coordinator = PlaybackCoordinator(audio, playback)
        coordinator.start()
        return coordinator

    # ── 1: start-then-restore receives the resume confirmation (§7) ──────
    def test_production_lifecycle_start_then_restore_receives_resume_confirmation(
        self, tmp_path
    ):
        db = tmp_path / "t25.db"
        _build_golden_state(db)

        # ── Session 2 EXACTLY the bootstrap order: construct -> start() ->
        # restore() (production lifecycle: start() then restore()). The
        # PlaybackCoordinator audio position path is started first, matching
        # the composition root. ──
        repo2, _s2, audio2, playback2, queue2, session2, coordinator2 = _build(db)
        self._wire_audio_path(audio2, queue2, playback2)
        coordinator2.start()
        coordinator2.restore()

        # Backend: acceptance + positionChanged through the AUDIO path (the
        # fake's position trigger -> PlaybackCoordinator -> update_position —
        # never a direct service call).
        audio2.trigger_media_accepted(_B)
        audio2.trigger_position(222000)

        # Restore authority ended: the confirmation made B@222000 durable;
        # status STOPPED, no autoplay.
        snap = repo2.load()
        assert snap.playback_path == "/m/b.flac"
        assert snap.position_ms == 222000
        assert playback2.state.status is PlaybackStatus.STOPPED
        assert audio2.state != "playing"

        # A later runtime position persists normally: the durable row advances.
        playback2.update_position(230000)
        assert repo2.load().position_ms == 230000

    # ── 2: restore's own notifications never self-checkpoint (§29-B) ─────
    def test_restore_notification_does_not_self_checkpoint(self, tmp_path):
        db = tmp_path / "t26.db"
        _build_golden_state(db)

        repo2, _s2, _a2, _p2, _q2, session2, coordinator2 = _build(db)
        coordinator2.start()  # production lifecycle: start() then restore()
        before = repo2.load()
        coordinator2.restore()
        after = repo2.load()

        # The queue.changed/playback.changed notifications fired by
        # restore_session/prepare_for_resume DURING restore() must not write a
        # degraded snapshot: the durable resume truth is identical before and
        # after the restore (before any backend confirmation).
        assert after == before
        assert after.playback_path == "/m/b.flac"
        assert after.position_ms == 222000

    # ── 3: a FAST backend's event is received inside the restore (§29-C) ──
    def test_resume_prepared_received_with_production_order(
        self, tmp_path, monkeypatch
    ):
        db = tmp_path / "t27.db"
        _build_golden_state(db)

        repo2, _s2, audio2, playback2, queue2, session2, coordinator2 = _build(db)
        self._wire_audio_path(audio2, queue2, playback2)
        coordinator2.start()  # production lifecycle: start() then restore()

        # The fake backend is FAST: acceptance + position confirmation fire
        # synchronously INSIDE the restore call (spy-wrapped prepare). With
        # start-then-restore ordering the resume_prepared subscription is
        # armed BEFORE the restore, so the event is received — not lost.
        orig_prepare = playback2.prepare_for_resume
        events = []
        playback2.subscribe_resume_prepared(lambda p, pos: events.append((p, pos)))

        def fast_prepare(path, position_ms):
            orig_prepare(path, position_ms)
            audio2.trigger_media_accepted(path)
            audio2.trigger_position(position_ms)

        monkeypatch.setattr(playback2, "prepare_for_resume", fast_prepare)
        coordinator2.restore()

        # The confirmation was received INSIDE the restore window: phase
        # released, durable truth B@222000, no eternal WAITING_POSITION.
        assert events == [(_B, 222000)]
        assert audio2.seek_calls == [222000]
        snap = repo2.load()
        assert snap.playback_path == "/m/b.flac"
        assert snap.position_ms == 222000
        assert playback2.state.status is PlaybackStatus.STOPPED

        # The release is real: a later runtime position persists normally.
        playback2.update_position(230000)
        assert repo2.load().position_ms == 230000


class TestZeroPositionAudioPath:
    """M5-PRODUCTION-LIFECYCLE-GATE — ZERO POSITION via the audio path
    (§29-G/H, §16).

    The resume confirmation must not depend on a positionChanged that Qt may
    not emit when the effective position already equals the requested value
    (e.g. seek to 0 from 0): after a non-reentrant seek() returns, if the
    backend position ALREADY equals the requested value, resume_prepared
    fires with that backend-reported position (audio.position() — never
    fabricated). The latch prevents double-fire. A clamped position is
    equally confirmed by the first post-acceptance position update through
    the audio channel.
    """

    def _wire_audio_path(self, audio, queue, playback):
        """(playback param kept for call-site compatibility; the coordinator
        only needs the audio port + playback service.)"""
        _ = (queue, playback)
        coordinator = PlaybackCoordinator(audio, playback)
        coordinator.start()
        return coordinator

    # ── 1: position 0 confirmed via the backend-reported position (§29-G) ─
    def test_zero_position_through_audio_event_path(self, tmp_path, monkeypatch):
        db = tmp_path / "t28.db"
        _build_golden_state(db, position_ms=0)

        repo2, _s2, audio2, playback2, queue2, session2, coordinator2 = _build(db)
        self._wire_audio_path(audio2, queue2, playback2)
        coordinator2.start()  # production lifecycle: start() then restore()
        prepare_calls = []
        orig_prepare = playback2.prepare_for_resume

        def spy_prepare(path, position_ms):
            prepare_calls.append((path, position_ms))
            orig_prepare(path, position_ms)

        monkeypatch.setattr(playback2, "prepare_for_resume", spy_prepare)
        events = []
        playback2.subscribe_resume_prepared(lambda p, pos: events.append((p, pos)))
        coordinator2.restore()
        assert prepare_calls == [(_B, 0)]

        # The backend accepts and seeks to 0 — but does NOT emit
        # positionChanged (Qt skips the signal when the effective position
        # already equals the requested value). The confirmation must come
        # from the backend-REPORTED position (audio.position()) after the
        # seek returns — never from a fabricated signal, never an eternal
        # WAITING_POSITION.
        audio2.trigger_media_accepted(_B)
        assert events == [(_B, 0)]  # RED: no post-seek check -> never fires
        # The event carried the backend-reported position — never fabricated.
        assert events[0][1] == audio2.position()

        # Durable truth B@0: position 0 IS the truth; restore completed.
        snap = repo2.load()
        assert snap.playback_path == "/m/b.flac"
        assert snap.position_ms == 0

        # The restore authority ended: a later runtime position tick through
        # the AUDIO path persists the new runtime truth.
        audio2.trigger_position(6000)
        assert repo2.load().position_ms == 6000

    # ── 2: a clamped position is still confirmed (§29-H) ─────────────────
    def test_clamped_position_still_confirmed(self, tmp_path, monkeypatch):
        db = tmp_path / "t29.db"
        _build_golden_state(db, position_ms=999999)

        repo2, _s2, audio2, playback2, queue2, session2, coordinator2 = _build(db)
        self._wire_audio_path(audio2, queue2, playback2)
        coordinator2.start()  # production lifecycle: start() then restore()
        prepare_calls = []
        orig_prepare = playback2.prepare_for_resume

        def spy_prepare(path, position_ms):
            prepare_calls.append((path, position_ms))
            orig_prepare(path, position_ms)

        monkeypatch.setattr(playback2, "prepare_for_resume", spy_prepare)
        coordinator2.restore()
        assert prepare_calls == [(_B, 999999)]

        # The backend CLAMPS: it reports 300000 through the audio position
        # channel. The first post-acceptance position update confirms,
        # whatever its value; the release makes the confirmed clamp the
        # durable truth.
        audio2.trigger_media_accepted(_B)
        audio2.trigger_position(300000)
        snap = repo2.load()
        assert snap.playback_path == "/m/b.flac"
        assert snap.position_ms == 300000
        assert playback2.state.status is PlaybackStatus.STOPPED


class TestRemoveCurrentPostRestore:
    """M5-PRODUCTION-LIFECYCLE-GATE — REMOVE-CURRENT RESURRECTION (§20,
    §21, §29-J/K).

    After the restore authority is released due to a queue coherence break
    (removing the restored current), subsequent checkpoints must NOT
    resurrect the old playback_path from PlaybackService's RETAINED file_path
    (M4 semantics keep file_path == B after stop()). The durable playback
    truth stays None@0 until a NEW coherent runtime identity (queue current
    valid AND matching playback.file_path) appears.
    """

    def test_remove_current_waiting_position_shutdown_persists_none(
        self, tmp_path, monkeypatch
    ):
        db = tmp_path / "t30.db"
        _build_golden_state(db)

        # ── Session 2: restore (WAITING_MEDIA); accept B (WAITING_POSITION,
        # no position confirmation); the user REMOVES the restored current B
        # -> current -1; the coordinator's coherence-break release runs
        # (public playback.stop()); shutdown persists the durable truth
        # None@0 — never the retained B. ──
        repo2, _s2, audio2, playback2, queue2, session2, coordinator2 = _build(db)
        session2.start()  # M4-R1 final seal: session live-sync armed
        coordinator2.start()  # production lifecycle: start() then restore()
        coordinator2.restore()
        audio2.trigger_media_accepted(_B)  # WAITING_MEDIA -> WAITING_POSITION
        queue2.remove(1)  # B removed -> Queue current gone; session SINGLE/B
        assert [t.file_path for t in queue2.state.tracks] == [_A, _C]
        # M4-R1 §27: the accepted path converges to SINGLE (playback never
        # fabricates a Queue current).
        assert session2.state.context_type.name == "SINGLE"
        assert session2.state.current_entry.file_path == _B
        coordinator2.shutdown()

        snap2 = repo2.load()
        assert snap2.context.context_type == "single"
        assert snap2.context.current_index == 0
        assert [e.file_path for e in snap2.queue_entries] == [
            "/m/a.flac",
            "/m/c.flac",
        ]
        assert [e.file_path for e in snap2.queue_entries] == [
            "/m/a.flac",
            "/m/c.flac",
        ]

        # ── Session 3: queue restored as A,C / current -1; NO fabricated
        # resume (the durable playback truth is None@0, never B@0). ──
        repo3, _s3, _a3, playback3, queue3, session3, coordinator3 = _build(db)
        coordinator3.start()
        prepare_calls = []
        orig_prepare = playback3.prepare_for_resume

        def spy_prepare(path, position_ms):
            prepare_calls.append((path, position_ms))
            orig_prepare(path, position_ms)

        monkeypatch.setattr(playback3, "prepare_for_resume", spy_prepare)
        coordinator3.restore()

        assert [t.file_path for t in queue3.state.tracks] == [_A, _C]
        # M4-R1: the persisted session is the SINGLE/B convergence (no
        # fabricated Queue current) — restored logically; the resume is
        # COHERENT with the session current (B), never fabricated from a
        # deleted Queue identity.
        assert session3.state.context_type.name == "SINGLE"
        assert session3.state.current_entry.file_path == _B
        assert prepare_calls == [(_B, 222000)]  # coherent session resume
        assert playback3.state.file_path is None  # committed only on acceptance
        snap3 = repo3.load()
        # M4-R1: the durable truth is the SINGLE/B session — coherent, never
        # a resurrected Queue identity.
        assert snap3.context.context_type == "single"
        assert snap3.playback_path == "/m/b.flac"

    def test_remove_current_then_second_checkpoint_does_not_resurrect_old_path(
        self, tmp_path, monkeypatch
    ):
        db = tmp_path / "t31.db"
        _build_golden_state(db)

        # ── Session 2: restore + accept (WAITING_POSITION); the user REMOVES
        # the restored current B -> the coherence break releases the authority
        # (public playback.stop()); even though playback.state.file_path is
        # STILL B after stop() (M4 semantics), a LATER legitimate checkpoint
        # must NOT resurrect it: the durable truth stays None@0 until a NEW
        # coherent runtime identity appears. ──
        repo2, _s2, audio2, playback2, queue2, session2, coordinator2 = _build(db)
        session2.start()  # M4-R1 final seal: session live-sync armed
        coordinator2.start()  # production lifecycle: start() then restore()
        coordinator2.restore()
        audio2.trigger_media_accepted(_B)  # WAITING_MEDIA -> WAITING_POSITION
        queue2.remove(1)  # B removed -> Queue current gone; session SINGLE/B
        assert [t.file_path for t in queue2.state.tracks] == [_A, _C]
        assert session2.state.context_type.name == "SINGLE"
        assert session2.state.current_entry.file_path == _B
        assert playback2.state.file_path == _B  # M4: stop() retains file_path

        queue2.add(Path("/m/d.flac"), "D")  # another legitimate checkpoint
        coordinator2.shutdown()

        snap2 = repo2.load()
        assert snap2.context.context_type == "single"  # session truth persists
        # the coherent SINGLE/B session keeps its position truth (never a
        # resurrected Queue identity)
        assert snap2.position_ms == 222000
        assert snap2.context.current_index == 0
        assert [e.file_path for e in snap2.queue_entries] == [
            "/m/a.flac",
            "/m/c.flac",
            "/m/d.flac",
        ]

        # ── Session 3: NO prepare — the old path never returns. ──
        repo3, _s3, _a3, playback3, queue3, session3, coordinator3 = _build(db)
        coordinator3.start()
        prepare_calls = []
        orig_prepare = playback3.prepare_for_resume

        def spy_prepare(path, position_ms):
            prepare_calls.append((path, position_ms))
            orig_prepare(path, position_ms)

        monkeypatch.setattr(playback3, "prepare_for_resume", spy_prepare)
        coordinator3.restore()

        assert [t.file_path for t in queue3.state.tracks] == [
            _A,
            _C,
            Path("/m/d.flac"),
        ]
        # M4-R1: the durable truth is the SINGLE/B session (coherent resume).
        assert session3.state.context_type.name == "SINGLE"
        assert session3.state.current_entry.file_path == _B
        assert prepare_calls == [(_B, 222000)]
        snap3 = repo3.load()
        assert snap3.context.context_type == "single"
        assert snap3.playback_path == "/m/b.flac"


class TestTerminalRestoreReconciliation:
    """M5-FINAL-TERMINAL-RECONCILIATION — POST-RESTORE TERMINAL RESOLUTION.

    The _restoring guard suppresses playback notifications during restore(),
    but a FAST backend can surface a TERMINAL outcome synchronously INSIDE
    the restore call (rejection, seek failure) — or the confirmation itself
    (fast clamp). The terminal events' notifications are consumed by the
    guard, so restore() must reconcile AFTER the _restoring zone closes:

    - POST-RESTORE TERMINAL RECONCILIATION: after restore() finishes, if the
      resume phase is STILL active AND PlaybackService already surfaced a
      terminal error (error_message is not None — a fast rejection or a fast
      seek failure consumed inside restore), the coordinator MUST release the
      resume authority and persist a coherent checkpoint — the state machine
      must never stay open forever (no eternal WAITING_MEDIA/WAITING_POSITION).
      A rejection inside restore -> the coherent post-rejection session
      (playback_path None / position 0 — no fabricated B) and the NEXT restore
      never prepares (test 1). A seek failure inside restore -> the honest
      runtime truth B@0 (the media WAS accepted, the seek never applied),
      never the hybrid B@222000, and the NEXT restore resumes from 0
      (test 2). No resume_prepared ever fires on the seek-failure path.
    - DURABLE MARKER: restore()'s tail must NOT overwrite
      ``_last_persisted_position_ms`` with the stale snapshot position when
      the resume was already confirmed during restore (fast clamp inside the
      restore window: confirmed 300000 vs snapshot 999999 — the CONFIRMED
      value wins as the throttle baseline, test 3).
    """

    def _wire_audio_path(self, audio, queue, playback):
        """(playback param kept for call-site compatibility; the coordinator
        only needs the audio port + playback service.)"""
        _ = (queue, playback)
        """Production position wiring: PlaybackCoordinator forwards the
        backend position channel into PlaybackService.update_position."""
        coordinator = PlaybackCoordinator(audio, playback)
        coordinator.start()
        return coordinator

    # ── 1: a fast rejection inside restore releases the authority ─────────
    def test_fast_rejection_during_restore_releases_authority(
        self, tmp_path, monkeypatch
    ):
        db = tmp_path / "t32.db"
        _build_golden_state(db)

        # ── Session 2 (production lifecycle: start() then restore()): the
        # backend is FAST and REJECTS synchronously INSIDE the restore call.
        # The rejection's playback notification is consumed by the _restoring
        # guard — the resume authority must NOT stay open forever. ──
        repo2, _s2, audio2, playback2, _q2, session2, coordinator2 = _build(db)
        coordinator2.start()
        orig_prepare = playback2.prepare_for_resume

        def rejecting_prepare(path, position_ms):
            orig_prepare(path, position_ms)
            audio2.trigger_media_rejected(path, "gone")  # terminal, inside restore

        monkeypatch.setattr(playback2, "prepare_for_resume", rejecting_prepare)
        coordinator2.restore()

        # The terminal rejection surfaced during restore resolved the restore
        # window: an explicit checkpoint writes the COHERENT post-rejection
        # session — queue restored, playback_path None / position 0 — never
        # the hybrid keeping the rejected B (no fabricated resume).
        coordinator2.checkpoint()
        snap = repo2.load()
        assert snap.playback_path is None  # RED: hybrid keeps B / phase open
        assert snap.position_ms == 0
        assert snap.context.current_index == 1
        assert [e.file_path for e in snap.queue_entries] == [
            "/m/a.flac",
            "/m/b.flac",
            "/m/c.flac",
        ]

        # ── Session 3: the durable never keeps B — NO prepare is requested
        # (queue restored only, no fabricated resume, no autoplay). ──
        repo3, _s3, _a3, playback3, queue3, session3, coordinator3 = _build(db)
        coordinator3.start()
        prepare_calls = []
        orig_prepare3 = playback3.prepare_for_resume

        def spy_prepare(path, position_ms):
            prepare_calls.append((path, position_ms))
            orig_prepare3(path, position_ms)

        monkeypatch.setattr(playback3, "prepare_for_resume", spy_prepare)
        coordinator3.restore()

        assert [t.file_path for t in queue3.state.tracks] == [_A, _B, _C]
        assert session3.state.current_index == 1
        assert prepare_calls == []  # RED: durable kept B -> prepare(B, 222000)

    # ── 2: a fast seek failure inside restore resolves deterministically ──
    def test_fast_seek_failure_during_restore_resolves_deterministically(
        self, tmp_path, monkeypatch
    ):
        db = tmp_path / "t33.db"
        _build_golden_state(db)

        # ── Session 2 (production lifecycle): the backend ACCEPTS, but the
        # seek RAISES synchronously inside the restore call (records the
        # attempt, then fails). The acceptance path hits the raising seek ->
        # error_message "seek failed", no resume_prepared, and the terminal
        # notifications are consumed by the _restoring guard. ──
        repo2, _s2, audio2, playback2, _q2, session2, coordinator2 = _build(db)
        coordinator2.start()
        events = []
        playback2.subscribe_resume_prepared(lambda p, pos: events.append((p, pos)))

        real_seek = audio2.seek

        def raising_seek(ms):
            real_seek(ms)  # record the seek attempt first
            raise RuntimeError("seek failed")

        monkeypatch.setattr(audio2, "seek", raising_seek)
        orig_prepare = playback2.prepare_for_resume

        def accepting_prepare(path, position_ms):
            orig_prepare(path, position_ms)
            audio2.trigger_media_accepted(path)  # acceptance -> raising seek

        monkeypatch.setattr(playback2, "prepare_for_resume", accepting_prepare)
        coordinator2.restore()

        # The media WAS accepted (file_path B committed) but the seek never
        # applied: the honest runtime truth is B@0. The terminal seek failure
        # surfaced during restore resolved the window — an explicit checkpoint
        # writes the COHERENT runtime truth B@0, never the hybrid B@222000.
        assert audio2.seek_calls == [222000]  # the seek attempt happened
        assert playback2.state.error_message == "seek failed"
        coordinator2.checkpoint()
        snap = repo2.load()
        assert snap.playback_path == "/m/b.flac"  # the media WAS accepted
        assert snap.position_ms == 0  # RED: hybrid writes the stale 222000
        assert snap.context.current_index == 1

        # The seek failure disarmed the confirmation latch: no resume_prepared
        # event fired during the whole flow.
        assert events == []

        # ── Session 3: resume from 0 — the honest runtime truth, never the
        # stale 222000. ──
        repo3, _s3, _a3, playback3, queue3, session3, coordinator3 = _build(db)
        coordinator3.start()
        prepare_calls = []
        orig_prepare3 = playback3.prepare_for_resume

        def spy_prepare(path, position_ms):
            prepare_calls.append((path, position_ms))
            orig_prepare3(path, position_ms)

        monkeypatch.setattr(playback3, "prepare_for_resume", spy_prepare)
        coordinator3.restore()

        assert [t.file_path for t in queue3.state.tracks] == [_A, _B, _C]
        assert session3.state.current_index == 1
        assert prepare_calls == [(_B, 0)]  # RED: durable kept 222000

    # ── 3: the confirmed clamp never regresses the throttle marker ────────
    def test_confirmed_clamp_during_restore_does_not_regress_marker(
        self, tmp_path, monkeypatch
    ):
        db = tmp_path / "t34.db"
        _build_golden_state(db, position_ms=999999)

        # ── Session 2 (production lifecycle, audio position path wired): the
        # backend is FAST — acceptance + a CLAMPED position confirmation
        # (300000 vs the persisted 999999) fire synchronously INSIDE the
        # restore call, confirming the resume inside the restore window. ──
        stub = _FailOnDemandRepo(SqliteSessionRepository(db))
        settings = SettingsService(FakeSettingsRepo())
        audio = FakeAudioPort()
        playback = PlaybackService(audio)
        queue = QueueService()
        session = PlaybackSessionService(playback, queue)
        coordinator = PersistenceCoordinator(stub, queue, session, playback, settings)
        self._wire_audio_path(audio, queue, playback)
        coordinator.start()
        orig_prepare = playback.prepare_for_resume

        def fast_clamped_prepare(path, position_ms):
            orig_prepare(path, position_ms)
            audio.trigger_media_accepted(path)
            audio.trigger_position(300000)  # backend clamp -> confirmation

        monkeypatch.setattr(playback, "prepare_for_resume", fast_clamped_prepare)
        coordinator.restore()

        # The confirmed clamp (300000) became the durable truth during the
        # restore (the coordinator's own confirmation checkpoint consumed one
        # save): drain the counter before the throttle assertions.
        assert audio.seek_calls == [999999]  # the persisted position was sought
        assert stub.load().playback_path == "/m/b.flac"
        assert stub.load().position_ms == 300000
        stub.save_calls = 0

        # THROTTLE BASELINE: restore()'s tail must NOT regress the marker to
        # the stale snapshot 999999 — the CONFIRMED 300000 wins as the
        # baseline for future position deltas.
        playback.update_position(303000)  # delta 3000 from the confirmed 300000
        assert stub.save_calls == 0  # RED: marker 999999 -> premature save
        assert stub.load().position_ms == 300000  # nothing durably written yet

        playback.update_position(306000)  # delta 6000 >= 5000 from 300000
        assert stub.save_calls == 1  # RED: second premature save -> count 2
        assert stub.load().position_ms == 306000
