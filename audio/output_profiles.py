"""Audio Output Profiles — defines playback modes and their DSP constraints."""
from dataclasses import dataclass

# ── Profile application lifecycle states (Patch 2 — transactional profiles) ──
# A profile moves through these states when applied via PlayerService.apply_profile:
#   requested -> applied -> effective -> persisted
# Any failure collapses to ``failed`` (with rollback when verification failed).
PROFILE_REQUESTED = "requested"
PROFILE_APPLIED = "applied"
PROFILE_EFFECTIVE = "effective"
PROFILE_PERSISTED = "persisted"
PROFILE_FAILED = "failed"

# ── Bit-perfect verification states (Corrección 2) ──
# ``bitperfect_state`` describes whether the *effective* signal path can carry a
# bit-perfect stream after a profile is applied.
#   requested:    profile asks for bit-perfect but nothing invalidates it yet
#   probable:     no DSP invalidator found, but hw_params could not be confirmed
#   verified:     ALSA hw_params match the source format (clean path)
#   invalidated:  an active DSP (volume/EQ/ReplayGain/resampling) breaks the path
#   unsupported:  profile is not bit-perfect (bit-perfect does not apply)
#   unknown:      could not determine the state
BITPERFECT_REQUESTED = "requested"
BITPERFECT_PROBABLE = "probable"
BITPERFECT_VERIFIED = "verified"
BITPERFECT_INVALIDATED = "invalidated"
BITPERFECT_UNSUPPORTED = "unsupported"
BITPERFECT_UNKNOWN = "unknown"
BITPERFECT_STATES = (
    BITPERFECT_REQUESTED,
    BITPERFECT_PROBABLE,
    BITPERFECT_VERIFIED,
    BITPERFECT_INVALIDATED,
    BITPERFECT_UNSUPPORTED,
    BITPERFECT_UNKNOWN,
)


@dataclass(frozen=True)
class ProfileApplyResult:
    """Typed outcome of a transactional profile application (Corrección 2).

    Captures the full requested -> validated -> applied -> effective ->
    persisted lifecycle in a single immutable value so callers (bridges, QML,
    tests) never have to trust a fabricated ``ok=True``. The legacy dict
    returned by :meth:`PlayerService.apply_profile` is derived from this
    structure to preserve the existing contract.
    """

    ok: bool
    requested_profile_id: str
    previous_profile_id: str
    validated_profile_id: str | None = None
    applied_profile_id: str | None = None
    effective_profile_id: str | None = None
    persisted_profile_id: str | None = None
    requested_backend: str | None = None
    effective_backend: str | None = None
    requested_device: str | None = None
    effective_device: str | None = None
    verification_level: str = "not_verifiable"
    rollback_attempted: bool = False
    rollback_ok: bool | None = None
    code: str = ""
    message: str = ""
    warnings: tuple[str, ...] = ()
    effective_format: dict | None = None


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

    # ── MPD profiles ──
    "michi_hifi_mpd": AudioOutputProfile(
        key="michi_hifi_mpd",
        name="Hi-Fi MPD",
        description="Reproducción Hi-Fi vía MPD. ALSA hw, sin DSP. Para DAC USB.",
        allows_volume_digital=False,
        allows_eq=False,
        allows_replaygain=False,
        allows_spectrum=False,
        allows_resample=False,
        allows_convert=False,
        allows_transmit=False,
        bitperfect=True,
        preferred_backend="mpd",
    ),
    "michi_bitperfect_mpd": AudioOutputProfile(
        key="michi_bitperfect_mpd",
        name="Bit-Perfect MPD",
        description="Bit-perfect verificable vía MPD. Sin DSP, sin volumen software, sin resampling.",
        allows_volume_digital=False,
        allows_eq=False,
        allows_replaygain=False,
        allows_spectrum=False,
        allows_resample=False,
        allows_convert=False,
        allows_transmit=False,
        bitperfect=True,
        preferred_backend="mpd",
    ),
    "michi_dsd_mpd": AudioOutputProfile(
        key="michi_dsd_mpd",
        name="DSD / DoP (MPD)",
        description="DSD nativo o DoP vía MPD. Sin DSP. Requiere DAC compatible.",
        allows_volume_digital=False,
        allows_eq=False,
        allows_replaygain=False,
        allows_spectrum=False,
        allows_resample=False,
        allows_convert=False,
        allows_transmit=False,
        bitperfect=True,
        dsd_mode="native",
        preferred_backend="mpd",
    ),
    "michi_server_renderer_mpd": AudioOutputProfile(
        key="michi_server_renderer_mpd",
        name="Servidor MPD Remoto",
        description="Reproductor remoto vía MPD. Michi envía la cola a un servidor MPD externo.",
        allows_volume_digital=False,
        allows_eq=False,
        allows_replaygain=False,
        allows_spectrum=False,
        allows_resample=False,
        allows_convert=False,
        allows_transmit=False,
        bitperfect=True,
        preferred_backend="mpd",
    ),
}


def get_profile(key: str) -> AudioOutputProfile:
    return PROFILES.get(key, PROFILES["standard"])


def is_mpd_profile(key: str) -> bool:
    return get_profile(key).preferred_backend == "mpd"


def is_bitperfect_profile(key: str) -> bool:
    return get_profile(key).bitperfect


def bitperfect_breakers() -> list[str]:
    """List of features that break bit-perfect playback."""
    return ["EQ", "ReplayGain", "volume digital", "spectrum",
            "resampling", "audioconvert", "transmit"]
