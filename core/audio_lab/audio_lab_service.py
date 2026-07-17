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
        self._profile_service = AudioLabProfileService(parent=self)
        self._conversion_service = AudioConversionService(
            db=self._db, wm=self._wm, profile_service=self._profile_service, parent=self
        )
        self._normalization_service = AudioNormalizationService(db=self._db, wm=self._wm, parent=self)
        self._replaygain_service = ReplayGainService(db=self._db, wm=self._wm, parent=self)
        self._integrity_service = AudioIntegrityService(db=self._db, wm=self._wm, parent=self)
        self._comparison_service = AudioComparisonService(parent=self)
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

    def get_overview_data(self) -> dict[str, Any]:
        """
        Retorna datos para la vista general de Audio Lab con 5 áreas principales.
        Cumple con la especificación: 5 tarjetas, no 8 herramientas sueltas.
        """
        # Verificar dependencias externas
        ffmpeg_available = self._check_ffmpeg()
        replaygain_available = self._check_replaygain()
        musicbrainz_available = self._check_musicbrainz()
        acoustid_available = self._check_acoustid()
        
        # Contar trabajos activos del worker manager
        active_jobs = 0
        if self._wm:
            try:
                all_jobs = self._wm.get_all_jobs() if hasattr(self._wm, 'get_all_jobs') else []
                active_jobs = len([j for j in all_jobs if getattr(j, 'status', None) == 'running'])
            except Exception:
                active_jobs = 0
        
        # Estado de las 5 áreas principales (especificación sección 3)
        areas = {
            "diagnostics": {
                "title": "Diagnóstico",
                "description": "Analiza, verifica integridad y compara archivos",
                "icon": "🔍",
                "status": "available",
                "tools": [
                    {"id": "analysis", "name": "Análisis Técnico", "status": "available"},
                    {"id": "integrity", "name": "Integridad", "status": "available"},
                    {"id": "comparison", "name": "Comparación A/B", "status": "available"}
                ]
            },
            "identifier": {
                "title": "Identificador de Audios",
                "description": "Identifica, corrige metadatos y carátulas",
                "icon": "🆔",
                "status": "available" if musicbrainz_available else "partial",
                "tools": [
                    {"id": "fingerprint", "name": "Fingerprint Acústico", "status": "available" if acoustid_available else "missing_dependency"},
                    {"id": "metadata", "name": "Editor de Metadatos", "status": "available"},
                    {"id": "covers", "name": "Carátulas", "status": "available"},
                    {"id": "lyrics", "name": "Letras", "status": "available"}
                ]
            },
            "backup": {
                "title": "Respaldar",
                "description": "Convierte, normaliza, ripea y organiza",
                "icon": "💾",
                "status": "available" if ffmpeg_available else "partial",
                "tools": [
                    {"id": "conversion", "name": "Conversión", "status": "available" if ffmpeg_available else "missing_dependency"},
                    {"id": "normalization", "name": "Normalización", "status": "available"},
                    {"id": "cd_ripping", "name": "Ripeo de CD", "status": "experimental"},
                    {"id": "organization", "name": "Organización", "status": "available"}
                ]
            },
            "output_profiles": {
                "title": "Perfiles de Salida",
                "description": "Configura DAC, EQ y reproducción",
                "icon": "🎧",
                "status": "available",
                "tools": [
                    {"id": "device_config", "name": "Configuración de Dispositivo", "status": "available"},
                    {"id": "replaygain", "name": "ReplayGain", "status": "available" if replaygain_available else "partial"},
                    {"id": "eq_dsp", "name": "EQ y DSP", "status": "available"}
                ]
            },
            "local_intelligence": {
                "title": "Inteligencia Local",
                "description": "Análisis acústico y automatización",
                "icon": "🧠",
                "status": "partial",
                "tools": [
                    {"id": "acoustic_features", "name": "Características Acústicas", "status": "experimental"},
                    {"id": "similar_songs", "name": "Canciones Similares", "status": "experimental"},
                    {"id": "local_radio", "name": "Radio Local", "status": "available"},
                    {"id": "smart_mix", "name": "Smart Mix", "status": "available"}
                ]
            }
        }
        
        return {
            "areas": areas,
            "dependencies": {
                "ffmpeg": ffmpeg_available,
                "replaygain": replaygain_available,
                "musicbrainz": musicbrainz_available,
                "acoustid": acoustid_available
            },
            "active_jobs": active_jobs,
            "last_analysis": self._get_last_analysis_date()
        }
    
    def _check_ffmpeg(self) -> bool:
        """Verifica si FFmpeg está disponible en el sistema."""
        try:
            import subprocess
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
            return result.returncode == 0
        except (Exception, FileNotFoundError):
            return False
    
    def _check_replaygain(self) -> bool:
        """Verifica si las herramientas de ReplayGain están disponibles."""
        try:
            import subprocess
            # metaflac es común para ReplayGain en FLAC
            result = subprocess.run(['metaflac', '--version'], capture_output=True, timeout=5)
            return result.returncode == 0
        except (Exception, FileNotFoundError):
            return False
    
    def _check_musicbrainz(self) -> bool:
        """Verifica si MusicBrainz está accesible."""
        try:
            import musicbrainzngs
            musicbrainzngs.set_useragent("MichiMusicPlayer", "0.11.0")
            return True
        except (Exception, ImportError):
            return False
    
    def _check_acoustid(self) -> bool:
        """Verifica si AcoustID está configurado con API key."""
        try:
            import acoustid
            # Verificar si hay API key configurada
            return hasattr(acoustid, 'api_key') and acoustid.api_key is not None
        except (Exception, ImportError):
            return False
    
    def _get_last_analysis_date(self) -> str | None:
        """Obtiene la fecha del último análisis completado."""
        # TODO: Implementar consulta real a la base de datos
        # Por ahora retorna None (nunca analizado)
        return None
