"""Tests for ArtworkPage — requires pytest-qt."""



def test_artwork_page_renders(qtbot):
    from ui.audio_lab.artwork_page import ArtworkPage
    page = ArtworkPage()
    qtbot.addWidget(page)
    page.show()
    assert page.isVisible()
    assert page.navigate_requested is not None




