from core.audio_lab.diagnostics_helpers import supports_spectral_analysis


class TestDiagnosticsHelpers:
    def test_flac_supported(self):
        assert supports_spectral_analysis("/path/file.flac") is True

    def test_mp3_not_supported(self):
        assert supports_spectral_analysis("/path/file.mp3") is False
