"""Encoder service — real audio encoding via flac/lame/ffmpeg QProcess."""

from __future__ import annotations

import logging
import os

from PySide6.QtCore import QObject, Signal, QProcess

logger = logging.getLogger("michi.audio_lab.encoder")


class EncoderService(QObject):
    encode_finished = Signal(str, str)
    encode_error = Signal(str, str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._processes: list[QProcess] = []

    def check_available_encoders(self) -> dict[str, bool]:
        import shutil
        return {
            "flac": shutil.which("flac") is not None,
            "lame": shutil.which("lame") is not None,
            "opus": shutil.which("opusenc") is not None,
            "ffmpeg": shutil.which("ffmpeg") is not None,
        }

    def _on_encoder_error(self, error: QProcess.ProcessError, input_path: str, proc=None):
        if proc:
            self._cleanup_process(proc)
        label = {
            QProcess.FailedToStart: "Programa no encontrado. ¿Está instalado?",
            QProcess.Crashed: "El proceso se detuvo inesperadamente.",
            QProcess.Timedout: "El proceso tardó demasiado.",
        }.get(error, f"Error de proceso ({error})")
        self.encode_error.emit(input_path, label)

    def encode_to_flac(self, input_path: str, output_path: str,
                       compression: int = 8):
        if not os.path.exists(input_path):
            self.encode_error.emit(input_path, "Archivo de entrada no encontrado.")
            return

        proc = QProcess(self)
        self._processes.append(proc)
        proc.finished.connect(
            lambda ec, es, ip=input_path, op=output_path:
            self._on_flac_done(ec, es, ip, op)
        )
        proc.errorOccurred.connect(
            lambda err, ip=input_path, p=proc: self._on_encoder_error(err, ip, p)
        )
        proc.start("flac", [
            "--best" if compression >= 8 else f"-{compression}",
            "-o", output_path, input_path,
        ])

    def encode_to_mp3(self, input_path: str, output_path: str, bitrate: int = 320):
        if not os.path.exists(input_path):
            self.encode_error.emit(input_path, "Archivo de entrada no encontrado.")
            return

        proc = QProcess(self)
        self._processes.append(proc)
        proc.finished.connect(
            lambda ec, es, ip=input_path, op=output_path:
            self._on_encode_done(ec, es, ip, op)
        )
        proc.errorOccurred.connect(
            lambda err, ip=input_path, p=proc: self._on_encoder_error(err, ip, p)
        )
        proc.start("lame", [
            "-b", str(bitrate), "--quiet", input_path, output_path,
        ])

    def encode_to_opus(self, input_path: str, output_path: str, bitrate: int = 192):
        if not os.path.exists(input_path):
            self.encode_error.emit(input_path, "Archivo de entrada no encontrado.")
            return

        proc = QProcess(self)
        self._processes.append(proc)
        proc.finished.connect(
            lambda ec, es, ip=input_path, op=output_path:
            self._on_encode_done(ec, es, ip, op)
        )
        proc.errorOccurred.connect(
            lambda err, ip=input_path, p=proc: self._on_encoder_error(err, ip, p)
        )
        proc.start("opusenc", [
            "--bitrate", str(bitrate), "--quiet", input_path, output_path,
        ])

    def encode_to_alac(self, input_path: str, output_path: str):
        if not os.path.exists(input_path):
            self.encode_error.emit(input_path, "Archivo de entrada no encontrado.")
            return

        proc = QProcess(self)
        self._processes.append(proc)
        proc.finished.connect(
            lambda ec, es, ip=input_path, op=output_path:
            self._on_encode_done(ec, es, ip, op)
        )
        proc.errorOccurred.connect(
            lambda err, ip=input_path, p=proc: self._on_encoder_error(err, ip, p)
        )
        proc.start("ffmpeg", [
            "-y", "-i", input_path, "-acodec", "alac", output_path,
        ])

    def encode_multiple_outputs(self, input_path: str, outputs: list[str],
                                output_dir: str):
        base = os.path.splitext(os.path.basename(input_path))[0]
        for fmt in outputs:
            ext = fmt if fmt != "flac" else "flac"
            out_path = os.path.join(output_dir, f"{base}.{ext}")
            if fmt == "flac":
                self.encode_to_flac(input_path, out_path)
            elif fmt == "mp3":
                self.encode_to_mp3(input_path, out_path, 320)

    def _on_flac_done(self, exit_code: int, _exit_status,
                      input_path: str, output_path: str):
        self._cleanup_process(self.sender())
        if exit_code == 0:
            self.encode_finished.emit(input_path, output_path)
        else:
            self.encode_error.emit(input_path, f"FLAC encoding failed (exit {exit_code})")

    def _on_encode_done(self, exit_code: int, _exit_status,
                        input_path: str, output_path: str):
        self._cleanup_process(self.sender())
        if exit_code == 0:
            self.encode_finished.emit(input_path, output_path)
        else:
            self.encode_error.emit(input_path, f"Encoding failed (exit {exit_code})")

    def _cleanup_process(self, proc):
        if proc in self._processes:
            self._processes.remove(proc)
