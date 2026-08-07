"""Debt D1 vertical slice — atomic playlist import.

PlaylistService is the single authority: batch additions honour an explicit
policy (ATOMIC_ROLLBACK / PARTIAL_COMMIT / SKIP_INVALID) echoed in every
result, file imports run through the same policy-aware path, long imports
run as durable ``playlist_import`` jobs, and cancellation is real (job
cancellation or an honest NO_ACTIVE_IMPORT — never a nominal ok).
"""
from __future__ import annotations

import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from core.jobs.handlers import make_playlist_import_handler  # noqa: E402
from core.jobs.job_service import DurableJobService, JobState  # noqa: E402
from core.playlist_service import (  # noqa: E402
    ATOMIC_ROLLBACK,
    PARTIAL_COMMIT,
    SKIP_INVALID,
    PlaylistService,
)
from core.worker_manager import WorkerManager  # noqa: E402
from library.library_db import LibraryDB  # noqa: E402

pytestmark = pytest.mark.isolation

TRACKS = [
    ("/m/one.flac", "one.flac", "/m", ".flac", "One", "Artist A",
     "Album A", 2020, "Rock", 200, 1000, "uid-1"),
    ("/m/two.flac", "two.flac", "/m", ".flac", "Two", "Artist A",
     "Album A", 2020, "Rock", 210, 1000, "uid-2"),
    ("/m/three.flac", "three.flac", "/m", ".flac", "Three", "Artist B",
     "Album B", 2021, "Jazz", 220, 900, "uid-3"),
    ("/m/four.flac", "four.flac", "/m", ".flac", "Four", "Artist B",
     "Album B", 2021, "Jazz", 230, 900, "uid-4"),
    ("/m/five.flac", "five.flac", "/m", ".flac", "Five", "Artist C",
     "Album C", 2022, "Pop", 240, 128, "uid-5"),
    ("/m/six.flac", "six.flac", "/m", ".flac", "Six", "Artist C",
     "Album C", 2022, "Pop", 250, 128, "uid-6"),
    ("/m/seven.flac", "seven.flac", "/m", ".flac", "Seven", "Artist D",
     "Album D", 2023, "Rock", 260, 320, "uid-7"),
    ("/m/eight.flac", "eight.flac", "/m", ".flac", "Eight", "Artist D",
     "Album D", 2023, "Rock", 270, 320, "uid-8"),
    ("/m/nine.flac", "nine.flac", "/m", ".flac", "Nine", "Artist E",
     "Album E", 2024, "Jazz", 280, 900, "uid-9"),
    ("/m/ten.flac", "ten.flac", "/m", ".flac", "Ten", "Artist E",
     "Album E", 2024, "Jazz", 290, 900, "uid-10"),
]


def _make_db() -> LibraryDB:
    db = LibraryDB(":memory:")
    db.conn.executemany(
        "INSERT INTO media_items "
        "(filepath, filename, directory, ext, kind, title, artist, album, "
        "year, genre, duration, bitrate, track_uid) "
        "VALUES (?, ?, ?, ?, 'audio', ?, ?, ?, ?, ?, ?, ?, ?)",
        TRACKS,
    )
    db.conn.commit()
    return db


@pytest.fixture
def app():
    from PySide6.QtCore import QCoreApplication
    instance = QCoreApplication.instance()
    return instance or QCoreApplication()


@pytest.fixture
def svc():
    return PlaylistService(db=_make_db())


@pytest.fixture
def job_service(tmp_path):
    return DurableJobService(db_path=str(tmp_path / "jobs.db"))


class _ImportPort:
    """PlaylistImportPort adapter — mirrors composition._PlaylistImportPort."""

    def __init__(self, playlist_service):
        self._svc = playlist_service

    def import_playlist(self, path, name="", policy=SKIP_INVALID, ctx=None):
        return self._svc.import_playlist_file(
            path, target_name=name or None, policy=policy, ctx=ctx)


def _register(service, playlist_service):
    service.register_handler(
        "playlist_import", make_playlist_import_handler(_ImportPort(playlist_service)))


class _SlowCtx:
    """Slows each cooperative check so a real cancel lands mid-import."""

    def __init__(self, real_ctx, delay: float = 0.05):
        self._real = real_ctx
        self._delay = delay

    def raise_if_cancelled(self):
        time.sleep(self._delay)
        self._real.token.raise_if_cancelled()


class _SlowImportPort:
    """PlaylistImportPort adapter that slows the cooperative checks."""

    def __init__(self, playlist_service, delay: float = 0.05):
        self._svc = playlist_service
        self._delay = delay

    def import_playlist(self, path, name="", policy=SKIP_INVALID, ctx=None):
        return self._svc.import_playlist_file(
            path, target_name=name or None, policy=policy,
            ctx=_SlowCtx(ctx, self._delay))


def _playlist_count(svc: PlaylistService, pid: int) -> int:
    detail = svc.get_detail(pid)
    return detail.get("count", 0) if detail.get("ok") else -1


def _point_media_items_at(db: LibraryDB, filepaths: list[str]) -> None:
    """Point the first N media_items rows at the given real files."""
    for i, fp in enumerate(filepaths):
        db.conn.execute("UPDATE media_items SET filepath=? WHERE id=?",
                        (fp, i + 1))
    db.conn.commit()


class TestAtomicRollback:
    def test_atomic_rollback(self, svc):
        pid = svc.create("Atomic")["id"]
        refs = [1, 2, 3, 4, 5, 6, 999, 7, 8, 9]

        result = svc.add_tracks(pid, refs, policy=ATOMIC_ROLLBACK)

        assert result["ok"] is False
        assert result["status"] == "FAILED"
        assert result["policy"] == ATOMIC_ROLLBACK
        assert result["requested"] == 10
        assert result["added"] == 0
        assert result["failed"] == 1
        assert result["duplicates"] == 0
        assert result["rollback_performed"] is True
        assert result["missing"] == [{"track_id": 999, "filepath": ""}]
        # The playlist exists but is EMPTY after the rollback.
        assert _playlist_count(svc, pid) == 0

    def test_policy_echoed_on_success(self, svc):
        pid = svc.create("AtomicOk")["id"]
        result = svc.add_tracks(pid, [1, 2, 3], policy=ATOMIC_ROLLBACK)
        assert result["ok"] is True
        assert result["status"] == "COMPLETED"
        assert result["policy"] == ATOMIC_ROLLBACK
        assert result["rollback_performed"] is False
        assert _playlist_count(svc, pid) == 3


class TestPartialCommit:
    def test_partial_commit_stops_at_first_failure(self, svc):
        pid = svc.create("Partial")["id"]
        refs = [1, 2, 3, 4, 5, 6, 999, 7, 8, 9]

        result = svc.add_tracks(pid, refs, policy=PARTIAL_COMMIT)

        assert result["ok"] is True
        assert result["status"] == "PARTIAL_SUCCESS"
        assert result["policy"] == PARTIAL_COMMIT
        assert result["requested"] == 10
        assert result["added"] == 6
        assert result["failed"] == 1
        assert result["skipped"] == 0
        assert result["missing"] == [{"track_id": 999, "filepath": ""}]
        assert _playlist_count(svc, pid) == 6


class TestSkipInvalid:
    def test_skip_invalid_missing_and_duplicates(self, svc):
        pid = svc.create("Skip")["id"]
        refs = [1, 1, 999, 2, 3]

        result = svc.add_tracks(pid, refs, policy=SKIP_INVALID)

        assert result["ok"] is True
        assert result["status"] == "PARTIAL_SUCCESS"
        assert result["policy"] == SKIP_INVALID
        assert result["requested"] == 5
        assert result["added"] == 3
        assert result["duplicates"] == 1
        assert result["skipped"] == 1
        assert result["failed"] == 0
        assert result["missing"] == [{"track_id": 999, "filepath": ""}]
        assert _playlist_count(svc, pid) == 3

    def test_duplicates_not_double_added(self, svc):
        pid = svc.create("Dup")["id"]

        result = svc.add_tracks(pid, [3, 3], policy=SKIP_INVALID)

        assert result["ok"] is True
        assert result["added"] == 1
        assert result["duplicates"] == 1
        assert _playlist_count(svc, pid) == 1


class TestImportFileReal:
    def test_import_file_real(self, svc, tmp_path):
        existing = []
        for i in range(3):
            fp = tmp_path / f"real-{i}.flac"
            fp.write_text("data")
            existing.append(str(fp))
        _point_media_items_at(svc._db, existing)
        missing_a = tmp_path / "missing-a.flac"
        missing_b = tmp_path / "missing-b.flac"
        m3u = tmp_path / "real.m3u"
        m3u.write_text(
            "#EXTM3U\n"
            f"{existing[0]}\n{existing[1]}\n{existing[2]}\n"
            f"{missing_a}\n{missing_b}\n")

        result = svc.import_playlist_file(str(m3u), policy=SKIP_INVALID)

        assert result["ok"] is True
        assert result["status"] == "PARTIAL_SUCCESS"
        assert result["policy"] == SKIP_INVALID
        assert result["requested"] == 5
        assert result["added"] == 3
        assert result["skipped"] == 2
        assert result["failed"] == 0
        assert len(result["missing"]) == 2
        assert result["rollback_performed"] is False
        pid = result["playlist_id"]
        assert _playlist_count(svc, pid) == 3


class TestImportViaJob:
    def test_import_via_job(self, app, job_service, svc, tmp_path):
        existing = []
        for i in range(3):
            fp = tmp_path / f"job-{i}.flac"
            fp.write_text("data")
            existing.append(str(fp))
        _point_media_items_at(svc._db, existing)
        m3u = tmp_path / "job.m3u"
        m3u.write_text("\n".join(existing))
        _register(job_service, svc)

        job_id = job_service.create_job(
            "playlist_import", owner="playlist",
            payload={"path": str(m3u), "name": "Job Import",
                     "policy": SKIP_INVALID})
        assert job_service.start_job(job_id) is True

        job = job_service.get_job(job_id)
        assert job.state == JobState.SUCCEEDED
        assert job.type == "playlist_import"
        assert job.owner == "playlist"
        result = job.result
        assert result["ok"] is True
        assert result["status"] == "COMPLETED"
        assert result["added"] == 3
        # Playlist read back through the service.
        pid = result["playlist_id"]
        assert _playlist_count(svc, pid) == 3
        readback = svc.list()
        assert any(p["id"] == pid and p["name"] == "Job Import"
                   for p in readback)

    def test_import_job_payload_preserved_on_retry(self, app, job_service, svc,
                                                   tmp_path):
        existing = []
        for i in range(2):
            fp = tmp_path / f"retry-{i}.flac"
            fp.write_text("data")
            existing.append(str(fp))
        _point_media_items_at(svc._db, existing)
        m3u = tmp_path / "retry.m3u"
        m3u.write_text("\n".join(existing))
        port = _ImportPort(svc)
        original = port.import_playlist
        calls = {"n": 0}

        def flaky(path, name="", policy=SKIP_INVALID, ctx=None):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("transient failure")
            return original(path, name, policy, ctx)

        port.import_playlist = flaky
        job_service.register_handler(
            "playlist_import", make_playlist_import_handler(port))

        job_id = job_service.create_job(
            "playlist_import", owner="playlist",
            payload={"path": str(m3u), "name": "Retry", "policy": SKIP_INVALID})
        job_service.start_job(job_id)
        assert job_service.get_job(job_id).state == JobState.FAILED

        assert job_service.retry_job(job_id) is True
        job = job_service.get_job(job_id)
        assert job.state == JobState.SUCCEEDED
        # The ORIGINAL payload survives the retry.
        assert job.payload["path"] == str(m3u)
        assert job.payload["name"] == "Retry"
        assert job.payload["policy"] == SKIP_INVALID
        pid = job.result["playlist_id"]
        assert _playlist_count(svc, pid) == 2


class TestCancelImportReal:
    def test_cancel_import_real(self, app, svc, tmp_path):
        # 120 valid entries with slowed cooperative checks: the REAL
        # cancellation path (cancel_import → cancel_job → token) lands
        # mid-import, AFTER memberships were inserted. ATOMIC_ROLLBACK must
        # roll the whole transaction back — no orphan playlist/tracks.
        existing = []
        for i in range(120):
            fp = tmp_path / f"cancel-{i}.flac"
            fp.write_text("data")
            existing.append(str(fp))
        m3u = tmp_path / "cancel.m3u"
        m3u.write_text("\n".join(existing))

        wm = WorkerManager()
        try:
            job_service2 = DurableJobService(
                db_path=str(tmp_path / "cancel-jobs.db"), worker_manager=wm)
            real_svc = PlaylistService(db=svc._db, job_service=job_service2)
            job_service2.register_handler(
                "playlist_import",
                make_playlist_import_handler(_SlowImportPort(real_svc)))

            job_id = job_service2.create_job(
                "playlist_import", owner="playlist",
                payload={"path": str(m3u), "name": "Cancel Me",
                         "policy": ATOMIC_ROLLBACK})
            assert job_service2.start_job(job_id) is True

            # Real cancellation through the service → job_service.
            cancel = real_svc.cancel_import(job_id)
            assert cancel["ok"] is True
            assert cancel["cancelled"] is True

            deadline = time.time() + 10
            while time.time() < deadline:
                app.processEvents()
                if job_service2.get_job(job_id).state == JobState.CANCELLED:
                    break
                time.sleep(0.02)
            job = job_service2.get_job(job_id)
            assert job.state == JobState.CANCELLED
            # No orphan state: the rolled-back playlist never exists.
            assert not any(p["name"] == "Cancel Me" for p in real_svc.list())
            # A finished import is no longer cancellable — honest answer.
            result = real_svc.cancel_import(job_id)
            assert result["ok"] is False
            assert result["error_code"] == "NO_ACTIVE_IMPORT"
        finally:
            wm.shutdown()

    def test_cancel_import_no_active_job(self, svc, job_service):
        svc_with_jobs = PlaylistService(db=svc._db, job_service=job_service)
        result = svc_with_jobs.cancel_import("ghost-job")
        assert result["ok"] is False
        assert result["error_code"] == "NO_ACTIVE_IMPORT"
        # No job service wired at all → still honest.
        result = svc.cancel_import("ghost-job")
        assert result["ok"] is False
        assert result["error_code"] == "NO_ACTIVE_IMPORT"

    def test_cancel_import_other_domain_job(self, svc, job_service):
        svc_with_jobs = PlaylistService(db=svc._db, job_service=job_service)
        job_id = job_service.create_job("mix_generate", owner="mix",
                                        payload={"strategy": "daily"})
        result = svc_with_jobs.cancel_import(job_id)
        assert result["ok"] is False
        assert result["error_code"] == "NO_ACTIVE_IMPORT"
