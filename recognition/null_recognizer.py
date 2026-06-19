"""Null Recognizer — placeholder, no internet calls."""

from recognition.models import DetectedTrack


class NullRecognizer:
    name = "none"

    def identify_current(self, source: str = "", filepath: str | None = None) -> DetectedTrack | None:
        return None
