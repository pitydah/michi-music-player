"""Fase Sync vertical slice — real device sync pipeline end to end.

Real pieces: fake discovery adapters (controlled DeviceInfo), real
SyncPlanner/TranscodePlanner/TransferAdapter/VerificationService, real
DurableJobService + WorkerManager, real SyncHistoryRepository (app DB),
real event bus. Only the EXTERNAL tool (ffmpeg) is simulated via a fake
ProcessController — the transcode control flow is real.

Falso éxito #8 contract: no parallel jobs, no hash() serials, no
in-memory history, no direct subprocess in the facade.
"""
from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication  # noqa: E402

from core.device_sync.discovery import DiscoveryComposite  # noqa: E402
from core.device_sync.models import DeviceInfo, DeviceProtocol  # noqa: E402
from core.device_sync.transfer import TransferAdapter  # noqa: E402
from core.event_bus import EventBus  # noqa: E402
from core.jobs.job_service import JobState  # noqa: E402
from core.worker_manager import WorkerManager  # noqa: E402

from tests.helpers.device_sync_stack import (  # noqa: E402
    make_device_sync_stack,
    register_handlers_for,
)

pytestmark = pytest.mark.isolation

_TERMINAL = (JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED)


# ── Controlled doubles ──


class FakeProc:
    """Fake SyncManagedProcess: simulates an external tool completing."""

    def __init__(self, cmd: str, args: list, stdout=None, slow: bool = False):
        self.pid = 4242
        self.cmd = cmd
        self.args = list(args)
        self.started_at = time.monotonic()
        self._stdout = stdout
        self._slow = slow
        self._polls = 0
        self._rc: int | None = None

    def poll(self) -> int | None:
        if self._slow:
            self._polls += 1
            time.sleep(0.02)
            if self._polls < 20:
                return None
        if self._rc is None:
            # Simulate the tool writing its output before exiting.
            tmp = self.args[-1]
            src = self.args[self.args.index("-i") + 1]
            with open(src, "rb") as fin, open(tmp, "wb") as fout:
                shutil.copyfileobj(fin, fout)
            self._rc = 0
        return self._rc

    def is_alive(self) -> bool:
        return self.poll() is None


class FakeProcessController:
    """ProcessController double: spawn_sync/cleanup_sync surface only."""

    def __init__(self, slow: bool = False):
        self.slow = slow
        self.spawned: list[list] = []
        self.cleaned: list[int] = []

    def spawn_sync(self, cmd: str = "", args=None, **kwargs):
        self.spawned.append([cmd] + list(args or []))
        return FakeProc(cmd, args or [], kwargs.get("stdout"), slow=self.slow)

    def cleanup_sync(self, pid: int) -> bool:
        self.cleaned.append(pid)
        return True

    def terminate_sync(self, pid: int) -> bool:
        return True

    def is_alive(self, pid: int) -> bool:
        return False

    def poll(self, pid: int) -> int | None:
        return 0


class FakeMscAdapter:
    """Controlled MSC adapter: one dedicated player (FUSE-style mount).

    Vendor FiiO is a brand HINT that contributes the capability profile
    (playlists) — protocol stays USB_MASS_STORAGE from the mount adapter.
    """

    def __init__(self, mount: Path, serial: str = "USB-SERIAL-001",
                 free_bytes: int = 10 * 1024**3, vendor: str = "FiiO",
                 model: str = "M11"):
        self.mount = mount
        self.serial = serial
        self.free_bytes = free_bytes
        self.vendor = vendor
        self.model = model

    def capability(self) -> str:
        return "msc"

    def discover(self) -> list[DeviceInfo]:
        if not self.mount.is_dir():
            return []
        return [DeviceInfo(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            label=self.mount.name,
            mount_point=str(self.mount),
            vendor=self.vendor,
            model=self.model,
            usb_serial=self.serial,
            volume_label=self.mount.name,
            music_directory="Music",
            free_bytes=self.free_bytes,
            total_bytes=64 * 1024**3,
            capabilities=["msc"],
        )]

    def probe(self, mount_path: str) -> DeviceInfo | None:
        if str(self.mount) == mount_path and self.mount.is_dir():
            return self.discover()[0]
        return None


class FakeMtpAdapter:
    """Controlled MTP adapter: declares MTP capability + narrow formats.

    The mount point simulates an MTP FUSE mount (jmtpfs/simple-mtpfs):
    MTP devices become filesystem-accessible, which is exactly how the
    transfer path reaches them.
    """

    def __init__(self, mount: Path, device_id: str = "MTP-PERSISTENT-7",
                 formats: set | None = None):
        self.mount = mount
        self.device_id = device_id
        self.formats = formats or {".mp3", ".aac", ".m4a"}

    def capability(self) -> str:
        return "mtp"

    def discover(self) -> list[DeviceInfo]:
        return [DeviceInfo(
            protocol=DeviceProtocol.ANDROID_MTP,
            label="Pixel Test",
            mount_point=str(self.mount),
            vendor="Google",
            model="Pixel",
            mtp_id=self.device_id,
            music_directory="Music",
            free_bytes=8 * 1024**3,
            total_bytes=128 * 1024**3,
            capabilities=["mtp"],
            declared_formats=set(self.formats),
        )]


class CorruptingTransferAdapter(TransferAdapter):
    """TransferAdapter that corrupts the destination after a success."""

    def transfer(self, item, ctx=None, progress_cb=None, device_mount=""):
        outcome = super().transfer(item, ctx, progress_cb, device_mount)
        if outcome.ok:
            Path(item.dest).write_bytes(b"CORRUPTED DATA")
        return outcome


def _source_tracks(tmp_path: Path) -> Path:
    music = tmp_path / "source"
    music.mkdir(exist_ok=True)
    flac = music / "track.flac"
    flac.write_bytes(b"fLaC" + bytes(range(256)) * 200)
    mp3 = music / "track.mp3"
    mp3.write_bytes(b"\xff\xfb" + bytes(range(256)) * 100)
    return music


@pytest.fixture
def app():
    instance = QCoreApplication.instance()
    return instance or QCoreApplication()


def _register(job_service, svc):
    register_handlers_for(svc, job_service)


def _wait_terminal(qtbot, job_service, job_id):
    qtbot.waitUntil(
        lambda: job_service.get_job(job_id) is not None
        and job_service.get_job(job_id).state in _TERMINAL,
        timeout=5000,
    )


# ── Vertical tests ──


class TestMscSyncFlow:
    def test_msc_sync_flow(self, app, qtbot, tmp_path):
        mount = tmp_path / "mount"
        mount.mkdir()
        (mount / "Music").mkdir()
        music = _source_tracks(tmp_path)
        events: list[dict] = []
        event_bus = EventBus()
        event_bus.subscribe("device_sync.completed", lambda data: events.append(data))

        wm = WorkerManager()
        svc = make_device_sync_stack(
            tmp_path,
            process_controller=FakeProcessController(),
            event_bus=event_bus,
            adapters=DiscoveryComposite([FakeMscAdapter(mount)]),
            worker_manager=wm,
        )
        job_service = svc._job_service
        _register(job_service, svc)

        result = svc.sync_to_device(
            "USB-SERIAL-001",
            [str(music / "track.flac"), str(music / "track.mp3")],
        )
        assert result["ok"] is True
        job_id = result["job_id"]

        _wait_terminal(qtbot, job_service, job_id)
        job = job_service.get_job(job_id)
        assert job.state == JobState.SUCCEEDED, job.errors

        dest_flac = mount / "Music" / "track.flac"
        dest_mp3 = mount / "Music" / "track.mp3"
        assert dest_flac.exists()
        assert dest_mp3.exists()
        assert dest_flac.stat().st_size == (music / "track.flac").stat().st_size

        history = svc.get_history()
        assert history and history[0]["status"] == "completed"
        assert history[0]["device_id"] == "USB-SERIAL-001"
        assert len(events) == 1
        assert events[0]["transferred"] == 2
        wm.shutdown()
        svc.shutdown()

    def test_format_compatible_is_copy(self, app, qtbot, tmp_path):
        mount = tmp_path / "mount"
        mount.mkdir()
        (mount / "Music").mkdir()
        music = _source_tracks(tmp_path)
        wm = WorkerManager()
        svc = make_device_sync_stack(
            tmp_path,
            process_controller=FakeProcessController(),
            adapters=DiscoveryComposite([FakeMscAdapter(mount)]),
            worker_manager=wm,
        )
        job_service = svc._job_service
        _register(job_service, svc)

        result = svc.sync_to_device("USB-SERIAL-001", [str(music / "track.mp3")])
        _wait_terminal(qtbot, job_service, result["job_id"])
        job = job_service.get_job(result["job_id"])
        assert job.state == JobState.SUCCEEDED, job.errors
        assert (mount / "Music" / "track.mp3").exists()
        assert list((mount / "Music").glob("*.part")) == []
        wm.shutdown()
        svc.shutdown()


class TestMtpSimulated:
    def test_mtp_sync_with_transcode(self, app, qtbot, tmp_path):
        mount = tmp_path / "mtp_mount"
        mount.mkdir()
        (mount / "Music").mkdir()
        music = _source_tracks(tmp_path)
        wm = WorkerManager()
        svc = make_device_sync_stack(
            tmp_path,
            process_controller=FakeProcessController(),
            adapters=DiscoveryComposite([FakeMtpAdapter(mount)]),
            worker_manager=wm,
        )
        job_service = svc._job_service
        _register(job_service, svc)

        result = svc.sync_to_device("MTP-PERSISTENT-7", [str(music / "track.flac")])
        _wait_terminal(qtbot, job_service, result["job_id"])
        job = job_service.get_job(result["job_id"])
        assert job.state == JobState.SUCCEEDED, job.errors

        # The transcode produced a real .mp3 on the device, verified.
        dest = mount / "Music" / "track.mp3"
        assert dest.exists()
        assert dest.stat().st_size > 0
        assert list((mount / "Music").glob("*.part")) == []
        wm.shutdown()
        svc.shutdown()

    def test_format_requires_transcode_planned(self, app, tmp_path):
        mount = tmp_path / "mtp_mount"
        mount.mkdir()
        (mount / "Music").mkdir()
        music = _source_tracks(tmp_path)
        svc = make_device_sync_stack(
            tmp_path,
            process_controller=FakeProcessController(),
            adapters=DiscoveryComposite([FakeMtpAdapter(mount)]),
        )
        result = svc.plan_sync("MTP-PERSISTENT-7", [str(music / "track.flac")])
        assert result["ok"] is True
        plan = result["plan"]
        assert plan["by_action"].get("transcode", 0) == 1
        assert plan["by_action"].get("copy", 0) == 0
        assert plan["total_files"] == 1
        assert plan["total_size"] == (music / "track.flac").stat().st_size
        svc.shutdown()


class TestSpaceValidation:
    def test_insufficient_space_fails_job(self, app, qtbot, tmp_path):
        mount = tmp_path / "mount"
        mount.mkdir()
        (mount / "Music").mkdir()
        music = _source_tracks(tmp_path)
        wm = WorkerManager()
        svc = make_device_sync_stack(
            tmp_path,
            process_controller=FakeProcessController(),
            adapters=DiscoveryComposite([
                FakeMscAdapter(mount, free_bytes=10),  # 10 bytes free
            ]),
            worker_manager=wm,
        )
        job_service = svc._job_service
        _register(job_service, svc)

        result = svc.sync_to_device("USB-SERIAL-001", [str(music / "track.flac")])
        _wait_terminal(qtbot, job_service, result["job_id"])
        job = job_service.get_job(result["job_id"])
        assert job.state == JobState.FAILED
        assert job.errors and job.errors[-1] == "SPACE_INSUFFICIENT"
        assert list((mount / "Music").iterdir()) == []
        history = svc.get_history()
        assert history and history[0]["status"] == "failed"
        wm.shutdown()
        svc.shutdown()


class TestVerification:
    def test_checksum_mismatch_fails(self, app, qtbot, tmp_path):
        mount = tmp_path / "mount"
        mount.mkdir()
        (mount / "Music").mkdir()
        music = _source_tracks(tmp_path)
        wm = WorkerManager()
        svc = make_device_sync_stack(
            tmp_path,
            process_controller=FakeProcessController(),
            adapters=DiscoveryComposite([FakeMscAdapter(mount)]),
            worker_manager=wm,
            transfer_adapter=CorruptingTransferAdapter(
                process_controller=FakeProcessController()),
        )
        job_service = svc._job_service
        _register(job_service, svc)

        result = svc.sync_to_device("USB-SERIAL-001", [str(music / "track.flac")])
        _wait_terminal(qtbot, job_service, result["job_id"])
        job = job_service.get_job(result["job_id"])
        assert job.state == JobState.FAILED
        assert job.errors and job.errors[-1] == "VERIFICATION_MISMATCH"
        history = svc.get_history()
        assert history and history[0]["status"] == "failed"
        assert "VERIFICATION_MISMATCH" in history[0]["error"]
        wm.shutdown()
        svc.shutdown()


class TestCancellation:
    def test_cancellation_no_partial_file(self, app, qtbot, tmp_path):
        mount = tmp_path / "mtp_mount"
        mount.mkdir()
        (mount / "Music").mkdir()
        music = _source_tracks(tmp_path)
        wm = WorkerManager()
        svc = make_device_sync_stack(
            tmp_path,
            process_controller=FakeProcessController(slow=True),
            adapters=DiscoveryComposite([FakeMtpAdapter(mount)]),
            worker_manager=wm,
        )
        job_service = svc._job_service
        _register(job_service, svc)

        result = svc.sync_to_device("MTP-PERSISTENT-7", [str(music / "track.flac")])
        job_id = result["job_id"]
        qtbot.waitUntil(
            lambda: job_service.get_job(job_id) is not None
            and job_service.get_job(job_id).state == JobState.RUNNING,
            timeout=5000,
        )
        assert job_service.cancel_job(job_id) is True
        _wait_terminal(qtbot, job_service, job_id)
        job = job_service.get_job(job_id)
        assert job.state == JobState.CANCELLED
        # No partial files left on the device.
        assert list((mount / "Music").iterdir()) == []
        wm.shutdown()
        svc.shutdown()

    def test_cancel_queued_job_no_partial(self, app, tmp_path):
        mount = tmp_path / "mtp_mount"
        mount.mkdir()
        (mount / "Music").mkdir()
        music = _source_tracks(tmp_path)
        svc = make_device_sync_stack(
            tmp_path,
            process_controller=FakeProcessController(),
            adapters=DiscoveryComposite([FakeMtpAdapter(mount)]),
        )
        job_service = svc._job_service
        _register(job_service, svc)

        job_id = job_service.create_job(
            "device_sync", owner="device:MTP-PERSISTENT-7",
            payload={"device_id": "MTP-PERSISTENT-7",
                     "track_ids": [str(music / "track.flac")]},
        )
        assert job_service.cancel_job(job_id) is True
        assert job_service.get_job(job_id).state == JobState.CANCELLED
        assert list((mount / "Music").iterdir()) == []
        svc.shutdown()


class TestRetry:
    def test_retry_same_payload(self, app, tmp_path):
        mount = tmp_path / "mount"
        mount.mkdir()
        (mount / "Music").mkdir()
        music = _source_tracks(tmp_path)
        svc = make_device_sync_stack(
            tmp_path,
            process_controller=FakeProcessController(),
            adapters=DiscoveryComposite([FakeMscAdapter(mount)]),
        )
        job_service = svc._job_service
        _register(job_service, svc)

        # Inline execution: first run fails (missing source), then retry
        # with the same payload succeeds after the file appears.
        missing = music / "late.flac"
        job_id = job_service.create_job(
            "device_sync", owner="device:USB-SERIAL-001",
            payload={"device_id": "USB-SERIAL-001",
                     "track_ids": [str(missing)],
                     "playlist_name": ""},
        )
        job_service.start_job(job_id)
        job = job_service.get_job(job_id)
        assert job.state == JobState.FAILED, job.errors

        missing.write_bytes(b"fLaC" + bytes(range(256)) * 50)
        assert job_service.retry_job(job_id) is True
        job = job_service.get_job(job_id)
        assert job.state == JobState.SUCCEEDED, job.errors
        assert job.payload["track_ids"] == [str(missing)]
        assert (mount / "Music" / "late.flac").exists()
        svc.shutdown()


class TestDeviceDisconnect:
    def test_device_disconnected_fails(self, app, qtbot, tmp_path):
        mount = tmp_path / "mount"
        mount.mkdir()
        (mount / "Music").mkdir()
        music = _source_tracks(tmp_path)
        wm = WorkerManager()
        svc = make_device_sync_stack(
            tmp_path,
            process_controller=FakeProcessController(),
            adapters=DiscoveryComposite([FakeMscAdapter(mount)]),
            worker_manager=wm,
        )
        job_service = svc._job_service
        _register(job_service, svc)

        # Pair the device first so the facade resolves it from the registry
        # even after the mount disappears (identity chain: USB serial).
        from core.device_sync.identity import resolve_identity

        resolved = resolve_identity(FakeMscAdapter(mount).discover()[0])
        assert svc.pair(svc._identity_from_info(resolved))["ok"] is True

        # Device disappears before the pipeline reaches the transfer step.
        shutil.rmtree(mount)
        result = svc.sync_to_device("USB-SERIAL-001", [str(music / "track.flac")])
        _wait_terminal(qtbot, job_service, result["job_id"])
        job = job_service.get_job(result["job_id"])
        assert job.state == JobState.FAILED
        assert job.errors and job.errors[-1] == "DEVICE_DISCONNECTED"
        assert list(Path(str(mount) + "_gone").parent.glob("**/*.part")) == []
        wm.shutdown()
        svc.shutdown()


class TestPlaylistGeneration:
    def test_playlist_written_and_persisted(self, app, qtbot, tmp_path):
        mount = tmp_path / "mount"
        mount.mkdir()
        (mount / "Music").mkdir()
        music = _source_tracks(tmp_path)
        wm = WorkerManager()
        svc = make_device_sync_stack(
            tmp_path,
            process_controller=FakeProcessController(),
            adapters=DiscoveryComposite([FakeMscAdapter(mount)]),
            worker_manager=wm,
        )
        job_service = svc._job_service
        _register(job_service, svc)

        result = svc.sync_to_device(
            "USB-SERIAL-001",
            [str(music / "track.flac"), str(music / "track.mp3")],
            playlist_name="Road Trip",
        )
        _wait_terminal(qtbot, job_service, result["job_id"])
        job = job_service.get_job(result["job_id"])
        assert job.state == JobState.SUCCEEDED, job.errors

        playlist = mount / "Music" / "Road Trip.m3u"
        assert playlist.exists()
        content = playlist.read_text(encoding="utf-8")
        assert "#EXTM3U" in content
        assert "track.flac" in content
        assert "track.mp3" in content

        history = svc.get_history()
        assert history and history[0]["status"] == "completed"
        assert history[0]["playlist_path"].endswith("Road Trip.m3u")
        wm.shutdown()
        svc.shutdown()


class TestResumeAfterRestart:
    def test_interrupted_job_retryable_same_payload(self, app, tmp_path):
        mount = tmp_path / "mount"
        mount.mkdir()
        (mount / "Music").mkdir()
        music = _source_tracks(tmp_path)
        jobs_db = str(tmp_path / "jobs.db")

        # Instance 1: create the job and simulate a crash while RUNNING.
        svc1 = make_device_sync_stack(
            tmp_path / "s1",
            process_controller=FakeProcessController(),
            adapters=DiscoveryComposite([FakeMscAdapter(mount)]),
            jobs_db=jobs_db,
        )
        js1 = svc1._job_service
        job_id = js1.create_job(
            "device_sync", owner="device:USB-SERIAL-001",
            payload={"device_id": "USB-SERIAL-001",
                     "track_ids": [str(music / "track.flac")],
                     "playlist_name": ""},
        )
        job = js1.get_job(job_id)
        job.state = JobState.RUNNING
        js1._save_job(job)
        svc1.shutdown()

        # Instance 2 (fresh process): RUNNING → INTERRUPTED, visible, retryable.
        svc2 = make_device_sync_stack(
            tmp_path / "s2",
            process_controller=FakeProcessController(),
            adapters=DiscoveryComposite([FakeMscAdapter(mount)]),
            jobs_db=jobs_db,
        )
        js2 = svc2._job_service
        recovered = js2.get_job(job_id)
        assert recovered is not None
        assert recovered.state == JobState.INTERRUPTED
        listed = [j for j in js2.list_jobs() if j["id"] == job_id]
        assert listed and listed[0]["state"] == "INTERRUPTED"

        _register(js2, svc2)
        assert js2.retry_job(job_id) is True
        job = js2.get_job(job_id)
        assert job.state == JobState.SUCCEEDED, job.errors
        assert job.payload["track_ids"] == [str(music / "track.flac")]
        assert (mount / "Music" / "track.flac").exists()
        svc2.shutdown()


class TestNoParallelJobs:
    def test_facade_has_no_jobs_dict(self):
        from core.device_sync_service import DeviceSyncService

        source = Path(DeviceSyncService.__module__.replace(".", "/") + ".py")
        text = source.read_text(encoding="utf-8")
        assert "self._jobs" not in text
        assert "import threading" not in text
        assert "import subprocess" not in text
        assert "subprocess.run" not in text
