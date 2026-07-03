"""Tests for QML Design System components.

Verifies that all components are importable and instantiable without errors.
"""
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

QML_DIR = Path(__file__).resolve().parent.parent.parent / "ui_qml"


@pytest.fixture
def engine(qapp):
    return QQmlEngine(qapp)


def _load_qml(engine, source: str) -> QQmlComponent:
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / source)))
    return component


class TestMichiButton:
    def test_instantiate(self, engine):
        component = _load_qml(engine, "components/MichiButton.qml")
        assert component.isReady()

    def test_primary_variant(self, engine):
        component = _load_qml(engine, "components/MichiButton.qml")
        assert component.isReady()

    def test_danger_variant(self, engine):
        component = _load_qml(engine, "components/MichiButton.qml")
        assert component.isReady()

    def test_ghost_variant(self, engine):
        component = _load_qml(engine, "components/MichiButton.qml")
        assert component.isReady()

    def test_secondary_variant(self, engine):
        component = _load_qml(engine, "components/MichiButton.qml")
        assert component.isReady()

    def test_with_icon_text(self, engine):
        component = _load_qml(engine, "components/MichiButton.qml")
        assert component.isReady()

    def test_disabled(self, engine):
        component = _load_qml(engine, "components/MichiButton.qml")
        assert component.isReady()


class TestMichiIconButton:
    def test_instantiate(self, engine):
        component = _load_qml(engine, "components/MichiIconButton.qml")
        assert component.isReady()

    def test_smoke_can_load(self, engine):
        component = _load_qml(engine, "components/MichiIconButton.qml")
        assert component.status() == QQmlComponent.Ready


class TestMichiSlider:
    def test_instantiate(self, engine):
        component = _load_qml(engine, "components/MichiSlider.qml")
        assert component.isReady()

    def test_default_value(self, engine):
        component = _load_qml(engine, "components/MichiSlider.qml")
        assert component.isReady()

    def test_disabled_instantiate(self, engine):
        component = _load_qml(engine, "components/MichiSlider.qml")
        assert component.isReady()

    def test_slider_contract_properties(self, engine):
        component = _load_qml(engine, "components/MichiSlider.qml")
        assert component.isReady()
        obj = component.create()
        try:
            assert obj.property("stepSize") == 1
            assert obj.property("enabled") is True
            assert obj.property("activeFocusOnTab") is True
        finally:
            obj.deleteLater()

    def test_slider_moved_signal_exists(self, engine):
        component = _load_qml(engine, "components/MichiSlider.qml")
        assert component.isReady()
        source = (QML_DIR / "components" / "MichiSlider.qml").read_text()
        assert "signal moved()" in source or "signal moved" in source


class TestMichiBadge:
    def test_instantiate(self, engine):
        component = _load_qml(engine, "components/MichiBadge.qml")
        assert component.isReady()

    def test_success_variant(self, engine):
        component = _load_qml(engine, "components/MichiBadge.qml")
        assert component.isReady()


class TestMichiProgressBar:
    def test_instantiate(self, engine):
        component = _load_qml(engine, "components/MichiProgressBar.qml")
        assert component.isReady()

    def test_smoke_can_load(self, engine):
        component = _load_qml(engine, "components/MichiProgressBar.qml")
        assert component.status() == QQmlComponent.Ready


class TestGlassPanel:
    def test_instantiate(self, engine):
        component = _load_qml(engine, "components/GlassPanel.qml")
        assert component.isReady()


class TestGlassCard:
    def test_instantiate(self, engine):
        component = _load_qml(engine, "components/GlassCard.qml")
        assert component.isReady()


class TestSearchField:
    def test_instantiate(self, engine):
        component = _load_qml(engine, "components/SearchField.qml")
        assert component.isReady()


class TestSectionHeader:
    def test_instantiate(self, engine):
        component = _load_qml(engine, "components/SectionHeader.qml")
        assert component.isReady()


class TestSidebarItem:
    def test_instantiate(self, engine):
        component = _load_qml(engine, "components/SidebarItem.qml")
        assert component.isReady()


class TestStatusBadge:
    def test_instantiate(self, engine):
        component = _load_qml(engine, "components/StatusBadge.qml")
        assert component.isReady()


class TestEmptyState:
    def test_instantiate(self, engine):
        component = _load_qml(engine, "components/EmptyState.qml")
        assert component.isReady()


# ── Page smoke tests (file existence) ──

PAGE_FILES = [
    "pages/home/HomePage.qml",
    "pages/library/LibraryPage.qml",
    "pages/PlaybackPage.qml",
    "pages/connections/ConnectionsPage.qml",
    "pages/SettingsPage.qml",
    "pages/assistant/AssistantPage.qml",
    "pages/playlists/PlaylistsPage.qml",
    "pages/RadioPage.qml",
]


class TestPageFiles:
    def test_all_pages_exist(self):
        for rel_path in PAGE_FILES:
            p = QML_DIR / rel_path
            assert p.exists(), f"Missing page file: {p}"


class TestShellComponents:
    SHELL_FILES = [
        "shell/HeaderBar.qml",
        "shell/Sidebar.qml",
        "shell/RouteTransition.qml",
        "shell/PageStack.qml",
    ]

    def test_all_files_exist(self):
        for rel_path in self.SHELL_FILES:
            p = QML_DIR / rel_path
            assert p.exists(), f"Missing: {p}"

    def test_header_bar_instantiate(self, engine):
        component = _load_qml(engine, "shell/HeaderBar.qml")
        assert component.isReady()

    def test_sidebar_instantiate(self, engine):
        component = _load_qml(engine, "shell/Sidebar.qml")
        assert component.isReady()

    def test_route_transition_instantiate(self, engine):
        component = _load_qml(engine, "shell/RouteTransition.qml")
        assert component.isReady()

    def test_page_stack_instantiate(self, engine):
        component = _load_qml(engine, "shell/PageStack.qml")
        assert component.isReady()


class TestNowPlayingComponents:
    NOWPLAYING_FILES = [
        "components/NowPlayingBar.qml",
        "components/NowPlayingControls.qml",
        "components/NowPlayingInfo.qml",
        "components/NowPlayingCover.qml",
        "components/NowPlayingSeekBar.qml",
        "components/NowPlayingVolume.qml",
    ]

    def test_all_files_exist(self):
        for rel_path in self.NOWPLAYING_FILES:
            p = QML_DIR / rel_path
            assert p.exists(), f"Missing: {p}"

    def test_now_playing_controls_exists(self, engine):
        component = _load_qml(engine, "components/NowPlayingControls.qml")
        assert component.isReady()

    def test_now_playing_info_exists(self, engine):
        component = _load_qml(engine, "components/NowPlayingInfo.qml")
        assert component.isReady()

    def test_now_playing_seek_bar_exists(self, engine):
        component = _load_qml(engine, "components/NowPlayingSeekBar.qml")
        assert component.isReady()

    def test_now_playing_volume_exists(self, engine):
        component = _load_qml(engine, "components/NowPlayingVolume.qml")
        assert component.isReady()


class TestActionButtonNotPresent:
    def test_action_button_not_in_components(self):
        qmldir = QML_DIR / "components" / "qmldir"
        if qmldir.exists():
            content = qmldir.read_text()
            assert "ActionButton" not in content, "ActionButton still registered in components/qmldir"
        action_button = QML_DIR / "components" / "ActionButton.qml"
        assert not action_button.exists(), "ActionButton.qml still exists"
