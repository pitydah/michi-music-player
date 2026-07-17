"""AudioLabService — lifecycle owner for Audio Lab subsystems."""
from __future__ import annotations

import importlib.util
import logging
import shutil
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
        self._started = False

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
        self._cd_ripper_service = None
        self._adc_recorder_service = None

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

    @property
    def cd_ripper(self):
        return self._cd_ripper_service

    @property
    def adc_recorder(self):
        return self._adc_recorder_service

    def start(self):
        """Initialize all modules exactly once for the service container."""
        if not self._started:
            self.setup()
            self._started = True
            self.stateChanged.emit("ready", self.capability_map())
        return self

    def setup(self):
        if self._probe_service is not None:
            return self

        from .adc_recorder_service import ADCRecorderService
        from .audio_analysis_service import AudioAnalysisService
        from .audio_batch_service import AudioBatchService
        from .audio_comparison_service import AudioComparisonService
        from .audio_conversion_service import AudioConversionService
        from .audio_integrity_service import AudioIntegrityService
        from .audio_lab_job_adapter import AudioLabJobAdapter
        from .audio_lab_profile_service import AudioLabProfileService
        from .audio_normalization_service import AudioNormalizationService
        from .audio_probe_service import AudioProbeService
        from .cd_ripper_service import CDRipperService
        from .replaygain_service import ReplayGainService

        self._probe_service = AudioProbeService(db=self._db, parent=self)
        self._analysis_service = AudioAnalysisService(db=self._db, wm=self._wm, parent=self)
        self._profile_service = AudioLabProfileService(parent=self)
        self._conversion_service = AudioConversionService(
            db=self._db,
            wm=self._wm,
            profile_service=self._profile_service,
            parent=self,
        )
        self._normalization_service = AudioNormalizationService(db=self._db, wm=self._wm, parent=self)
        self._replaygain_service = ReplayGainService(db=self._db, wm=self._wm, parent=self)
        self._integrity_service = AudioIntegrityService(db=self._db, wm=self._wm, parent=self)
        self._comparison_service = AudioComparisonService(parent=self)
        self._batch_service = AudioBatchService(db=self._db, wm=self._wm, parent=self)
        self._job_adapter = AudioLabJobAdapter(
            db=self._db,
            wm=self._wm,
            probe=self._probe_service,
            analysis=self._analysis_service,
            conversion=self._conversion_service,
            normalization=self._normalization_service,
            replaygain=self._replaygain_service,
            integrity=self._integrity_service,
            comparison=self._comparison_service,
            parent=self,
        )
        self._cd_ripper_service = CDRipperService()
        self._adc_recorder_service = ADCRecorderService()
        return self

    def capability_map(self) -> dict[str, bool]:
        cd_capability = self._cd_ripper_service.capability() if self._cd_ripper_service else {}
        return {
            "probe": self._probe_service is not None,
            "analysis": self._analysis_service is not None,
            "conversion": self._conversion_service is not None and shutil.which("ffmpeg") is not None,
            "normalization": self._normalization_service is not None and shutil.which("ffmpeg") is not None,
            "replaygain": self._replaygain_service is not None,
            "integrity": self._integrity_service is not None,
            "comparison": self._comparison_service is not None,
            "batch": self._batch_service is not None,
            "profiles": self._profile_service is not None,
            "cd_ripping": bool(cd_capability.get("available")),
            "adc_recording": bool(self._adc_recorder_service and self._adc_recorder_service.available()),
        }

    def status(self) -> dict[str, Any]:
        caps = self.capability_map()
        return {
            "available": self._started and any(caps.values()),
            "started": self._started,
            "capabilities": caps,
        }

    @staticmethod
    def _tool_status(available: bool, experimental: bool = False) -> str:
        if not available:
            return "missing_dependency"
        return "experimental" if experimental else "available"

    @staticmethod
    def _area_status(tool_statuses: list[str]) -> str:
        if all(status == "available" for status in tool_statuses):
            return "available"
        if all(status == "missing_dependency" for status in tool_statuses):
            return "unavailable"
        return "partial"

    def get_overview_data(self) -> dict[str, Any]:
        caps = self.capability_map()
        ffmpeg_available = shutil.which("ffmpeg") is not None
        musicbrainz_available = importlib.util.find_spec("musicbrainzngs") is not None
        acoustid_available = importlib.util.find_spec("acoustid") is not None

        active_jobs = 0
        if self._wm:
            try:
                jobs = self._wm.get_all_jobs() if hasattr(self._wm, "get_all_jobs") else []
                active_jobs = sum(
                    1 for job in jobs if str(getattr(job, "status", "")).casefold() == "running"
                )
            except Exception as exc:
                logger.debug("Could not read Audio Lab jobs: %s", exc)

        diagnostic_tools = [
            {"id": "analysis", "name": "Análisis técnico", "status": self._tool_status(caps["analysis"])},
            {"id": "integrity", "name": "Integridad", "status": self._tool_status(caps["integrity"])},
            {"id": "comparison", "name": "Comparación A/B", "status": self._tool_status(caps["comparison"])},
        ]
        identifier_tools = [
            {
                "id": "fingerprint",
                "name": "Fingerprint acústico",
                "status": self._tool_status(acoustid_available, experimental=True),
            },
            {
                "id": "metadata",
                "name": "Editor de metadatos",
                "status": self._tool_status(self._db is not None),
            },
            {
                "id": "musicbrainz",
                "name": "Consulta MusicBrainz",
                "status": self._tool_status(musicbrainz_available, experimental=True),
            },
        ]
        backup_tools = [
            {"id": "conversion", "name": "Conversión", "status": self._tool_status(caps["conversion"])},
            {
                "id": "normalization",
                "name": "Normalización",
                "status": self._tool_status(caps["normalization"]),
            },
            {
                "id": "cd_ripping",
                "name": "Ripeo de CD",
                "status": self._tool_status(caps["cd_ripping"], experimental=True),
            },
            {
                "id": "adc_recording",
                "name": "Grabación analógica",
                "status": self._tool_status(caps["adc_recording"], experimental=True),
            },
        ]
        output_tools = [
            {"id": "profiles", "name": "Perfiles", "status": self._tool_status(caps["profiles"])},
            {"id": "replaygain", "name": "ReplayGain", "status": self._tool_status(caps["replaygain"])},
            {"id": "eq_dsp", "name": "EQ y DSP", "status": "available"},
        ]
        intelligence_tools = [
            {"id": "acoustic_features", "name": "Características acústicas", "status": "experimental"},
            {"id": "similar_songs", "name": "Canciones similares", "status": "experimental"},
            {"id": "smart_mix", "name": "Smart Mix", "status": "available"},
        ]

        areas = {
            "diagnostics": {
                "key": "diagnostics",
                "title": "Diagnóstico",
                "description": "Analiza, verifica integridad y compara archivos",
                "icon": "🔍",
                "status": self._area_status([tool["status"] for tool in diagnostic_tools]),
                "tools": diagnostic_tools,
            },
            "identifier": {
                "key": "identifier",
                "title": "Identificador de audios",
                "description": "Identifica y corrige metadatos con proveedores disponibles",
                "icon": "🆔",
                "status": self._area_status([tool["status"] for tool in identifier_tools]),
                "tools": identifier_tools,
            },
            "backup": {
                "key": "backup",
                "title": "Respaldar",
                "description": "Convierte, normaliza, ripea CD y digitaliza fuentes analógicas",
                "icon": "💾",
                "status": self._area_status([tool["status"] for tool in backup_tools]),
                "tools": backup_tools,
            },
            "output_profiles": {
                "key": "output_profiles",
                "title": "Perfiles de salida",
                "description": "Configura DAC, ReplayGain, EQ y reproducción",
                "icon": "🎧",
                "status": self._area_status([tool["status"] for tool in output_tools]),
                "tools": output_tools,
            },
            "local_intelligence": {
                "key": "local_intelligence",
                "title": "Inteligencia local",
                "description": "Análisis acústico y automatización local",
                "icon": "🧠",
                "status": "partial",
                "tools": intelligence_tools,
            },
        }
        return {
            "areas": areas,
            "dependencies": {
                "ffmpeg": ffmpeg_available,
                "cdparanoia": shutil.which("cdparanoia") is not None,
                "cd_discid": shutil.which("cd-discid") is not None,
                "musicbrainz": musicbrainz_available,
                "acoustid": acoustid_available,
            },
            "capabilities": caps,
            "active_jobs": active_jobs,
            "last_analysis": self._get_last_analysis_date(),
        }

    def _get_last_analysis_date(self) -> str | None:
        if self._db is None:
            return None
        query = getattr(self._db, "query_one", None)
        if not callable(query):
            return None
        try:
            row = query(
                "SELECT completed_at FROM audio_lab_jobs "
                "WHERE status='completed' ORDER BY completed_at DESC LIMIT 1"
            )
        except Exception:
            return None
        if not row:
            return None
        if isinstance(row, dict):
            return row.get("completed_at")
        try:
            return str(row[0])
        except (IndexError, TypeError):
            return None

    def shutdown(self) -> None:
        for service in (
            self._adc_recorder_service,
            self._cd_ripper_service,
            self._job_adapter,
            self._batch_service,
            self._conversion_service,
            self._normalization_service,
            self._replaygain_service,
            self._analysis_service,
        ):
            shutdown = getattr(service, "shutdown", None)
            if callable(shutdown):
                try:
                    shutdown()
                except Exception as exc:
                    logger.debug("Audio Lab shutdown failed for %s: %s", type(service).__name__, exc)
        self._started = False
        self.stateChanged.emit("stopped", {})
