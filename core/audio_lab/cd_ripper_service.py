"""
Servicio de Ripeo de CD de Audio.
Permite extraer pistas de CDs de audio a formatos digitales.
"""
import os
import subprocess
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import logging
import contextlib

logger = logging.getLogger(__name__)

@dataclass
class CDRomDrive:
    device: str
    model: str
    is_audio_capable: bool

@dataclass
class CDTrack:
    track_number: int
    title: str
    artist: str
    duration: float  # seconds
    start_sector: int
    end_sector: int

@dataclass
class CDInfo:
    album_title: str
    album_artist: str
    year: int
    genre: str
    tracks: List[CDTrack]
    disc_id: str
    total_tracks: int

class CDRipperService:
    """Servicio para ripeo de CDs de audio."""

    def __init__(self):
        self.supported_formats = ['flac', 'wav', 'mp3', 'opus', 'aac']
        self.default_format = 'flac'
        self.default_quality = 'lossless'
        self._cancel_requested = False
        self._rip_process: Any = None

    def detect_drives(self) -> List[CDRomDrive]:
        """Detecta unidades de CD/DVD disponibles en el sistema."""
        drives = []

        # Linux: /dev/sr*, /dev/cdrom
        if os.name == 'posix':
            for device in ['/dev/sr0', '/dev/sr1', '/dev/cdrom']:
                if os.path.exists(device):
                    try:
                        # Intentar obtener información del dispositivo
                        result = subprocess.run(
                            ['cdparanoia', '-V'],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        model = "Unknown Drive"
                        if result.returncode == 0:
                            # Parsear salida de cdparanoia para obtener modelo
                            for line in result.stdout.split('\n'):
                                if 'drive' in line.lower():
                                    model = line.strip()
                                    break

                        drives.append(CDRomDrive(
                            device=device,
                            model=model,
                            is_audio_capable=True
                        ))
                    except Exception as e:
                        logger.warning(f"Error al verificar unidad {device}: {e}")

        # Windows: letras de unidad
        elif os.name == 'nt':
            import string
            for drive_letter in string.ascii_uppercase:
                drive_path = f"{drive_letter}:"
                try:
                    # Verificar si es una unidad óptica
                    result = subprocess.run(
                        ['wmic', 'cdrom', 'get', 'drive'],
                        capture_output=True,
                        text=True
                    )
                    if drive_path in result.stdout:
                        drives.append(CDRomDrive(
                            device=drive_path,
                            model=f"CD Drive ({drive_letter}:)",
                            is_audio_capable=True
                        ))
                except Exception:
                    continue

        return drives

    def get_cd_info(self, device: str) -> Optional[CDInfo]:
        """Obtiene información del CD insertado usando cd-discid."""
        try:
            result = subprocess.run(
                ['cd-discid', device],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                logger.error(f"Error al leer Disc ID: {result.stderr}")
                return None

            parts = result.stdout.strip().split()
            if len(parts) < 3:
                logger.error("Salida de cd-discid demasiado corta: %s", result.stdout)
                return None

            disc_id = parts[0]
            # Los offsets de pista son los elementos 1..n-1
            offsets = [int(x) for x in parts[1:-1]]
            # El ultimo elemento es la duracion total del CD en segundos
            leadout_seconds = int(parts[-1])

            first_offset = offsets[0] if offsets else 0
            # El leadout absoluto en frames = duracion en segundos * 75 + primer offset
            leadout_frame = leadout_seconds * 75 + first_offset

            tracks = []
            for i, start in enumerate(offsets):
                end = offsets[i + 1] if i + 1 < len(offsets) else leadout_frame
                duration = (end - start) / 75.0
                if duration <= 0:
                    duration = 2.0
                tracks.append(CDTrack(
                    track_number=i + 1,
                    title=f"Track {i + 1}",
                    artist="Unknown",
                    duration=round(duration, 1),
                    start_sector=start,
                    end_sector=end,
                ))

            return CDInfo(
                album_title="Unknown Album",
                album_artist="Various Artists",
                year=0,
                genre="Unknown",
                tracks=tracks,
                disc_id=disc_id,
                total_tracks=len(tracks),
            )
        except Exception as e:
            logger.error(f"Error al obtener información del CD: {e}")
            return None

    def _build_command(self, format: str, device: str, track_number: int,
                       output_path: str) -> list[str] | None:
        codec_args = {
            'flac': ['-c:a', 'flac', '-compression_level', '8'],
            'wav': ['-c:a', 'pcm_s16le'],
            'mp3': ['-c:a', 'libmp3lame', '-b:a', '320k'],
        }
        args = codec_args.get(format)
        if args is None:
            return None
        return ['ffmpeg', '-f', 'cdaudio', '-i', f'{device}:{track_number}'] + args + ['-y', output_path]

    def rip_track(
        self,
        device: str,
        track_number: int,
        output_path: str,
        format: str = 'flac',
        quality: str = 'lossless'
    ) -> Dict[str, Any]:
        """Extrae una pista individual del CD."""
        result = {
            'success': False,
            'error': None,
            'output_file': output_path,
            'log': []
        }

        try:
            cmd = self._build_command(format, device, track_number, output_path)
            if cmd is None:
                result['error'] = f"Formato {format} no soportado"
                return result

            logger.info(f"Ejecutando ripeo: {' '.join(cmd)}")
            self._cancel_requested = False
            self._rip_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            try:
                stdout, stderr = self._rip_process.communicate(timeout=300)
                if self._cancel_requested:
                    result['error'] = "CANCELLED"
                    result['log'].append("Ripeo cancelado por el usuario")
                    return result
                if self._rip_process.returncode == 0:
                    result['success'] = True
                    result['log'].append(f"Pista {track_number} extraída exitosamente")
                else:
                    result['error'] = stderr
                    result['log'].append(f"Error en ripeo: {stderr}")
            except subprocess.TimeoutExpired:
                if self._rip_process:
                    self._rip_process.kill()
                    self._rip_process.wait()
                result['error'] = "Tiempo de espera agotado durante el ripeo"
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Error en ripeo de pista {track_number}: {e}")

        return result

    def rip_full_cd(
        self,
        device: str,
        output_dir: str,
        format: str = 'flac',
        quality: str = 'lossless',
        include_log: bool = True
    ) -> Dict[str, Any]:
        """Extrae todo el CD a una carpeta."""
        result = {
            'success': False,
            'tracks_completed': 0,
            'tracks_failed': 0,
            'errors': [],
            'log_file': None
        }

        # Obtener información del CD
        cd_info = self.get_cd_info(device)
        if not cd_info:
            result['errors'].append("No se pudo obtener información del CD")
            return result

        # Crear directorio de salida
        album_dir = os.path.join(output_dir, f"{cd_info.album_artist} - {cd_info.album_title}")
        os.makedirs(album_dir, exist_ok=True)

        log_entries = []

        # Extraer cada pista
        for i in range(1, cd_info.total_tracks + 1):
            filename = f"{i:02d}. {cd_info.tracks[i-1].title if i <= len(cd_info.tracks) else f'Track {i}'}.{format}"
            output_path = os.path.join(album_dir, filename)

            track_result = self.rip_track(device, i, output_path, format, quality)

            if track_result['success']:
                result['tracks_completed'] += 1
                log_entries.extend(track_result['log'])
            else:
                result['tracks_failed'] += 1
                result['errors'].append(f"Pista {i}: {track_result['error']}")

        # Generar log si se solicita
        if include_log and log_entries:
            log_path = os.path.join(album_dir, "ripping_log.txt")
            with open(log_path, 'w') as f:
                f.write(f"CD Rip Log - {cd_info.album_title}\n")
                f.write(f"Disc ID: {cd_info.disc_id}\n")
                f.write("="*50 + "\n")
                for entry in log_entries:
                    f.write(entry + "\n")
                if result['errors']:
                    f.write("\nErrors:\n")
                    for error in result['errors']:
                        f.write(f"- {error}\n")
            result['log_file'] = log_path

        result['success'] = result['tracks_failed'] == 0
        return result

    def cancel_rip(self):
        """Cancela el ripeo en curso."""
        self._cancel_requested = True
        if self._rip_process and self._rip_process.poll() is None:
            try:
                self._rip_process.terminate()
                self._rip_process.wait(timeout=5)
            except Exception:
                with contextlib.suppress(Exception):
                    self._rip_process.kill()
