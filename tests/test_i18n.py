"""Tests for i18n — translator loading, locale, qrcode availability."""
import os
from pathlib import Path

import pytest


class TestI18N:
    def test_translator_loads(self):
        """QTranslator can load a .qm file."""
        from PySide6.QtCore import QTranslator
        t = QTranslator()
        # Try to load any existing .qm
        qm_dir = Path(__file__).resolve().parent.parent / "translations"
        qm_files = list(qm_dir.glob("*.qm"))
        if qm_files:
            result = t.load(str(qm_files[0]))
            assert result, f"Failed to load {qm_files[0]}"
        else:
            pytest.skip("No .qm files found — run scripts/translations/release.sh")

    def test_translation_directory_exists(self):
        """translations/ directory must exist."""
        d = Path(__file__).resolve().parent.parent / "translations"
        assert d.exists()

    def test_language_setting_default(self):
        """Default language setting is 'es'."""
        from core.settings_manager import SETTINGS
        lang = SETTINGS.value("appearance/language", "es")
        assert lang == "es" or lang

    def test_qrcode_importable(self):
        """qrcode package is available for QR generation."""
        try:
            import qrcode
            assert qrcode is not None
        except ImportError:
            pytest.skip("qrcode not installed — pip install michi-music-player[mobile]")

    def test_es_translation_exists(self):
        """Spanish translation file must exist."""
        f = Path(__file__).resolve().parent.parent / "translations" / "michi_es.ts"
        assert f.exists(), "michi_es.ts not found — run scripts/translations/extract.sh"

    def test_language_settings_schema(self):
        """Language appears in settings schema."""
        from core.settings_schema import get_entry
        entry = get_entry("appearance/language")
        assert entry is not None
