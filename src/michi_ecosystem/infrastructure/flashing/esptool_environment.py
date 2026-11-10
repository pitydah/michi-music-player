"""esptool environment contract (A2): installed / version / supported.

One supported major is declared: **v5** (``esptool>=5,<6`` in the ``flashing``
extra). Missing or unsupported tooling fails closed — no destructive operation
runs without a supported esptool.
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass

SUPPORTED_MAJOR = 5

_VERSION_RE = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?")


class EsptoolEnvironmentError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class EsptoolEnvironment:
    installed: bool
    version: str | None
    supported: bool


def parse_version(output: str) -> str | None:
    match = _VERSION_RE.search(output)
    return match.group(0) if match else None


def probe_esptool(
    python: str = sys.executable,
    *,
    runner: Callable[..., subprocess.CompletedProcess] | None = None,
) -> EsptoolEnvironment:
    """Probe the installed esptool without touching any USB device."""
    run = runner or subprocess.run
    try:
        completed = run(
            [python, "-m", "esptool", "version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return EsptoolEnvironment(installed=False, version=None, supported=False)
    if completed.returncode != 0:
        return EsptoolEnvironment(installed=False, version=None, supported=False)
    version = parse_version(completed.stdout or "")
    if version is None:
        return EsptoolEnvironment(installed=True, version=None, supported=False)
    major = int(version.split(".")[0])
    return EsptoolEnvironment(
        installed=True, version=version, supported=major == SUPPORTED_MAJOR
    )


def require_supported_esptool(environment: EsptoolEnvironment) -> None:
    """Fail closed when the tooling contract cannot be honored."""
    if not environment.installed:
        raise EsptoolEnvironmentError(
            "ESPTOOL_MISSING",
            "esptool no está instalado; no se puede flashear de forma segura.",
        )
    if not environment.supported:
        raise EsptoolEnvironmentError(
            "ESPTOOL_UNSUPPORTED_VERSION",
            f"esptool {environment.version} no está soportado "
            f"(se requiere la major {SUPPORTED_MAJOR}).",
        )
