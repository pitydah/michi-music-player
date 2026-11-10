"""esptool subprocess backend (master plan §142): argument lists only.

Credentials never appear in command arguments: only opaque bounded blobs are
written through secure temporary files (0700 dir, 0600 file) removed
immediately. ``verify_segment`` performs a real read-back (``read-flash``)
plus SHA-256 comparison; subcommand names follow modern esptool.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path

from michi_ecosystem.domain.flashing import PhysicalDeviceIdentity
from michi_ecosystem.ports.flash_backend import (
    FlashBackendError,
    FlashResetError,
)

DEFAULT_TIMEOUT_SECONDS = 300.0

_MAC_RE = re.compile(r"MAC:\s*([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})")


def chip_id_command(python: str, port: str) -> list[str]:
    return [python, "-m", "esptool", "--port", port, "chip-id"]


def read_mac_command(python: str, port: str) -> list[str]:
    """Dedicated eFuse MAC read (esptool v5), not incidental chip-id stdout."""
    return [python, "-m", "esptool", "--port", port, "read-mac"]


def erase_command(python: str, port: str) -> list[str]:
    return [python, "-m", "esptool", "--port", port, "erase-flash"]


def write_command(python: str, port: str, offset: int, image: Path) -> list[str]:
    return [
        python,
        "-m",
        "esptool",
        "--port",
        port,
        "write-flash",
        hex(offset),
        str(image),
    ]


def read_command(
    python: str, port: str, offset: int, size: int, image: Path
) -> list[str]:
    return [
        python,
        "-m",
        "esptool",
        "--port",
        port,
        "read-flash",
        hex(offset),
        hex(size),
        str(image),
    ]


def reset_command(python: str, port: str) -> list[str]:
    # esptool v5 syntax is `hard-reset` (hyphen), verified by a real-parser
    # smoke test; `hard_reset` is rejected as an invalid choice.
    return [python, "-m", "esptool", "--port", port, "--after", "hard-reset", "chip-id"]


def _parse_chip(stdout: str) -> str | None:
    lowered = stdout.lower()
    if "esp32-s3" in lowered:
        return "esp32s3"
    if "esp32" in lowered:
        return "esp32"
    return None


class EsptoolBackend:
    def __init__(
        self,
        *,
        python: str = sys.executable,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        runner: Callable[..., subprocess.CompletedProcess] | None = None,
    ) -> None:
        self._python = python
        self._timeout = timeout
        self._runner = runner or subprocess.run

    def _run(
        self, args: Sequence[str], *, check: bool = True
    ) -> subprocess.CompletedProcess:
        try:
            completed = self._runner(
                list(args),
                check=False,
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise FlashBackendError(f"esptool failed to start: {exc}") from exc
        if check and completed.returncode != 0:
            detail = (completed.stderr or "").strip()[:200]
            raise FlashBackendError(
                f"esptool exited with {completed.returncode}: {detail}"
            )
        return completed

    def probe_chip(self, port: str) -> str | None:
        completed = self._run(chip_id_command(self._python, port), check=False)
        if completed.returncode != 0:
            return None
        return _parse_chip(completed.stdout or "")

    def read_device_identity(self, port: str) -> PhysicalDeviceIdentity | None:
        """Stable identity: chip target (``chip-id``) + eFuse MAC (``read-mac``).

        The MAC survives re-enumeration; when it cannot be read the identity is
        unknown and destructive operations fail closed.
        """
        chip_result = self._run(chip_id_command(self._python, port), check=False)
        chip = (
            _parse_chip(chip_result.stdout or "")
            if chip_result.returncode == 0
            else None
        )
        mac_result = self._run(read_mac_command(self._python, port), check=False)
        if mac_result.returncode != 0:
            return None
        match = _MAC_RE.search(mac_result.stdout or "")
        if chip is None or match is None:
            return None
        mac = match.group(1).lower()
        return PhysicalDeviceIdentity(chip_target=chip, chip_uid=mac, mac=mac)

    def erase_flash(self, port: str) -> None:
        self._run(erase_command(self._python, port))

    def write_segment(self, port: str, offset: int, payload: bytes) -> None:
        with tempfile.TemporaryDirectory(prefix="michi-flash-") as tmp:
            os.chmod(tmp, 0o700)
            image = Path(tmp) / "segment.bin"
            image.write_bytes(payload)
            os.chmod(image, 0o600)
            self._run(write_command(self._python, port, offset, image))

    def read_region(self, port: str, offset: int, size: int) -> bytes:
        """Read a flash region back (verification and installation forensics)."""
        if size <= 0:
            raise FlashBackendError("cannot read an empty region")
        with tempfile.TemporaryDirectory(prefix="michi-read-") as tmp:
            os.chmod(tmp, 0o700)
            image = Path(tmp) / "readback.bin"
            self._run(read_command(self._python, port, offset, size, image))
            return image.read_bytes()

    def verify_segment(
        self, port: str, offset: int, size: int, expected_sha256: str
    ) -> bool:
        if size <= 0:
            raise FlashBackendError("cannot verify a segment without size")
        data = self.read_region(port, offset, size)
        if len(data) != size:
            return False
        return hashlib.sha256(data).hexdigest() == expected_sha256.strip().lower()

    def hard_reset(self, port: str) -> None:
        completed = self._run(reset_command(self._python, port), check=False)
        if completed.returncode != 0:
            detail = (completed.stderr or "").strip()[:200]
            raise FlashResetError(
                f"no se pudo reiniciar la placa (esptool {completed.returncode}): "
                f"{detail}"
            )
