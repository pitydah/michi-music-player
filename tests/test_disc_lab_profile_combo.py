"""Tests: Disc Lab profile combo and EncoderService error cleanup."""

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QProcess


class TestDiscLabProfileCombo:

    @pytest.fixture
    def page(self, monkeypatch):
        monkeypatch.setattr("ui.audio_lab.michi_disc_lab_page.check_all_tools",
                            lambda: {})
        monkeypatch.setattr("ui.audio_lab.michi_disc_lab_page.DiscDetectionService",
                            MagicMock)
        monkeypatch.setattr("ui.audio_lab.michi_disc_lab_page.RipJobManager",
                            MagicMock)
        monkeypatch.setattr("ui.audio_lab.michi_disc_lab_page.EncoderService",
                            MagicMock)
        from ui.audio_lab.michi_disc_lab_page import MichiDiscLabPage
        return MichiDiscLabPage()

    def test_unavailable_profile_disabled(self, page):
        combo = page._profile_combo
        count = combo.count()
        found_disabled = False
        for i in range(count):
            if not combo.model().item(i).isEnabled():
                found_disabled = True
                assert combo.itemData(i) is None
        assert found_disabled, "No disabled profile found"

    def test_available_profile_has_format_data(self, page):
        combo = page._profile_combo
        count = combo.count()
        found_available = False
        for i in range(count):
            if combo.model().item(i).isEnabled():
                assert combo.itemData(i) is not None
                found_available = True
        assert found_available, "No available profile found"

    def test_on_import_returns_if_no_profile(self, page):
        page._profile_combo.setCurrentIndex(0)
        if page._profile_combo.currentData() is None:
            page._destination = "/tmp"
            page._drive_status.setText = MagicMock()
            page._on_import_disc()
            page._drive_status.setText.assert_called_once()


class TestEncoderServiceErrors:

    @pytest.fixture
    def encoder(self):
        from ui.audio_lab.services.encoder_service import EncoderService
        return EncoderService()

    def test_failed_to_start_cleans_up_process(self, encoder):
        mock_proc = MagicMock(spec=QProcess)
        encoder._processes = [mock_proc]
        encoder._on_encoder_error(QProcess.FailedToStart, "/tmp/a.wav", mock_proc)
        assert mock_proc not in encoder._processes

    def test_encoder_error_emitted(self, encoder):
        errors = []
        encoder.encode_error.connect(lambda ip, msg: errors.append((ip, msg)))
        encoder._on_encoder_error(QProcess.FailedToStart, "/tmp/a.wav")
        assert len(errors) == 1

    def test_no_zombie_process_after_error(self, encoder):
        mock_proc = MagicMock(spec=QProcess)
        encoder._processes = [mock_proc]
        initial_count = len(encoder._processes)
        encoder._on_encoder_error(QProcess.Crashed, "/tmp/a.wav", mock_proc)
        assert len(encoder._processes) < initial_count
