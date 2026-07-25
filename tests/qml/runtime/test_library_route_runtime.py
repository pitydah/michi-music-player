from __future__ import annotations

from pathlib import Path

import pytest


from .qml_component_helper import (
    QML_ROOT,
    create_qml_engine,
    load_qml_component,
)

REPO = Path(__file__).resolve().parents[3]
PLACEHOLDER_FULL = QML_ROOT / "pages" / "PlaceholderPage.qml"


def _assert_loaded_ok(result: dict, label: str) -> None:
    failures = []
    if result["status"] != "Ready":
        failures.append(f"status={result['status']} (expected Ready)")
    if result["errors"]:
        for err in result["errors"]:
            failures.append(
                f"  {err['url']}:{err['line']}:{err['column']} — {err['description']}"
            )
    if result["object"] is None:
        failures.append("object is None")

    source_resolved = Path(result["source"])
    if source_resolved == PLACEHOLDER_FULL:
        failures.append("resolved to PlaceholderPage.qml instead of expected source")

    assert not failures, f"{label}:\n" + "\n".join(failures)


def test_library_page_loads(qapp) -> None:
    engine = create_qml_engine()
    result = load_qml_component(
        "../pages/library/LibraryPage.qml",
        engine=engine,
        timeout_ms=10000,
    )
    _assert_loaded_ok(result, "LibraryPage.qml")

    if result.get("component"):
        result["component"].deleteLater()
    if result.get("object"):
        result["object"].deleteLater()
    if result.get("engine"):
        result["engine"].deleteLater()


def test_michi_library_toolbar_loads(qapp) -> None:
    engine = create_qml_engine()
    result = load_qml_component(
        "../components/MichiLibraryToolbar.qml",
        engine=engine,
        timeout_ms=10000,
    )
    _assert_loaded_ok(result, "MichiLibraryToolbar.qml")

    if result.get("component"):
        result["component"].deleteLater()
    if result.get("object"):
        result["object"].deleteLater()
    if result.get("engine"):
        result["engine"].deleteLater()


def test_michi_search_field_loads(qapp) -> None:
    engine = create_qml_engine()
    result = load_qml_component(
        "../components/MichiSearchField.qml",
        engine=engine,
        timeout_ms=10000,
    )
    _assert_loaded_ok(result, "MichiSearchField.qml")

    if result.get("component"):
        result["component"].deleteLater()
    if result.get("object"):
        result["object"].deleteLater()
    if result.get("engine"):
        result["engine"].deleteLater()


def test_library_filter_bar_loads(qapp) -> None:
    engine = create_qml_engine()
    result = load_qml_component(
        "../pages/library/LibraryFilterBar.qml",
        engine=engine,
        timeout_ms=10000,
    )
    _assert_loaded_ok(result, "LibraryFilterBar.qml")

    if result.get("component"):
        result["component"].deleteLater()
    if result.get("object"):
        result["object"].deleteLater()
    if result.get("engine"):
        result["engine"].deleteLater()


def test_library_status_header_loads(qapp) -> None:
    engine = create_qml_engine()
    result = load_qml_component(
        "../pages/library/LibraryStatusHeader.qml",
        engine=engine,
        timeout_ms=10000,
    )
    _assert_loaded_ok(result, "LibraryStatusHeader.qml")

    if result.get("component"):
        result["component"].deleteLater()
    if result.get("object"):
        result["object"].deleteLater()
    if result.get("engine"):
        result["engine"].deleteLater()


LIBRARY_SUB_ROUTES = [
    ("library.songs", "../pages/library/tracks/TracksPage.qml"),
    ("library.albums", "../pages/library/AlbumGridPage.qml"),
    ("library.artists", "../pages/library/ArtistGridPage.qml"),
    ("library.folders", "../pages/library/FolderBrowserPage.qml"),
]


@pytest.mark.parametrize(
    ("route", "source"),
    [pytest.param(r, s, id=r) for r, s in LIBRARY_SUB_ROUTES],
)
def test_library_sub_route_loads(qapp, route: str, source: str) -> None:
    result = load_qml_component(source, timeout_ms=10000)
    _assert_loaded_ok(result, f"{route} ({source})")

    if result.get("component"):
        result["component"].deleteLater()
    if result.get("object"):
        result["object"].deleteLater()
    if result.get("engine"):
        result["engine"].deleteLater()
