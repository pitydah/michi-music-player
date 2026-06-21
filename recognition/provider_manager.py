"""Provider Manager — selects and configures the active recognizer."""
from PySide6.QtCore import QObject, Signal

from recognition.base_recognizer import BaseRecognizer
from recognition.null_recognizer import NullRecognizer


class ProviderManager(QObject):
    provider_changed = Signal(str, bool)  # provider_name, is_configured
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_provider = "none"
        self._recognizer: BaseRecognizer = NullRecognizer()
        self._api_keys: dict[str, str] = {}

    @property
    def recognizer(self) -> BaseRecognizer:
        return self._recognizer

    @property
    def current_provider(self) -> str:
        return self._current_provider

    def set_api_key(self, provider: str, key: str):
        self._api_keys[provider] = key
        if provider == self._current_provider:
            self._recognizer.configure(key)

    def select_provider(self, name: str):
        self._current_provider = name
        if name == "none":
            self._recognizer = NullRecognizer()
        elif name == "shazamio":
            self._recognizer = _ShazamIOStub()
        elif name == "audd":
            self._recognizer = _AudDStub()
        elif name == "acrcloud":
            self._recognizer = _ACRCloudStub()
        elif name == "acoustid":
            self._recognizer = _AcoustIDStub()
        else:
            self._recognizer = NullRecognizer()

        key = self._api_keys.get(name, "")
        self._recognizer.configure(key)
        ok = self._recognizer.is_configured()
        self.provider_changed.emit(name, ok)

    def test_current(self) -> tuple[bool, str]:
        return self._recognizer.test_connection()


# ── Provider stubs (real implementations Phase 2) ──

class _ShazamIOStub(BaseRecognizer):
    name = "shazamio"
    requires_api_key = False

    def identify(self, sample_bytes=None, source="", filepath=""):
        import importlib.util
        if importlib.util.find_spec("shazamio") is None:
            return None
        return None  # placeholder


class _AudDStub(BaseRecognizer):
    name = "audd"
    requires_api_key = True

    def identify(self, sample_bytes=None, source="", filepath=""):
        return None  # requires API key + audio capture


class _ACRCloudStub(BaseRecognizer):
    name = "acrcloud"
    requires_api_key = True

    def identify(self, sample_bytes=None, source="", filepath=""):
        return None


class _AcoustIDStub(BaseRecognizer):
    name = "acoustid"
    requires_api_key = False  # optional

    def identify(self, sample_bytes=None, source="", filepath=""):
        return None
