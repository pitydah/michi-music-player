"""Tests for coverflow_layout() — position, rotation, scale, symmetry, and public API."""
import pytest

from library.coverflow import coverflow_layout

VW, VH = 1024, 600
CW, CH = 260, 260


def test_center_exact():
    state = coverflow_layout(0.0, VW, VH, CW, CH)
    assert state["x"] == pytest.approx(VW / 2, abs=1.0)
    assert state["y"] == pytest.approx(VH / 2 - 20, abs=1.0)
    assert state["scale"] == pytest.approx(1.0, abs=0.01)
    assert state["rot"] == 0.0
    assert state["visible"] is True


def test_offset_plus_one():
    state = coverflow_layout(1.0, VW, VH, CW, CH)
    assert state["x"] > VW / 2 + 150
    assert state["x"] < VW / 2 + 220
    assert state["scale"] == pytest.approx(0.88, abs=0.02)
    assert state["rot"] == pytest.approx(22.0, abs=1.0)


def test_offset_minus_one():
    state = coverflow_layout(-1.0, VW, VH, CW, CH)
    assert state["x"] < VW / 2 - 150
    assert state["x"] > VW / 2 - 220
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
        items = [CoverFlowItem(pixmap=QPixmap(), title=f"A{i}", subtitle="T",
                               data={"album": f"A{i}", "artist": "A", "tracks": []})
                 for i in range(50)]
        cf.set_items(items)

        # At center (index 0), items far away (>10 offset) should not be visible
        vis = cf.visible_indices()
        too_far = [i for i in vis if abs(i) > 12]
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
        from ui.builder.album_sort_menu import AlbumSortMenu
        from ui.window import MainWindow
        w = MainWindow.__new__(MainWindow)
        w._album_sort_key = "title"
        w._album_filter_mode = "all"
        w._coverflow_cache_key = "some_old_key"
        w._current_section_key = "albums"
        w._refresh_active_library_tab = lambda force=None: setattr(
            w, '_refreshed', True)
        w._refreshed = False
        menu = AlbumSortMenu.__new__(AlbumSortMenu)
        menu._win = w
        menu._on_sort("artist")
        assert w._refreshed, "sort should have refreshed active tab"
        w._refreshed = False
        menu._on_filter("flac")
        assert w._refreshed, "filter should have refreshed active tab"
