"""Host serial scanner (pyserial) with access-denied detection (§135).

Ports are candidates, not identity; a permission error is distinct from
"no device": the UI must never ask the user to run the app as root.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable
from typing import Any

from michi_ecosystem.ports.serial_devices import SerialCandidate


def _default_list_ports() -> Iterable[Any]:
    from serial.tools import list_ports

    return list_ports.comports()


def _default_access_check(device: str) -> bool:
    return os.access(device, os.R_OK | os.W_OK)


def _candidate_from(info: Any, *, access_fn: Callable[[str], bool]) -> SerialCandidate:
    device = str(getattr(info, "device", "") or "")
    try:
        allowed = access_fn(device)
    except OSError:
        allowed = False
    return SerialCandidate(
        port=device,
        description=str(getattr(info, "description", "") or ""),
        vid=getattr(info, "vid", None),
        pid=getattr(info, "pid", None),
        serial_number=str(getattr(info, "serial_number", "") or ""),
        access_denied=not allowed,
    )


class PyserialScanner:
    """Enumerates USB serial candidates (``/dev/ttyACM*``, ``/dev/ttyUSB*``)."""

    def __init__(
        self,
        *,
        list_ports_fn: Callable[[], Iterable[Any]] | None = None,
        access_fn: Callable[[str], bool] | None = None,
    ) -> None:
        self._list_ports = list_ports_fn or _default_list_ports
        self._access = access_fn or _default_access_check

    def scan(self) -> tuple[SerialCandidate, ...]:
        candidates = [
            _candidate_from(info, access_fn=self._access) for info in self._list_ports()
        ]
        return tuple(sorted(candidates, key=lambda candidate: candidate.port))

    def port_still_present(self, port: str) -> bool:
        return any(candidate.port == port for candidate in self.scan())
