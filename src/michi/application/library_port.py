"""Application ports — library scanner interface."""

from abc import ABC, abstractmethod
from pathlib import Path


class LibraryScannerPort(ABC):
    """Abstract library scanner. Infrastructure implements filesystem access."""

    @abstractmethod
    def scan(self, root: Path) -> list[Path]: ...
