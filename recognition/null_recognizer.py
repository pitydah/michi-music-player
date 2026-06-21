"""Null Recognizer — fallback when no provider is configured."""
from recognition.base_recognizer import BaseRecognizer


class NullRecognizer(BaseRecognizer):
    name = "none"

    def identify(self, sample_bytes=None, source="", filepath=""):
        return None
