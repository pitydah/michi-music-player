"""Runtime geometry gates for the Album Detail refinement.

Static source seals are insufficient for the original regression: the QML was
valid while ColumnLayout pressure collapsed the productive track table. These
gates mount the real LibraryContentHost/AlbumsView/AlbumDetailView chain and
measure rendered geometry at compact through XL widths, including a 360 px
content height that approximates the space left inside the shell at the
application's minimum-height window.
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

import pytest  # noqa: E402
from PySide6.QtCore import QPointF  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from test_library_context_host_a1 import (  # noqa: E402
    _find_any,
    _mount,
    _row,
    _wait_for,
)


@pytest.fixture(scope="module")
def qapp():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    yield app


@pytest.mark.parametrize(
    ("width", "height"),
    [
        (800, 360),
        (900, 480),
        (1200, 800),
        (1600, 900),
    ],
)
def test_album_detail_track_viewport_survives_context_pressure(qapp, width, height):
    view, _library = _mount(qapp, [_row()])
    view.resize(width, height)
    QTest.qWait(80)

    host = view.rootObject()
    host.setProperty("currentTab", "albums")
    QTest.qWait(280)

    detail = _find_any(host, lambda c: c.objectName() == "albumDetailView")
    assert detail is not None, "AlbumDetailView must be mounted"

    context_scroll = _find_any(detail, lambda c: c.objectName() == "albumContextScroll")
    table = _find_any(detail, lambda c: c.objectName() == "albumTracksTable")
    row = _wait_for(detail, "trackId", "T-1")

    assert context_scroll is not None
    assert table is not None
    assert row is not None

    # The context region is bounded and can scroll instead of consuming the
    # entire detail. The productive table must retain enough real height for
    # its header plus at least one actionable row.
    assert context_scroll.height() <= 441
    assert table.height() >= 80, (
        f"track table collapsed at {width}x{height}: {table.height()} px"
    )

    scene_top = row.mapToScene(QPointF(0, 0)).y()
    scene_bottom = scene_top + row.height()
    assert scene_top < view.height() and scene_bottom > 0, (
        f"first album track is outside viewport at {width}x{height}: "
        f"scene={scene_top:.1f}..{scene_bottom:.1f}, view={view.height()}"
    )

    view.close()
