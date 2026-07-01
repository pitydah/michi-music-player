"""Tests for ALSA hw_params parser."""


class TestParseHwParams:
    def test_parse_44100_s16le(self):
        from audio.diagnostics.alsa_hw_params import parse_hw_params
        text = """access: MMAP_INTERLEAVED
format: S16_LE
subformat: STD
channels: 2
rate: 44100 (44100/1)
period_size: 1024
buffer_size: 8192
"""
        p = parse_hw_params(text)
        assert p.sample_rate == 44100
        assert p.format == "S16_LE"
        assert p.channels == 2
        assert p.period_size == 1024
        assert p.buffer_size == 8192
        assert p.access == "MMAP_INTERLEAVED"

    def test_parse_96000_s24le(self):
        from audio.diagnostics.alsa_hw_params import parse_hw_params
        text = """access: RW_INTERLEAVED
format: S24_LE
subformat: STD
channels: 2
rate: 96000 (96000/1)
period_size: 2048
buffer_size: 16384
"""
        p = parse_hw_params(text)
        assert p.sample_rate == 96000
        assert p.format == "S24_LE"
        assert p.channels == 2

    def test_parse_192000_s32le(self):
        from audio.diagnostics.alsa_hw_params import parse_hw_params
        text = """access: MMAP_INTERLEAVED
format: S32_LE
subformat: STD
channels: 2
rate: 192000 (192000/1)
period_size: 4096
buffer_size: 32768
"""
        p = parse_hw_params(text)
        assert p.sample_rate == 192000
        assert p.format == "S32_LE"

    def test_parse_s24_3le(self):
        from audio.diagnostics.alsa_hw_params import parse_hw_params
        text = """access: RW_INTERLEAVED
format: S24_3LE
subformat: STD
channels: 2
rate: 44100 (44100/1)
period_size: 1024
buffer_size: 8192
"""
        p = parse_hw_params(text)
        assert p.format == "S24_3LE"

    def test_parse_empty_text(self):
        from audio.diagnostics.alsa_hw_params import parse_hw_params
        p = parse_hw_params("")
        assert p.sample_rate == 0
        assert p.format == ""

    def test_parse_partial(self):
        from audio.diagnostics.alsa_hw_params import parse_hw_params
        text = "rate: 48000\nformat: S16_LE\n"
        p = parse_hw_params(text)
        assert p.sample_rate == 48000
        assert p.format == "S16_LE"

    def test_access_rw(self):
        from audio.diagnostics.alsa_hw_params import parse_hw_params
        text = "access: RW_INTERLEAVED\nrate: 44100\nformat: S16_LE\n"
        p = parse_hw_params(text)
        assert p.access == "RW_INTERLEAVED"


class TestBitperfectReport:
    def test_default_not_clean(self):
        from audio.diagnostics.bitperfect_report import BitperfectReport
        r = BitperfectReport()
        assert r.is_clean() is False
        assert r.status == "off"

    def test_verified_is_clean(self):
        from audio.diagnostics.bitperfect_report import BitperfectReport
        r = BitperfectReport(status="verified", verified=True)
        assert r.is_clean() is True

    def test_broken_not_clean(self):
        from audio.diagnostics.bitperfect_report import BitperfectReport
        r = BitperfectReport(
            status="broken",
            reasons=["EQ activo", "Resampling activo"])
        assert r.is_clean() is False
        assert len(r.reasons) == 2

    def test_reasons_list(self):
        from audio.diagnostics.bitperfect_report import BitperfectReport
        r = BitperfectReport(status="not_verified",
                             reasons=["No se pudo leer hw_params"])
        assert len(r.reasons) == 1
