"""Runtime QML coverage for the shell visual-regression repair."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt, QObject, QPoint, QPointF, Property, QUrl, Signal, Slot
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

QML_DIR = Path(__file__).resolve().parents[2] / "ui_qml"
REPO_DIR = QML_DIR.parent


class HomeBridgeStub(QObject):
    snapshotChanged = Signal()

    def __init__(self, tracks: int, sources: int, jobs: int = 0, degraded: bool = False) -> None:
        super().__init__()
        self._tracks = tracks
        self._sources = sources
        self._jobs = jobs
        self._degraded = degraded

    @Property(int, notify=snapshotChanged)
    def libraryTracks(self) -> int:  # noqa: N802
        return self._tracks

    @Property(int, notify=snapshotChanged)
    def libraryAlbums(self) -> int:  # noqa: N802
        return max(0, self._tracks // 10)

    @Property(int, notify=snapshotChanged)
    def libraryArtists(self) -> int:  # noqa: N802
        return max(0, self._tracks // 20)

    @Property(int, notify=snapshotChanged)
    def sourcesCount(self) -> int:  # noqa: N802
        return self._sources

    @Property(int, notify=snapshotChanged)
    def activeJobs(self) -> int:  # noqa: N802
        return self._jobs

    @Property(bool, notify=snapshotChanged)
    def hasPlayback(self) -> bool:  # noqa: N802
        return False

    @Property(str, notify=snapshotChanged)
    def currentTrackTitle(self) -> str:  # noqa: N802
        return ""

    @Property(str, notify=snapshotChanged)
    def currentArtist(self) -> str:  # noqa: N802
        return ""

    @Property(bool, notify=snapshotChanged)
    def degraded(self) -> bool:
        return self._degraded

    @Property(str, notify=snapshotChanged)
    def degradedMessage(self) -> str:  # noqa: N802
        return "Conexiones no disponibles" if self._degraded else ""

    @Property(str, notify=snapshotChanged)
    def ecosystemState(self) -> str:  # noqa: N802
        return "not_configured"

    @Slot(result=bool)
    def refresh(self) -> bool:
        self.snapshotChanged.emit()
        return True


class NavigationStub(QObject):
    @Slot(str)
    def navigate(self, _route: str) -> None:
        pass


def _component(engine: QQmlEngine, relative_path: str) -> QQmlComponent:
    engine.addImportPath(str(QML_DIR))
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / relative_path)))
    assert component.isReady(), component.errorString()
    return component


def _process(qapp, delay: int = 30) -> None:
    qapp.processEvents()
    QTest.qWait(delay)
    qapp.processEvents()


def _named(root: QObject, name: str) -> QObject:
    found = root.findChild(QObject, name)
    assert found is not None, f"QML object not found: {name}"
    return found


def _visible_texts(item: QObject) -> list[str]:
    texts = []
    for child in item.findChildren(QQuickItem):
        text = child.property("text")
        if isinstance(text, str) and text and child.isVisible():
            texts.append(text)
    return texts


def _assert_visual_children_inside(container: QQuickItem, tolerance: float = 1.1) -> None:
    for child in container.findChildren(QQuickItem):
        if child is container or not child.isVisible() or child.width() <= 0 or child.height() <= 0:
            continue
        origin = child.mapToItem(container, QPointF(0, 0))
        right = origin.x() + child.width()
        bottom = origin.y() + child.height()
        assert origin.x() >= -tolerance, (child.objectName(), origin.x())
        assert origin.y() >= -tolerance, (child.objectName(), origin.y())
        assert right <= container.width() + tolerance, (child.objectName(), right, container.width())
        assert bottom <= container.height() + tolerance, (child.objectName(), bottom, container.height())


@pytest.mark.parametrize("material", ["GlassMaterial", "HeroMaterial"])
def test_material_content_is_above_background_and_clickable(qapp, material: str) -> None:
    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))
    source = f"""
import QtQuick
import QtQuick.Controls
import "{QML_DIR.as_uri()}/materials"
Window {{
    width: 360; height: 180; visible: true
    property int clickCount: 0
    {material} {{
        objectName: "testedMaterial"; anchors.fill: parent
        Text {{ objectName: "materialText"; x: 24; y: 24; text: "Contenido visible" }}
        Button {{
            objectName: "materialButton"; x: 24; y: 72; width: 150; height: 44
            text: "Acción"; onClicked: clickCount += 1
        }}
    }}
}}
"""
    component = QQmlComponent(engine)
    component.setData(source.encode(), QUrl.fromLocalFile(str(QML_DIR / "MaterialHarness.qml")))
    assert component.isReady(), component.errorString()
    window = component.create()
    assert window is not None
    try:
        _process(qapp)
        tested = _named(window, "testedMaterial")
        background = _named(tested, material.removesuffix("Material").lower() + "BackgroundLayer")
        content = _named(tested, material.removesuffix("Material").lower() + "ContentLayer")
        text = _named(tested, "materialText")
        button = _named(tested, "materialButton")
        assert text.property("visible") is True
        assert content.property("z") > background.property("z")
        scene_pos = button.mapToScene(QPointF(button.width() / 2, button.height() / 2))
        QTest.mouseClick(window, Qt.LeftButton, pos=QPoint(round(scene_pos.x()), round(scene_pos.y())))
        _process(qapp)
        assert window.property("clickCount") == 1
    finally:
        window.close()
        window.deleteLater()
        engine.deleteLater()


def _home_page(qapp, tracks: int, sources: int, width: int = 1200, degraded: bool = False):
    engine = QQmlEngine()
    bridge = HomeBridgeStub(tracks, sources, degraded=degraded)
    navigation = NavigationStub()
    engine.rootContext().setContextProperty("homeBridge", bridge)
    engine.rootContext().setContextProperty("navigationBridge", navigation)
    component = _component(engine, "pages/home/HomePage.qml")
    page = component.createWithInitialProperties({"width": width, "height": 900})
    assert page is not None
    page.setParent(engine)
    _process(qapp)
    return engine, page, bridge, navigation


def test_home_empty_and_ready_render_real_content(qapp) -> None:
    for tracks, sources, expected_state in ((0, 0, "EMPTY"), (120, 1, "READY")):
        engine, page, bridge, navigation = _home_page(qapp, tracks, sources)
        try:
            assert page.property("state") == expected_state
            hero = _named(page, "homeHero")
            if expected_state == "EMPTY":
                welcome = _named(page, "homeEmptyWelcome")
                assert welcome.property("visible") is True
                assert "Tu música comienza aquí" in _visible_texts(welcome)
                assert _named(page, "homeHero").property("visible") is False
                assert _named(page, "homeQuickGrid").property("visible") is False
            else:
                assert "Centro Michi" in _visible_texts(hero)
                for card_name in ("libraryStatusCard", "ecosystemCard", "assistantCard"):
                    card = _named(page, card_name)
                    assert card.property("visible") is True
                    assert _visible_texts(card), f"{card_name} contains no visible text"
        finally:
            page.deleteLater()
            engine.deleteLater()
            bridge.deleteLater()
            navigation.deleteLater()


@pytest.mark.parametrize("width", [500, 700, 900, 1500])
def test_home_quick_grid_uses_available_width(qapp, width: int) -> None:
    engine, page, bridge, navigation = _home_page(qapp, 120, 1, width)
    try:
        grid = _named(page, "homeQuickGrid")
        columns = grid.property("columnCount")
        assert 1 <= columns <= 4
        assert grid.property("cellWidth") >= 260 or columns == 1
    finally:
        page.deleteLater()
        engine.deleteLater()
        bridge.deleteLater()
        navigation.deleteLater()


def test_home_degraded_state_keeps_useful_content(qapp) -> None:
    engine, page, bridge, navigation = _home_page(qapp, 120, 1, degraded=True)
    try:
        assert page.property("state") == "DEGRADED"
        assert _named(page, "homeDegradedCard").property("visible") is True
        assert _named(page, "libraryStatusCard").property("visible") is True
        assert _named(page, "homeQuickGrid").property("visible") is True
    finally:
        page.deleteLater()
        engine.deleteLater()
        bridge.deleteLater()
        navigation.deleteLater()


def test_ecosystem_card_has_no_visual_overflow(qapp) -> None:
    engine = QQmlEngine()
    component = _component(engine, "pages/home/EcosystemCard.qml")
    card = component.createWithInitialProperties({"width": 640, "height": 210})
    assert card is not None
    try:
        _process(qapp)
        _assert_visual_children_inside(card)
    finally:
        card.deleteLater()
        engine.deleteLater()


def test_sidebar_icon_inventory_exists_and_loads(qapp) -> None:
    from ui_qml_bridge.route_registry import ROUTES
    icon_dir = QML_DIR.parent / "icons" / "sidebar"

    sidebar_routes = [
        r for r, info in ROUTES.items()
        if info.get("sidebar_visible") and info.get("sidebar_group") != "fixed_bottom"
    ]
    assert len(sidebar_routes) >= 10

    for route_key in sidebar_routes:
        info = ROUTES[route_key]
        icon_name = info.get("icon", "")
        if not icon_name:
            continue
        icon_path = icon_dir / f"{icon_name}.svg"
        assert icon_path.is_file(), f"Missing sidebar icon for {route_key}: {icon_path}"
        svg = icon_path.read_text(encoding="utf-8")
        assert 'viewBox="0 0 24 24"' in svg, f"Bad viewBox in {icon_path}"
        assert "<text" not in svg, f"Text in icon {icon_path}"
        assert "gradient" not in svg, f"Gradient in icon {icon_path}"


@pytest.mark.parametrize("width,height", [(1366, 96), (700, 112)])
def test_now_playing_bar_children_stay_inside(qapp, width: int, height: int) -> None:
    engine = QQmlEngine()
    component = _component(engine, "components/NowPlayingBar.qml")
    bar = component.createWithInitialProperties({"width": width})
    assert bar is not None
    try:
        _process(qapp)
        assert bar.property("height") == height
        _assert_visual_children_inside(bar, tolerance=2.1)
    finally:
        bar.deleteLater()
        engine.deleteLater()


def test_main_qml_produces_root_objects(qapp) -> None:
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_DIR))
    engine.load(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))
    try:
        _process(qapp, 50)
        assert engine.rootObjects()
        assert engine.rootObjects()[0].objectName() == "mainWindow"
    finally:
        for root in engine.rootObjects():
            root.close()
        engine.deleteLater()
