"""AudioLabService — orchestrator for Audio Lab subsystems.

Coordinates probe, analysis, conversion, normalization, ReplayGain,
integrity, comparison, batch, and profile services.
"""
from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QObject, Signal

from core.worker_manager import WorkerManager

logger = logging.getLogger("michi.audio_lab.service")


class AudioLabService(QObject):
    stateChanged = Signal(str, object)

    def __init__(self, db: Any = None, worker_manager: WorkerManager | None = None, parent=None):
        super().__init__(parent)
        self._db = db
        self._wm = worker_manager
        self._subscribers: dict[str, list] = {}

        self._probe_service = None
        self._analysis_service = None
        self._conversion_service = None
        self._normalization_service = None
        self._replaygain_service = None
        self._integrity_service = None
        self._comparison_service = None
        self._batch_service = None
        self._profile_service = None
        self._job_adapter = None

    @property
    def probe(self):
        return self._probe_service

    @property
    def analysis(self):
        return self._analysis_service

    @property
    def conversion(self):
        return self._conversion_service

    @property
    def normalization(self):
        return self._normalization_service

    @property
    def replaygain(self):
        return self._replaygain_service

    @property
    def integrity(self):
        return self._integrity_service

    @property
    def comparison(self):
        return self._comparison_service

    @property
    def batch(self):
        return self._batch_service

    @property
    def profiles(self):
        return self._profile_service

    @property
    def jobs(self):
        return self._job_adapter

    def setup(self):
        from .audio_probe_service import AudioProbeService
        from .audio_analysis_service import AudioAnalysisService
        from .audio_conversion_service import AudioConversionService
        from .audio_normalization_service import AudioNormalizationService
        from .replaygain_service import ReplayGainService
        from .audio_integrity_service import AudioIntegrityService
        from .audio_comparison_service import AudioComparisonService
        from .audio_batch_service import AudioBatchService
        from .audio_lab_profile_service import AudioLabProfileService
        from .audio_lab_job_adapter import AudioLabJobAdapter

        self._probe_service = AudioProbeService(db=self._db, parent=self)
        self._analysis_service = AudioAnalysisService(db=self._db, wm=self._wm, parent=self)
        self._conversion_service = AudioConversionService(
            db=self._db, wm=self._wm, profile_service=self._profile_service, parent=self
        )
        self._normalization_service = AudioNormalizationService(db=self._db, wm=self._wm, parent=self)
        self._replaygain_service = ReplayGainService(db=self._db, wm=self._wm, parent=self)
        self._integrity_service = AudioIntegrityService(db=self._db, wm=self._wm, parent=self)
        self._comparison_service = AudioComparisonService(parent=self)
        self._profile_service = AudioLabProfileService(parent=self)
        self._batch_service = AudioBatchService(db=self._db, wm=self._wm, parent=self)
        self._job_adapter = AudioLabJobAdapter(
            db=self._db, wm=self._wm,
            probe=self._probe_service, analysis=self._analysis_service,
            conversion=self._conversion_service, normalization=self._normalization_service,
            replaygain=self._replaygain_service, integrity=self._integrity_service,
            comparison=self._comparison_service, parent=self,
        )

    def capability_map(self) -> dict[str, bool]:
        return {
            "probe": self._probe_service is not None,
            "analysis": self._analysis_service is not None,
            "conversion": self._conversion_service is not None,
            "normalization": self._normalization_service is not None,
            "replaygain": self._replaygain_service is not None,
            "integrity": self._integrity_service is not None,
            "comparison": self._comparison_service is not None,
            "batch": self._batch_service is not None,
            "profiles": self._profile_service is not None,
        }

    def status(self) -> dict[str, Any]:
        caps = self.capability_map()
        return {
            "available": any(caps.values()),
            "capabilities": caps,
            "uptime": 0.0,
        }
