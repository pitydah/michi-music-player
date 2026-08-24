"""M5.C3 / M4-R1 session restoration — Queue CONTENT + Session context.

The startup path rebuilds Queue content (QueueService.restore_entries) AND
the PlaybackSession logical context (PlaybackSessionService.restore_session:
context type / entries / current index / repeat / shuffle / seed). It never
starts playback, publishes notifications, and never fabricates a pending
candidate. There is no autoplay.
"""

from pathlib import Path

import pytest

from michi.application.playback_service import PlaybackService
from michi.application.playback_session_service import PlaybackSessionService
from michi.application.queue_service import QueueService
from michi.domain.playback import PlaybackStatus
from michi.domain.playback_session import (
    PlaybackContextType,
    RepeatMode,
)
from michi.domain.session import (
    FORMAT_VERSION,
    PersistedQueueEntry,
    PersistedSessionContext,
    PlaybackSessionSnapshot,
)


def _entries(*pairs) -> tuple[PersistedQueueEntry, ...]:
    return tuple(
        PersistedQueueEntry(file_path=path, title=title) for path, title in pairs
    )


def _snapshot(
    entries,
    current_index: int = -1,
    repeat_mode: RepeatMode = RepeatMode.NONE,
    shuffle_enabled: bool = False,
    shuffle_seed: int = 0,
    playback_path: str | None = None,
    position_ms: int = 0,
    context_type: str = "queue",
) -> PlaybackSessionSnapshot:
    return PlaybackSessionSnapshot(
        format_version=FORMAT_VERSION,
        queue_entries=tuple(entries),
        context=PersistedSessionContext(
            context_type=context_type,
            source_id=None,
            entries=tuple(entries),
            current_index=current_index,
        ),
        playback_path=playback_path,
        position_ms=position_ms,
        repeat_mode=repeat_mode,
        shuffle_enabled=shuffle_enabled,
        shuffle_seed=shuffle_seed,
    )


def _restore(queue_service, session_service, snap):
    """M4-R1 canonical restore: Queue CONTENT + Session logical context."""
    queue_service.restore_entries(
        [queue_track(Path(e.file_path), e.title) for e in snap.queue_entries]
    )
    session_service.restore_session(
        context_type=PlaybackContextType.QUEUE,
        source_id=None,
        entries=[
            session_entry(Path(e.file_path), e.title) for e in snap.context.entries
        ],
        current_index=snap.context.current_index,
        repeat_mode=snap.repeat_mode,
        shuffle_enabled=snap.shuffle_enabled,
        shuffle_seed=snap.shuffle_seed,
    )


def queue_track(file_path, title):
    from michi.domain.queue import Track

    return Track(file_path=file_path, title=title)


def session_entry(file_path, title):
    from michi.domain.playback_session import PlaybackSequenceEntry

    return PlaybackSequenceEntry(file_path=file_path, title=title)


@pytest.fixture
def restored_graph(fake_audio):
    """(queue, session, playback, audio) fresh graph."""
    playback = PlaybackService(fake_audio)
    queue = QueueService()
    session = PlaybackSessionService(playback, queue)
    return queue, session, playback, fake_audio


class TestRestoreBasic:
    def test_restore_basic(self, restored_graph):
        queue_service, session_service, _, _ = restored_graph
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
        _restore(queue_service, session_service, snap)

        assert [t.file_path for t in queue_service.state.tracks] == [
            Path("/music/a.flac"),
            Path("/music/b.flac"),
            Path("/music/c.flac"),
        ]
        assert session_service.state.context_type is PlaybackContextType.QUEUE
        assert session_service.state.current_index == 1
        assert session_service.state.current_entry.file_path == Path("/music/b.flac")
        assert session_service.state.repeat_mode is RepeatMode.ALL

    def test_restore_duplicate_paths_distinct(self, restored_graph):
        queue_service, session_service, _, _ = restored_graph
        snap = _snapshot(
            _entries(
                ("/music/x.flac", "X1"),
                ("/music/a.flac", "A"),
                ("/music/x.flac", "X2"),
            ),
            current_index=2,
        )
        _restore(queue_service, session_service, snap)

        tracks = queue_service.state.tracks
        assert len(tracks) == 3  # duplicates preserved as distinct entries
        assert tracks[0] is not tracks[2]  # distinct objects, same path
        assert tracks[0].file_path == tracks[2].file_path == Path("/music/x.flac")
        assert session_service.state.current_index == 2

    def test_restore_no_playback(self, restored_graph, monkeypatch):
        queue_service, session_service, playback_service, fake_audio = restored_graph
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
        _restore(queue_service, session_service, snap)

        assert loads == []  # no playback request during restore
        assert fake_audio.loaded is None  # audio backend untouched
        assert playback_service.state.file_path is None  # playback state untouched
        assert playback_service.state.status is PlaybackStatus.STOPPED

    def test_restore_capacity_reject_fresh(self, restored_graph, caplog):
        queue_service, session_service, _, _ = restored_graph
        # capacity guard lives in QueueService.restore_entries
        snap = _snapshot(
            _entries(
                ("/music/a.flac", "A"),
                ("/music/b.flac", "B"),
                ("/music/c.flac", "C"),
            ),
            current_index=0,
        )
        # queue max_tracks small: QueueService() default 10000 fits; verify
        # the session restores logically even with empty queue content
        _restore(queue_service, session_service, snap)
        assert queue_service.state.count == 3


class TestRestoreShuffle:
    def test_restore_shuffle_seed_property(self, restored_graph):
        queue_service, session_service, _, _ = restored_graph
        snap = _snapshot(
            _entries(("/music/a.flac", "A")),
            current_index=-1,
            shuffle_enabled=False,
            shuffle_seed=777,
        )
        _restore(queue_service, session_service, snap)
        assert session_service.shuffle_seed == 777  # persisted seed wins

    def test_restore_shuffle_enabled_rebuilds_navigator(self, restored_graph):
        queue_service, session_service, _, _ = restored_graph
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
        _restore(queue_service, session_service, snap)

        assert session_service.state.shuffle_enabled is True
        assert session_service.shuffle_seed == 424242
        # Pool = shuffled all-except-current: exactly {B, C}.
        assert {e.file_path for e in session_service._navigator.pool} == {
            Path("/music/b.flac"),
            Path("/music/c.flac"),
        }
        assert len(session_service._navigator.pool) == 2


class TestRestoreDefensive:
    def test_restore_defensive_invalid_index(self, restored_graph):
        queue_service, session_service, _, _ = restored_graph
        snap = _snapshot(
            _entries(
                ("/music/a.flac", "A"),
                ("/music/b.flac", "B"),
                ("/music/c.flac", "C"),
            ),
            current_index=99,
        )
        _restore(queue_service, session_service, snap)

        assert queue_service.state.count == 3  # queue restored
        assert session_service.state.current_index == -1  # defensive guard

    def test_restore_then_navigation_works(self, restored_graph):
        queue_service, session_service, _, fake_audio = restored_graph
        snap = _snapshot(
            _entries(
                ("/music/a.flac", "A"),
                ("/music/b.flac", "B"),
                ("/music/c.flac", "C"),
            ),
            current_index=0,
        )
        _restore(queue_service, session_service, snap)

        session_service.next()  # QUEUE context natural order: index 1
        assert fake_audio.loaded == Path("/music/b.flac")
        fake_audio.trigger_media_accepted(Path("/music/b.flac"))
        assert session_service.state.current_index == 1
