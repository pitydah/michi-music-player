"""R7-12 — falsifiable closure gates for Cover Flow pointer lifecycle.

These tests intentionally stay narrow.  The productive authority remains
AlbumsView -> Loader -> AlbumPathView -> AlbumBrowseState.  They seal the
specific regression where one physical drag that becomes a flick could arm
pointer intent twice and overwrite the identity captured at movement start.
"""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import QPoint, Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtTest import QSignalSpy, QTest  # noqa: E402

from tests.test_album_browse_identity_modes_runtime import (  # noqa: E402
    _assert_visual_identity,
    _bounded_wait,
    _loaded_view,
    _mount_albums_view,
    _path_delegates,
    _process,
    _switch_mode,
    _variant,
)

QML = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"


@pytest.fixture(scope="module")
def qapp():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    yield app


def _cover_world(tmp_path):
    world = _mount_albums_view(tmp_path)
    _switch_mode(world, "cover")
    return world


def _model(world):
    item = _loaded_view(world)
    model = item.property("albumModel")
    return model.toVariant() if hasattr(model, "toVariant") else model


def _invoke_noargs(item, name):
    meta = item.metaObject()
    index = meta.indexOfMethod(f"{name}()")
    assert index >= 0, f"{name}() no existe en AlbumPathView"
    assert meta.method(index).invoke(item), f"no se pudo invocar {name}()"


def _delegate_for_key(item, key):
    return next(
        (
            delegate
            for delegate in _path_delegates(item)
            if _variant(delegate.property("modelData")).get("key") == key
        ),
        None,
    )


def _delegate_center_in_view(world, delegate):
    content = world["view"].contentItem()
    mapped = delegate.mapToItem(content, 0, 0)
    return QPoint(
        int(mapped.x() + delegate.width() / 2),
        int(mapped.y() + delegate.height() / 2),
    )


def _movement_settled(item, movement_ended):
    return movement_ended.count() >= 1 and item.property("moving") is False


class TestPointerLifecycleContract:
    def test_qml_has_one_movement_authority_and_idempotent_begin(self):
        """Static topology seal: flick phases may not arm/settle identity."""
        source = (QML / "views" / "AlbumPathView.qml").read_text(encoding="utf-8")
        assert "onMovementStarted: albumsPath.beginPointerIntent()" in source
        assert "onMovementEnded: albumsPath.settlePointerIntent()" in source
        assert "onFlickStarted:" not in source
        assert "onFlickEnded:" not in source

        begin = source[source.index("function beginPointerIntent()") :]
        begin = begin[: begin.index("function settlePointerIntent()")]
        assert "if (browsePointerIntentActive)" in begin
        assert "browsePointerStartKey = browseState ? browseState.currentKey" in begin

    def test_duplicate_begin_cannot_overwrite_start_identity(self, tmp_path, qapp):
        """RED on 7ed8a99: a second begin (the old flickStarted path) must
        not replace A with an external X.  At settle, X wins and the visual
        projection is restored to X instead of being overwritten by B."""
        world = _cover_world(tmp_path)
        try:
            item = _loaded_view(world)
            model = _model(world)
            assert len(model) >= 3
            state = world["state"]
            a_key = model[0]["key"]
            b_key = model[1]["key"]
            x_key = model[2]["key"]

            state.setProperty("currentKey", a_key)
            item.setProperty("currentIndex", 0)
            QTest.qWait(200)
            _process()

            _invoke_noargs(item, "beginPointerIntent")
            assert item.property("browsePointerIntentActive") is True
            assert item.property("browsePointerStartKey") == a_key

            # External intent wins while the physical movement is alive.
            state.setProperty("currentKey", x_key)

            # Simulate a duplicate phase-start call.  The historical bug
            # rewrote startKey to X here, making the stale gesture authoritative.
            _invoke_noargs(item, "beginPointerIntent")
            assert item.property("browsePointerStartKey") == a_key, (
                "duplicate begin overwrote the identity captured at movement start"
            )

            # Gesture projection drifts to B before it settles.
            item.setProperty("currentIndex", 1)
            assert model[item.property("currentIndex")]["key"] == b_key

            _invoke_noargs(item, "settlePointerIntent")
            QTest.qWait(120)
            _process()

            assert item.property("browsePointerIntentActive") is False
            assert item.property("browsePointerStartKey") == ""
            assert state.property("currentKey") == x_key, (
                "stale pointer gesture overwrote the newer external identity"
            )
            index = _assert_visual_identity(world, "cover")
            assert model[index]["key"] == x_key
        finally:
            world["view"].close()


class TestRealPointerEvidence:
    def test_real_flick_emits_flick_signal_and_commits_after_movement(
        self, tmp_path, qapp
    ):
        """A genuine mouse flick must emit flickStarted, settle, and leave
        visual identity == canonical identity.  Merely waiting for
        flicking == false is not accepted as evidence that a flick occurred."""
        world = _cover_world(tmp_path)
        try:
            item = _loaded_view(world)
            model = _model(world)
            assert len(model) >= 3
            state = world["state"]
            state.setProperty("currentKey", model[0]["key"])
            item.setProperty("currentIndex", 0)
            QTest.qWait(220)
            _process()

            delegate = _delegate_for_key(item, model[0]["key"])
            assert delegate is not None, "delegate inicial de Cover Flow no encontrado"
            start = _delegate_center_in_view(world, delegate)

            movement_started = QSignalSpy(item.movementStarted)
            flick_started = QSignalSpy(item.flickStarted)
            movement_ended = QSignalSpy(item.movementEnded)
            assert movement_started.isValid()
            assert flick_started.isValid()
            assert movement_ended.isValid()

            # Fast, continuous release velocity.  Multiple small moves keep
            # this a real pointer gesture rather than a programmatic index set.
            QTest.mousePress(world["view"], Qt.LeftButton, Qt.NoModifier, start)
            for delta in (35, 75, 120, 170, 225, 285):
                QTest.mouseMove(world["view"], QPoint(start.x() - delta, start.y()))
                QTest.qWait(8)
            QTest.mouseRelease(
                world["view"],
                Qt.LeftButton,
                Qt.NoModifier,
                QPoint(start.x() - 285, start.y()),
            )

            assert _bounded_wait(lambda: flick_started.count() >= 1, timeout_ms=1500), (
                "el gesto no produjo flickStarted: no es evidencia de flick real"
            )
            assert movement_started.count() >= 1
            assert _bounded_wait(
                lambda: _movement_settled(item, movement_ended),
                timeout_ms=4000,
            ), "el movimiento/flick no terminó"
            QTest.qWait(120)
            _process()

            index = _assert_visual_identity(world, "cover")
            assert index != 0, "el flick fue observado pero no desplazó el álbum"
            assert state.property("currentKey") == model[index]["key"]
            assert item.property("browsePointerIntentActive") is False
            assert item.property("browsePointerStartKey") == ""
        finally:
            world["view"].close()

    def test_direct_double_click_a_to_b_transfers_and_opens(self, tmp_path, qapp):
        """No priming single click: A selected -> direct mouseDClick(B)
        must transfer canonical identity to B and open exactly B."""
        world = _cover_world(tmp_path)
        try:
            item = _loaded_view(world)
            model = _model(world)
            assert len(model) >= 2
            state = world["state"]
            a_key = model[0]["key"]
            b_key = model[1]["key"]
            state.setProperty("currentKey", a_key)
            item.setProperty("currentIndex", 0)
            QTest.qWait(220)
            _process()

            delegate_b = _delegate_for_key(item, b_key)
            assert delegate_b is not None, "delegate B de Cover Flow no encontrado"
            pos = _delegate_center_in_view(world, delegate_b)
            opened = []
            world["lb"].library_changed.connect(
                lambda: opened.append(world["lb"].property("selectedAlbumKey"))
            )

            # Deliberately NO QTest.mouseClick() before mouseDClick().
            QTest.mouseDClick(world["view"], Qt.LeftButton, Qt.NoModifier, pos)
            assert _bounded_wait(
                lambda: (
                    b_key in opened or world["lb"].property("selectedAlbumKey") == b_key
                ),
                timeout_ms=2000,
            ), f"double click directo no abrió B: {opened}"
            assert state.property("currentKey") == b_key, (
                "double click directo abrió sin transferir identidad canónica a B"
            )
        finally:
            world["view"].close()
