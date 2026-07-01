"""Tests for MusicBrainzPage — requires pytest-qt."""

from unittest.mock import patch


def test_musicbrainz_page_renders(qtbot):
    from ui.audio_lab.musicbrainz_page import MusicBrainzPage
    page = MusicBrainzPage()
    qtbot.addWidget(page)
    page.show()
    assert page.isVisible()
    assert page.navigate_requested is not None


def test_musicbrainz_apply_disabled_without_result(qtbot):
    from ui.audio_lab.musicbrainz_page import MusicBrainzPage
    page = MusicBrainzPage()
    qtbot.addWidget(page)
    assert not page._apply_btn.isEnabled()


def test_musicbrainz_kb_unavailable_no_crash(qtbot):
    from ui.audio_lab.musicbrainz_page import MusicBrainzPage
    page = MusicBrainzPage()
    qtbot.addWidget(page)
    page._search_input.setText("test")
    page._do_search()
    # No deberia crashear aunque KnowledgeBroker no este disponible


def test_musicbrainz_confirm_before_write(qtbot):
    """Verifica que write_tags no se llama sin confirmacion."""
    from ui.audio_lab.musicbrainz_page import MusicBrainzPage
    page = MusicBrainzPage()
    qtbot.addWidget(page)
    page._target = "/tmp/test.flac"
    page._results = [{"name": "Artist", "mbid": "abc123"}]
    page._results_list.addItem("Artist")
    page._results_list.setCurrentRow(0)
    page._apply_btn.setEnabled(True)
    # Simular confirmacion cancelada directamente
    with patch("ui.audio_lab.musicbrainz_page.QMessageBox.question",
               return_value=0x10000), \
         patch("metadata.tag_writer.write_tags") as mock_write:
        page._apply_btn.click()
        mock_write.assert_not_called()
