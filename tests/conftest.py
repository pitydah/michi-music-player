"""Tests for Astra Music Player."""

import pytest
from PySide6.QtWidgets import QApplication

_app = None


@pytest.fixture(scope="session")
def qapp():
    global _app
    if _app is None:
        _app = QApplication.instance() or QApplication([])
    return _app


@pytest.fixture
def library_db(qapp):
    from library.library_db import LibraryDB
    db = LibraryDB()
    yield db
    db.close()
