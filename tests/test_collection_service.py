from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from core.library.collection_service import CollectionService
from ui_qml_bridge.library_bridge import LibraryBridge


def _rule(field: str, operator: str, value: object) -> dict[str, object]:
    return {"field": field, "operator": operator, "value": value}


def test_collection_crud_persists_and_updates_timestamps() -> None:
    stored: dict[str, str] = {}

    with (
        patch("core.settings_manager.get", side_effect=lambda key: stored.get(key, "[]")),
        patch("core.settings_manager.set_", side_effect=stored.__setitem__),
        patch("core.library.collection_service.time.time", side_effect=[10.0, 20.0]),
    ):
        service = CollectionService()
        created = service.create("Jazz", [_rule("genre", "eq", "Jazz")])
        updated = service.update(created["collection"]["id"], name="Late jazz")

        assert created["ok"] is True
        assert updated["collection"]["name"] == "Late jazz"
        assert updated["collection"]["created"] == 10.0
        assert updated["collection"]["updated"] == 20.0
        assert json.loads(stored["library/smart_collections"])[0]["name"] == "Late jazz"


def test_collection_load_ignores_invalid_records_and_delete_reports_missing() -> None:
    payload = json.dumps([
        {
            "id": "valid",
            "name": "Rated",
            "rules": [{"field": "rating", "operator": "gte", "value": 4}],
            "logic": "AND",
        },
        {"id": "broken"},
    ])

    with patch("core.settings_manager.get", return_value=payload):
        service = CollectionService()

    assert [entry["id"] for entry in service.list()] == ["valid"]
    assert service.delete("missing") == {"ok": False, "error": "NOT_FOUND"}


def test_collection_rejects_invalid_logic_and_rules_without_persisting() -> None:
    with (
        patch("core.settings_manager.get", return_value="[]"),
        patch("core.settings_manager.set_") as save,
    ):
        service = CollectionService()
        invalid_logic = service.create("Broken", [_rule("genre", "eq", "Jazz")], "XOR")
        invalid_rule = service.create("Broken", [_rule("genre", "starts_with", "J")])

    assert invalid_logic == {"ok": False, "error": "INVALID_LOGIC"}
    assert invalid_rule == {"ok": False, "error": "INVALID_RULE"}
    save.assert_not_called()


def test_collection_query_applies_and_or_numeric_and_between_rules() -> None:
    tracks = [
        {"title": "Blue Train", "genre": "Jazz", "year": 1957, "play_count": 8},
        {"title": "Kind of Blue", "genre": "Jazz", "year": 1959, "play_count": 2},
        {"title": "Blue Monday", "genre": "Rock", "year": 1983, "play_count": 12},
    ]
    query_service = MagicMock()
    query_service.count_tracks.return_value = len(tracks)
    query_service.fetch_tracks.return_value = tracks

    with patch("core.settings_manager.get", return_value="[]"):
        service = CollectionService(query_service=query_service)
    first = service.create(
        "Classic jazz",
        [_rule("genre", "eq", "jazz"), _rule("year", "between", [1955, 1960])],
    )["collection"]
    second = service.create(
        "Blue or popular",
        [_rule("title", "contains", "blue"), _rule("plays", "gt", 10)],
        logic="OR",
    )["collection"]

    and_result = service.query(first["id"])
    or_result = service.query(second["id"], limit=2, offset=1)

    assert [item["title"] for item in and_result["items"]] == ["Blue Train", "Kind of Blue"]
    assert or_result["total"] == 3
    assert [item["title"] for item in or_result["items"]] == ["Blue Train", "Kind of Blue"]


def test_library_bridge_delegates_collection_slots() -> None:
    collection_service = MagicMock()
    collection_service.list.return_value = [{"id": "one", "name": "Jazz"}]
    collection_service.create.return_value = {"ok": True, "collection": {"id": "two"}}
    collection_service.delete.return_value = {"ok": True, "id": "one"}
    collection_service.query.return_value = {"ok": True, "items": [{"title": "Blue"}]}
    bridge = LibraryBridge(
        query_service=MagicMock(),
        collection_service=collection_service,
    )

    assert bridge.getCollections() == [{"id": "one", "name": "Jazz"}]
    assert bridge.createCollection(
        "Recent jazz", json.dumps([_rule("year", "gte", 2020)]), "AND"
    )["ok"] is True
    assert bridge.deleteCollection("one") == {"ok": True, "id": "one"}
    assert bridge.queryCollection("two", 50, 10)["items"] == [{"title": "Blue"}]
    collection_service.create.assert_called_once_with(
        "Recent jazz", [_rule("year", "gte", 2020)], "AND"
    )
