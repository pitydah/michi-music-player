"""DAC-V35-020 — libasound.so.2 vía ctypes (spec §13).

Secuencia exacta del worker (nunca set_rate_near como prueba de soporte,
nunca sustitución *_near):

    open -> hw_params_any -> set_rate_resample(0) -> set_access ->
    set_channels(exacto) -> set_format(exacto) -> set_rate(exacto) ->
    hw_params -> readback -> get_sbits -> close (finally)

Los samples nunca viajan por JSON: solo control-plane de baja frecuencia.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import logging

logger = logging.getLogger(__name__)

SND_PCM_STREAM_PLAYBACK = 0
SND_PCM_ACCESS_RW_INTERLEAVED = 3

# snd_pcm_format_t (valores ABI estables de asoundlib.h)
FORMAT_IDS: dict[str, int] = {
    "U8": 1,
    "S16_LE": 2,
    "S16_BE": 3,
    "S24_LE": 6,
    "S24_BE": 7,
    "S32_LE": 10,
    "S32_BE": 11,
    "FLOAT_LE": 14,
    "S24_3LE": 32,
    "S24_3BE": 33,
}

_LIBRARY: ctypes.CDLL | None = None


class AlsaRuntimeMissingError(RuntimeError):
    """libasound.so.2 no disponible (alsa_runtime_missing)."""


class AlsaProbeError(RuntimeError):
    """Error de un paso concreto del probe (layer-aware)."""

    def __init__(self, step: str, errno_code: int, message: str) -> None:
        super().__init__(f"{step}: {message} (errno {errno_code})")
        self.step = step
        self.errno_code = errno_code
        self.message = message


class NegotiatedPcm:
    __slots__ = (
        "access",
        "channels",
        "format_id",
        "rate_hz",
        "significant_bits",
    )

    def __init__(
        self,
        *,
        access: int,
        channels: int,
        format_id: int,
        rate_hz: int,
        significant_bits: int,
    ) -> None:
        self.access = access
        self.channels = channels
        self.format_id = format_id
        self.rate_hz = rate_hz
        self.significant_bits = significant_bits


def _load_library() -> ctypes.CDLL:
    global _LIBRARY
    if _LIBRARY is not None:
        return _LIBRARY
    name = ctypes.util.find_library("asound") or "libasound.so.2"
    try:
        lib = ctypes.CDLL(name)
    except OSError as exc:  # pragma: no cover - depende del sistema
        raise AlsaRuntimeMissingError(f"libasound no disponible: {exc}") from exc
    _configure(lib)
    _LIBRARY = lib
    return lib


def _configure(lib: ctypes.CDLL) -> None:
    lib.snd_pcm_open.argtypes = [
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_int,
    ]
    lib.snd_pcm_open.restype = ctypes.c_int
    lib.snd_pcm_close.argtypes = [ctypes.c_void_p]
    lib.snd_pcm_close.restype = ctypes.c_int
    lib.snd_pcm_hw_params_malloc.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
    lib.snd_pcm_hw_params_malloc.restype = ctypes.c_int
    lib.snd_pcm_hw_params_free.argtypes = [ctypes.c_void_p]
    lib.snd_pcm_hw_params_any.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    lib.snd_pcm_hw_params_any.restype = ctypes.c_int
    lib.snd_pcm_hw_params_set_rate_resample.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint,
    ]
    lib.snd_pcm_hw_params_set_rate_resample.restype = ctypes.c_int
    lib.snd_pcm_hw_params_set_access.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_int,
    ]
    lib.snd_pcm_hw_params_set_access.restype = ctypes.c_int
    lib.snd_pcm_hw_params_set_channels.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint,
    ]
    lib.snd_pcm_hw_params_set_channels.restype = ctypes.c_int
    lib.snd_pcm_hw_params_set_format.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_int,
    ]
    lib.snd_pcm_hw_params_set_format.restype = ctypes.c_int
    lib.snd_pcm_hw_params_set_rate.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.c_int,
    ]
    lib.snd_pcm_hw_params_set_rate.restype = ctypes.c_int
    lib.snd_pcm_hw_params.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    lib.snd_pcm_hw_params.restype = ctypes.c_int
    lib.snd_pcm_hw_params_get_access.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    lib.snd_pcm_hw_params_get_access.restype = ctypes.c_int
    lib.snd_pcm_hw_params_get_channels.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_uint),
    ]
    lib.snd_pcm_hw_params_get_channels.restype = ctypes.c_int
    lib.snd_pcm_hw_params_get_format.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    lib.snd_pcm_hw_params_get_format.restype = ctypes.c_int
    lib.snd_pcm_hw_params_get_rate.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_uint),
        ctypes.POINTER(ctypes.c_int),
    ]
    lib.snd_pcm_hw_params_get_rate.restype = ctypes.c_int
    lib.snd_pcm_hw_params_get_sbits.argtypes = [ctypes.c_void_p]
    lib.snd_pcm_hw_params_get_sbits.restype = ctypes.c_int
    lib.snd_strerror.argtypes = [ctypes.c_int]
    lib.snd_strerror.restype = ctypes.c_char_p
    lib.snd_asoundlib_version.argtypes = []
    lib.snd_asoundlib_version.restype = ctypes.c_char_p


def library_version() -> str:
    """Versión de libasound (diagnóstico)."""
    lib = _load_library()
    raw = lib.snd_asoundlib_version()
    return raw.decode("utf-8", "replace") if raw else "unknown"


def _raise_if(lib: ctypes.CDLL, err: int, step: str) -> None:
    if err >= 0:
        return
    code = -err
    try:
        message = lib.snd_strerror(err).decode("utf-8", "replace")
    except Exception:  # pragma: no cover - snd_strerror nunca debería fallar
        message = f"alsa error {code}"
    raise AlsaProbeError(step, code, message)


def probe_exact(
    locator: str,
    *,
    rate_hz: int,
    transport_format: str,
    channels: int,
) -> NegotiatedPcm:
    """Abre/negocia EXACTAMENTE el tuple pedido y lee el resultado.

    Raises AlsaProbeError con el step que falló (clasificación
    layer-aware) o AlsaRuntimeMissingError si no hay libasound.
    """
    if not locator.startswith("hw:"):
        raise AlsaProbeError(
            "validate",
            22,
            "el locator debe ser exacto (hw:CARD=...,DEV=...)",
        )
    lib = _load_library()
    pcm = ctypes.c_void_p()
    params = ctypes.c_void_p()
    _raise_if(
        lib,
        lib.snd_pcm_open(
            ctypes.byref(pcm), locator.encode("utf-8"), SND_PCM_STREAM_PLAYBACK, 0
        ),
        "open",
    )
    try:
        _raise_if(
            lib, lib.snd_pcm_hw_params_malloc(ctypes.byref(params)), "hw_params_malloc"
        )
        try:
            _raise_if(lib, lib.snd_pcm_hw_params_any(pcm, params), "hw_params_any")
            _raise_if(
                lib,
                lib.snd_pcm_hw_params_set_rate_resample(pcm, params, 0),
                "set_rate_resample",
            )
            _raise_if(
                lib,
                lib.snd_pcm_hw_params_set_access(
                    pcm, params, SND_PCM_ACCESS_RW_INTERLEAVED
                ),
                "set_access",
            )
            _raise_if(
                lib,
                lib.snd_pcm_hw_params_set_channels(pcm, params, channels),
                "set_channels",
            )
            format_id = FORMAT_IDS.get(transport_format)
            if format_id is None:
                raise AlsaProbeError(
                    "set_format",
                    22,
                    f"formato de transporte desconocido: {transport_format}",
                )
            _raise_if(
                lib,
                lib.snd_pcm_hw_params_set_format(pcm, params, format_id),
                "set_format",
            )
            _raise_if(
                lib,
                lib.snd_pcm_hw_params_set_rate(pcm, params, rate_hz, 0),
                "set_rate",
            )
            _raise_if(lib, lib.snd_pcm_hw_params(pcm, params), "hw_params")

            access = ctypes.c_int(0)
            got_channels = ctypes.c_uint(0)
            got_format = ctypes.c_int(0)
            got_rate = ctypes.c_uint(0)
            direction = ctypes.c_int(0)
            lib.snd_pcm_hw_params_get_access(params, ctypes.byref(access))
            lib.snd_pcm_hw_params_get_channels(params, ctypes.byref(got_channels))
            lib.snd_pcm_hw_params_get_format(params, ctypes.byref(got_format))
            lib.snd_pcm_hw_params_get_rate(
                params, ctypes.byref(got_rate), ctypes.byref(direction)
            )
            significant_bits = int(lib.snd_pcm_hw_params_get_sbits(params))
            return NegotiatedPcm(
                access=access.value,
                channels=int(got_channels.value),
                format_id=int(got_format.value),
                rate_hz=int(got_rate.value),
                significant_bits=significant_bits,
            )
        finally:
            lib.snd_pcm_hw_params_free(params)
    finally:
        lib.snd_pcm_close(pcm)
