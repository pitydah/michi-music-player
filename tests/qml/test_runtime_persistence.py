"""Tests for core/runtime_persistence.py — RuntimePersistence."""
import os
import tempfile
import json

import pytest

from core.runtime_persistence import (
    RuntimePersistence,
    PersistedQueue,
    PersistedPageState,
    PersistedJob,
    PersistedNotification,
    ConnectionProfileData,
    DeviceProfileData,
    AudioLabProfileData,
    CURRENT_SCHEMA_VERSION,
)


@pytest.fixture
def base_dir():
    with tempfile.TemporaryDirectory() as td:
        yield td


@pytest.fixture
def rp(base_dir):
    return RuntimePersistence(base_dir=base_dir)


def test_save_and_load_queue(rp):
    q = PersistedQueue(track_id="track_1", uid="uid_abc", current_index=2, position=45.5, shuffle=True, repeat="all", source="local")
    rp.save_queue(q)
    loaded = rp.load_queue()
    assert loaded is not None
    assert loaded.track_id == "track_1"
    assert loaded.uid == "uid_abc"
    assert loaded.current_index == 2
    assert loaded.position == 45.5
    assert loaded.shuffle is True
    assert loaded.repeat == "all"
    assert loaded.source == "local"
    assert loaded.schema_version == CURRENT_SCHEMA_VERSION


def test_load_queue_nonexistent(rp):
    assert rp.load_queue() is None


def test_save_and_load_page_state(rp):
    ps = PersistedPageState(current_route="/library/albums", scroll_position=120.5, filters={"genre": "Rock", "year": 2020})
    rp.save_page_state(ps)
    loaded = rp.load_page_state()
    assert loaded is not None
    assert loaded.current_route == "/library/albums"
    assert loaded.scroll_position == 120.5
    assert loaded.filters["genre"] == "Rock"


def test_save_and_load_jobs(rp):
    jobs = [
        PersistedJob(id="j1", type="scan", state="running", progress=50.0, payload={"path": "/music"}),
        PersistedJob(id="j2", type="convert", state="completed", progress=100.0),
    ]
    rp.save_jobs(jobs)
    loaded = rp.load_jobs()
    assert len(loaded) == 2
    assert loaded[0].id == "j1"
    assert loaded[0].type == "scan"
    assert loaded[0].state == "running"
    assert loaded[1].id == "j2"


def test_save_and_load_notifications(rp):
    notifs = [
        PersistedNotification(id="n1", type="warning", message="Disk full", timestamp=1000.0),
        PersistedNotification(id="n2", type="info", message="Scan complete", timestamp=2000.0),
    ]
    rp.save_notifications(notifs)
    loaded = rp.load_notifications()
    assert len(loaded) == 2
    assert loaded[0].id == "n1"
    assert loaded[0].message == "Disk full"
    assert loaded[1].id == "n2"


def test_save_and_load_connection_profiles(rp):
    profiles = [
        ConnectionProfileData(id="c1", name="Home Server", server_type="subsonic", url="http://192.168.1.100:4533"),
        ConnectionProfileData(id="c2", name="Remote", server_type="subsonic", url="https://music.example.com"),
    ]
    rp.save_connection_profiles(profiles)
    loaded = rp.load_connection_profiles()
    assert len(loaded) == 2
    assert loaded[0].name == "Home Server"
    assert loaded[1].url == "https://music.example.com"


def test_save_and_load_device_profiles(rp):
    profiles = [
        DeviceProfileData(id="d1", name="USB DAC", backend="alsa", output_device="hw:0,0"),
    ]
    rp.save_device_profiles(profiles)
    loaded = rp.load_device_profiles()
    assert len(loaded) == 1
    assert loaded[0].name == "USB DAC"
    assert loaded[0].output_device == "hw:0,0"


def test_save_and_load_audio_lab_profiles(rp):
    profiles = [
        AudioLabProfileData(id="a1", name="Lossless FLAC", format="FLAC", codec="flac", bitrate=0),
    ]
    rp.save_audio_lab_profiles(profiles)
    loaded = rp.load_audio_lab_profiles()
    assert len(loaded) == 1
    assert loaded[0].name == "Lossless FLAC"
    assert loaded[0].format == "FLAC"


def test_atomic_write_no_partial(base_dir):
    rp = RuntimePersistence(base_dir=base_dir)
    q = PersistedQueue(track_id="t1", uid="u1", current_index=0, position=10.0)
    rp.save_queue(q)
    queue_path = os.path.join(base_dir, "queue_state.json")
    assert os.path.isfile(queue_path)
    with open(queue_path) as f:
        data = json.load(f)
    assert data["track_id"] == "t1"
    assert data["schema_version"] == CURRENT_SCHEMA_VERSION


def test_schema_version_in_files(rp):
    ps = PersistedPageState(current_route="/home")
    rp.save_page_state(ps)
    page_path = os.path.join(rp._base_dir, "page_state.json")
    with open(page_path) as f:
        data = json.load(f)
    assert data.get("schema_version") == CURRENT_SCHEMA_VERSION


def test_load_corrupted_file_returns_none(base_dir):
    os.makedirs(base_dir, exist_ok=True)
    queue_path = os.path.join(base_dir, "queue_state.json")
    with open(queue_path, "w") as f:
        f.write("{corrupt-json")
    rp = RuntimePersistence(base_dir=base_dir)
    assert rp.load_queue() is None


def test_load_empty_jobs_returns_empty_list(rp):
    assert rp.load_jobs() == []


def test_load_empty_notifications_returns_empty_list(rp):
    assert rp.load_notifications() == []
