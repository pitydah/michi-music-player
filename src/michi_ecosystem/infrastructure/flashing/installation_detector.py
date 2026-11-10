"""Read-only installation forensics for CREATE_NEW safety (WP-3).

ESP-IDF conventions used (read-only probes only):

- partition table at ``0x8000`` (the bootloader default location);
- partition entries with magic bytes ``AA 50`` and app type ``0x00``;
- ESP app image magic byte ``0xE9`` at the app partition offset.

Evidence rules (fail closed):

- probe region fully erased (0xFF/0x00)          -> BLANK
- valid table and/or readable app image present -> INSTALLED
- anything else (unreadable, non-erased but     -> UNKNOWN
  unrecognized)

A firmware-side product marker contract is requested upstream (STREAM-REQ-005);
while it is open this detector is forensic, and UNKNOWN always blocks CREATE_NEW.
"""

from __future__ import annotations

import struct
from collections.abc import Callable

from michi_ecosystem.ports.flash_backend import FlashBackendError
from michi_ecosystem.ports.installation_detector import (
    FlashReaderPort,
    InstallationEvidence,
    InstallationReport,
)

PARTITION_TABLE_OFFSET = 0x8000
PARTITION_TABLE_SIZE = 0x1000
_ENTRY_SIZE = 32
_APP_TYPE = 0x00
_IMAGE_MAGIC = 0xE9


def _is_erased(data: bytes) -> bool:
    """NOR flash erased state is 0xFF only; anything else needs recognition."""
    return all(byte == 0xFF for byte in data)


def _parse_app_entries(table: bytes) -> list[tuple[int, str]]:
    entries: list[tuple[int, str]] = []
    for start in range(0, len(table) - _ENTRY_SIZE + 1, _ENTRY_SIZE):
        chunk = table[start : start + _ENTRY_SIZE]
        if chunk[0] != 0xAA or chunk[1] != 0x50:
            break
        entry_type = chunk[2]
        offset = struct.unpack_from("<I", chunk, 4)[0]
        label = chunk[12:28].split(b"\x00", 1)[0].decode("ascii", "replace")
        if entry_type == _APP_TYPE:
            entries.append((offset, label))
    return entries


def analyze_installation(
    table: bytes, read_header: Callable[[int], bytes]
) -> InstallationReport:
    """Pure analysis with an injected header reader (tests need no hardware)."""
    if _is_erased(table):
        return InstallationReport(
            InstallationEvidence.BLANK, "tabla de particiones vacía"
        )
    entries = _parse_app_entries(table)
    if not entries:
        return InstallationReport(
            InstallationEvidence.UNKNOWN, "contenido no reconocible"
        )
    for offset, label in entries:
        try:
            header = read_header(offset)
        except FlashBackendError:
            return InstallationReport(
                InstallationEvidence.UNKNOWN, "no se pudo leer la partición app"
            )
        if header and header[0] == _IMAGE_MAGIC:
            return InstallationReport(
                InstallationEvidence.INSTALLED,
                f"app presente: {label or hex(offset)}",
            )
    return InstallationReport(
        InstallationEvidence.INSTALLED, "tabla de particiones existente"
    )


class EspInstallationDetector:
    """Detector over a flash reader (the esptool backend satisfies the port)."""

    def __init__(self, reader: FlashReaderPort) -> None:
        self._reader = reader

    def inspect(self, port: str) -> InstallationReport:
        try:
            table = self._reader.read_region(
                port, PARTITION_TABLE_OFFSET, PARTITION_TABLE_SIZE
            )
        except FlashBackendError as exc:
            return InstallationReport(
                InstallationEvidence.UNKNOWN, f"lectura falló: {exc}"
            )
        if len(table) != PARTITION_TABLE_SIZE:
            return InstallationReport(
                InstallationEvidence.UNKNOWN, "lectura incompleta"
            )

        def read_header(offset: int) -> bytes:
            return self._reader.read_region(port, offset, 4)

        return analyze_installation(table, read_header)
