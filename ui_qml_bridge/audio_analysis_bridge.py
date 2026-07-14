"""AudioAnalysisBridge — Advanced Audio Lab analysis bridge.

CJ: Analysis, ReplayGain, Normalization (destructive distinction), Integrity, Comparison, Batch.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal, Slot

logger = logging.getLogger("michi.audio_analysis")


def _typed_error(code: str, message: str = "") -> dict:
    return {"ok": False, "error": code, "message": message or code}


class AudioAnalysisBridge(QObject):
    dataChanged = Signal()

    def __init__(self, analysis_service=None, replaygain_service=None,
                 normalization_service=None, integrity_service=None,
                 comparison_service=None, batch_service=None, parent=None):
        super().__init__(parent)
        self._analysis = analysis_service
        self._replaygain = replaygain_service
        self._normalization = normalization_service
        self._integrity = integrity_service
        self._comparison = comparison_service
        self._batch = batch_service

    # ── Analysis ──

    @Slot(str, result=dict)
    def analyzeFile(self, filepath: str):
        if not self._analysis:
            return _typed_error("NO_ANALYSIS")
        try:
            result = self._analysis.analyze_file(filepath)
            return {"ok": True, **result}
        except Exception as e:
            return _typed_error("ANALYSIS_FAILED", str(e))

    @Slot(str, result=dict)
    def analyzeCodec(self, filepath: str):
        result = self.analyzeFile(filepath)
        return {"ok": result.get("ok", False), "codec": result.get("codec", "unknown")}

    @Slot(str, result=dict)
    def analyzeLoudness(self, filepath: str):
        if not self._analysis:
            return _typed_error("NO_ANALYSIS")
        try:
            r = self._analysis.analyze_file(filepath)
            return {"ok": True, "loudness": r.get("loudness", 0.0),
                    "peak": r.get("peak", 0.0)}
        except Exception as e:
            return _typed_error("LOUDNESS_FAILED", str(e))

    @Slot(str, result=dict)
    def detectClipping(self, filepath: str):
        if not self._analysis:
            return _typed_error("NO_ANALYSIS")
        try:
            result = self._analysis.analyze_file(filepath)
            peak = result.get("peak", 0.0)
            return {"ok": True, "clipping": peak >= 1.0, "peak": peak}
        except Exception as e:
            return _typed_error("CLIPPING_FAILED", str(e))

    @Slot(str, result=dict)
    def detectSilence(self, filepath: str):
        if not self._analysis:
            return _typed_error("NO_ANALYSIS")
        try:
            result = self._analysis.analyze_file(filepath)
            return {"ok": True, "silence": result.get("silence", False),
                    "silence_duration": result.get("silence_duration", 0.0)}
        except Exception as e:
            return _typed_error("SILENCE_FAILED", str(e))

    @Slot(str, result=dict)
    def computeChecksum(self, filepath: str):
        import hashlib
        try:
            h = hashlib.sha256()
            with open(filepath, "rb") as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    h.update(chunk)
            return {"ok": True, "checksum": h.hexdigest(), "algorithm": "sha256"}
        except Exception as e:
            return _typed_error("CHECKSUM_FAILED", str(e))

    @Slot(str, result=dict)
    def decodeFile(self, filepath: str):
        if not self._analysis:
            return _typed_error("NO_ANALYSIS")
        try:
            result = self._analysis.analyze_file(filepath)
            return {"ok": True, "decode_status": result.get("decode_status", "ok")}
        except Exception as e:
            return _typed_error("DECODE_FAILED", str(e))

    # ── ReplayGain ──

    @Slot(str, result=dict)
    def analyzeReplayGain(self, filepath: str):
        if not self._replaygain:
            return _typed_error("NO_REPLAYGAIN")
        try:
            result = self._replaygain.analyze(filepath)
            return {"ok": True, "track_gain": result.get("track_gain", 0.0),
                    "track_peak": result.get("track_peak", 0.0),
                    "album_gain": result.get("album_gain", 0.0),
                    "album_peak": result.get("album_peak", 0.0)}
        except Exception as e:
            return _typed_error("REPLAYGAIN_ANALYSIS_FAILED", str(e))

    @Slot(str, result=dict)
    def previewReplayGain(self, filepath: str):
        return self.analyzeReplayGain(filepath)

    @Slot(str, result=dict)
    def writeReplayGainTags(self, filepath: str):
        if not self._replaygain:
            return _typed_error("NO_REPLAYGAIN")
        try:
            self._replaygain.apply(filepath)
            return {"ok": True, "applied": True}
        except Exception as e:
            return _typed_error("REPLAYGAIN_WRITE_FAILED", str(e))

    @Slot("QVariantList", result=dict)
    def batchReplayGain(self, filepaths: list):
        results = []
        for fp in filepaths:
            r = self.analyzeReplayGain(fp)
            results.append({"filepath": fp, "ok": r.get("ok", False)})
        return {"ok": True, "results": results}

    @Slot(str, result=dict)
    def verifyReplayGain(self, filepath: str):
        if not self._replaygain:
            return _typed_error("NO_REPLAYGAIN")
        try:
            result = self._replaygain.verify(filepath)
            return {"ok": True, "verified": result.get("verified", False)}
        except Exception as e:
            return _typed_error("VERIFY_FAILED", str(e))

    # ── Normalization ──

    @Slot(str, result=dict)
    def normalizeFile(self, filepath: str):
        if not self._normalization:
            return _typed_error("NO_NORMALIZATION")
        try:
            result = self._normalization.normalize(filepath)
            return {"ok": True, "job_id": result}
        except Exception as e:
            return _typed_error("NORMALIZE_FAILED", str(e))

    @Slot(str, result=dict)
    def normalizeDestructive(self, filepath: str):
        return self.normalizeFile(filepath)

    # ── Integrity ──

    @Slot(str, result=dict)
    def checkIntegrity(self, filepath: str):
        if not self._integrity:
            return _typed_error("NO_INTEGRITY")
        try:
            result = self._integrity.check(filepath)
            status = result.status if hasattr(result, 'status') else "unknown"
            return {"ok": True, "status": status, "valid": status == "VALID"}
        except Exception as e:
            return _typed_error("INTEGRITY_FAILED", str(e))

    # ── Comparison ──

    @Slot(str, str, result=dict)
    def compareFiles(self, file_a: str, file_b: str):
        if not self._comparison:
            return _typed_error("NO_COMPARISON")
        try:
            result = self._comparison.compare(file_a, file_b)
            return {"ok": True, "identical": result.identical if hasattr(result, 'identical') else False}
        except Exception as e:
            return _typed_error("COMPARE_FAILED", str(e))

    # ── Batch ──

    @Slot("QVariantList", result=dict)
    def batchAnalyze(self, filepaths: list):
        if not self._batch:
            return _typed_error("NO_BATCH")
        try:
            batch_id = self._batch.create_batch(filepaths)
            return {"ok": True, "batch_id": batch_id}
        except Exception as e:
            return _typed_error("BATCH_FAILED", str(e))

    @Slot(str, result=dict)
    def batchCancel(self, batch_id: str):
        if not self._batch:
            return _typed_error("NO_BATCH")
        try:
            self._batch.cancel(batch_id)
            return {"ok": True}
        except Exception as e:
            return _typed_error("BATCH_CANCEL_FAILED", str(e))
