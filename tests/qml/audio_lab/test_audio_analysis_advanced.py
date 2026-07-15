from __future__ import annotations
"""CJ — Advanced Audio Lab: Analysis, ReplayGain, Normalization, Integrity, Comparison, Batch."""

import os
import tempfile

import pytest
from unittest.mock import MagicMock

pytestmark = pytest.mark.isolation


class TestAudioAnalysisAdvanced:
    @pytest.fixture
    def sample_wav(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x02\x00\x44\xac\x00\x00\x10\xb1\x02\x00\x04\x00\x10\x00data\x00\x00\x00\x00")
            path = f.name
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def mock_analysis(self):
        svc = MagicMock()
        svc.analyze_file.return_value = {
            "codec": "pcm_s16le", "sample_rate": 44100, "bit_depth": 16,
            "channels": 2, "loudness": -12.5, "peak": 0.85,
            "clipping": False, "silence": False, "decode_status": "ok",
        }
        return svc

    @pytest.fixture
    def mock_replaygain(self):
        svc = MagicMock()
        svc.analyze.return_value = {"track_gain": -5.3, "track_peak": 0.95,
                                     "album_gain": -6.1, "album_peak": 0.92}
        svc.apply.return_value = {"applied": True}
        svc.verify.return_value = {"verified": True}
        return svc

    @pytest.fixture
    def mock_integrity(self):
        svc = MagicMock()
        result = MagicMock()
        result.status = "VALID"
        result.is_valid = True
        svc.check.return_value = result
        return svc

    @pytest.fixture
    def mock_comparison(self):
        svc = MagicMock()
        result = MagicMock()
        result.identical = True
        result.file_a = "/a.flac"
        result.file_b = "/b.flac"
        result.dimensions = []
        svc.compare.return_value = result
        return svc

    def test_analysis_codec_detection(self, mock_analysis, sample_wav):
        from ui_qml_bridge.audio_analysis_bridge import AudioAnalysisBridge
        bridge = AudioAnalysisBridge(analysis_service=mock_analysis)
        result = bridge.analyzeCodec(sample_wav)
        assert result["ok"] is True
        assert result["codec"] == "pcm_s16le"

    def test_analysis_loudness(self, mock_analysis, sample_wav):
        from ui_qml_bridge.audio_analysis_bridge import AudioAnalysisBridge
        bridge = AudioAnalysisBridge(analysis_service=mock_analysis)
        result = bridge.analyzeLoudness(sample_wav)
        assert result["ok"] is True
        assert result["loudness"] == -12.5
        assert result["peak"] == 0.85

    def test_analysis_clipping_detection(self, mock_analysis, sample_wav):
        from ui_qml_bridge.audio_analysis_bridge import AudioAnalysisBridge
        bridge = AudioAnalysisBridge(analysis_service=mock_analysis)
        result = bridge.detectClipping(sample_wav)
        assert result["ok"] is True
        assert result["clipping"] is False

    def test_analysis_silence_detection(self, mock_analysis, sample_wav):
        from ui_qml_bridge.audio_analysis_bridge import AudioAnalysisBridge
        bridge = AudioAnalysisBridge(analysis_service=mock_analysis)
        result = bridge.detectSilence(sample_wav)
        assert result["ok"] is True
        assert result["silence"] is False

    def test_analysis_checksum(self, sample_wav):
        from ui_qml_bridge.audio_analysis_bridge import AudioAnalysisBridge
        bridge = AudioAnalysisBridge()
        result = bridge.computeChecksum(sample_wav)
        assert result["ok"] is True
        assert result["algorithm"] == "sha256"
        assert len(result["checksum"]) == 64

    def test_analysis_decode(self, mock_analysis, sample_wav):
        from ui_qml_bridge.audio_analysis_bridge import AudioAnalysisBridge
        bridge = AudioAnalysisBridge(analysis_service=mock_analysis)
        result = bridge.decodeFile(sample_wav)
        assert result["ok"] is True
        assert result["decode_status"] == "ok"

    def test_replaygain_analyze(self, mock_replaygain, sample_wav):
        from ui_qml_bridge.audio_analysis_bridge import AudioAnalysisBridge
        bridge = AudioAnalysisBridge(replaygain_service=mock_replaygain)
        result = bridge.analyzeReplayGain(sample_wav)
        assert result["ok"] is True
        assert result["track_gain"] == -5.3

    def test_replaygain_write_tags(self, mock_replaygain, sample_wav):
        from ui_qml_bridge.audio_analysis_bridge import AudioAnalysisBridge
        bridge = AudioAnalysisBridge(replaygain_service=mock_replaygain)
        result = bridge.writeReplayGainTags(sample_wav)
        assert result["ok"] is True
        assert result["applied"] is True

    def test_replaygain_verify(self, mock_replaygain, sample_wav):
        from ui_qml_bridge.audio_analysis_bridge import AudioAnalysisBridge
        bridge = AudioAnalysisBridge(replaygain_service=mock_replaygain)
        result = bridge.verifyReplayGain(sample_wav)
        assert result["ok"] is True
        assert result["verified"] is True

    def test_replaygain_batch(self, mock_replaygain, sample_wav):
        from ui_qml_bridge.audio_analysis_bridge import AudioAnalysisBridge
        bridge = AudioAnalysisBridge(replaygain_service=mock_replaygain)
        result = bridge.batchReplayGain([sample_wav, sample_wav])
        assert result["ok"] is True
        assert len(result["results"]) == 2

    def test_integrity_check(self, mock_integrity, sample_wav):
        from ui_qml_bridge.audio_analysis_bridge import AudioAnalysisBridge
        bridge = AudioAnalysisBridge(integrity_service=mock_integrity)
        result = bridge.checkIntegrity(sample_wav)
        assert result["ok"] is True
        assert result["valid"] is True

    def test_comparison(self, mock_comparison):
        from ui_qml_bridge.audio_analysis_bridge import AudioAnalysisBridge
        bridge = AudioAnalysisBridge(comparison_service=mock_comparison)
        result = bridge.compareFiles("/a.flac", "/b.flac")
        assert result["ok"] is True
        assert result["identical"] is True

    def test_batch_analyze(self):
        from ui_qml_bridge.audio_analysis_bridge import AudioAnalysisBridge
        mock_batch = MagicMock()
        mock_batch.create_batch.return_value = "batch_001"
        bridge = AudioAnalysisBridge(batch_service=mock_batch)
        result = bridge.batchAnalyze(["/a.flac", "/b.flac"])
        assert result["ok"] is True
        assert result["batch_id"] == "batch_001"

    def test_batch_cancel(self):
        from ui_qml_bridge.audio_analysis_bridge import AudioAnalysisBridge
        mock_batch = MagicMock()
        bridge = AudioAnalysisBridge(batch_service=mock_batch)
        result = bridge.batchCancel("batch_001")
        assert result["ok"] is True

    def test_no_service_returns_error(self):
        from ui_qml_bridge.audio_analysis_bridge import AudioAnalysisBridge
        bridge = AudioAnalysisBridge()
        result = bridge.analyzeFile("/nonexistent.flac")
        assert result["ok"] is False

    def test_normalize_destructive(self):
        from ui_qml_bridge.audio_analysis_bridge import AudioAnalysisBridge
        mock_norm = MagicMock()
        mock_norm.normalize.return_value = "norm_job_001"
        bridge = AudioAnalysisBridge(normalization_service=mock_norm)
        result = bridge.normalizeDestructive("/test.flac")
        assert result["ok"] is True
