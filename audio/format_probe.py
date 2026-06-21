"""Audio Format Probe — extracts technical metadata about a track."""
from dataclasses import dataclass, field


@dataclass
class AudioFormatInfo:
    path_or_uri: str = ""
    is_stream: bool = False
    container: str = ""
    codec: str = ""
    is_pcm: bool = False
    is_lossless: bool = False
    is_dsd: bool = False
    is_dsf: bool = False
    is_dff: bool = False
    is_dst: bool = False
    dsd_rate: int = 0
    dsd_speed: str = ""
    sample_rate: int = 0
    bit_depth: int = 0
    channels: int = 0
    bitrate: int = 0
    duration: float = 0.0
    replaygain_track_db: float | None = None
    replaygain_album_db: float | None = None
    has_gapless_tags: bool = False
    warnings: list[str] = field(default_factory=list)


def probe_format(filepath: str, item=None) -> AudioFormatInfo:
    """Probe a filepath or MediaItem for audio format info."""
    import os

    info = AudioFormatInfo(path_or_uri=filepath)
    ext = os.path.splitext(filepath)[1].lower().lstrip(".")

    # Stream detection
    if filepath.startswith(("http://", "https://", "rtmp://", "rtsp://")):
        info.is_stream = True
        info.container = ext or "stream"
        return info

    info.container = ext

    # From MediaItem if available
    if item:
        info.sample_rate = getattr(item, "sample_rate", 0) or 0
        info.bit_depth = getattr(item, "bit_depth", 0) or 0
        info.channels = getattr(item, "channels", 0) or 0
        info.bitrate = getattr(item, "bitrate", 0) or 0
        info.duration = getattr(item, "duration", 0.0) or 0.0

    # Try mutagen for deeper probe
    try:
        from mutagen import File as MutagenFile
        mf = MutagenFile(filepath)
        if mf and mf.info:
            if not info.sample_rate:
                info.sample_rate = getattr(mf.info, 'sample_rate', 0) or 0
            if not info.bitrate:
                info.bitrate = getattr(mf.info, 'bitrate', 0) or 0
            if not info.channels:
                info.channels = getattr(mf.info, 'channels', 0) or 0
            if not info.duration:
                info.duration = getattr(mf.info, 'length', 0.0) or 0.0
            if not info.bit_depth:
                info.bit_depth = getattr(mf.info, 'bits_per_sample', 0) or 0
    except Exception:
        pass

    # DSD detection
    if ext in ("dsf", "dff"):
        info.is_dsd = True
        info.is_dsf = ext == "dsf"
        info.is_dff = ext == "dff"
        info.dsd_rate = info.sample_rate or _default_dsd_rate(ext)
        info.dsd_speed = _dsd_speed_label(info.dsd_rate)
        info.codec = "DSD"

        # DST check for DFF
        if ext == "dff":
            try:
                with open(filepath, "rb") as f:
                    header = f.read(12)
                    if header[:4] == b"FRM8":
                        f.read(4)  # skip file size
                        f.read(4)  # skip "DSD "
                        f.read(4)  # skip "FMT "
                        f.read(4)  # skip chunk size
                        fmt = f.read(4)
                        if fmt == b"DST " or fmt == b"DST\x20":
                            info.is_dst = True
                            info.warnings.append(
                                "DST comprimido no soportado")
            except OSError:
                pass
        return info

    # PCM/lossless detection
    lossless_exts = {"flac", "alac", "wav", "aiff", "aif", "wv", "ape", "tta", "shn"}
    lossy_exts = {"mp3", "aac", "ogg", "opus", "m4a", "wma", "ac3"}

    if ext in lossless_exts:
        info.is_pcm = True
        info.is_lossless = True
        info.codec = ext.upper()
    elif ext in lossy_exts:
        info.is_pcm = True
        info.codec = ext.upper()
    else:
        info.is_pcm = True

    return info


def _default_dsd_rate(ext: str) -> int:
    return 2822400


def _dsd_speed_label(rate: int) -> str:
    if rate >= 11289600:
        return "DSD256"
    if rate >= 5644800:
        return "DSD128"
    return "DSD64"
