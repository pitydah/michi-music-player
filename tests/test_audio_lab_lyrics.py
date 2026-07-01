"""Tests for LyricsPage — requires pytest-qt."""



def test_lyrics_page_renders(qtbot):
    from ui.audio_lab.lyrics_page import LyricsPage
    page = LyricsPage()
    qtbot.addWidget(page)
    page.show()
    assert page.isVisible()
    assert page.navigate_requested is not None


def test_lyrics_search_no_title_does_nothing(qtbot):
    from ui.audio_lab.lyrics_page import LyricsPage
    page = LyricsPage()
    qtbot.addWidget(page)
    page._title_input.setText("")
    page._search_lyrics()
    # No deberia crashear


def test_lyrics_lrclib_unavailable_no_crash(qtbot):
    from ui.audio_lab.lyrics_page import LyricsPage
    page = LyricsPage()
    qtbot.addWidget(page)
    page._title_input.setText("Test Song")
    page._artist_input.setText("Test Artist")
    page._search_lyrics()
