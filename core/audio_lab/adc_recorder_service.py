"""
Servicio de Grabación desde ADC (Analog-to-Digital Converter).
Soporta tocadiscos USB, cassettes y otras fuentes analógicas.
"""
import os
import subprocess
import tempfile
import threading
import time
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass
from pathlib import Path
import logging
import json

logger = logging.getLogger(__name__)

@dataclass
class AudioDevice:
    device_id: int
    name: str
    is_usb: bool
    is_turntable: bool
    brand: Optional[str]
    channels: int
    sample_rate: int

@dataclass
class RecordingSession:
    session_id: str
    input_device: AudioDevice
    output_path: str
    format: str
    start_time: float
    end_time: Optional[float]
    duration: float
    file_size: int
    markers: List[Dict[str, Any]]  # Puntos de corte para pistas
    status: str  # 'recording', 'paused', 'stopped', 'completed'

class USBTurntableDetector:
    """Detecta tocadiscos con USB conectados al sistema."""
    
    # Marcas comunes de tocadiscos USB
    TURNTABLE_BRANDS = [
        'audio-technica', 'audiotechnica', 'pro-ject', 'project', 
        'rega', 'numark', 'sony', 'pioneer', 'technics', 'yamaha',
        'denon', 'marantz', 'cambridge audio', 'art', 'behringer'
    ]
    
    def __init__(self):
        self.detected_devices: List[AudioDevice] = []
        
    def scan_usb_devices(self) -> List[AudioDevice]:
        """Escanea dispositivos USB de audio conectados."""
        devices = []
        
        try:
            # Linux: usar lsusb y arecord
            if os.name == 'posix':
                devices.extend(self._scan_linux())
            # Windows: usar pyaudio o wmic
            elif os.name == 'nt':
                devices.extend(self._scan_windows())
            # macOS: usar system_profiler
            elif os.name == 'darwin':
                devices.extend(self._scan_macos())
        except Exception as e:
            logger.error(f"Error al escanear dispositivos USB: {e}")
            
        self.detected_devices = devices
        return devices
    
    def _scan_linux(self) -> List[AudioDevice]:
        """Escanea dispositivos en Linux."""
        devices = []
        
        try:
            # Obtener lista de dispositivos de captura con arecord
            result = subprocess.run(
                ['arecord', '-l'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'card' in line.lower() and 'device' in line.lower():
                        # Parsear línea: card X: USB Audio [Device Name], device Y
                        parts = line.split(':')
                        if len(parts) >= 2:
                            card_info = parts[1].strip()
                            device_name = card_info.split(',')[0] if ',' in card_info else card_info
                            
                            # Verificar si es USB
                            is_usb = 'usb' in line.lower() or 'USB' in line
                            
                            # Verificar si parece un tocadiscos
                            is_turntable = False
                            brand = None
                            device_lower = device_name.lower()
                            
                            for tb_brand in self.TURNTABLE_BRANDS:
                                if tb_brand in device_lower:
                                    is_turntable = True
                                    brand = tb_brand.title()
                                    break
                                    
                            # Obtener ID del dispositivo
                            device_id = None
                            for part in line.split():
                                if part.isdigit():
                                    device_id = int(part)
                                    break
                                    
                            if device_id is not None:
                                devices.append(AudioDevice(
                                    device_id=device_id,
                                    name=device_name,
                                    is_usb=is_usb,
                                    is_turntable=is_turntable,
                                    brand=brand,
                                    channels=2,  # Estéreo por defecto
                                    sample_rate=44100  # CD quality por defecto
                                ))
        except Exception as e:
            logger.warning(f"Error en escaneo Linux: {e}")
            
        return devices
    
    def _scan_windows(self) -> List[AudioDevice]:
        """Escanea dispositivos en Windows."""
        devices = []
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                
                # Solo dispositivos de entrada
                if info['maxInputChannels'] > 0:
                    device_name = info['name']
                    is_usb = 'usb' in device_name.lower()
                    
                    is_turntable = False
                    brand = None
                    device_lower = device_name.lower()
                    
                    for tb_brand in self.TURNTABLE_BRANDS:
                        if tb_brand in device_lower:
                            is_turntable = True
                            brand = tb_brand.title()
                            break
                            
                    devices.append(AudioDevice(
                        device_id=i,
                        name=device_name,
                        is_usb=is_usb,
                        is_turntable=is_turntable,
                        brand=brand,
                        channels=min(info['maxInputChannels'], 2),
                        sample_rate=int(info['defaultSampleRate'])
                    ))
                    
            p.terminate()
        except ImportError:
            logger.warning("PyAudio no disponible en Windows")
        except Exception as e:
            logger.warning(f"Error en escaneo Windows: {e}")
            
        return devices
    
    def _scan_macos(self) -> List[AudioDevice]:
        """Escanea dispositivos en macOS."""
        devices = []
        try:
            result = subprocess.run(
                ['system_profiler', 'SPUSBDataType', '-json'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                # Parsear estructura JSON de macOS para encontrar dispositivos de audio USB
                # Implementación simplificada
                pass
        except Exception as e:
            logger.warning(f"Error en escaneo macOS: {e}")
            
        return devices
    
    def get_turntables(self) -> List[AudioDevice]:
        """Retorna solo los tocadiscos USB detectados."""
        return [d for d in self.detected_devices if d.is_turntable]
    
    def apply_riaa_eq(self, device: AudioDevice) -> bool:
        """
        Aplica ecualización RIAA si se detecta entrada PHONO.
        Retorna True si se aplicó, False si no fue necesario o falló.
        """
        if device.is_turntable and device.brand:
            logger.info(f"Aplicando EQ RIAA para tocadiscos {device.brand}")
            # Aquí se configuraría el pipeline de audio con filtro RIAA
            # Esto depende del backend de audio (GStreamer, etc.)
            return True
        return False


class ADCRecorderService: 
    """Servicio para grabación desde convertidores analógico-digitales."""
    
    SUPPORTED_FORMATS = ['wav', 'flac', 'mp3', 'opus']
    DSP_FILTERS = ['declicker', 'dehisser', 'riaa_eq', 'noise_gate', 'normalize']
    
    def __init__(self):
        self.turntable_detector = USBTurntableDetector()
        self.active_session: Optional[RecordingSession] = None
        self.recording_thread: Optional[threading.Thread] = None
        self.is_recording = False
        self.is_paused = False

    def __del__(self):
        self.stop_recording()

    def available(self) -> bool:
        """Devuelve True si hay un backend de captura disponible."""
        import shutil
        if not shutil.which("ffmpeg"):
            return False
        if not shutil.which("arecord"):
            try:
                import pyaudio
                p = pyaudio.PyAudio()
                count = p.get_device_count()
                p.terminate()
                if count > 0:
                    return True
            except Exception:
                pass
            return False
        return True
        
    def detect_devices(self) -> List[AudioDevice]:
        """Detecta todos los dispositivos de entrada disponibles."""
        return self.turntable_detector.scan_usb_devices()
    
    def get_recommended_device(self) -> Optional[AudioDevice]:
        """Obtiene el dispositivo recomendado (prioriza tocadiscos USB)."""
        devices = self.detect_devices()
        
        # Prioridad 1: Tocadiscos USB
        turntables = [d for d in devices if d.is_turntable]
        if turntables:
            return turntables[0]
            
        # Prioridad 2: Cualquier dispositivo USB
        usb_devices = [d for d in devices if d.is_usb]
        if usb_devices:
            return usb_devices[0]
            
        # Prioridad 3: Cualquier dispositivo de entrada
        if devices:
            return devices[0]
            
        return None
    
    def start_recording(
        self,
        device: AudioDevice,
        output_path: str,
        format: str = 'wav',
        sample_rate: int = 44100,
        bit_depth: int = 16,
        channels: int = 2,
        apply_dsp: List[str] = None
    ) -> Dict[str, Any]:
        """Inicia una sesión de grabación."""
        result = {'success': False, 'error': None, 'session_id': None}
        
        if self.is_recording:
            result['error'] = "Ya hay una grabación en curso"
            return result
            
        try:
            # Validar formato
            if format not in self.SUPPORTED_FORMATS:
                result['error'] = f"Formato {format} no soportado"
                return result
                
            # Crear sesión
            session_id = f"rec_{int(time.time())}"
            self.active_session = RecordingSession(
                session_id=session_id,
                input_device=device,
                output_path=output_path,
                format=format,
                start_time=time.time(),
                end_time=None,
                duration=0,
                file_size=0,
                markers=[],
                status='recording'
            )
            
            # Construir comando ffmpeg
            dsp_filters = apply_dsp or []
            filter_chain = []
            
            if 'riaa_eq' in dsp_filters or (device.is_turntable and 'riaa_eq' not in dsp_filters):
                filter_chain.append('equalizer=f=50:t=q:w=1:g=-20')  # RIAA simplificado
                filter_chain.append('equalizer=f=500:t=q:w=1:g=0')
                filter_chain.append('equalizer=f=2122:t=q:w=1:g=20')
                
            if 'declicker' in dsp_filters:
                filter_chain.append('afftdn=nf=-70')  # Reducción de clicks
                
            if 'dehisser' in dsp_filters:
                filter_chain.append('afftdn=nf=-80')  # Reducción de hiss
                
            filter_str = ','.join(filter_chain) if filter_chain else ''
            
            cmd = [
                'ffmpeg',
                '-f', 'alsa' if os.name == 'posix' else 'dshow',
                '-i', f'hw:{device.device_id}' if os.name == 'posix' else f'audio={device.device_id}',
                '-ar', str(sample_rate),
                '-ac', str(channels),
                '-sample_fmt', f's{bit_depth//8}',
            ]
            
            if filter_str:
                cmd.extend(['-af', filter_str])
                
            # Formato de salida
            if format == 'wav':
                cmd.extend(['-c:a', 'pcm_s16le', output_path])
            elif format == 'flac':
                cmd.extend(['-c:a', 'flac', '-compression_level', '8', output_path])
            elif format == 'mp3':
                cmd.extend(['-c:a', 'libmp3lame', '-b:a', '320k', output_path])
            elif format == 'opus':
                cmd.extend(['-c:a', 'libopus', '-b:a', '256k', output_path])
                
            logger.info(f"Iniciando grabación: {' '.join(cmd)}")
            
            # Iniciar proceso en hilo separado
            def record_thread():
                try:
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    
                    self.is_recording = True
                    self.is_paused = False
                    
                    # Monitorear progreso
                    while self.is_recording:
                        if self.is_paused:
                            time.sleep(0.1)
                            continue
                            
                        # Actualizar duración y tamaño
                        if os.path.exists(output_path):
                            self.active_session.duration = time.time() - self.active_session.start_time
                            self.active_session.file_size = os.path.getsize(output_path)
                            
                        time.sleep(1)
                        
                    # Detener grabación
                    process.terminate()
                    process.wait(timeout=5)
                    
                    self.active_session.end_time = time.time()
                    self.active_session.duration = self.active_session.end_time - self.active_session.start_time
                    self.active_session.status = 'completed'
                    
                    logger.info(f"Grabación completada: {self.active_session.duration:.2f}s, {self.active_session.file_size} bytes")
                    
                except Exception as e:
                    logger.error(f"Error en grabación: {e}")
                    self.active_session.status = 'error'
                finally:
                    self.is_recording = False
                    
            self.recording_thread = threading.Thread(target=record_thread)
            self.recording_thread.start()
            
            result['success'] = True
            result['session_id'] = session_id
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Error al iniciar grabación: {e}")
            
        return result
    
    def pause_recording(self):
        """Pausa la grabación actual."""
        if self.is_recording and not self.is_paused:
            self.is_paused = True
            self.active_session.status = 'paused'
            logger.info("Grabación pausada")
            
    def resume_recording(self):
        """Reanuda la grabación pausada."""
        if self.is_recording and self.is_paused:
            self.is_paused = False
            self.active_session.status = 'recording'
            logger.info("Grabación reanudada")
            
    def stop_recording(self):
        """Detiene la grabación actual."""
        if self.is_recording:
            self.is_recording = False
            logger.info("Deteniendo grabación...")
            
            # Esperar a que el hilo termine
            if self.recording_thread:
                self.recording_thread.join(timeout=10)
                
    def add_marker(self, timestamp: Optional[float] = None, label: str = "") -> Dict[str, Any]:
        """Agrega un marcador (punto de corte) en la grabación actual."""
        if not self.active_session or not self.is_recording:
            return {'success': False, 'error': 'No hay grabación activa'}
            
        ts = timestamp or (time.time() - self.active_session.start_time)
        marker = {
            'timestamp': ts,
            'label': label or f"Pista {len(self.active_session.markers) + 1}",
            'created_at': time.time()
        }
        
        self.active_session.markers.append(marker)
        logger.info(f"Marcador agregado en {ts:.2f}s: {label}")
        
        return {'success': True, 'marker': marker}
    
    def split_by_markers(self, input_file: str, output_dir: str) -> Dict[str, Any]:
        """Divide una grabación en pistas usando los marcadores."""
        result = {'success': False, 'tracks': [], 'errors': []}
        
        if not self.active_session or not self.active_session.markers:
            result['errors'].append("No hay marcadores para dividir")
            return result
            
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            markers = sorted(self.active_session.markers, key=lambda m: m['timestamp'])
            
            for i, marker in enumerate(markers):
                start_time = marker['timestamp']
                end_time = markers[i+1]['timestamp'] if i+1 < len(markers) else self.active_session.duration
                
                duration = end_time - start_time
                output_filename = f"{i+1:02d}_{marker['label']}.{self.active_session.format}"
                output_path = os.path.join(output_dir, output_filename)
                
                # Usar ffmpeg para cortar
                cmd = [
                    'ffmpeg',
                    '-i', input_file,
                    '-ss', str(start_time),
                    '-t', str(duration),
                    '-c', 'copy',  # Sin re-codificar
                    '-y', output_path
                ]
                
                process = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if process.returncode == 0:
                    result['tracks'].append({
                        'index': i+1,
                        'label': marker['label'],
                        'start': start_time,
                        'duration': duration,
                        'file': output_path
                    })
                else:
                    result['errors'].append(f"Error al cortar pista {i+1}: {process.stderr}")
                    
            result['success'] = len(result['errors']) == 0
            
        except Exception as e:
            result['errors'].append(str(e))
            logger.error(f"Error al dividir por marcadores: {e}")
            
        return result
    
    def get_recording_status(self) -> Dict[str, Any]:
        """Obtiene el estado de la grabación actual."""
        if not self.active_session:
            return {'active': False}
            
        return {
            'active': self.is_recording,
            'paused': self.is_paused,
            'session_id': self.active_session.session_id,
            'device': self.active_session.input_device.name,
            'duration': time.time() - self.active_session.start_time if self.is_recording else self.active_session.duration,
            'file_size': self.active_session.file_size,
            'markers_count': len(self.active_session.markers),
            'status': self.active_session.status,
            'output_path': self.active_session.output_path
        }
