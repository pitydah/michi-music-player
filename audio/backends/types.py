from dataclasses import dataclass, field
from typing import Literal


PlaybackStateName = Literal["stopped", "playing", "paused", "buffering", "error"]


@dataclass
class BackendCapabilities:
    backend_id: str
    display_name: str
    supports_eq: bool = False
    supports_replaygain: bool = False
    supports_spectrum: bool = False
    supports_radio: bool = False
    supports_streams: bool = False
    supports_bitperfect: bool = False
    supports_dsd: bool = False
    supports_dop: bool = False
    supports_remote: bool = False
    supports_server_mode: bool = False
    supports_digital_volume: bool = True


@dataclass
class PlaybackSnapshot:
    backend_id: str
    state: PlaybackStateName
    current_path: str = ""
    current_uri: str = ""
    title: str = ""
    artist: str = ""
    album: str = ""
    position_seconds: float = 0.0
    duration_seconds: float = 0.0
    volume: int = 70
    queue_index: int = -1
    queue_length: int = 0
    error: str = ""


@dataclass
class AudioDiagnostics:
    backend_id: str
    profile: str
    device_name: str = ""
    device_string: str = ""
    input_codec: str = ""
    input_sample_rate: int = 0
    input_bit_depth: int = 0
    input_channels: int = 0
    output_sample_rate: int = 0
    output_format: str = ""
    output_channels: int = 0
    bitperfect_requested: bool = False
    bitperfect_possible: bool = False
    bitperfect_verified: bool = False
    bitperfect_status: str = "unknown"
    dsp_active: bool = False
    eq_active: bool = False
    replaygain_active: bool = False
    spectrum_active: bool = False
    resampling_active: bool = False
    digital_volume_active: bool = False
    warnings: list[str] = field(default_factory=list)
