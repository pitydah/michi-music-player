"""M5.C8 — Restart Golden Gate: the M5 acceptance gate (§42-44).

The gate proves the C2-C7 pieces compose: a full session (queue, committed
current, playback position, repeat ALL, shuffle with seed, volume/muted,
theme, window geometry) survives a restart and resumes coherently. The
golden uses the PUBLIC service API only — no internal state fabrication:

- Queue construction: ``queue.add`` x3, ``queue.play_index`` + backend
  acceptance commits the current identity.
- Position seam: ``playback.update_position`` (the same public seam the C5
  coordinator tests use) — position flows into ``PlaybackState.position_ms``
  and is captured by the snapshot.
- Repeat/shuffle: ``queue.set_repeat_mode`` / ``queue.set_shuffle_enabled``;
  the queue is constructed with ``shuffle_seed=424242`` so the persisted
  seed equals 424242.
- Volume/muted: public playback setters ``playback.set_volume(37)`` /
  ``playback.set_muted(True)`` ONLY. The started PersistenceCoordinator
  observes the runtime volume/mute changes (last-observed detection) and
  syncs them through the settings public API ``snapshot_volume() →
  set_playback_preferences → save()`` with NO graceful-shutdown dependency
  — the golden stays on the checkpoint path (§42) and ``shutdown()`` is
  never called. NOTE: bootstrap's startup apply path is the reverse
  direction: ``settings.load() → playback.restore_volume(volume, muted)``
  (src/michi/bootstrap/__init__.py).
- Theme/geometry: ``settings.set_theme`` / ``settings.set_window_geometry``.
  A real ``SQLiteSettingsRepository`` is required here because the C5 test
  fake (FakeSettingsRepo) does not round-trip theme/window_geometry — the
  production SQLite repository does (M5.C6).
- Restart: the graph is DESTROYED (del, no shutdown) and rebuilt fresh on
  the SAME db; the reconstructed queue starts with the DEFAULT seed and
  restore() sets it back to the persisted 424242.

§44 (abrupt termination) proves restart does not depend on graceful
shutdown: a RUNTIME checkpoint (no shutdown call) is the only durable state.
"""

from pathlib import Path

from michi.application.persistence_coordinator import PersistenceCoordinator
from michi.application.playback_service import PlaybackService
from michi.application.playback_session_service import PlaybackSessionService
from michi.application.queue_service import QueueService
from michi.application.settings_service import SettingsService
from michi.domain.playback import PlaybackStatus
from michi.domain.queue import RepeatMode
from michi.domain.settings import WindowGeometry
from michi.infrastructure.session_repository import SqliteSessionRepository
from michi.infrastructure.sqlite_settings import SQLiteSettingsRepository
from tests.conftest import FakeAudioPort, FakeSettingsRepo

_A = Path("/m/a.flac")
_B = Path("/m/b.flac")
_C = Path("/m/c.flac")


def _build(
    db_path: Path,
    settings_repo=None,
    shuffle_seed: int | None = None,
    start: bool = False,
):
    """Fresh services + coordinator on the same db (no shutdown).

    ``start=True`` expresses the target lifecycle: the coordinator must be
    explicitly started for the runtime volume/mute sync to be active. Every
    SESSION-2 graph uses ``start=True`` because the production bootstrap
    order is construct -> ``start()`` -> ``restore()`` (the subscriptions are
    armed before the restore; see src/michi/bootstrap/__init__.py).
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
    if start:
        coordinator.start()
    return repo, settings, audio, playback, queue, session, coordinator


def _spy_resume(playback, calls):
    """Spy on prepare_for_resume, forwarding to the original."""
    orig = playback.prepare_for_resume

    def spy_prepare(path, position_ms):
        calls.append((path, position_ms))
        orig(path, position_ms)

    return orig, spy_prepare


class TestRestartGolden:
    def test_restart_golden_full_session(self, tmp_path, monkeypatch):
        db = tmp_path / "t1.db"

        # ── Session 1: build the full golden state and checkpoint ──
        settings_repo = SQLiteSettingsRepository(db)
        repo1, settings1, audio1, playback1, queue1, session1, coordinator1 = _build(
            db, settings_repo=settings_repo, shuffle_seed=424242, start=True
        )
        # Volume/muted through the PUBLIC playback setters ONLY — the started
        # coordinator's RUNTIME sync persists them (no manual
        # set_playback_preferences/save, no shutdown).
        playback1.set_volume(37)
        playback1.set_muted(True)
        # Theme + geometry through the settings public API.
        settings1.set_theme("dark")
        settings1.set_window_geometry(WindowGeometry(10, 20, 1100, 700, False))

        queue1.add(_A, "A")
        queue1.add(_B, "B")
        queue1.add(_C, "C")
        session1.play_queue_index(1)  # B pending
        audio1.trigger_media_accepted(_B)  # B committed, current 1
        playback1.update_position(222000)
        session1.set_repeat_mode(RepeatMode.ALL)
        session1.set_shuffle_enabled(True)
        coordinator1.checkpoint()  # the golden uses the checkpoint path

        # Destroy WITHOUT shutdown: restart must not depend on graceful stop.
        del coordinator1, queue1, playback1, audio1, repo1

        # ── Session 2: fresh services + coordinator on the SAME db ──
        # Production lifecycle: start() then restore() — the subscriptions
        # are armed before the restore (target bootstrap order).
        repo2, settings2, audio2, playback2, queue2, session2, coordinator2 = _build(
            db, settings_repo=SQLiteSettingsRepository(db), start=True
        )
        prepare_calls = []
        _orig_prepare, spy_prepare = _spy_resume(playback2, prepare_calls)
        monkeypatch.setattr(playback2, "prepare_for_resume", spy_prepare)
        play_calls = []
        orig_play = audio2.play

        def spy_play():
            play_calls.append(1)
            orig_play()

        monkeypatch.setattr(audio2, "play", spy_play)

        coordinator2.restore()

        # §42 — queue fully restored.
        assert [t.file_path for t in queue2.state.tracks] == [_A, _B, _C]
        assert session2.state.current_index == 1
        assert session2.state.repeat_mode is RepeatMode.ALL
        assert session2.state.shuffle_enabled is True
        # Reconstructed with the DEFAULT seed; restore sets the persisted one.
        assert session2.shuffle_seed == 424242

        # §42 — settings fully restored (real SQLite round-trip).
        assert settings2.state.volume == 37
        assert settings2.state.muted is True
        assert settings2.state.theme == "dark"
        assert settings2.state.window_geometry == WindowGeometry(
            10, 20, 1100, 700, False
        )

        # §42 — coherent resume requested: load + seek, NEVER autoplay.
        assert prepare_calls == [(_B, 222000)]
        assert play_calls == []
        assert audio2.state != "playing"
        # Playback identity committed only after backend acceptance.
        assert playback2.state.file_path is None
        audio2.trigger_media_accepted(_B)
        assert playback2.state.file_path == _B
        assert playback2.state.status is PlaybackStatus.STOPPED
        assert audio2.seek_calls == [222000]  # post-acceptance seek
        assert play_calls == []  # acceptance never autoplays

        # §42 — the golden's final action: the user presses play, then the
        # backend reports PLAYING and status maps truthfully.
        playback2.play()
        assert audio2.state == "playing"
        assert play_calls == [1]
        audio2.trigger_playback_state(PlaybackStatus.PLAYING)
        assert playback2.state.status is PlaybackStatus.PLAYING

    def test_restart_golden_duplicate_paths(self, tmp_path, monkeypatch):
        db = tmp_path / "t2.db"
        x = Path("/music/x.flac")
        a = Path("/music/a.flac")

        # ── Session 1 ──
        repo1, settings1, audio1, playback1, queue1, session1, coordinator1 = _build(db)
        queue1.add(x, "X1")
        queue1.add(a, "A")
        queue1.add(x, "X2")  # same path, distinct Track object
        session1.play_queue_index(2)
        audio1.trigger_media_accepted(x)  # committed current = X2 (identity)
        playback1.update_position(5555)
        coordinator1.checkpoint()
        del coordinator1, queue1, playback1, audio1, repo1

        # ── Session 2 ──
        # Production lifecycle: start() then restore() (target bootstrap order).
        repo2, settings2, audio2, playback2, queue2, session2, coordinator2 = _build(
            db, start=True
        )
        prepare_calls = []
        _orig_prepare, spy_prepare = _spy_resume(playback2, prepare_calls)
        monkeypatch.setattr(playback2, "prepare_for_resume", spy_prepare)
        coordinator2.restore()

        tracks = queue2.state.tracks
        assert len(tracks) == 3  # duplicates survive as distinct entries
        assert tracks[0] is not tracks[2]  # no collapse by path
        assert tracks[0].file_path == tracks[2].file_path == x
        assert tracks[1].file_path == a
        assert session2.state.current_index == 2
        # Resume coherence: entries[2] == playback path x.flac → prepare X2.
        assert prepare_calls == [(x, 5555)]
        assert playback2.state.file_path is None
        audio2.trigger_media_accepted(x)
        assert playback2.state.file_path == x
        assert playback2.state.status is PlaybackStatus.STOPPED

    def test_abrupt_termination_restores_checkpoint(self, tmp_path, monkeypatch):
        db = tmp_path / "t3.db"

        # ── Session 1: RUNTIME checkpoint, then destroy WITHOUT shutdown ──
        repo1, settings1, audio1, playback1, queue1, session1, coordinator1 = _build(
            db, shuffle_seed=424242
        )
        queue1.add(_A, "A")
        queue1.add(_B, "B")
        queue1.add(_C, "C")
        session1.play_queue_index(1)
        audio1.trigger_media_accepted(_B)
        playback1.update_position(42424)
        session1.set_repeat_mode(RepeatMode.ALL)
        session1.set_shuffle_enabled(True)
        coordinator1.checkpoint()  # runtime checkpoint — NO shutdown() call
        del coordinator1, queue1, playback1, audio1, repo1

        # ── Session 2 ──
        # Production lifecycle: start() then restore() (target bootstrap order).
        repo2, settings2, audio2, playback2, queue2, session2, coordinator2 = _build(
            db, start=True
        )
        prepare_calls = []
        _orig_prepare, spy_prepare = _spy_resume(playback2, prepare_calls)
        monkeypatch.setattr(playback2, "prepare_for_resume", spy_prepare)
        coordinator2.restore()

        # §44 — the last checkpoint state is restored, no graceful shutdown
        # needed: queue/current/repeat/shuffle/seed/position all survive.
        assert [t.file_path for t in queue2.state.tracks] == [_A, _B, _C]
        assert session2.state.current_index == 1
        assert session2.state.repeat_mode is RepeatMode.ALL
        assert session2.state.shuffle_enabled is True
        assert session2.shuffle_seed == 424242
        assert prepare_calls == [(_B, 42424)]
        audio2.trigger_media_accepted(_B)
        assert audio2.seek_calls == [42424]  # restored position sought
        assert playback2.state.file_path == _B
        assert playback2.state.status is PlaybackStatus.STOPPED
