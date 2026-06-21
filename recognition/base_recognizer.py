"""Base Recognizer — abstract interface for music identification providers."""
from abc import ABC, abstractmethod


class BaseRecognizer(ABC):
    name: str = "base"
    requires_api_key: bool = False
    api_key: str = ""

    def configure(self, api_key: str = ""):
        self.api_key = api_key

    def is_configured(self) -> bool:
        if self.requires_api_key:
            return bool(self.api_key)
        return True

    @abstractmethod
    def identify(self, sample_bytes: bytes | None = None,
                 source: str = "", filepath: str = "") -> dict | None:
        """Identify a track. Returns dict with title/artist/album/confidence or None."""
        ...

    def test_connection(self) -> tuple[bool, str]:
        """Test if the provider is reachable."""
        return True, ""
