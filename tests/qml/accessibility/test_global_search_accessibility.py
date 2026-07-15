from __future__ import annotations

"""MS: Specialized accessibility — Global Search page."""


def test_global_search_page_has_focus():
    filepath = "ui_qml/pages/search/GlobalSearchPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "focus: true" in content


def test_global_search_page_has_accessible_role():
    filepath = "ui_qml/pages/search/GlobalSearchPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "Accessible.role" in content


def test_global_search_page_has_accessible_name():
    filepath = "ui_qml/pages/search/GlobalSearchPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "Accessible.name" in content


def test_global_search_page_keyboard_navigation():
    filepath = "ui_qml/pages/search/GlobalSearchPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "activeFocusOnTab" in content


def test_global_search_page_keyboard_activation():
    filepath = "ui_qml/pages/search/GlobalSearchPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "Keys.onReturnPressed" in content or "Keys.onEscapePressed" in content


def test_global_search_page_searching_accessible():
    filepath = "ui_qml/pages/search/GlobalSearchPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "searching" in content.lower()


def test_global_search_page_error_accessible():
    filepath = "ui_qml/pages/search/GlobalSearchPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "ErrorState" in content


def test_global_search_page_cancel_accessible():
    filepath = "ui_qml/pages/search/GlobalSearchPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "clearQuery" in content or "cancel" in content.lower()


def test_global_search_page_reduced_motion():
    filepath = "ui_qml/pages/search/GlobalSearchPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "MichiTheme" in content


def test_global_search_page_font_scaling():
    filepath = "ui_qml/pages/search/GlobalSearchPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "pixelSize" in content
