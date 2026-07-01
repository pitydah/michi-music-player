"""Tests for MichiDiscLabPage — requires pytest-qt."""



def test_disc_lab_page_renders(qtbot):
    from ui.audio_lab.michi_disc_lab_page import MichiDiscLabPage
    page = MichiDiscLabPage()
    qtbot.addWidget(page)
    page.show()
    assert page.isVisible()


def test_disc_lab_detects_tools(qtbot):
    from ui.audio_lab.michi_disc_lab_page import MichiDiscLabPage
    page = MichiDiscLabPage()
    qtbot.addWidget(page)
    page._update_diagnostics()
    # No debe crashear
    assert page._diag_text is not None


def test_disc_lab_no_drive_no_crash(qtbot):
    from ui.audio_lab.michi_disc_lab_page import MichiDiscLabPage
    page = MichiDiscLabPage()
    qtbot.addWidget(page)
    page._on_import_disc()
    # No debe crashear si no hay disco
