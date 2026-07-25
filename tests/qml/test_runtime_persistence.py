"""Tests for RuntimePersistence's dictionary/list storage API."""

import json

import pytest

from core.runtime_persistence import CURRENT_SCHEMA_VERSION, RuntimePersistence


@pytest.fixture
def base_dir(tmp_path):
    return tmp_path / "runtime"


@pytest.fixture
def persistence(base_dir):
    return RuntimePersistence(base_dir=str(base_dir))


def test_write_and_read_dictionary(persistence, base_dir):
    queue = {"version": 3, "items": [{"track_uid": "uid1"}], "shuffle": False}

    persistence.write("queue", queue)

    assert persistence.read("queue") == queue
    on_disk = json.loads((base_dir / "queue_state.json").read_text())
    assert on_disk == {**queue, "schema_version": CURRENT_SCHEMA_VERSION}


@pytest.mark.parametrize(
    ("namespace", "filename"),
    [
        ("jobs", "jobs.json"),
        ("notifications", "notifications.json"),
        ("connection_profiles", "connection_profiles.json"),
        ("device_profiles", "device_profiles.json"),
        ("audio_lab_profiles", "audio_lab_profiles.json"),
    ],
)
def test_write_and_read_lists(persistence, base_dir, namespace, filename):
    values = [{"id": "one"}, {"id": "two"}]

    persistence.write(namespace, values)

    assert persistence.read(namespace) == values
    assert json.loads((base_dir / filename).read_text()) == values


def test_read_missing_namespace_returns_none(persistence):
    assert persistence.read("queue") is None
    assert persistence.read("unknown") is None


def test_delete_removes_persisted_value(persistence, base_dir):
    persistence.write("page_state", {"current_route": "/library"})

    persistence.delete("page_state")

    assert persistence.read("page_state") is None
    assert not (base_dir / "page_state.json").exists()


def test_transaction_updates_dictionary(persistence):
    persistence.write("page_state", {"current_route": "/home"})

    with persistence.transaction("page_state") as state:
        state["current_route"] = "/library/albums"
        state["filters"] = {"genre": "Rock"}

    assert persistence.read("page_state") == {
        "current_route": "/library/albums",
        "filters": {"genre": "Rock"},
        "schema_version": CURRENT_SCHEMA_VERSION,
    }


def test_corrupted_file_returns_none(base_dir):
    base_dir.mkdir()
    (base_dir / "queue_state.json").write_text("{corrupt-json")

    persistence = RuntimePersistence(base_dir=str(base_dir))

    assert persistence.read("queue") is None
