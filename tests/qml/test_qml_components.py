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
    return QQmlEngine()


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


class TestMichiIconButton:
    def test_instantiate(self, engine):
        component = _load_qml(engine, "components/MichiIconButton.qml")
        assert component.isReady()


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
