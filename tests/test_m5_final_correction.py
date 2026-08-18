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

from michi.application.persistence_coordinator import PersistenceCoordinator
from michi.application.playback_service import PlaybackService
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
    repo, _settings, audio, playback, queue, coordinator = _build(
        db_path, shuffle_seed=shuffle_seed
    )
    coordinator.start()
    queue.add(_A, "A")
    queue.add(_B, "B")
    queue.add(_C, "C")
    queue.play_index(1)  # B pending
    audio.trigger_media_accepted(_B)  # B committed, current 1
    playback.update_position(position_ms)
    queue.set_repeat_mode(repeat_mode)
    queue.set_shuffle_enabled(shuffle_enabled)
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
        _r2, _s2, audio2, _p2, _q2, coordinator2 = _build(db)
        coordinator2.start()
        coordinator2.restore()
        coordinator2.shutdown()  # must SKIP the degraded final checkpoint
        del coordinator2, audio2

        # ── Session 3: the durable B@222000 survived the shutdown during the
        # pending window — the resume is requested again (never B@0/null) ──
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

    def test_queue_change_during_pending_window_does_not_degrade_snapshot(
        self, tmp_path
    ):
        db = tmp_path / "t13.db"
        _build_golden_state(db)

        # ── Session 2: restore; the resume is still pending (WAITING_MEDIA) ──
        repo2, _s2, _a2, playback2, queue2, coordinator2 = _build(db)
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
        _r2, _s2, _a2, _p2, _q2, coordinator2 = _build(db)
        coordinator2.start()
        coordinator2.restore()
        coordinator2.shutdown()
        del coordinator2

        # ── Session 3: resume resolves normally — prepare, accept (STOPPED +
        # seek to the persisted position), then a legit checkpoint persists
        # the NEW runtime truth ──
        repo3, _s3, audio3, playback3, _q3, coordinator3 = _build(db)
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
        _r2, _s2, audio2, playback2, _q2, coordinator2 = _build(db)
        coordinator2.start()
        coordinator2.restore()
        audio2.trigger_media_accepted(_B)  # WAITING_MEDIA -> WAITING_POSITION
        coordinator2.shutdown()
        del coordinator2, audio2, playback2

        # ── Session 3: the durable B@222000 survived — never B@0 ──
        _r3, _s3, _a3, playback3, _q3, coordinator3 = _build(db)
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

        # ── Session 2: restore (pending); a user queue.add DURING the window
        # fires queue.changed -> the hybrid checkpoint persists the LIVE queue
        # alongside the restored playback truth; destroy abruptly (no
        # acceptance, no shutdown). ──
        _r2, _s2, _a2, _p2, queue2, coordinator2 = _build(db)
        coordinator2.start()
        coordinator2.restore()
        queue2.add(Path("/m/d.flac"), "D")
        del coordinator2, queue2  # abrupt kill during the window

        # ── Session 3: the hybrid survived — queue A,B,C,D; current still B
        # (index 1); the restore is requested at the restored position. ──
        _r3, _s3, _a3, playback3, queue3, coordinator3 = _build(db)
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
        assert queue3.state.current_index == 1
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
        _r2, _s2, _a2, _p2, queue2, coordinator2 = _build(db)
        coordinator2.start()
        coordinator2.restore()
        queue2.move(1, 2)
        assert [t.file_path for t in queue2.state.tracks] == [_A, _C, _B]
        assert queue2.state.current_index == 2
        del coordinator2, queue2  # abrupt kill during the window

        # ── Session 3: order A,C,B with current B at index 2 and the restored
        # position intact — coherence (queue[2] == B) keeps the resume. ──
        _r3, _s3, _a3, playback3, queue3, coordinator3 = _build(db)
        coordinator3.start()
        prepare_calls = []
        orig_prepare = playback3.prepare_for_resume

        def spy_prepare(path, position_ms):
            prepare_calls.append((path, position_ms))
            orig_prepare(path, position_ms)

        monkeypatch.setattr(playback3, "prepare_for_resume", spy_prepare)
        coordinator3.restore()

        assert [t.file_path for t in queue3.state.tracks] == [_A, _C, _B]
        assert queue3.state.current_index == 2
        assert prepare_calls == [(_B, 222000)]

    # ── 4: removing the restored current clears the resume truth ──────────
    def test_remove_restored_current_clears_resume_truth(self, tmp_path, monkeypatch):
        db = tmp_path / "t18.db"
        _build_golden_state(db)

        # ── Session 2: restore (pending); the user REMOVES the restored
        # current (B). The queue drops to A,C with current -1 (no fictitious
        # identity) and the pending resume is superseded/cancelled through the
        # queue/playback public machinery; kill abruptly. ──
        _r2, _s2, _a2, _p2, queue2, coordinator2 = _build(db)
        coordinator2.start()
        coordinator2.restore()
        queue2.remove(1)  # removes the restored current B
        assert [t.file_path for t in queue2.state.tracks] == [_A, _C]
        assert queue2.state.current_index == -1
        del coordinator2, queue2  # abrupt kill during the window

        # ── Session 3: NO fabricated resume — no prepare is requested at all;
        # the queue restores as A,C with no current; no autoplay. ──
        _r3, _s3, _a3, playback3, queue3, coordinator3 = _build(db)
        coordinator3.start()
        prepare_calls = []
        orig_prepare = playback3.prepare_for_resume

        def spy_prepare(path, position_ms):
            prepare_calls.append((path, position_ms))
            orig_prepare(path, position_ms)

        monkeypatch.setattr(playback3, "prepare_for_resume", spy_prepare)
        coordinator3.restore()

        assert [t.file_path for t in queue3.state.tracks] == [_A, _C]
        assert queue3.state.current_index == -1
        assert prepare_calls == []  # no fabricated B; no autoplay

    # ── 5: repeat change during the window is durable ─────────────────────
    def test_repeat_change_during_restore_is_durable(self, tmp_path, monkeypatch):
        db = tmp_path / "t19.db"
        _build_golden_state(db, repeat_mode=RepeatMode.NONE)

        # ── Session 2: restore (pending); repeat -> ALL DURING the window;
        # kill abruptly. ──
        _r2, _s2, _a2, _p2, queue2, coordinator2 = _build(db)
        coordinator2.start()
        coordinator2.restore()
        queue2.set_repeat_mode(RepeatMode.ALL)
        del coordinator2, queue2  # abrupt kill during the window

        # ── Session 3: the repeat change survived — repeat ALL AND the
        # restored position intact. ──
        _r3, _s3, _a3, playback3, queue3, coordinator3 = _build(db)
        coordinator3.start()
        prepare_calls = []
        orig_prepare = playback3.prepare_for_resume

        def spy_prepare(path, position_ms):
            prepare_calls.append((path, position_ms))
            orig_prepare(path, position_ms)

        monkeypatch.setattr(playback3, "prepare_for_resume", spy_prepare)
        coordinator3.restore()

        assert queue3.state.repeat_mode is RepeatMode.ALL
        assert prepare_calls == [(_B, 222000)]

    # ── 6: shuffle change during the window is durable ────────────────────
    def test_shuffle_change_during_restore_is_durable(self, tmp_path, monkeypatch):
        db = tmp_path / "t20.db"
        _build_golden_state(db, shuffle_enabled=False)  # seed 424242 travels

        # ── Session 2: restore (pending); shuffle ON during the window (the
        # restored RNG, seeded 424242, drives the navigator reset); kill. ──
        _r2, _s2, _a2, _p2, queue2, coordinator2 = _build(db)
        coordinator2.start()
        coordinator2.restore()
        queue2.set_shuffle_enabled(True)
        del coordinator2, queue2  # abrupt kill during the window

        # ── Session 3: shuffle True + seed 424242 AND the restored position
        # intact. ──
        _r3, _s3, _a3, playback3, queue3, coordinator3 = _build(db)
        coordinator3.start()
        prepare_calls = []
        orig_prepare = playback3.prepare_for_resume

        def spy_prepare(path, position_ms):
            prepare_calls.append((path, position_ms))
            orig_prepare(path, position_ms)

        monkeypatch.setattr(playback3, "prepare_for_resume", spy_prepare)
        coordinator3.restore()

        assert queue3.state.shuffle_enabled is True
        assert queue3.shuffle_seed == 424242
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
        repo2, _s2, audio2, playback2, _q2, coordinator2 = _build(db)
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
        _r3, _s3, _a3, playback3, _q3, coordinator3 = _build(db)
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
        _r2, _s2, audio2, playback2, _q2, coordinator2 = _build(db)
        coordinator2.start()
        coordinator2.restore()
        audio2.trigger_media_accepted(_B)
        playback2.update_position(300000)  # backend clamp -> confirmation
        coordinator2.shutdown()

        # ── Session 3: prepare(B, 300000) — the clamp became the durable
        # truth, NOT the golden 999999. ──
        _r3, _s3, _a3, playback3, _q3, coordinator3 = _build(db)
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
        _r2, _s2, audio2, _p2, queue2, coordinator2 = _build(db)
        coordinator2.start()
        coordinator2.restore()
        audio2.trigger_media_rejected(_B, "gone")
        queue2.add(Path("/m/d.flac"), "D")  # legit checkpoint after release
        coordinator2.shutdown()

        snap = _r2.load()
        assert snap.playback_path is None  # no fabricated B
        assert snap.position_ms == 0
        assert snap.queue_current_index == 1
        assert [e.file_path for e in snap.queue_entries] == [
            "/m/a.flac",
            "/m/b.flac",
            "/m/c.flac",
            "/m/d.flac",
        ]

        # ── Session 3: queue restored; NO resume requested — the rejected
        # truth is never retained indefinitely. ──
        _r3, _s3, _a3, playback3, queue3, coordinator3 = _build(db)
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
        assert queue3.state.current_index == 1
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
        _r2, _s2, audio2, playback2, queue2, coordinator2 = _build(db)
        coordinator2.start()
        coordinator2.restore()
        queue2.play_index(2)  # user selects C; C supersedes B's prepare
        audio2.trigger_media_accepted(_B)  # LATE stale B acceptance: ignored
        audio2.trigger_media_accepted(_C)  # C commits -> queue current 2
        coordinator2.shutdown()

        snap = _r2.load()
        assert snap.queue_current_index == 2
        assert snap.playback_path == "/m/c.flac"
        assert snap.position_ms == 0  # C's runtime position (no seek/update)

        # ── Session 3: the C session is durable — prepare(C, 0); NEVER a
        # prepare for the superseded B. ──
        _r3, _s3, _a3, playback3, _q3, coordinator3 = _build(db)
        coordinator3.start()
        prepare_calls = []
        orig_prepare = playback3.prepare_for_resume

        def spy_prepare(path, position_ms):
            prepare_calls.append((path, position_ms))
            orig_prepare(path, position_ms)

        monkeypatch.setattr(playback3, "prepare_for_resume", spy_prepare)
        coordinator3.restore()

        assert prepare_calls == [(_C, 0)]
