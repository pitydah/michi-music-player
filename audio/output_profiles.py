"""Audio Output Profiles — defines playback modes and their DSP constraints."""
from dataclasses import dataclass


@dataclass
class AudioOutputProfile:
    key: str
    name: str
    description: str
    allows_volume_digital: bool = True
    allows_eq: bool = True
    allows_replaygain: bool = True
    allows_spectrum: bool = True
    allows_resample: bool = True
    allows_convert: bool = True
    allows_transmit: bool = True
    bitperfect: bool = False
    dsd_mode: str = ""  # "", "pcm", "dop", "native"
    preferred_backend: str = "auto"
    preferred_device: str = ""


PROFILES: dict[str, AudioOutputProfile] = {
    "standard": AudioOutputProfile(
        key="standard",
        name="Estándar",
        description="Máxima compatibilidad. PipeWire/PulseAudio, EQ, ReplayGain y spectrum activos.",
        preferred_backend="auto",
    ),
    "hifi_pcm": AudioOutputProfile(
        key="hifi_pcm",
        name="Hi-Fi PCM",
        description="Conserva el sample rate original. EQ y ReplayGain opcionales. Para DAC o buena salida.",
        preferred_backend="auto",
    ),
    "bitperfect_pcm": AudioOutputProfile(
        key="bitperfect_pcm",
        name="Bit-Perfect PCM",
        description="Salida directa sin procesamiento. Requiere ALSA hw. Sin EQ, volumen digital ni ReplayGain.",
        allows_volume_digital=False,
        allows_eq=False,
        allows_replaygain=False,
        allows_spectrum=False,
        allows_resample=False,
        allows_convert=False,
        allows_transmit=False,
        bitperfect=True,
        preferred_backend="alsa",
    ),
    "dsd_to_pcm": AudioOutputProfile(
        key="dsd_to_pcm",
        name="DSD → PCM",
        description="Convierte DSD a PCM Hi-Res. Sin EQ ni ReplayGain por defecto. DAC recomendado.",
        allows_eq=False,
        allows_replaygain=False,
        dsd_mode="pcm",
        preferred_backend="auto",
    ),
    "dop_experimental": AudioOutputProfile(
        key="dop_experimental",
        name="DoP (Experimental)",
        description="DSD over PCM. Solo ALSA hw compatible. Sin DSP. Experimental.",
        allows_volume_digital=False,
        allows_eq=False,
        allows_replaygain=False,
        allows_spectrum=False,
        allows_resample=False,
        allows_convert=False,
        allows_transmit=False,
        dsd_mode="dop",
        preferred_backend="alsa",
    ),
    "streaming": AudioOutputProfile(
        key="streaming",
        name="Streaming",
        description="Radio y streams HTTP. Sin gapless. Con buffering y reconnect.",
        allows_eq=False,
        preferred_backend="auto",
    ),
    "pure_audio": AudioOutputProfile(
        key="pure_audio",
        name="Pure Audio",
        description="Escucha critica sin interrupciones. Sin DSP, sin cola visible, sin pausas entre tracks del mismo album.",
        allows_volume_digital=False,
        allows_eq=False,
        allows_replaygain=False,
        allows_spectrum=False,
        allows_resample=False,
        allows_convert=False,
        allows_transmit=False,
        bitperfect=True,
        preferred_backend="alsa",
    ),
    "studio_monitor": AudioOutputProfile(
        key="studio_monitor",
        name="Studio Monitor",
        description="Salida plana para monitores de estudio. EQ forzado a bypass, sin ReplayGain, sin spectrum.",
        allows_eq=False,
        allows_replaygain=False,
        allows_spectrum=False,
        preferred_backend="auto",
    ),
    "multiroom": AudioOutputProfile(
        key="multiroom",
        name="Multiroom / Snapcast",
        description="Audio transmitido a zonas múltiples. Resample a 48kHz stereo para compatibilidad con Snapcast/HA.",
        allows_eq=True,
        allows_replaygain=True,
        allows_spectrum=False,
        allows_resample=True,
        allows_convert=True,
        allows_transmit=True,
        bitperfect=False,
        preferred_backend="auto",
    ),
}


def get_profile(key: str) -> AudioOutputProfile:
    return PROFILES.get(key, PROFILES["standard"])


def bitperfect_breakers() -> list[str]:
    """List of features that break bit-perfect playback."""
    return ["EQ", "ReplayGain", "volume digital", "spectrum",
            "resampling", "audioconvert", "transmit"]
