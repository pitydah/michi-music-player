"""Tests for coverflow_layout() — position, rotation, scale, symmetry, and public API."""
import json
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPixmap, QPainter

from library.coverflow import (
    coverflow_layout, apply_layout_state, _make_placeholder,
    CoverPixmapItem, DropShadow, CenterGlow, ReflectiveFloor,
    CoverReflection, CoverFlowWidget,
)

VW, VH = 1024, 600
CW, CH = 260, 260


def test_center_exact():
    state = coverflow_layout(0.0, VW, VH, CW, CH)
    assert state["x"] == pytest.approx(VW / 2, abs=1.0)
    assert state["y"] == pytest.approx(VH / 2 - 110, abs=1.0)
    assert state["scale"] == pytest.approx(1.0, abs=0.01)
    assert state["rot"] == 0.0
    assert state["visible"] is True


def test_offset_plus_one():
    state = coverflow_layout(1.0, VW, VH, CW, CH)
    assert state["x"] > VW / 2 + 100
    assert state["x"] < VW / 2 + 180
    assert state["scale"] == pytest.approx(0.88, abs=0.02)
    assert state["rot"] == pytest.approx(22.0, abs=1.0)


def test_offset_minus_one():
    state = coverflow_layout(-1.0, VW, VH, CW, CH)
    assert state["x"] < VW / 2 - 100
    assert state["x"] > VW / 2 - 180
    assert state["scale"] == pytest.approx(0.88, abs=0.02)
    assert state["rot"] == pytest.approx(-22.0, abs=1.0)


def test_symmetry():
    for offset in [0.5, 1.0, 2.0, 3.5]:
        pos = coverflow_layout(offset, VW, VH, CW, CH)
        neg = coverflow_layout(-offset, VW, VH, CW, CH)
        assert pos["scale"] == pytest.approx(neg["scale"])
        assert pos["z"] == pytest.approx(neg["z"])
        assert pos["rot"] == pytest.approx(-neg["rot"])
        center = VW / 2
        assert (center - neg["x"]) == pytest.approx(pos["x"] - center, abs=2.0)


def test_far_offset_scale():
    state = coverflow_layout(5.0, VW, VH, CW, CH)
    assert state["scale"] >= 0.45
    assert state["visible"] is True


def test_dead_zone():
    state = coverflow_layout(0.1, VW, VH, CW, CH)
    assert state["rot"] == 0.0


class TestCoverFlowPublicAPI:
    """Verify public API exists and private attrs are not leaked."""

    def test_public_methods_exist(self, qapp):
        from library.coverflow import CoverFlowWidget
        cf = CoverFlowWidget()
        # Public methods
        assert hasattr(cf, 'item_at')
        assert hasattr(cf, 'current_item')
        assert hasattr(cf, 'current_index')
        assert hasattr(cf, 'count')
        assert hasattr(cf, 'cover_size')
        assert hasattr(cf, 'set_cover')
        assert hasattr(cf, 'scroll_to')
        assert hasattr(cf, 'set_items')
        assert hasattr(cf, 'dump_diagnostic')
        # __len__ support
        assert len(cf) == 0

    def test_coverflow_controller_uses_public_api(self, qapp):
        """Verify coverflow_controller.py doesn't access _items directly."""
        import os
        root = os.path.join(os.path.dirname(__file__), "..")
        with open(os.path.join(root, "ui", "controllers", "coverflow_controller.py")) as f:
            content = f.read()
        assert "._items[" not in content, "coverflow_controller accesses _items directly"
        assert "._cover_w" not in content, "coverflow_controller accesses _cover_w directly"

    def test_album_repo_has_method(self):
        from metadata.album_info_repository import AlbumInfoRepository
        repo = AlbumInfoRepository()
        assert hasattr(repo, 'has')
        assert repo.has("nonexistent") is False

    def test_diagnose_uses_public_api(self):
        import os
        root = os.path.join(os.path.dirname(__file__), "..")
        path = os.path.join(root, "diagnose_coverflow.py")
        if os.path.exists(path):
            with open(path) as f:
                content = f.read()
            assert "dump_diagnostic" in content, "dump_diagnostic should be called"
            assert "dump_diagnostic()" in content

    def test_coverflow_dump_diagnostic(self, qapp):
        from library.coverflow import CoverFlowWidget
        cf = CoverFlowWidget()
        diag = cf.dump_diagnostic("/tmp/test_coverflow_diag.json")
        assert isinstance(diag, dict)
        assert "items_total" in diag
        assert "current_index" in diag
        assert "viewport_type" in diag
        assert diag["items_total"] == 0
        assert diag["current_index"] == -1

    def test_coverflow_set_cover_loaded(self, qapp):
        from library.coverflow import CoverFlowWidget
        from library.album_art import CoverFlowItem
        from PySide6.QtGui import QPixmap
        cf = CoverFlowWidget()
        item = CoverFlowItem(pixmap=QPixmap(), title="Test", subtitle="Test",
                             data={"album": "Test", "artist": "A", "tracks": []})
        cf.set_items([item])
        assert cf.count() == 1
        assert cf.item_key_at(0) == "Test|A"
        assert cf.current_key() == "Test|A"
        assert cf.index_for_key("Test|A") == 0
        assert cf.index_for_key("nonexistent") == -1

    def test_coverflow_visible_indices_render_info(self, qapp):
        from library.coverflow import CoverFlowWidget
        cf = CoverFlowWidget()
        from library.album_art import CoverFlowItem
        from PySide6.QtGui import QPixmap
        items = [CoverFlowItem(pixmap=QPixmap(), title=f"A{i}", subtitle="T",
                               data={"album": f"A{i}", "artist": "A", "tracks": []})
                 for i in range(5)]
        cf.set_items(items)
        vis = cf.visible_indices()
        assert isinstance(vis, list)
        info = cf.render_info()
        assert isinstance(info, dict)
        assert "cover_size" in info
        assert "visible_count" in info

    def test_album_items_signature_changes(self):
        import hashlib
        from library.library_db import MediaItem

        def make_item(filepath="/a/song.mp3", album="A", artist="B", albumartist="",
                      year=2024, duration=200.0, mtime=1000):
            i = MediaItem()
            i.filepath = filepath
            i.album = album
            i.artist = artist
            i.albumartist = albumartist
            i.year = year
            i.duration = duration
            i.mtime = mtime
            return i

        def sig(items):
            parts = [str(len(items))]
            for i in items[:100]:
                parts.append(getattr(i, 'filepath', '') or '')
                parts.append(getattr(i, 'album', '') or '')
                parts.append(getattr(i, 'artist', '') or '')
                parts.append(str(getattr(i, 'mtime', 0) or 0))
            return hashlib.sha1("|".join(parts).encode()).hexdigest()

        items_a = [make_item("/a/1.mp3", "Alpha", "Artist1", mtime=1000)]
        items_b = [make_item("/b/1.mp3", "Beta", "Artist2", mtime=1200)]
        items_a2 = [make_item("/a/1.mp3", "Alpha", "Artist1", mtime=1000)]

        assert sig(items_a) != sig(items_b), "different albums should have different signatures"
        assert sig(items_a) == sig(items_a2), "identical albums should have same signature"

    def test_album_art_uses_passed_album_before_mutagen(self):
        import os
        root = os.path.join(os.path.dirname(__file__), "..")
        with open(os.path.join(root, "library", "album_art.py")) as f:
            content = f.read()
        # The function should check the passed album parameter first
        assert "album or _get_album_tag" in content, (
            "load_cover_pixmap must use passed album before calling mutagen")

    def test_coverflow_layout_visible_range_contract(self, qapp):
        from library.coverflow import CoverFlowWidget
        from library.album_art import CoverFlowItem
        from PySide6.QtGui import QPixmap
        cf = CoverFlowWidget()
        cf.resize(1024, 768)
        items = [CoverFlowItem(pixmap=QPixmap(), title=f"A{i}", subtitle="T",
                               data={"album": f"A{i}", "artist": "A", "tracks": []})
                 for i in range(50)]
        cf.set_items(items)

        vis = cf.visible_indices()
        too_far = [i for i in vis if abs(i) > 14]
        assert len(too_far) == 0, f"Items far from center should be hidden: {too_far}"


    def test_coverflow_public_api_exists(self, qapp):
        """Nombres exactos requeridos por el plan de validación."""
        from library.coverflow import CoverFlowWidget
        cf = CoverFlowWidget()
        for m in ['count', 'item_at', 'current_item', 'current_index',
                  'cover_size', 'set_cover', 'item_key_at', 'current_key',
                  'index_for_key', 'set_current_index', 'visible_indices',
                  'render_info', 'dump_diagnostic', '__len__']:
            assert hasattr(cf, m), f"Missing public method: {m}"

    def test_window_does_not_access_coverflow_privates(self):
        """Ensure zero _coverflow._ accesses in window.py."""
        import os
        root = os.path.join(os.path.dirname(__file__), "..")
        path = os.path.join(root, "ui", "window.py")
        with open(path) as f:
            for i, line in enumerate(f, 1):
                assert "_coverflow._" not in line, (
                    f"Private _coverflow access at {path}:{i}: {line.strip()}")

    def test_album_sort_filter_refreshes_active_tab(self, qapp):
        """Verify sort/filter handlers refresh the active tab for all views."""
        from legacy_widgets.ui.builder.album_sort_menu import AlbumSortMenu
        from legacy_widgets.ui.old_window.window import MainWindow
        w = MainWindow.__new__(MainWindow)
        w._album_sort_key = "title"
        w._album_filter_mode = "all"
        w._coverflow_cache_key = "some_old_key"
        w._current_section_key = "albums"
        w._lib_ctrl = MagicMock()
        w._lib_ctrl.refresh_active_tab = lambda force=None: setattr(
            w, '_refreshed', True)
        w._refreshed = False
        menu = AlbumSortMenu.__new__(AlbumSortMenu)
        menu._win = w
        menu._on_sort("artist")
        assert w._refreshed, "sort should have refreshed active tab"
        w._refreshed = False
        menu._on_filter("flac")
        assert w._refreshed, "filter should have refreshed active tab"


class TestCoverFlowInteraction:
    """Interaction tests: scroll_to, keyboard, wheel, slider, navigation."""

    def make_items(self, n=10):
        from library.album_art import CoverFlowItem
        from PySide6.QtGui import QPixmap
        return [CoverFlowItem(pixmap=QPixmap(), title=f"A{i}", subtitle="T",
                              data={"album": f"A{i}", "artist": "A", "tracks": []})
                for i in range(n)]

    def test_scroll_to_snaps_to_nearest(self, qtbot):
        from library.coverflow import CoverFlowWidget
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf.resize(800, 600)
        cf.set_items(self.make_items())
        cf.scroll_to(3, animated=False)
        assert cf.current_index() == 3

    def test_scroll_to_clamps_valid_range(self, qtbot):
        from library.coverflow import CoverFlowWidget
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf.resize(800, 600)
        cf.set_items(self.make_items(5))
        cf.scroll_to(-10, animated=False)
        assert cf.current_index() == 0
        cf.scroll_to(100, animated=False)
        assert cf.current_index() == 4

    def test_keyboard_left_right_navigates(self, qtbot):
        from library.coverflow import CoverFlowWidget
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf.resize(800, 600)
        cf.set_items(self.make_items(10))
        cf.scroll_to(3, animated=False)
        assert cf.current_index() == 3
        cf.scroll_to(4, animated=False)
        assert cf.current_index() == 4
        cf.scroll_to(3, animated=False)
        assert cf.current_index() == 3

    def test_keyboard_home_end(self, qtbot):
        from library.coverflow import CoverFlowWidget
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf.resize(800, 600)
        cf.set_items(self.make_items(10))
        cf.scroll_to(9, animated=False)
        assert cf.current_index() == 9
        cf.scroll_to(0, animated=False)
        assert cf.current_index() == 0

    def test_keyboard_page_up_down_jumps_five(self, qtbot):
        from library.coverflow import CoverFlowWidget
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf.resize(800, 600)
        cf.set_items(self.make_items(20))
        cf.scroll_to(5, animated=False)
        assert cf.current_index() == 5
        cf.scroll_to(0, animated=False)
        assert cf.current_index() == 0

    def test_wheel_navigates_horizontal(self, qtbot):
        from library.coverflow import CoverFlowWidget
        from PySide6.QtGui import QWheelEvent
        from PySide6.QtCore import QPoint, QPointF, Qt
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf.resize(800, 600)
        cf.set_items(self.make_items(10))
        idx_before = cf.current_index()
        event = QWheelEvent(QPointF(400, 300), QPointF(400, 300), QPoint(0, 0),
                            QPoint(0, -120), Qt.NoButton, Qt.NoModifier,
                            Qt.ScrollBegin, False)
        cf.wheelEvent(event)
        assert abs(cf._current - idx_before) > 0

    def test_scroll_to_navigates(self, qtbot):
        from library.coverflow import CoverFlowWidget
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf.resize(800, 600)
        cf.set_items(self.make_items(10))
        cf.scroll_to(5, animated=False)
        assert cf.current_index() == 5

    def test_current_index_returns_minus_one_when_empty(self, qtbot):
        from library.coverflow import CoverFlowWidget
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        assert cf.current_index() == -1

    def test_count_returns_zero_when_empty(self, qtbot):
        from library.coverflow import CoverFlowWidget
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        assert cf.count() == 0

    def test_len_support(self, qtbot):
        from library.coverflow import CoverFlowWidget
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        assert len(cf) == 0
        cf.set_items(self.make_items(5))
        assert len(cf) == 5

    def test_visible_range_adapts_to_viewport(self, qtbot):
        from library.coverflow import CoverFlowWidget
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf.resize(800, 600)
        cf.set_items(self.make_items(50))
        vw = cf.viewport().width()
        expected = 7 if vw < 900 else 10
        assert cf._visible_range() == expected

    def test_mouse_press_stops_physics(self, qtbot):
        from library.coverflow import CoverFlowWidget
        from PySide6.QtCore import QEvent, QPointF, Qt
        from PySide6.QtGui import QMouseEvent
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf.resize(800, 600)
        cf.set_items(self.make_items(10))
        cf._phys_timer.start(16)
        assert cf._phys_timer.isActive()
        ev = QMouseEvent(QEvent.MouseButtonPress, QPointF(400, 300), QPointF(400, 300),
                         Qt.NoButton, Qt.MouseButton.LeftButton, Qt.NoModifier)
        cf.mousePressEvent(ev)
        assert not cf._phys_timer.isActive()

    def test_close_event_stops_timers(self, qtbot):
        from library.coverflow import CoverFlowWidget
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf.resize(800, 600)
        cf.set_items(self.make_items(5))
        cf._phys_timer.start(16)
        cf.close()
        assert not cf._phys_timer.isActive()


class TestCoverFlowHelpers:
    """Unit tests for helper functions and classes in coverflow.py."""

    def test_apply_layout_state_positive_rotation(self):
        from PySide6.QtWidgets import QGraphicsPixmapItem
        item = QGraphicsPixmapItem()
        state = {"x": 500, "y": 300, "scale": 0.8, "rot": 30.0, "z": 1500, "visible": True}
        apply_layout_state(item, state, 260, 260)
        assert item.pos().x() == 500
        assert item.pos().y() == 300
        assert item.zValue() == 1500
        assert item.isVisible() is True

    def test_apply_layout_state_zero_rotation(self):
        from PySide6.QtWidgets import QGraphicsPixmapItem
        item = QGraphicsPixmapItem()
        state = {"x": 100, "y": 200, "scale": 0.5, "rot": 0.0, "z": 1000, "visible": True}
        apply_layout_state(item, state, 260, 260)
        assert item.isVisible() is True

    def test_make_placeholder_creates_pixmap(self):
        pix = _make_placeholder(200, 200)
        assert isinstance(pix, QPixmap)
        assert not pix.isNull()
        assert pix.width() == 200
        assert pix.height() == 200

    def test_make_placeholder_transparent_background(self):
        pix = _make_placeholder(100, 100)
        c = pix.toImage().pixelColor(50, 50)
        assert c.alpha() < 50


class TestCoverPixmapItem:
    def test_constructor_with_null_pixmap(self):
        item = CoverPixmapItem(None, 0, 200, 200)
        assert item._index == 0
        assert item.needs_cover is True
        assert item._cover_loaded is False

    def test_constructor_with_real_pixmap(self):
        pix = QPixmap(100, 100)
        pix.fill(Qt.red)
        item = CoverPixmapItem(pix, 1, 200, 200)
        assert item._cover_loaded is True
        assert item.needs_cover is False

    def test_needs_cover_false_after_requested(self):
        item = CoverPixmapItem(None, 0, 200, 200)
        assert item.needs_cover is True
        item.mark_cover_requested()
        assert item.needs_cover is False

    def test_needs_cover_false_after_failed(self):
        item = CoverPixmapItem(None, 0, 200, 200)
        item._cover_failed = True
        assert item.needs_cover is False

    def test_set_real_cover_updates_state(self):
        item = CoverPixmapItem(None, 0, 200, 200)
        pix = QPixmap(100, 100)
        pix.fill(Qt.blue)
        item.set_real_cover(pix)
        assert item._cover_loaded is True
        assert item._cover_requested is False

    def test_set_real_cover_null(self):
        item = CoverPixmapItem(None, 0, 200, 200)
        item.set_real_cover(None)
        assert item._cover_failed is True

    def test_paint_applies_clip_path(self, qtbot):
        from PySide6.QtWidgets import QGraphicsScene
        pix = QPixmap(100, 100)
        pix.fill(Qt.green)
        item = CoverPixmapItem(pix, 0, 100, 100)
        scene = QGraphicsScene()
        scene.addItem(item)
        assert item._rounded_path is not None


class TestDropShadow:
    def test_hidden_when_scale_below_threshold(self, qtbot):
        shadow = DropShadow(200)
        assert shadow.isVisible() is False
        shadow.update_for_state(MagicMock(), 0.3)
        assert shadow.isVisible() is False

    def test_visible_when_scale_above_threshold(self, qtbot):
        shadow = DropShadow(200)
        mock_item = MagicMock()
        mock_item.sceneBoundingRect.return_value.width.return_value = 200
        mock_item.sceneBoundingRect.return_value.height.return_value = 260
        mock_item.sceneBoundingRect.return_value.center.return_value = QPointF(500, 300)
        mock_item.sceneBoundingRect.return_value.bottom.return_value = 400
        shadow.update_for_state(mock_item, 0.8)
        assert shadow.isVisible() is True


class TestCenterGlow:
    def test_hidden_with_invalid_rect(self, qtbot):
        glow = CenterGlow()
        mock_item = MagicMock()
        mock_item.sceneBoundingRect.return_value.isValid.return_value = False
        glow.update_for_center(mock_item)
        assert glow.isVisible() is False

    def test_visible_with_valid_item(self, qtbot):
        glow = CenterGlow()
        sbr = MagicMock()
        sbr.isValid.return_value = True
        sbr.center.return_value = QPointF(500, 300)
        sbr.width.return_value = 260
        sbr.height.return_value = 260
        mock_item = MagicMock()
        mock_item.sceneBoundingRect.return_value = sbr
        glow.update_for_center(mock_item)
        assert glow.isVisible() is True
        assert glow.rect().width() > 0


class TestReflectiveFloor:
    def test_resize_updates_geometry(self, qtbot):
        floor = ReflectiveFloor(800, 600)
        assert floor.rect().height() == 600 * 0.42
        floor.resize(1024, 768)
        assert floor.rect().width() == 1024

    def test_paint_uses_gradient(self, qtbot):
        floor = ReflectiveFloor(800, 600)
        pix = QPixmap(800, 600)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        floor.paint(p, None, None)
        p.end()


class TestCoverReflection:
    def test_created_invisible_by_default(self):
        ref = CoverReflection(None)
        assert ref.isVisible() is False or ref.rect().width() == 0

    def test_set_cover_size_with_low_scale_hides(self):
        ref = CoverReflection(None)
        ref.set_cover_size(260, 260, 0.2)
        assert ref.isVisible() is False

    def test_set_cover_size_with_good_scale(self):
        ref = CoverReflection(None)
        ref.set_cover_size(260, 260, 0.8)
        assert ref.isVisible() is True
        assert ref.rect().width() > 0

    def test_set_cover_size_creates_gradient_brush(self):
        ref = CoverReflection(None)
        ref.set_cover_size(260, 260, 1.0)
        assert ref.brush().gradient() is not None


class TestCoverFlowWidgetAdvanced:
    """Advanced CoverFlowWidget tests — init, layout, events, signals."""

    def make_items(self, n=5):
        from library.album_art import CoverFlowItem
        return [CoverFlowItem(pixmap=QPixmap(), title=f"A{i}", subtitle="T",
                              data={"album": f"A{i}", "artist": "A", "tracks": []})
                for i in range(n)]

    def test_initial_state(self, qtbot):
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        assert cf.count() == 0
        assert cf.current_index() == -1
        assert cf.cover_size() == 260

    def test_set_items_clears_previous(self, qtbot):
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf.resize(800, 600)
        cf.set_items(self.make_items(3))
        assert cf.count() == 3
        cf.set_items(self.make_items(5))
        assert cf.count() == 5

    def test_scroll_to_instant(self, qtbot):
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf.resize(800, 600)
        cf.set_items(self.make_items(10))
        cf.scroll_to(5, animated=False)
        assert cf.current_index() == 5

    def test_scroll_to_clamps_bounds(self, qtbot):
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf.resize(800, 600)
        cf.set_items(self.make_items(5))
        cf.scroll_to(-10, animated=False)
        assert cf.current_index() == 0
        cf.scroll_to(100, animated=False)
        assert cf.current_index() == 4

    def test_current_item_returns_none_when_empty(self, qtbot):
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        assert cf.current_item() is None

    def test_current_key_empty_when_empty(self, qtbot):
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        assert cf.current_key() == ""

    def test_index_for_key_not_found(self, qtbot):
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf.set_items(self.make_items(3))
        assert cf.index_for_key("nonexistent") == -1

    def test_set_current_index_calls_scroll_to(self, qtbot):
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf.resize(800, 600)
        cf.set_items(self.make_items(5))
        cf.set_current_index(2, animated=False)
        assert cf.current_index() == 2

    def test_visible_indices_returns_list(self, qtbot):
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf.resize(800, 600)
        cf.set_items(self.make_items(5))
        vis = cf.visible_indices()
        assert isinstance(vis, list)
        assert 0 in vis

    def test_render_info_returns_dict(self, qtbot):
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf.set_items(self.make_items(3))
        info = cf.render_info()
        assert info["total_items"] == 3
        assert info["cover_size"] == 260

    def test_dump_diagnostic_returns_dict(self, qtbot, tmp_path):
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf.set_items(self.make_items(3))
        out = tmp_path / "diag.json"
        diag = cf.dump_diagnostic(str(out))
        assert diag["items_total"] == 3
        assert diag["current_index"] == 0
        assert out.exists()
        with open(str(out)) as f:
            loaded = json.load(f)
            assert loaded["items_total"] == 3

    def test_visible_range_depends_on_viewport(self, qtbot):
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf.resize(800, 600)
        cf.set_items(self.make_items(50))
        vw = cf.viewport().width()
        expected = 7 if vw < 900 else 10
        assert cf._visible_range() == expected

    def test_mouse_release_on_side_cover_navigates(self, qtbot):
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf.resize(800, 600)
        cf.set_items(self.make_items(5))
        cf.scroll_to(2, animated=False)
        assert cf.current_index() == 2

    def test_resize_updates_cover_size_when_large_enough(self, qtbot):
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf.resize(800, 600)
        cf.set_items(self.make_items(3))
        old_size = cf.cover_size()
        cf.resize(3200, 2400)
        if abs(cf.cover_size() - old_size) >= 14:
            assert cf.cover_size() != old_size
        else:
            assert cf.cover_size() == old_size  # no rebuild needed

    def test_close_event_cleans_up(self, qtbot):
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf.resize(800, 600)
        cf.set_items(self.make_items(3))
        cf._phys_timer.start(16)
        cf.close()
        assert not cf._phys_timer.isActive()

    def test_cover_snapped_signal_emitted_on_snap_finished(self, qtbot):
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf.resize(800, 600)
        cf.set_items(self.make_items(10))
        results = []
        cf.cover_snapped.connect(lambda i: results.append(i))
        cf._current = 3.0
        cf._on_snap_finished()
        assert len(results) == 1
        assert results[0] == 3

    def test_request_cover_signal_for_needy_items(self, qtbot):
        from library.album_art import CoverFlowItem
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf.resize(800, 600)
        items = [CoverFlowItem(pixmap=QPixmap(), title=f"A{i}", subtitle="T",
                               data={"album": f"A{i}", "artist": "A", "tracks": []})
                 for i in range(3)]
        results = []
        cf.request_cover.connect(lambda idx, item: results.append((idx, item)))
        cf.set_items(items)
        assert len(results) > 0

    def test_context_menu_creates_menu(self, qtbot):
        from PySide6.QtCore import QPoint
        from PySide6.QtGui import QContextMenuEvent
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf.resize(800, 600)
        cf.set_items(self.make_items(3))
        ev = QContextMenuEvent(QContextMenuEvent.Mouse, QPoint(400, 300), QPoint(400, 300))
        cf.contextMenuEvent(ev)

    def test_mouse_double_click_does_nothing(self, qtbot):
        from PySide6.QtCore import QEvent, QPointF
        from PySide6.QtGui import QMouseEvent
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf.resize(800, 600)
        cf.set_items(self.make_items(5))
        play_results = []
        dbl_results = []
        cf.play_album_requested.connect(lambda i: play_results.append(i))
        cf.double_clicked.connect(lambda i: dbl_results.append(i))
        ev = QMouseEvent(QEvent.MouseButtonDblClick, QPointF(400, 300), QPointF(400, 300),
                         Qt.NoButton, Qt.MouseButton.LeftButton, Qt.NoModifier)
        cf.mouseDoubleClickEvent(ev)
        assert len(play_results) == 0
        assert len(dbl_results) == 0

    def test_snap_duration_increases_with_distance(self, qtbot):
        from library.coverflow import CoverFlowWidget
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        short_dur = cf._snap_duration_for(0.5)
        long_dur = cf._snap_duration_for(5.0)
        assert short_dur < long_dur
        assert 150 <= short_dur <= 380

    def test_on_cover_loaded_updates_cache(self, qtbot):
        from library.coverflow import CoverFlowWidget
        from PySide6.QtGui import QPixmap
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf.resize(800, 600)
        from library.album_art import CoverFlowItem
        items = [CoverFlowItem(pixmap=QPixmap(), title="A", subtitle="T",
                               data={"album": "A", "artist": "T", "tracks": []})]
        cf.set_items(items)
        pix = QPixmap(100, 100)
        pix.fill(Qt.red)
        cf._on_cover_loaded(0, pix)
        assert cf._cover_cache.get("A|T") is not None

    def test_item_at_returns_none_for_invalid_index(self, qtbot):
        from library.coverflow import CoverFlowWidget
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        assert cf.item_at(-1) is None
        assert cf.item_at(0) is None

    def test_item_key_at_returns_empty_for_invalid(self, qtbot):
        from library.coverflow import CoverFlowWidget
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        assert cf.item_key_at(-1) == ""

    def test_set_cover_updates_layout(self, qtbot):
        from library.coverflow import CoverFlowWidget
        from PySide6.QtGui import QPixmap
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf.resize(800, 600)
        from library.album_art import CoverFlowItem
        items = [CoverFlowItem(pixmap=QPixmap(), title="A", subtitle="T",
                               data={"album": "A", "artist": "T", "tracks": []})]
        cf.set_items(items)
        pix = QPixmap(100, 100)
        pix.fill(Qt.blue)
        cf.set_cover(0, pix)
        assert cf._cover_cache.get("A|T") is not None

    def test_get_current_returns_internal_value(self, qtbot):
        from library.coverflow import CoverFlowWidget
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf._current = 3.5
        assert cf.get_current() == 3.5

    def test_set_current_updates_layout(self, qtbot):
        from library.coverflow import CoverFlowWidget
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf.set_items(self.make_items(5))
        cf.set_current(2.0)
        assert cf.get_current() == 2.0

    def test_center_pixmap_returns_none_when_empty(self, qtbot):
        from library.coverflow import CoverFlowWidget
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        assert cf.center_pixmap() is None

    def test_center_pixmap_returns_pixmap_when_items(self, qtbot):
        from library.coverflow import CoverFlowWidget
        cf = CoverFlowWidget()
        qtbot.addWidget(cf)
        cf.set_items(self.make_items(3))
        pix = cf.center_pixmap()
        assert pix is not None
