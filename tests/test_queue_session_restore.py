"""Tests for QueueService.restore_session — M5.C3 startup snapshot restoration.

The startup path rebuilds the queue and playback-mode state from a persisted
`PlaybackSessionSnapshot` (domain, built directly here), restores the shuffle
seed so navigation is deterministically reconstructable, never starts
playback, and publishes exactly one change notification. Pending candidates
are never restored; there is no autoplay.
"""

from pathlib import Path

from michi.domain.playback import PlaybackStatus
from michi.domain.queue import RepeatMode
from michi.domain.session import (
    FORMAT_VERSION,
    PersistedQueueEntry,
    PlaybackSessionSnapshot,
)


def _snapshot(
    entries,
    current_index: int = -1,
    repeat_mode: RepeatMode = RepeatMode.NONE,
    shuffle_enabled: bool = False,
    shuffle_seed: int = 0,
    playback_path: str | None = None,
    position_ms: int = 0,
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


def _entries(*pairs) -> tuple[PersistedQueueEntry, ...]:
    return tuple(
        PersistedQueueEntry(file_path=path, title=title) for path, title in pairs
    )


class TestRestoreBasic:
    def test_restore_basic(self, queue_service):
        snap = _snapshot(
            _entries(
                ("/music/a.flac", "A"),
                ("/music/b.flac", "B"),
                ("/music/c.flac", "C"),
            ),
            current_index=1,
            repeat_mode=RepeatMode.ALL,
        )
        calls = []
        queue_service.subscribe_changed(lambda: calls.append(1))
        queue_service.restore_session(snap)

        assert [t.file_path for t in queue_service.state.tracks] == [
            Path("/music/a.flac"),
            Path("/music/b.flac"),
            Path("/music/c.flac"),
        ]
        assert [t.title for t in queue_service.state.tracks] == ["A", "B", "C"]
        assert queue_service.state.current_index == 1
        assert queue_service.state.current_track.file_path == Path("/music/b.flac")
        assert queue_service.state.repeat_mode is RepeatMode.ALL
        assert calls == [1]  # exactly one notification

    def test_restore_duplicate_paths_distinct(self, queue_service):
        snap = _snapshot(
            _entries(
                ("/music/x.flac", "X1"),
                ("/music/a.flac", "A"),
                ("/music/x.flac", "X2"),
            ),
            current_index=2,
        )
        queue_service.restore_session(snap)

        tracks = queue_service.state.tracks
        assert len(tracks) == 3  # duplicates preserved as distinct entries
        assert tracks[0] is not tracks[2]  # distinct objects, same path
        assert tracks[0].file_path == tracks[2].file_path == Path("/music/x.flac")
        assert queue_service.state.current_index == 2
        assert queue_service.state.current_track.file_path == Path("/music/x.flac")

    def test_restore_atomic_single_notify(self, queue_service):
        snap = _snapshot(
            _entries(("/music/a.flac", "A"), ("/music/b.flac", "B")),
            current_index=0,
        )
        calls = []
        queue_service.subscribe_changed(lambda: calls.append(1))
        queue_service.restore_session(snap)
        assert calls == [1]  # exactly one notification, no more

    def test_restore_no_playback(
        self, queue_service, playback_service, fake_audio, monkeypatch
    ):
        snap = _snapshot(
            _entries(
                ("/music/a.flac", "A"),
                ("/music/b.flac", "B"),
                ("/music/c.flac", "C"),
            ),
            current_index=1,
        )
        loads = []
        orig = playback_service.load_and_play

        def spy(path, **kwargs):
            loads.append(path)
            orig(path, **kwargs)

        monkeypatch.setattr(playback_service, "load_and_play", spy)
        queue_service.restore_session(snap)

        assert loads == []  # no playback request during restore
        assert fake_audio.loaded is None  # audio backend untouched
        assert playback_service.state.file_path is None  # playback state untouched
        assert playback_service.state.status is PlaybackStatus.STOPPED

    def test_restore_capacity_reject_fresh(self, playback_service, caplog):
        from michi.application.queue_service import QueueService

        service = QueueService(playback_service, max_tracks=2)
        snap = _snapshot(
            _entries(
                ("/music/a.flac", "A"),
                ("/music/b.flac", "B"),
                ("/music/c.flac", "C"),
            ),
            current_index=0,
        )
        calls = []
        service.subscribe_changed(lambda: calls.append(1))

        with caplog.at_level("WARNING"):
            service.restore_session(snap)

        assert "exceeds max_tracks" in caplog.text
        assert service.state.count == 0  # fresh empty queue — never truncated
        assert service.state.current_index == -1
        assert service.state.repeat_mode is RepeatMode.NONE
        assert service.state.shuffle_enabled is False
        assert calls == [1]  # one notification for the fresh reset


class TestRestoreShuffle:
    def test_restore_shuffle_enabled_rebuilds_navigator(self, queue_service):
        snap = _snapshot(
            _entries(
                ("/music/a.flac", "A"),
                ("/music/b.flac", "B"),
                ("/music/c.flac", "C"),
            ),
            current_index=0,
            shuffle_enabled=True,
            shuffle_seed=424242,
        )
        queue_service.restore_session(snap)

        assert queue_service.state.shuffle_enabled is True
        assert queue_service.shuffle_seed == 424242
        # Pool = shuffled all-except-current: exactly {B, C}.
        assert {t.file_path for t in queue_service._navigator.pool} == {
            Path("/music/b.flac"),
            Path("/music/c.flac"),
        }
        assert len(queue_service._navigator.pool) == 2
        # History = [current] (the committed entry).
        assert queue_service._navigator.history == [queue_service.state.current_track]
        assert queue_service.state.current_track.file_path == Path("/music/a.flac")

    def test_restore_shuffle_seed_deterministic(self, playback_service):
        from michi.application.queue_service import QueueService

        snap = _snapshot(
            _entries(
                ("/music/a.flac", "A"),
                ("/music/b.flac", "B"),
                ("/music/c.flac", "C"),
            ),
            current_index=0,
            shuffle_enabled=True,
            shuffle_seed=424242,
        )
        first = QueueService(playback_service)
        second = QueueService(playback_service)
        first.restore_session(snap)
        second.restore_session(snap)

        # Same persisted seed → identical pool ORDER in both services.
        assert [t.file_path for t in first._navigator.pool] == [
            t.file_path for t in second._navigator.pool
        ]

    def test_restore_shuffle_seed_property(self, queue_service, playback_service):
        from michi.application.queue_service import QueueService

        snap = _snapshot(
            _entries(("/music/a.flac", "A")),
            current_index=-1,
            shuffle_enabled=False,
            shuffle_seed=777,
        )
        queue_service.restore_session(snap)
        assert queue_service.shuffle_seed == 777  # persisted seed wins

        defaulted = QueueService(playback_service)
        assert isinstance(defaulted.shuffle_seed, int)
        assert defaulted.shuffle_seed > 0  # positive seed by default


class TestRestoreDefensive:
    def test_restore_defensive_invalid_index(self, queue_service):
        # Bypasses the strict codec: a snapshot with an out-of-range index.
        snap = _snapshot(
            _entries(
                ("/music/a.flac", "A"),
                ("/music/b.flac", "B"),
                ("/music/c.flac", "C"),
            ),
            current_index=99,
        )
        queue_service.restore_session(snap)

        assert queue_service.state.count == 3  # queue restored
        assert queue_service.state.current_index == -1  # defensive guard

    def test_restore_index_negative_queue_only(self, queue_service, fake_audio):
        snap = _snapshot(
            _entries(("/music/a.flac", "A"), ("/music/b.flac", "B")),
            current_index=-1,
            playback_path=None,
        )
        queue_service.restore_session(snap)

        assert queue_service.state.count == 2  # queue restored
        assert queue_service.state.current_index == -1
        assert fake_audio.loaded is None  # no playback

    def test_restore_then_navigation_works(self, queue_service, fake_audio):
        snap = _snapshot(
            _entries(
                ("/music/a.flac", "A"),
                ("/music/b.flac", "B"),
                ("/music/c.flac", "C"),
            ),
            current_index=0,
        )
        queue_service.restore_session(snap)

        queue_service.next()  # natural order: index 1
        assert fake_audio.loaded == Path("/music/b.flac")
        fake_audio.trigger_media_accepted(Path("/music/b.flac"))
        assert queue_service.state.current_index == 1

    def test_restore_no_pending(self, queue_service, fake_audio):
        snap = _snapshot(
            _entries(("/music/a.flac", "A"), ("/music/b.flac", "B")),
            current_index=-1,
        )
        queue_service.restore_session(snap)

        queue_service.play_current()  # no committed current → no-op, no load
        assert fake_audio.loaded is None
        assert queue_service.state.current_index == -1


class TestConstructorSeed:
    def test_constructor_shuffle_seed_param(self, playback_service):
        from michi.application.queue_service import QueueService

        service = QueueService(playback_service, shuffle_seed=7)
        assert service.shuffle_seed == 7
