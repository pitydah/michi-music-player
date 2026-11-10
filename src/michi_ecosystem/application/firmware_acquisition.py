"""Firmware acquisition service (E1/E3).

Resolves, downloads and verifies firmware BEFORE the factory can plan or
approve anything. Product selection is the official recommended release;
``dev_local`` exists only behind an explicit developer-mode flag (E7).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from michi_ecosystem.domain.firmware import (
    FirmwareProvenance,
    FirmwareRelease,
)
from michi_ecosystem.infrastructure.flashing.github_firmware_repository import (
    FirmwareRepositoryError,
)
from michi_ecosystem.ports.firmware_repository import FirmwareRepositoryPort


class FirmwareSelection(StrEnum):
    OFFICIAL_RECOMMENDED = "official_recommended"
    DEV_LOCAL = "dev_local"


@dataclass(frozen=True)
class AcquiredFirmware:
    source: FirmwareSelection
    reference: str  # manifest path usable by the factory catalog loader
    release: FirmwareRelease | None = None
    provenance: FirmwareProvenance | None = None


class FirmwareAcquisitionError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class FirmwareAcquisitionService:
    def __init__(
        self,
        *,
        repository: FirmwareRepositoryPort | None = None,
        dev_repository=None,
    ) -> None:
        self._repository = repository
        self._dev_repository = dev_repository

    def acquire_recommended(
        self,
        board: str,
        channel: str = "stable",
        *,
        progress: Callable[[int, int | None], None] | None = None,
    ) -> AcquiredFirmware:
        if self._repository is None:
            raise FirmwareAcquisitionError(
                "OFFICIAL_FIRMWARE_UNAVAILABLE",
                "No hay firmware oficial disponible todavía.",
            )
        try:
            release = self._repository.recommended(board, channel)
        except FirmwareRepositoryError as exc:
            raise FirmwareAcquisitionError(exc.code, exc.message) from exc
        if release is None:
            raise FirmwareAcquisitionError(
                "OFFICIAL_FIRMWARE_UNAVAILABLE",
                "No hay firmware oficial disponible todavía.",
            )
        try:
            resolved = self._repository.materialize(release, progress=progress)
        except FirmwareRepositoryError as exc:
            raise FirmwareAcquisitionError(exc.code, exc.message) from exc
        return AcquiredFirmware(
            source=FirmwareSelection.OFFICIAL_RECOMMENDED,
            reference=str(resolved.manifest.source),
            release=release,
            provenance=resolved.provenance,
        )

    def acquire_dev_local(
        self, reference: str, *, developer_mode: bool
    ) -> AcquiredFirmware:
        if not developer_mode:
            raise FirmwareAcquisitionError(
                "DEV_MODE_REQUIRED",
                "el firmware local requiere modo desarrollador explícito",
            )
        if self._dev_repository is None:
            raise FirmwareAcquisitionError(
                "DEV_REPOSITORY_NOT_CONFIGURED",
                "no hay repositorio local configurado",
            )
        try:
            manifest = self._dev_repository.load(reference)
        except KeyError as exc:
            raise FirmwareAcquisitionError("DEV_FIRMWARE_NOT_FOUND", str(exc)) from exc
        return AcquiredFirmware(
            source=FirmwareSelection.DEV_LOCAL,
            reference=str(manifest.source),
        )
