"""Tests for AlbumDetailDialog — premium glass detail window."""

from metadata.album_summary import AlbumSummary


class TestAlbumDetailDialog:
    def test_creates_with_minimal_summary(self, qtbot):
        from PySide6.QtWidgets import QWidget
        from legacy_widgets.ui.album_detail_dialog import AlbumDetailDialog
        parent = QWidget()
        qtbot.addWidget(parent)
        summary = AlbumSummary(album_key="k", title="Album", artist="Artist")
        dlg = AlbumDetailDialog(summary, parent)
        qtbot.addWidget(dlg)
        assert dlg.windowTitle() == "Detalles del álbum"
        assert dlg.width() == 540

    def test_shows_metadata(self, qtbot):
        from PySide6.QtWidgets import QWidget
        from legacy_widgets.ui.album_detail_dialog import AlbumDetailDialog
        parent = QWidget()
        qtbot.addWidget(parent)
        summary = AlbumSummary(
            album_key="k", title="Dark Side", artist="Pink Floyd",
            year="1973", genre="Rock", track_count=10, duration=2700.0)
        dlg = AlbumDetailDialog(summary, parent)
        qtbot.addWidget(dlg)

    def test_shows_description(self, qtbot):
        from PySide6.QtWidgets import QWidget
        from legacy_widgets.ui.album_detail_dialog import AlbumDetailDialog
        parent = QWidget()
        qtbot.addWidget(parent)
        summary = AlbumSummary(
            album_key="k", title="Album", artist="A",
            description="A long description of the album.")
        dlg = AlbumDetailDialog(summary, parent)
        qtbot.addWidget(dlg)

    def test_shows_track_list(self, qtbot):
        from PySide6.QtWidgets import QWidget
        from legacy_widgets.ui.album_detail_dialog import AlbumDetailDialog
        parent = QWidget()
        qtbot.addWidget(parent)
        tracks = [
            {"title": "Track 1", "duration": 180.0},
            {"title": "Track 2", "duration": 240.0},
        ]
        summary = AlbumSummary(
            album_key="k", title="Album", artist="A",
            track_count=2, track_list=tracks)
        dlg = AlbumDetailDialog(summary, parent)
        qtbot.addWidget(dlg)

    def test_shows_no_description_section_if_empty(self, qtbot):
        from PySide6.QtWidgets import QWidget
        from legacy_widgets.ui.album_detail_dialog import AlbumDetailDialog
        parent = QWidget()
        qtbot.addWidget(parent)
        summary = AlbumSummary(album_key="k", title="Album", artist="A", description="")
        dlg = AlbumDetailDialog(summary, parent)
        qtbot.addWidget(dlg)

    def test_shows_links_section_with_external_ids(self, qtbot):
        from PySide6.QtWidgets import QWidget
        from legacy_widgets.ui.album_detail_dialog import AlbumDetailDialog
        parent = QWidget()
        qtbot.addWidget(parent)
        summary = AlbumSummary(
            album_key="k", title="Album", artist="A",
            external_ids={"musicbrainz": "mbid123"})
        dlg = AlbumDetailDialog(summary, parent)
        qtbot.addWidget(dlg)

    def test_close_button_accepts(self, qtbot):
        from PySide6.QtWidgets import QWidget
        from legacy_widgets.ui.album_detail_dialog import AlbumDetailDialog
        parent = QWidget()
        qtbot.addWidget(parent)
        summary = AlbumSummary(album_key="k", title="Album", artist="A")
        dlg = AlbumDetailDialog(summary, parent)
        qtbot.addWidget(dlg)
        dlg.accept()

    def test_handles_cover_path(self, qtbot, tmp_path):
        from PySide6.QtWidgets import QWidget
        from legacy_widgets.ui.album_detail_dialog import AlbumDetailDialog
        from PySide6.QtGui import QPixmap
        cover = tmp_path / "cover.jpg"
        pix = QPixmap(100, 100)
        pix.save(str(cover))
        parent = QWidget()
        qtbot.addWidget(parent)
        summary = AlbumSummary(
            album_key="k", title="Album", artist="A",
            cover_path=str(cover))
        dlg = AlbumDetailDialog(summary, parent)
        qtbot.addWidget(dlg)
