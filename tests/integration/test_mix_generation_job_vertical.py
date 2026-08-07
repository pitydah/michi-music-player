"""Fase Mix: vertical slice — MixBridge.generate runs MixService.generate
through a DURABLE job ("mix_generate", owner="mix").

The bridge never runs generation synchronously and never re-wraps outcomes:
the canonical MixService result ({ok, status, tracks}) flows service →
job result → bridge → QML-visible state 1:1.  NO_MATCHES / EMPTY_LIBRARY /
INVALID_STRATEGY are ok=False end-to-end; a raised service error fails the
JOB (never an empty-list success).
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication  # noqa: E402

from core.jobs.handlers import make_mix_generate_handler  # noqa: E402
from core.jobs.job_service import DurableJobService, JobState  # noqa: E402
from core.library.library_query_service import LibraryQueryService  # noqa: E402
from core.mix_service import MixService  # noqa: E402
from core.playlist_service import PlaylistService  # noqa: E402
from library.library_db import LibraryDB  # noqa: E402
from recommendation.smart_mix_service import SmartMixService  # noqa: E402
from ui_qml_bridge.mix_bridge import MixBridge  # noqa: E402

pytestmark = pytest.mark.isolation

TRACKS = [
    ("/m/jazz-one.flac", "jazz-one.flac", "/m", ".flac", "Jazz One",
     "Miles Davis", "Kind of Blue", 1959, "Jazz", 370, 900, "uid-j1"),
    ("/m/jazz-two.flac", "jazz-two.flac", "/m", ".flac", "Jazz Two",
     "John Coltrane", "A Love Supreme", 1965, "Jazz", 480, 900, "uid-j2"),
    ("/m/rock-one.flac", "rock-one.flac", "/m", ".flac", "Rock One",
     "Led Zeppelin", "IV", 1971, "Rock", 420, 1000, "uid-r1"),
]


def _make_db(tracks: list | None = None) -> LibraryDB:
    db = LibraryDB(":memory:")
    if tracks:
        db.conn.executemany(
            "INSERT INTO media_items "
            "(filepath, filename, directory, ext, kind, title, artist, album, "
            "year, genre, duration, bitrate, track_uid) "
            "VALUES (?, ?, ?, ?, 'audio', ?, ?, ?, ?, ?, ?, ?, ?)",
            tracks,
        )
        db.conn.executemany(
            "INSERT INTO favorites (track_id, device) VALUES (?, 'desktop')",
            [(t[0],) for t in tracks],
        )
    db.conn.commit()
    return db


def _stack(db: LibraryDB):
    query_service = LibraryQueryService(db=db)
    playlist_service = PlaylistService(db=db)
    mix_service = MixService(
        db=db,
        smart_mix_service=SmartMixService(db=db),
        library_query_service=query_service,
        playlist_service=playlist_service,
    )
    return mix_service, playlist_service


@pytest.fixture
def app():
    instance = QCoreApplication.instance()
    return instance or QCoreApplication()


@pytest.fixture
def job_service(tmp_path):
    """Inline DurableJobService (no WorkerManager): the handler completes
    synchronously inside start_job, mirroring the async signal flow."""
    svc = DurableJobService(db_path=str(tmp_path / "jobs.db"))
    return svc


def _bridge(mix_service, job_service, playlist_service=None):
    return MixBridge(
        mix_service=mix_service,
        job_service=job_service,
        playlist_service=playlist_service,
    )


class _MixPort:
    """MixGenerationPort adapter — mirrors core.composition.jobs._MixPort."""

    def __init__(self, mix_service):
        self._mix = mix_service

    def generate(self, strategy, seed=None, limit=30, ctx=None):
        if self._mix is None:
            raise RuntimeError("MixService unavailable")
        return self._mix.generate(strategy=strategy, seed=seed, limit=limit)


def _register(service, mix_service):
    service.register_handler("mix_generate",
                             make_mix_generate_handler(_MixPort(mix_service)))


class TestGenerateViaJob:
    def test_generate_via_job(self, app, job_service, tmp_path):
        db = _make_db(TRACKS)
        mix_service, _pl = _stack(db)
        _register(job_service, mix_service)
        bridge = _bridge(mix_service, job_service)

        result = bridge.loadMix("favorites", '{"limit": 10}')

        # A durable job owned by "mix" exists and completed.
        jobs = [j for j in job_service.list_jobs(owner="mix")]
        assert len(jobs) == 1
        assert jobs[0]["type"] == "mix_generate"
        assert jobs[0]["state"] == JobState.SUCCEEDED.value
        assert jobs[0]["payload"]["strategy"] == "favorites"
        assert jobs[0]["result"]["ok"] is True
        assert jobs[0]["result"]["status"] == "COMPLETED_WITH_TRACKS"

        # The bridge exposes the canonical outcome, not a re-wrap.
        assert result["ok"] is True
        assert result["job_id"] == jobs[0]["id"]
        assert bridge.stateName == "COMPLETED_WITH_TRACKS"
        assert len(bridge.currentSongs) == len(TRACKS)
        assert bridge.errorMessage == ""

    def test_empty_library_not_success(self, app, job_service):
        db = _make_db()
        mix_service, _pl = _stack(db)
        _register(job_service, mix_service)
        bridge = _bridge(mix_service, job_service)

        result = bridge.loadMix("daily_mix", "")

        assert result["ok"] is True  # the JOB was accepted
        jobs = job_service.list_jobs(owner="mix")
        assert jobs[0]["result"]["ok"] is False
        assert jobs[0]["result"]["status"] == "EMPTY_LIBRARY"
        assert bridge.stateName == "EMPTY_LIBRARY"
        assert bridge.currentSongs == []
        assert bridge.errorMessage  # honest message, not a silent empty success

    def test_no_matches_not_success(self, app, job_service):
        db = _make_db(TRACKS)
        mix_service, _pl = _stack(db)
        _register(job_service, mix_service)
        bridge = _bridge(mix_service, job_service)

        result = bridge.loadMix("by_year", '{"year": 1990}')

        assert result["ok"] is True  # job accepted
        jobs = job_service.list_jobs(owner="mix")
        assert jobs[0]["result"]["ok"] is False
        assert jobs[0]["result"]["status"] == "NO_MATCHES"
        assert bridge.stateName == "NO_MATCHES"
        assert bridge.currentSongs == []

    def test_invalid_strategy(self, app, job_service):
        db = _make_db(TRACKS)
        mix_service, _pl = _stack(db)
        _register(job_service, mix_service)
        bridge = _bridge(mix_service, job_service)

        result = bridge.loadMix("nuclear_launch", "")

        assert result["ok"] is False  # unknown category rejected at configure
        assert result["error_code"] == "UNKNOWN_CATEGORY"
        jobs = job_service.list_jobs(owner="mix")
        assert jobs == []

    def test_invalid_strategy_via_job(self, app, job_service):
        """A raw job with an unknown strategy lands INVALID_STRATEGY (ok=False)
        and the bridge state matches — no fake success."""
        db = _make_db(TRACKS)
        mix_service, _pl = _stack(db)
        _register(job_service, mix_service)
        bridge = _bridge(mix_service, job_service)

        job_id = job_service.create_job(
            "mix_generate", owner="mix",
            payload={"strategy": "nuclear_launch", "seed": {}, "limit": 10})
        bridge._job_id = job_id
        job_service.start_job(job_id)

        job = job_service.get_job(job_id)
        assert job.result["ok"] is False
        assert job.result["status"] == "INVALID_STRATEGY"
        assert bridge.stateName == "INVALID_STRATEGY"
        assert bridge.currentSongs == []

    def test_cancel_mix_only_own_job(self, app, job_service, tmp_path):
        """Re-assert F2 through the bridge path: cancelling the mix job never
        touches an unrelated RUNNING scan job."""
        import threading
        import time

        from core.worker_manager import WorkerManager

        db_path = str(tmp_path / "wm.db")
        release = threading.Event()

        def _blocking_handler(event):
            def handler(job, ctx):
                while not event.is_set():
                    ctx.token.raise_if_cancelled()
                    time.sleep(0.01)
                return {"ok": True, "finished": True}
            return handler

        wm = WorkerManager()
        try:
            svc = DurableJobService(db_path=db_path, worker_manager=wm)
            svc.register_handler("library_scan", _blocking_handler(release))
            svc.register_handler("mix_generate", _blocking_handler(release))

            scan_id = svc.create_job("library_scan", owner="job_bridge",
                                     payload={"folder_path": "/music/a"})
            assert svc.start_job(scan_id) is True

            bridge = MixBridge(mix_service=None, job_service=svc)
            bridge._current_mix_id = "daily_mix"
            result = bridge.generate()
            assert result["ok"] is True
            mix_id = result["job_id"]
            assert svc.get_job(mix_id).state == JobState.RUNNING

            cancel = bridge.cancelGeneration()
            assert cancel["ok"] is True

            deadline = time.time() + 10
            while time.time() < deadline:
                app.processEvents()
                if svc.get_job(mix_id).state == JobState.CANCELLED:
                    break
                time.sleep(0.02)
            assert svc.get_job(mix_id).state == JobState.CANCELLED
            # The unrelated scan is untouched.
            assert svc.get_job(scan_id).state == JobState.RUNNING

            release.set()
            deadline = time.time() + 10
            while time.time() < deadline:
                app.processEvents()
                if svc.get_job(scan_id).state in (JobState.SUCCEEDED,
                                                  JobState.FAILED):
                    break
                time.sleep(0.02)
            assert svc.get_job(scan_id).state == JobState.SUCCEEDED
        finally:
            release.set()
            wm.shutdown()

    def test_service_error_not_empty(self, app, job_service, monkeypatch):
        db = _make_db(TRACKS)
        mix_service, _pl = _stack(db)

        def _boom(strategy, seed=None, limit=30, ctx=None):
            raise RuntimeError("generator exploded")

        monkeypatch.setattr(mix_service, "generate", _boom)
        _register(job_service, mix_service)
        bridge = _bridge(mix_service, job_service)

        result = bridge.loadMix("favorites", "")

        assert result["ok"] is True  # job accepted
        jobs = job_service.list_jobs(owner="mix")
        assert jobs[0]["state"] == JobState.FAILED.value
        assert "generator exploded" in jobs[0]["errors"][0]
        # The bridge surfaces FAILED — never an empty ok list.
        assert bridge.stateName == "FAILED"
        assert bridge.currentSongs == []
        assert bridge.errorMessage


class TestSavePlaylist:
    def test_save_playlist_real_id(self, app, job_service):
        db = _make_db(TRACKS)
        mix_service, playlist_service = _stack(db)
        _register(job_service, mix_service)
        bridge = _bridge(mix_service, job_service, playlist_service)

        result = bridge.loadMix("favorites", '{"limit": 10}')
        assert bridge.stateName == "COMPLETED_WITH_TRACKS"

        saved = bridge.saveMixAsPlaylist("Mix Guardado")

        assert saved["ok"] is True
        playlist_id = saved["playlist_id"]
        assert isinstance(playlist_id, int)
        assert not isinstance(playlist_id, dict)
        detail = playlist_service.get_detail(playlist_id)
        assert detail["ok"] is True
        assert detail["count"] == len(TRACKS)

    def test_partial_playlist_save(self, app, job_service, monkeypatch):
        db = _make_db(TRACKS)
        mix_service, playlist_service = _stack(db)
        _register(job_service, mix_service)
        bridge = _bridge(mix_service, job_service, playlist_service)

        result = bridge.loadMix("favorites", "")
        assert bridge.stateName == "COMPLETED_WITH_TRACKS"

        original = playlist_service.add_track

        def _failing_add(pid, track_id=0, filepath=""):
            if track_id == 2:
                return {"ok": False, "error": "ADD_TRACK_FAILED"}
            return original(pid, track_id, filepath)

        monkeypatch.setattr(playlist_service, "add_track", _failing_add)

        saved = bridge.saveMixAsPlaylist("Mix Parcial")

        assert saved["ok"] is True
        assert saved["status"] == "PARTIAL_SUCCESS"
        assert saved["requested"] == len(TRACKS)
        assert saved["added"] == len(TRACKS) - 1
        assert saved["failed"] == 1

    def test_never_full_success_with_empty_playlist(self, app, job_service,
                                                    monkeypatch):
        db = _make_db(TRACKS)
        mix_service, playlist_service = _stack(db)
        _register(job_service, mix_service)
        bridge = _bridge(mix_service, job_service, playlist_service)

        bridge.loadMix("favorites", "")

        def _failing_add(pid, track_id=0, filepath=""):
            return {"ok": False, "error": "ADD_TRACK_FAILED"}

        monkeypatch.setattr(playlist_service, "add_track", _failing_add)

        saved = bridge.saveMixAsPlaylist("Mix Vacio")

        assert saved["ok"] is False
        assert saved["status"] == "FAILED"
        assert saved["added"] == 0
        assert saved["failed"] == len(TRACKS)


class TestStateMapping:
    def test_qml_state_matches_canonical(self):
        """The canonical status → QML-visible state mapping is 1:1."""
        from core.mix.models import MixGenerationStatus
        from ui_qml_bridge.mix_bridge import status_to_qml_state

        canonical = [s.value for s in MixGenerationStatus]
        for status in canonical:
            assert status_to_qml_state(status) == status

        mapped = [status_to_qml_state(s) for s in canonical]
        assert len(set(mapped)) == len(mapped), "mapping must be injective"
        assert status_to_qml_state("") == "FAILED"
        assert status_to_qml_state("WEIRD") == "FAILED"
