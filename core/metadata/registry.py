from __future__ import annotations

from core.metadata.models import FormatCapability


class MetadataFormatRegistry:
    def __init__(self):
        self._formats: dict[str, FormatCapability] = {}

    def register(self, cap: FormatCapability):
        self._formats[cap.format_id] = cap

    def get(self, format_id: str) -> FormatCapability | None:
        return self._formats.get(format_id)

    def get_by_extension(self, ext: str) -> FormatCapability | None:
        ext = ext.lower().lstrip(".")
        for cap in self._formats.values():
            if ext in cap.extensions:
                return cap
        return None

    def list_readable(self) -> list[FormatCapability]:
        return [c for c in self._formats.values() if c.readable]

    def list_writable(self) -> list[FormatCapability]:
        return [c for c in self._formats.values() if c.writable]

    def is_readable(self, ext: str) -> bool:
        cap = self.get_by_extension(ext)
        return cap is not None and cap.readable

    def is_writable(self, ext: str) -> bool:
        cap = self.get_by_extension(ext)
        return cap is not None and cap.writable

    def all(self) -> list[FormatCapability]:
        return list(self._formats.values())

    @staticmethod
    def default_registry() -> MetadataFormatRegistry:
        reg = MetadataFormatRegistry()
        reg.register(FormatCapability(
            format_id="mp3_id3",
            extensions=["mp3"],
            mime_types=["audio/mpeg", "audio/mp3"],
            readable=True, writable=True,
            artwork_readable=True, artwork_writable=True,
            lyrics_readable=True, lyrics_writable=True,
            multi_value_support=False,
            custom_field_support=True,
            lossless_write=False,
        ))
        reg.register(FormatCapability(
            format_id="flac",
            extensions=["flac"],
            mime_types=["audio/flac"],
            readable=True, writable=True,
            artwork_readable=True, artwork_writable=True,
            lyrics_readable=True, lyrics_writable=True,
            multi_value_support=True,
            custom_field_support=True,
            lossless_write=True,
        ))
        reg.register(FormatCapability(
            format_id="ogg_vorbis",
            extensions=["ogg", "oga"],
            mime_types=["audio/ogg", "audio/vorbis"],
            readable=True, writable=True,
            artwork_readable=True, artwork_writable=True,
            lyrics_readable=True, lyrics_writable=True,
            multi_value_support=True,
            custom_field_support=True,
            lossless_write=True,
        ))
        reg.register(FormatCapability(
            format_id="opus",
            extensions=["opus"],
            mime_types=["audio/opus", "audio/ogg"],
            readable=True, writable=True,
            artwork_readable=True, artwork_writable=True,
            lyrics_readable=True, lyrics_writable=True,
            multi_value_support=True,
            custom_field_support=True,
            lossless_write=True,
        ))
        reg.register(FormatCapability(
            format_id="mp4",
            extensions=["m4a", "mp4", "m4b"],
            mime_types=["audio/mp4", "audio/aac", "audio/m4a"],
            readable=True, writable=True,
            artwork_readable=True, artwork_writable=True,
            lyrics_readable=True, lyrics_writable=True,
            multi_value_support=False,
            custom_field_support=True,
            lossless_write=False,
        ))
        reg.register(FormatCapability(
            format_id="wav",
            extensions=["wav"],
            mime_types=["audio/wav", "audio/x-wav"],
            readable=True, writable=False,
            artwork_readable=False, artwork_writable=False,
            lyrics_readable=False, lyrics_writable=False,
            multi_value_support=False,
            custom_field_support=False,
            lossless_write=True,
        ))
        reg.register(FormatCapability(
            format_id="aiff",
            extensions=["aiff", "aif"],
            mime_types=["audio/aiff", "audio/x-aiff"],
            readable=True, writable=False,
            artwork_readable=False, artwork_writable=False,
            lyrics_readable=False, lyrics_writable=False,
            multi_value_support=False,
            custom_field_support=False,
            lossless_write=True,
        ))
        reg.register(FormatCapability(
            format_id="ape",
            extensions=["ape"],
            mime_types=["audio/ape", "audio/x-ape"],
            readable=True, writable=False,
            artwork_readable=False, artwork_writable=False,
            lyrics_readable=False, lyrics_writable=False,
            multi_value_support=True,
            custom_field_support=True,
            lossless_write=True,
        ))
        reg.register(FormatCapability(
            format_id="wma_asf",
            extensions=["wma"],
            mime_types=["audio/x-ms-wma"],
            readable=True, writable=False,
            artwork_readable=False, artwork_writable=False,
            lyrics_readable=False, lyrics_writable=False,
            multi_value_support=True,
            custom_field_support=False,
            lossless_write=False,
        ))
        reg.register(FormatCapability(
            format_id="dsf",
            extensions=["dsf"],
            mime_types=["audio/dsf", "audio/x-dsf"],
            readable=True, writable=False,
            artwork_readable=False, artwork_writable=False,
            lyrics_readable=False, lyrics_writable=False,
            multi_value_support=False,
            custom_field_support=False,
            lossless_write=True,
        ))
        return reg
