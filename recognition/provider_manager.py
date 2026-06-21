"""Provider Manager — selects and configures the active recognizer."""
from PySide6.QtCore import QObject, Signal

from recognition.base_recognizer import BaseRecognizer
from recognition.null_recognizer import NullRecognizer

# Lazy-load real providers to avoid mandatory deps
_SHARED_PROVIDERS: dict[str, BaseRecognizer] = {}


def _get_provider(name: str) -> BaseRecognizer | None:
    """Get or create a recognizer instance by name. Returns None if unavailable."""
    if name in _SHARED_PROVIDERS:
        return _SHARED_PROVIDERS[name]

    inst = None
    try:
        if name == "shazamio":
            from recognition.providers.shazam import ShazamProvider
            inst = ShazamProvider()
        elif name == "audd":
            from recognition.providers.audd import AudDProvider
            inst = AudDProvider()
        elif name == "acoustid":
            from recognition.providers.acoustid import AcoustIDProvider
            inst = AcoustIDProvider()
    except ImportError:
        pass

    if inst is not None:
        _SHARED_PROVIDERS[name] = inst
    return inst


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
            ok = self._recognizer.is_configured()
            self.provider_changed.emit(provider, ok)

    def select_provider(self, name: str):
        self._current_provider = name

        if name == "none":
            self._recognizer = NullRecognizer()
        elif name in ("shazamio", "audd", "acoustid"):
            real = _get_provider(name)
            self._recognizer = real if real is not None else NullRecognizer()
        else:
            self._recognizer = NullRecognizer()

        key = self._api_keys.get(name, "")
        self._recognizer.configure(key)
        ok = self._recognizer.is_configured()
        self.provider_changed.emit(name, ok)

    def test_current(self) -> tuple[bool, str]:
        return self._recognizer.test_connection()
