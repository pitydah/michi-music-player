"""Contract tests for the canonical QML queue-item projection."""

from __future__ import annotations

import hashlib
from types import SimpleNamespace

import pytest

from ui_qml.models.queue_item import QueueItem, _cover_key_for_path, queue_item_from_raw

pytestmark = [pytest.mark.qml_module("queue")]

EXPECTED_KEYS = {
    "track_id",
    "track_uid",
    "title",
    "artist",
    "album",
    "album_key",
    "duration",
    "is_current",
    "position",
    "cover_key",
    "source_type",
}


def test_dict_and_object_inputs_converge_without_private_references() -> None:
    values = {
        "track_id": 42,
        "track_uid": "uid-42",
        "title": "Blue Train",
        "artist": "John Coltrane",
        "album": "Blue Train",
        "album_key": "album-42",
        "duration": 643.8,
        "filepath": "/music/blue-train.flac",
        "source_type": "local_file",
    }

    dict_projection = queue_item_from_raw(values, index=3, current_index=3).as_dict()
    object_projection = queue_item_from_raw(
        SimpleNamespace(**values), index=3, current_index=3
    ).as_dict()

    assert dict_projection == object_projection
    assert set(dict_projection) == EXPECTED_KEYS
    assert dict_projection["track_id"] == "42"
    assert dict_projection["duration"] == 643
    assert dict_projection["position"] == 3
    assert dict_projection["is_current"] is True
    assert "filepath" not in dict_projection
    assert "queue_index" not in dict_projection


def test_missing_values_use_typed_defaults_and_non_current_position() -> None:
    projection = queue_item_from_raw({}, index=2, current_index=1).as_dict()

    assert projection == {
        "track_id": "",
        "track_uid": "",
        "title": "",
        "artist": "",
        "album": "",
        "album_key": "",
        "duration": 0,
        "is_current": False,
        "position": 2,
        "cover_key": "",
        "source_type": "local_file",
    }
    assert isinstance(projection["duration"], int)
    assert isinstance(projection["position"], int)
    assert isinstance(projection["is_current"], bool)


def test_legacy_names_and_explicit_cover_key_are_normalized() -> None:
    projection = queue_item_from_raw(
        {
            "id": "legacy-7",
            "name": "Legacy title",
            "path": "/private/legacy.ogg",
            "cover_key": "provided-cover",
            "source_type": "",
        },
        index=0,
        current_index=-1,
    ).as_dict()

    assert projection["track_id"] == "legacy-7"
    assert projection["title"] == "Legacy title"
    assert projection["cover_key"] == "provided-cover"
    assert projection["source_type"] == "local_file"
    assert projection["is_current"] is False


def test_cover_key_is_stable_and_derived_from_private_path() -> None:
    filepath = "/music/Kind of Blue.flac"
    expected = f"track_{hashlib.md5(filepath.encode()).hexdigest()[:12]}"

    assert _cover_key_for_path(filepath) == expected
    assert queue_item_from_raw(
        {"filepath": filepath}, index=0, current_index=0
    ).as_dict()["cover_key"] == expected
    assert _cover_key_for_path("") == ""


def test_queue_item_defaults_match_qml_contract() -> None:
    assert QueueItem().as_dict() == {
        "track_id": "",
        "track_uid": "",
        "title": "",
        "artist": "",
        "album": "",
        "album_key": "",
        "duration": 0,
        "is_current": False,
        "position": 0,
        "cover_key": "",
        "source_type": "local_file",
    }
