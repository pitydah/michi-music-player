"""Persistence health taxonomy — typed diagnostics. No Qt, no I/O."""

from dataclasses import dataclass
from enum import Enum


class PersistenceHealth(Enum):
    MISSING = "missing"
    HEALTHY = "healthy"
    CORRUPT_DATABASE = "corrupt_database"
    MALFORMED_DATA = "malformed_data"
    LOCKED = "locked"
    ACCESS_FAILURE = "access_failure"
    IO_FAILURE = "io_failure"
    UNKNOWN_FAILURE = "unknown_failure"


@dataclass(frozen=True)
class PersistenceDiagnostic:
    health: PersistenceHealth
    message: str = ""
