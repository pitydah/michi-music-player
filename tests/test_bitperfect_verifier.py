"""Tests for Bit-Perfect Verifier.

Uses mocked ALSA hw_params and AudioFormatInfo/AudioDiagnostics.
"""

from unittest.mock import patch


class MockFormat:
    sample_rate = 44100
    bit_depth = 16
    channels = 2
    is_dsd = False
    is_stream = False
    codec = "FLAC"


class MockProfile:
    bitperfect = True
    key = "bitperfect_pcm"


class MockDiagnostics:
    device_string = "alsasink device=hw:0,0"
    eq_active = False
    replaygain_active = False
    spectrum_active = False
    resampling_active = False


class TestBitperfectVerifier:
    def test_off_when_not_bitperfect(self):
        from audio.diagnostics.bitperfect_verifier import verify_bitperfect
        from audio.format_probe import AudioFormatInfo

        class NonBPProfile:
            bitperfect = False
            key = "standard"

        fmt = AudioFormatInfo()
        report = verify_bitperfect(fmt, NonBPProfile(), MockDiagnostics())
        assert report.status == "off"
        assert report.requested is False

    def test_broken_with_eq(self):
        from audio.diagnostics.bitperfect_verifier import verify_bitperfect
        from audio.format_probe import AudioFormatInfo

        class EqDiag:
            device_string = "alsasink device=hw:0,0"
            eq_active = True
            replaygain_active = False
            spectrum_active = False
            resampling_active = False

        fmt = AudioFormatInfo(sample_rate=44100)
        report = verify_bitperfect(fmt, MockProfile(), EqDiag())
        assert report.reasons
        assert any("EQ" in r for r in report.reasons)

    def test_broken_with_replaygain(self):
        from audio.diagnostics.bitperfect_verifier import verify_bitperfect
        from audio.format_probe import AudioFormatInfo

        class RgDiag:
            device_string = "alsasink device=hw:0,0"
            eq_active = False
            replaygain_active = True
            spectrum_active = False
            resampling_active = False

        fmt = AudioFormatInfo(sample_rate=44100)
        report = verify_bitperfect(fmt, MockProfile(), RgDiag())
        assert any("ReplayGain" in r for r in report.reasons)

    def test_broken_with_spectrum(self):
        from audio.diagnostics.bitperfect_verifier import verify_bitperfect
        from audio.format_probe import AudioFormatInfo

        class SpecDiag:
            device_string = "alsasink device=hw:0,0"
            eq_active = False
            replaygain_active = False
            spectrum_active = True
            resampling_active = False

        fmt = AudioFormatInfo(sample_rate=44100)
        report = verify_bitperfect(fmt, MockProfile(), SpecDiag())
        assert any("Spectrum" in r for r in report.reasons)

    def test_broken_with_plughw(self):
        from audio.diagnostics.bitperfect_verifier import verify_bitperfect
        from audio.format_probe import AudioFormatInfo

        class PlugDiag:
            device_string = "alsasink device=plughw:0,0"
            eq_active = False
            replaygain_active = False
            spectrum_active = False
            resampling_active = False

        fmt = AudioFormatInfo(sample_rate=44100)
        report = verify_bitperfect(fmt, MockProfile(), PlugDiag())
        assert any("plughw" in r for r in report.reasons)

    def test_not_verified_no_active_device(self):
        from audio.diagnostics.bitperfect_verifier import verify_bitperfect
        from audio.format_probe import AudioFormatInfo

        with patch("audio.diagnostics.bitperfect_verifier.find_active_hw_params") as mock_find:
            mock_find.return_value = []
            fmt = AudioFormatInfo(sample_rate=44100)
            report = verify_bitperfect(fmt, MockProfile(), MockDiagnostics())
            assert report.status in ("not_verified", "broken")

    def test_not_verified_no_proc(self):
        from audio.diagnostics.bitperfect_verifier import verify_bitperfect
        from audio.format_probe import AudioFormatInfo

        with patch("audio.diagnostics.bitperfect_verifier.find_active_hw_params") as mock_find:
            mock_find.return_value = []
            fmt = AudioFormatInfo(sample_rate=44100)
            report = verify_bitperfect(fmt, MockProfile(), MockDiagnostics())
            assert "hw_params" in " ".join(report.reasons).lower() or report.status == "not_verified"

    def test_broken_channels_mismatch(self):
        from audio.diagnostics.bitperfect_verifier import verify_bitperfect
        from audio.format_probe import AudioFormatInfo
        from audio.diagnostics.alsa_hw_params import AlsaHwParams

        class MonoDiag:
            device_string = "alsasink device=hw:0,0"
            eq_active = False
            replaygain_active = False
            spectrum_active = False
            resampling_active = False

        fmt = AudioFormatInfo(sample_rate=44100, channels=2)
        mock_hw = AlsaHwParams(card=0, device=0, sample_rate=44100,
                                format="S16_LE", channels=6)
        with patch("audio.diagnostics.bitperfect_verifier.find_active_hw_params") as mock_find:
            mock_find.return_value = [mock_hw]
            report = verify_bitperfect(fmt, MockProfile(), MonoDiag())
            assert any("Canales" in r for r in report.reasons)
            assert report.status == "broken"

    def test_not_verified_when_no_matching_device(self):
        from audio.diagnostics.bitperfect_verifier import verify_bitperfect
        from audio.format_probe import AudioFormatInfo
        from audio.diagnostics.alsa_hw_params import AlsaHwParams

        class Hw1Diag:
            device_string = "alsasink device=hw:1,0"
            eq_active = False
            replaygain_active = False
            spectrum_active = False
            resampling_active = False

        fmt = AudioFormatInfo(sample_rate=44100, channels=2)
        mock_hw = AlsaHwParams(card=0, device=0, sample_rate=44100,
                                format="S16_LE", channels=2)
        with patch("audio.diagnostics.bitperfect_verifier.find_active_hw_params") as mock_find:
            mock_find.return_value = [mock_hw]
            report = verify_bitperfect(fmt, MockProfile(), Hw1Diag())
            assert report.status == "not_verified"
            assert any("no coincide" in r for r in report.reasons)
