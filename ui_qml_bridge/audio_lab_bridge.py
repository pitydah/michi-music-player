from __future__ import annotations

import logging
import uuid

from PySide6.QtCore import QObject, Signal, Property, Slot

logger = logging.getLogger("michi.audio_lab.bridge")


class AudioLabBridge(QObject):
    dataChanged = Signal()
    jobProgress = Signal(str, str, float)
    jobCompleted = Signal(str, str, object)
    jobFailed = Signal(str, str)
    serviceAvailableChanged = Signal()

    def __init__(self, audio_lab_service=None, job_service=None,
                 process_controller=None, confirmation_service=None,
                 navigation_bridge=None, capability_bridge=None,
                 notification_bridge=None, parent=None):
        super().__init__(parent)
        self._svc = audio_lab_service
        self._jobs = job_service
        self._pc = process_controller
        self._confirm = confirmation_service
        self._nav = navigation_bridge
        self._cap = capability_bridge
        self._notify = notification_bridge
        self._active_jobs: dict[str, dict] = {}

    @Property(bool, notify=dataChanged)
    def serviceAvailable(self):
        return self._svc is not None

    @Property(bool, notify=dataChanged)
    def jobServiceAvailable(self):
        return self._jobs is not None

    @Slot(result=dict)
    def capabilityMap(self):
        if not self._svc:
            return {}
        return self._svc.capability_map()

    def _run_async(self, job_id: str, run_fn, on_done):
        if self._pc and hasattr(self._pc, 'run_in_thread'):
            self._pc.run_in_thread(job_id, run_fn, on_done=on_done)
        else:
            result = run_fn()
            on_done(result)

    def _job_preview(self, module_attr: str, method: str, filepath: str, *args):
        if not self._svc:
            return {"ok": False, "error_code": "SERVICE_UNAVAILABLE"}
        module = getattr(self._svc, module_attr, None)
        if not module:
            return {"ok": False, "error_code": "SERVICE_UNAVAILABLE"}
        try:
            fn = getattr(module, method)
            result = fn(filepath, *args)
            return {"ok": True, "result": result}
        except Exception as e:
            return {"ok": False, "error_code": "PREVIEW_FAILED", "detail": str(e)}

    def _job_validate(self, module_attr: str, method: str, filepath: str):
        if not self._svc:
            return {"ok": False, "error_code": "SERVICE_UNAVAILABLE"}
        module = getattr(self._svc, module_attr, None)
        if not module:
            return {"ok": False, "error_code": "SERVICE_UNAVAILABLE"}
        try:
            fn = getattr(module, method)
            result = fn(filepath)
            return {"ok": True, "result": result}
        except Exception as e:
            return {"ok": False, "error_code": "VALIDATE_FAILED", "detail": str(e)}

    def _start_job(self, job_prefix: str, job_type: str, filepath: str,
                   run_fn, result_builder):
        if not self._svc:
            return ""
        module = getattr(self._svc, job_type, None)
        if not module:
            return ""
        job_id = f"{job_prefix}_{uuid.uuid4().hex[:8]}"
        self._active_jobs[job_id] = {"type": job_type, "filepath": filepath, "status": "running"}

        def _done(result):
            d = result_builder(result)
            self._active_jobs[job_id]["status"] = d.get("status", "completed")
            self._active_jobs[job_id]["result"] = d
            if d.get("status") == "completed":
                self.jobCompleted.emit(job_id, job_type, d)
            else:
                self.jobFailed.emit(job_id, d.get("error", "unknown"))
            self.dataChanged.emit()

        self._run_async(job_id, run_fn, _done)
        self.dataChanged.emit()
        return job_id

    @Slot(str, result=dict)
    def previewAnalysis(self, filepath: str):
        r = self._job_preview("analysis", "analyze_file", filepath)
        if not r.get("ok"):
            return r
        result = r["result"]
        return {
            "filepath": result.get("filepath", filepath),
            "format": result.get("format", ""),
            "sample_rate": result.get("sample_rate", 0),
            "bit_depth": result.get("bit_depth", 0),
            "channels": result.get("channels", 0),
            "bitrate": result.get("bitrate", 0),
            "duration": result.get("duration", 0.0),
            "codec": result.get("codec", ""),
            "status": result.get("status", "unknown"),
            "ok": result.get("status") not in ("error",),
        }

    @Slot(str, result=dict)
    def validateAnalysis(self, filepath: str):
        r = self._job_validate("analysis", "analyze_file", filepath)
        if not r.get("ok"):
            return r
        result = r["result"]
        valid = result.get("status") not in ("error", "unsupported", "disabled")
        return {"ok": valid, "filepath": filepath, "status": result.get("status")}

    @Slot(str, result=str)
    def startAnalysis(self, filepath: str):
        return self._start_job(
            "analysis", "analysis", filepath,
            lambda: self._svc.analysis.analyze_file(filepath),
            lambda r: {"filepath": filepath, "format": r.get("format", ""),
                        "status": "completed" if r.get("status") not in ("error",) else "failed",
                        "error": r.get("status", "")},
        )

    @Slot(str, str, result=dict)
    def previewConversion(self, filepath: str, target_format: str = "flac"):
        if not self._svc:
            return {"ok": False, "error_code": "SERVICE_UNAVAILABLE"}
        module = getattr(self._svc, "conversion", None)
        if not module:
            return {"ok": False, "error_code": "SERVICE_UNAVAILABLE"}
        try:
            from core.audio_lab.audio_conversion_service import ConversionProfile
            profile = ConversionProfile(format=target_format.upper())
            result = module.preview(filepath, profile)
            return result
        except Exception as e:
            return {"ok": False, "error_code": "PREVIEW_FAILED", "detail": str(e)}

    @Slot(str, str, result=str)
    def startConversion(self, filepath: str, target_format: str = "flac"):
        if not self._svc:
            return ""
        module = getattr(self._svc, "conversion", None)
        if not module:
            return ""
        from core.audio_lab.audio_conversion_service import ConversionProfile
        profile = ConversionProfile(format=target_format.upper())
        job_id = module.convert(filepath, profile)
        self._active_jobs[job_id] = {"type": "conversion", "filepath": filepath, "status": "running"}
        module.conversionCompleted.connect(
            lambda jid, target: self._on_job_done(jid, "conversion", {"target": target})
        )
        module.conversionFailed.connect(
            lambda jid, err: self._on_job_failed(jid, "conversion", err)
        )
        self.dataChanged.emit()
        return job_id

    def _on_job_done(self, job_id, job_type, result):
        if job_id in self._active_jobs:
            self._active_jobs[job_id]["status"] = "completed"
            self._active_jobs[job_id]["result"] = result
            self.jobCompleted.emit(job_id, job_type, result)
            self.dataChanged.emit()

    def _on_job_failed(self, job_id, job_type, error):
        if job_id in self._active_jobs:
            self._active_jobs[job_id]["status"] = "failed"
            self._active_jobs[job_id]["error"] = error
            self.jobFailed.emit(job_id, error)
            self.dataChanged.emit()

    @Slot(str, result=dict)
    def previewNormalization(self, filepath: str):
        if not self._svc:
            return {"ok": False, "error_code": "SERVICE_UNAVAILABLE"}
        module = getattr(self._svc, "normalization", None)
        if not module:
            return {"ok": False, "error_code": "SERVICE_UNAVAILABLE"}
        try:
            result = module.measure_loudness(filepath)
            return {
                "ok": result.status == "completed",
                "filepath": result.filepath,
                "integrated_loudness": result.integrated_loudness,
                "true_peak": result.true_peak,
                "loudness_range": result.loudness_range,
            }
        except Exception as e:
            return {"ok": False, "error_code": "PREVIEW_FAILED", "detail": str(e)}

    @Slot(str, str, result=dict)
    def startNormalization(self, filepath: str, confirmation_token: str = ""):
        """Inicia la normalización con parámetros manuales."""
        if not self._svc:
            return {"ok": False, "error_code": "SERVICE_UNAVAILABLE"}
        module = getattr(self._svc, "normalization", None)
        if not module:
            return {"ok": False, "error_code": "SERVICE_UNAVAILABLE"}
        try:
            needs_confirm = module.normalize_file(
                filepath, destructive=True, confirmation_token=confirmation_token or None
            )
            if isinstance(needs_confirm, dict) and needs_confirm.get("requires_confirmation"):
                return needs_confirm
            return {"ok": True, "status": "metadata_only", "message": "Usar ReplayGain para normalizacion no destructiva"}
        except Exception as e:
            return {"ok": False, "error_code": "NORMALIZE_FAILED", "detail": str(e)}

    @Slot(str, result=dict)
    def previewReplayGain(self, filepath: str):
        if not self._svc:
            return {"ok": False, "error_code": "SERVICE_UNAVAILABLE"}
        module = getattr(self._svc, "replaygain", None)
        if not module:
            return {"ok": False, "error_code": "SERVICE_UNAVAILABLE"}
        try:
            result = module.analyze_track(filepath)
            return {
                "ok": result.status == "completed",
                "filepath": result.filepath,
                "track_gain": result.track_gain,
                "track_peak": result.track_peak,
            }
        except Exception as e:
            return {"ok": False, "error_code": "PREVIEW_FAILED", "detail": str(e)}

    @Slot(str, result=dict)
    def validateReplayGain(self, filepath: str):
        if not self._svc:
            return {"ok": False, "error_code": "SERVICE_UNAVAILABLE"}
        module = getattr(self._svc, "replaygain", None)
        if not module:
            return {"ok": False, "error_code": "SERVICE_UNAVAILABLE"}
        try:
            result = module.analyze_track(filepath)
            return {
                "ok": result.status == "completed",
                "filepath": result.filepath,
                "status": result.status,
            }
        except Exception as e:
            return {"ok": False, "error_code": "VALIDATE_FAILED", "detail": str(e)}

    @Slot(str, result=str)
    def startReplayGain(self, filepath: str):
        return self._start_job(
            "rg", "replaygain", filepath,
            lambda: self._run_replaygain(filepath),
            lambda r: {"track_gain": getattr(r, "track_gain", 0),
                        "track_peak": getattr(r, "track_peak", 0),
                        "status": "completed" if getattr(r, "status", "") == "completed" else "failed",
                        "error": getattr(r, "error", "")},
        )

    def _run_replaygain(self, filepath: str):
        if not self._svc or not self._svc.replaygain:
            return {"status": "failed", "error": "SERVICE_UNAVAILABLE"}
        result = self._svc.replaygain.analyze_track(filepath)
        if result.status == "completed":
            self._svc.replaygain.write_tags(
                filepath, result.track_gain, result.track_peak,
                album_gain=result.album_gain, album_peak=result.album_peak
            )
        return result

    @Slot(str, result=dict)
    def previewIntegrity(self, filepath: str):
        if not self._svc:
            return {"ok": False, "error_code": "SERVICE_UNAVAILABLE"}
        module = getattr(self._svc, "integrity", None)
        if not module:
            return {"ok": False, "error_code": "SERVICE_UNAVAILABLE"}
        try:
            result = module.check(filepath, quick=True)
            return {
                "ok": result.is_valid,
                "filepath": result.filepath,
                "status": result.status,
                "issues": result.issues,
                "duration": result.duration,
                "size": result.file_size,
                "is_valid": result.is_valid,
            }
        except Exception as e:
            return {"ok": False, "error_code": "PREVIEW_FAILED", "detail": str(e)}

    @Slot(str, result=dict)
    def validateIntegrity(self, filepath: str):
        return self.previewIntegrity(filepath)

    @Slot(str, result=str)
    def startIntegrity(self, filepath: str):
        return self._start_job(
            "integrity", "integrity", filepath,
            lambda: self._svc.integrity.check(filepath, quick=False),
            lambda r: {"is_valid": r.is_valid, "issues": r.issues, "checksum": r.checksum,
                        "status": "completed"},
        )

    @Slot(str, str, result=dict)
    def previewComparison(self, file_a: str, file_b: str):
        if not self._svc:
            return {"ok": False, "error_code": "SERVICE_UNAVAILABLE"}
        module = getattr(self._svc, "comparison", None)
        if not module:
            return {"ok": False, "error_code": "SERVICE_UNAVAILABLE"}
        try:
            result = module.compare(file_a, file_b)
            return {
                "ok": not result.error,
                "identical": result.identical,
                "dimensions": [{
                    "key": d.key, "label": d.label,
                    "value_a": d.value_a, "value_b": d.value_b,
                    "identical": d.identical,
                } for d in result.dimensions],
            }
        except Exception as e:
            return {"ok": False, "error_code": "PREVIEW_FAILED", "detail": str(e)}

    @Slot(str, str, result=str)
    def startComparison(self, file_a: str, file_b: str):
        if not self._svc:
            return ""
        module = getattr(self._svc, "comparison", None)
        if not module:
            return ""
        job_id = f"compare_{uuid.uuid4().hex[:8]}"
        self._active_jobs[job_id] = {"type": "comparison", "status": "running"}

        def _run():
            return module.compare(file_a, file_b)

        def _done(result):
            d = {"identical": result.identical, "dimensions": len(result.dimensions)}
            self._active_jobs[job_id]["status"] = "completed"
            self._active_jobs[job_id]["result"] = d
            self.jobCompleted.emit(job_id, "comparison", d)
            self.dataChanged.emit()

        self._run_async(job_id, _run, _done)
        self.dataChanged.emit()
        return job_id

    @Slot(str, result=dict)
    def cancelJob(self, job_id: str):
        if job_id in self._active_jobs:
            self._active_jobs[job_id]["status"] = "cancelled"
            if self._pc and hasattr(self._pc, 'cancel'):
                self._pc.cancel(job_id)
            self.dataChanged.emit()
            return {"ok": True, "job_id": job_id}
        if self._jobs and hasattr(self._jobs, 'cancel'):
            result = self._jobs.cancel(job_id)
            if result and result.get("ok"):
                self.dataChanged.emit()
                return result
        return {"ok": False, "error_code": "JOB_NOT_FOUND"}

    @Slot(str, result=dict)
    def retryJob(self, job_id: str):
        info = self._active_jobs.get(job_id)
        if not info:
            return {"ok": False, "error_code": "JOB_NOT_FOUND"}
        job_type = info.get("type")
        filepath = info.get("filepath", "")
        if job_type == "analysis" and filepath:
            new_id = self.startAnalysis(filepath)
            return {"ok": True, "new_job_id": new_id, "type": job_type}
        if job_type == "replaygain" and filepath:
            new_id = self.startReplayGain(filepath)
            return {"ok": True, "new_job_id": new_id, "type": job_type}
        if job_type == "integrity" and filepath:
            new_id = self.startIntegrity(filepath)
            return {"ok": True, "new_job_id": new_id, "type": job_type}
        return {"ok": False, "error_code": "RETRY_UNSUPPORTED"}

    @Slot(result=dict)
    def cleanupCompleted(self):
        count = 0
        finished = [jid for jid, info in self._active_jobs.items()
                    if info.get("status") in ("completed", "failed", "cancelled")]
        for jid in finished:
            del self._active_jobs[jid]
            count += 1
        self.dataChanged.emit()
        return {"ok": True, "cleaned": count}

    @Slot(str, result=dict)
    def jobStatus(self, job_id: str):
        info = self._active_jobs.get(job_id)
        if info:
            return {"ok": True, "job_id": job_id, "status": info.get("status"),
                    "type": info.get("type"), "filepath": info.get("filepath", "")}
        if self._jobs and hasattr(self._jobs, 'status'):
            result = self._jobs.status(job_id)
            if result and result.get("ok"):
                return result
        return {"ok": False, "error_code": "JOB_NOT_FOUND"}

    @Slot(result=dict)
    def activeJobs(self):
        return {jid: info.get("status") for jid, info in self._active_jobs.items()}

    @Slot(result=dict)
    def refresh(self):
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(str, result=dict)
    def navigateTo(self, route: str):
        if self._nav:
            return self._nav.navigate(route)
        return {"ok": False, "error_code": "NAVIGATION_UNAVAILABLE"}

    @Slot(str, result=dict)
    def requireConfirmation(self, action: str):
        if self._confirm:
            return self._confirm.request(action)
        return {"ok": False, "error_code": "CONFIRMATION_UNAVAILABLE"}

    @Slot(result=dict)
    def partialFailureReport(self):
        failed = [{"job_id": jid, "type": info.get("type"), "error": info.get("error", "")}
                  for jid, info in self._active_jobs.items()
                  if info.get("status") == "failed"]
        return {"ok": True, "has_failures": bool(failed), "failures": failed}

    @Slot(result=dict)
    def getOverviewData(self):
        """Retorna datos para la vista de 5 tarjetas principales."""
        if not self._svc:
            return {"ok": False, "error_code": "SERVICE_UNAVAILABLE"}
        try:
            data = self._svc.get_overview_data()
            return {"ok": True, **data}
        except Exception as e:
            logger.error(f"Error getting overview data: {e}")
            return {"ok": False, "error_code": "OVERVIEW_ERROR", "message": str(e)}

    @Slot(str, result=dict)
    def navigateToArea(self, area_key: str):
        """Navega a una página específica del área (hub interno)."""
        route_map = {
            "diagnostics": "audio_lab.diagnostics_hub",
            "identifier": "audio_lab.identifier_hub",
            "backup": "audio_lab.backup_hub",
            "output_profiles": "audio_lab.output_profiles_hub",
            "local_intelligence": "audio_lab.local_intelligence_hub"
        }
        route = route_map.get(area_key)
        if not route:
            return {"ok": False, "error_code": "INVALID_AREA"}
        return self.navigateTo(route)

    # ==================== CD RIPPER ====================
    
    @Slot(result=list)
    def detectCDDrives(self) -> list:
        """Detecta unidades de CD disponibles."""
        if not self._svc:
            return []
        try:
            from core.audio_lab.cd_ripper_service import CDRipperService
            ripper = CDRipperService()
            drives = ripper.detect_drives()
            return [{
                'device': d.device,
                'model': d.model,
                'is_audio_capable': d.is_audio_capable
            } for d in drives]
        except Exception as e:
            logger.error(f"Error detecting CD drives: {e}")
            return []
    
    @Slot(str, result=dict)
    def getCDInfo(self, device: str) -> dict:
        """Obtiene información del CD insertado."""
        if not self._svc:
            return {'ok': False, 'error': 'Service unavailable'}
        try:
            from core.audio_lab.cd_ripper_service import CDRipperService
            ripper = CDRipperService()
            cd_info = ripper.get_cd_info(device)
            if cd_info:
                return {
                    'ok': True,
                    'album_title': cd_info.album_title,
                    'album_artist': cd_info.album_artist,
                    'year': cd_info.year,
                    'genre': cd_info.genre,
                    'disc_id': cd_info.disc_id,
                    'total_tracks': cd_info.total_tracks,
                    'tracks': [{
                        'track_number': t.track_number,
                        'title': t.title,
                        'artist': t.artist,
                        'duration': t.duration
                    } for t in cd_info.tracks]
                }
            return {'ok': False, 'error': 'No CD info available'}
        except Exception as e:
            logger.error(f"Error getting CD info: {e}")
            return {'ok': False, 'error': str(e)}
    
    @Slot(str, str, str, str, result=dict)
    def ripCDTrack(self, device: str, track_number: int, output_path: str, format: str = 'flac') -> dict:
        """Extrae una pista individual del CD."""
        if not self._svc:
            return {'ok': False, 'error': 'Service unavailable'}
        try:
            from core.audio_lab.cd_ripper_service import CDRipperService
            ripper = CDRipperService()
            result = ripper.rip_track(device, int(track_number), output_path, format)
            return {'ok': result['success'], **result}
        except Exception as e:
            logger.error(f"Error ripping CD track: {e}")
            return {'ok': False, 'error': str(e)}
    
    @Slot(str, str, str, str, bool, result=dict)
    def ripFullCD(self, device: str, output_dir: str, format: str = 'flac', quality: str = 'lossless', include_log: bool = True) -> dict:
        """Extrae todo el CD."""
        if not self._svc:
            return {'ok': False, 'error': 'Service unavailable'}
        try:
            from core.audio_lab.cd_ripper_service import CDRipperService
            ripper = CDRipperService()
            result = ripper.rip_full_cd(device, output_dir, format, quality, include_log)
            return {'ok': result['success'], **result}
        except Exception as e:
            logger.error(f"Error ripping full CD: {e}")
            return {'ok': False, 'error': str(e)}

    # ==================== ADC RECORDER / TURNTABLE ====================
    
    @Slot(result=list)
    def detectAudioDevices(self) -> list:
        """Detecta dispositivos de entrada de audio (incluye tocadiscos USB)."""
        if not self._svc:
            return []
        try:
            from core.audio_lab.adc_recorder_service import ADCRecorderService
            recorder = ADCRecorderService()
            devices = recorder.detect_devices()
            return [{
                'device_id': d.device_id,
                'name': d.name,
                'is_usb': d.is_usb,
                'is_turntable': d.is_turntable,
                'brand': d.brand,
                'channels': d.channels,
                'sample_rate': d.sample_rate
            } for d in devices]
        except Exception as e:
            logger.error(f"Error detecting audio devices: {e}")
            return []
    
    @Slot(result=dict)
    def getRecommendedDevice(self) -> dict:
        """Obtiene el dispositivo recomendado (prioriza tocadiscos USB)."""
        if not self._svc:
            return {'ok': False, 'error': 'Service unavailable'}
        try:
            from core.audio_lab.adc_recorder_service import ADCRecorderService
            recorder = ADCRecorderService()
            device = recorder.get_recommended_device()
            if device:
                return {
                    'ok': True,
                    'device_id': device.device_id,
                    'name': device.name,
                    'is_usb': device.is_usb,
                    'is_turntable': device.is_turntable,
                    'brand': device.brand
                }
            return {'ok': False, 'error': 'No devices found'}
        except Exception as e:
            logger.error(f"Error getting recommended device: {e}")
            return {'ok': False, 'error': str(e)}
    
    @Slot(int, str, str, int, int, int, list, result=dict)
    def startRecording(self, device_id: int, output_path: str, format: str = 'wav', 
                       sample_rate: int = 44100, bit_depth: int = 16, channels: int = 2, 
                       dsp_filters: list = None) -> dict:
        """Inicia grabación desde dispositivo ADC."""
        if not self._svc:
            return {'ok': False, 'error': 'Service unavailable'}
        try:
            from core.audio_lab.adc_recorder_service import ADCRecorderService, AudioDevice
            recorder = ADCRecorderService()
            
            # Crear dispositivo desde ID
            devices = recorder.detect_devices()
            device = next((d for d in devices if d.device_id == device_id), None)
            if not device:
                return {'ok': False, 'error': 'Device not found'}
            
            result = recorder.start_recording(
                device=device,
                output_path=output_path,
                format=format,
                sample_rate=sample_rate,
                bit_depth=bit_depth,
                channels=channels,
                apply_dsp=dsp_filters or []
            )
            return {'ok': result['success'], **result}
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            return {'ok': False, 'error': str(e)}
    
    @Slot(result=dict)
    def pauseRecording(self) -> dict:
        """Pausa la grabación actual."""
        if not self._svc:
            return {'ok': False, 'error': 'Service unavailable'}
        try:
            from core.audio_lab.adc_recorder_service import ADCRecorderService
            recorder = ADCRecorderService()
            recorder.pause_recording()
            return {'ok': True}
        except Exception as e:
            logger.error(f"Error pausing recording: {e}")
            return {'ok': False, 'error': str(e)}
    
    @Slot(result=dict)
    def resumeRecording(self) -> dict:
        """Reanuda la grabación pausada."""
        if not self._svc:
            return {'ok': False, 'error': 'Service unavailable'}
        try:
            from core.audio_lab.adc_recorder_service import ADCRecorderService
            recorder = ADCRecorderService()
            recorder.resume_recording()
            return {'ok': True}
        except Exception as e:
            logger.error(f"Error resuming recording: {e}")
            return {'ok': False, 'error': str(e)}
    
    @Slot(result=dict)
    def stopRecording(self) -> dict:
        """Detiene la grabación actual."""
        if not self._svc:
            return {'ok': False, 'error': 'Service unavailable'}
        try:
            from core.audio_lab.adc_recorder_service import ADCRecorderService
            recorder = ADCRecorderService()
            recorder.stop_recording()
            return {'ok': True}
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            return {'ok': False, 'error': str(e)}
    
    @Slot(str, float, result=dict)
    def addMarker(self, label: str = "", timestamp: float = None) -> dict:
        """Agrega un marcador en la grabación actual."""
        if not self._svc:
            return {'ok': False, 'error': 'Service unavailable'}
        try:
            from core.audio_lab.adc_recorder_service import ADCRecorderService
            recorder = ADCRecorderService()
            result = recorder.add_marker(timestamp=timestamp, label=label)
            return {'ok': result['success'], **result}
        except Exception as e:
            logger.error(f"Error adding marker: {e}")
            return {'ok': False, 'error': str(e)}
    
    @Slot(str, str, result=dict)
    def splitByMarkers(self, input_file: str, output_dir: str) -> dict:
        """Divide grabación por marcadores."""
        if not self._svc:
            return {'ok': False, 'error': 'Service unavailable'}
        try:
            from core.audio_lab.adc_recorder_service import ADCRecorderService
            recorder = ADCRecorderService()
            result = recorder.split_by_markers(input_file, output_dir)
            return {'ok': result['success'], **result}
        except Exception as e:
            logger.error(f"Error splitting by markers: {e}")
            return {'ok': False, 'error': str(e)}
    
    @Slot(result=dict)
    def getRecordingStatus(self) -> dict:
        """Obtiene estado de la grabación actual."""
        if not self._svc:
            return {'active': False}
        try:
            from core.audio_lab.adc_recorder_service import ADCRecorderService
            recorder = ADCRecorderService()
            return recorder.get_recording_status()
        except Exception as e:
            logger.error(f"Error getting recording status: {e}")
            return {'active': False, 'error': str(e)}
