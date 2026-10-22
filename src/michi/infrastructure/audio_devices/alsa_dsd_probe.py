"""AP2-F08 — exact ALSA Native DSD qualification probe (worker-side).

This module performs an exact-open/readback on a selected ALSA binding:

    open -> hw_params_any -> resample(0) -> access -> channels -> format
         -> rate(exact) -> hw_params -> readback -> close

It never uses ``*_near``, never guesses a device and never produces positive
capability from a BUSY/REMOVED/TIMEOUT observation. DSD grouping is explicit:
the ALSA frame rate is ``source_bits_per_second_per_channel / width``.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import errno
import hashlib
import json
import platform

from michi.application.dsd_output_planner import AlsaDsdTuple
from michi.domain.dsd_signal import AlsaDsdGrouping

SND_PCM_STREAM_PLAYBACK = 0
SND_PCM_ACCESS_RW_INTERLEAVED = 3

#: snd_pcm_format_t ABI values from /usr/include/alsa/pcm.h.
ALSA_DSD_FORMAT_IDS: dict[AlsaDsdGrouping, int] = {
    AlsaDsdGrouping.DSD_U8: 48,
    AlsaDsdGrouping.DSD_U16_LE: 49,
    AlsaDsdGrouping.DSD_U32_LE: 50,
    AlsaDsdGrouping.DSD_U16_BE: 51,
    AlsaDsdGrouping.DSD_U32_BE: 52,
}
_ALSA_ID_TO_GROUPING = {value: key for key, value in ALSA_DSD_FORMAT_IDS.items()}
_UNKNOWN_ERRNOS = frozenset(
    {
        errno.EBUSY,
        errno.ENODEV,
        errno.EAGAIN,
        errno.EINTR,
        errno.ETIMEDOUT,
    }
)


class AlsaDsdProbeError(RuntimeError):
    """The probe could not even attempt the exact-open (library unavailable)."""


class AlsaDsdProbeEvidence:
    """Immutable result of one exact DSD candidate probe."""

    __slots__ = (
        "stable_device_id",
        "requested",
        "negotiated",
        "supported",
        "disposition",
        "errno",
        "environment_fingerprint",
        "binding_generation",
        "evidence_ref",
        "detail",
    )

    def __init__(
        self,
        *,
        stable_device_id: str,
        requested: AlsaDsdTuple,
        negotiated: AlsaDsdTuple | None,
        supported: bool | None,
        disposition: str,
        errno_code: int | None,
        environment_fingerprint: str,
        binding_generation: int,
        evidence_ref: str,
        detail: str = "",
    ) -> None:
        self.stable_device_id = stable_device_id
        self.requested = requested
        self.negotiated = negotiated
        self.supported = supported
        self.disposition = disposition
        self.errno = errno_code
        self.environment_fingerprint = environment_fingerprint
        self.binding_generation = binding_generation
        self.evidence_ref = evidence_ref
        self.detail = detail

    def as_dict(self) -> dict:
        return {
            "stable_device_id": self.stable_device_id,
            "requested": _tuple_dict(self.requested),
            "negotiated": (
                _tuple_dict(self.negotiated) if self.negotiated is not None else None
            ),
            "supported": self.supported,
            "disposition": self.disposition,
            "errno": self.errno,
            "environment_fingerprint": self.environment_fingerprint,
            "binding_generation": self.binding_generation,
            "evidence_ref": self.evidence_ref,
            "detail": self.detail,
        }


def _tuple_dict(tuple_: AlsaDsdTuple) -> dict:
    return {
        "format_name": tuple_.format_name,
        "frame_rate_hz": tuple_.frame_rate_hz,
        "channels": tuple_.channels,
        "sample_width_bits": tuple_.sample_width_bits,
        "source_bits_per_second_per_channel": (
            tuple_.source_bits_per_second_per_channel
        ),
    }


def classify_alsa_dsd_result(
    requested: AlsaDsdTuple,
    negotiated: AlsaDsdTuple | None,
    errno_code: int | None,
) -> tuple[bool | None, str]:
    """Pure classification; never turns a transient failure into UNSUPPORTED."""
    if errno_code is None or errno_code == 0:
        if negotiated is None:
            return None, "ALSA_DSD_READBACK_UNAVAILABLE"
        if negotiated == requested:
            return True, "ALSA_DSD_EXACT_NEGOTIATED"
        return False, "ALSA_DSD_READBACK_MISMATCH"
    if errno_code == errno.EINVAL:
        return False, "ALSA_DSD_EXACT_TUPLE_REJECTED"
    if errno_code in _UNKNOWN_ERRNOS:
        return None, "ALSA_DSD_PROBE_UNKNOWN"
    return None, "ALSA_DSD_PROBE_ERROR"


def environment_fingerprint() -> str:
    try:
        lib = _load_library()
        raw_version = lib.snd_asoundlib_version()
        version = raw_version.decode("ascii", "replace") if raw_version else "?"
    except Exception:  # noqa: BLE001 - fingerprint degrades explicitly
        version = "alsa-runtime-missing"
    payload = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "alsa": version,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _load_library() -> ctypes.CDLL:
    name = ctypes.util.find_library("asound") or "libasound.so.2"
    try:
        lib = ctypes.CDLL(name)
    except OSError as exc:
        raise AlsaDsdProbeError(f"libasound unavailable: {exc}") from exc
    _configure(lib)
    return lib


def _configure(lib: ctypes.CDLL) -> None:
    lib.snd_asoundlib_version.argtypes = []
    lib.snd_asoundlib_version.restype = ctypes.c_char_p
    lib.snd_strerror.argtypes = [ctypes.c_int]
    lib.snd_strerror.restype = ctypes.c_char_p
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
    lib.snd_pcm_hw_params_free.restype = None
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
    lib.snd_pcm_hw_params_get_channels.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_uint),
    ]
    lib.snd_pcm_hw_params_get_channels.restype = ctypes.c_int


def _evidence_ref(
    stable_device_id: str,
    requested: AlsaDsdTuple,
    negotiated: AlsaDsdTuple | None,
    supported: bool | None,
    disposition: str,
    errno_code: int | None,
    environment: str,
    binding_generation: int,
) -> str:
    payload = {
        "device": stable_device_id,
        "requested": _tuple_dict(requested),
        "negotiated": _tuple_dict(negotiated) if negotiated else None,
        "supported": supported,
        "disposition": disposition,
        "errno": errno_code,
        "environment": environment,
        "generation": binding_generation,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return f"alsa-dsd:{digest}"


def probe_alsa_dsd(
    stable_device_id: str,
    locator: str,
    requested: AlsaDsdTuple,
    *,
    binding_generation: int,
    environment: str | None = None,
    library: ctypes.CDLL | None = None,
) -> AlsaDsdProbeEvidence:
    """Exact-open/readback one DSD candidate. Raises only if ALSA is missing."""
    if not stable_device_id.strip() or not locator.strip():
        raise ValueError("stable_device_id and locator are required")
    if (
        not isinstance(binding_generation, int)
        or isinstance(binding_generation, bool)
        or binding_generation < 0
    ):
        raise ValueError("binding_generation must be a non-negative integer")
    if not isinstance(requested, AlsaDsdTuple):
        raise TypeError("requested must be an AlsaDsdTuple")
    env = environment or environment_fingerprint()
    lib = library if library is not None else _load_library()
    handle = ctypes.c_void_p()
    params = ctypes.c_void_p()
    negotiated: AlsaDsdTuple | None = None
    errno_code: int | None = None
    detail = ""
    pcm = None
    try:
        rc = lib.snd_pcm_open(
            ctypes.byref(handle),
            locator.encode(),
            SND_PCM_STREAM_PLAYBACK,
            0,
        )
        if rc < 0:
            errno_code = -rc
            detail = _strerror(lib, rc)
            raise _ProbeAbortError
        pcm = handle

        def _step(rc: int) -> None:
            """Check ONE ALSA result before issuing the next operation."""
            nonlocal errno_code, detail
            if rc < 0:
                errno_code = -rc
                detail = _strerror(lib, rc)
                raise _ProbeAbortError

        _step(lib.snd_pcm_hw_params_malloc(ctypes.byref(params)))
        _step(lib.snd_pcm_hw_params_any(pcm, params))
        _step(lib.snd_pcm_hw_params_set_rate_resample(pcm, params, 0))
        _step(
            lib.snd_pcm_hw_params_set_access(pcm, params, SND_PCM_ACCESS_RW_INTERLEAVED)
        )
        _step(lib.snd_pcm_hw_params_set_channels(pcm, params, requested.channels))
        _step(
            lib.snd_pcm_hw_params_set_format(
                pcm, params, ALSA_DSD_FORMAT_IDS[requested.grouping]
            )
        )
        _step(lib.snd_pcm_hw_params_set_rate(pcm, params, requested.frame_rate_hz, 0))
        _step(lib.snd_pcm_hw_params(pcm, params))
        negotiated = _readback(lib, pcm, params, requested)
    except _ProbeAbortError:
        pass
    finally:
        if params:
            lib.snd_pcm_hw_params_free(params)
        if pcm:
            lib.snd_pcm_close(pcm)

    supported, disposition = classify_alsa_dsd_result(requested, negotiated, errno_code)
    ref = _evidence_ref(
        stable_device_id,
        requested,
        negotiated,
        supported,
        disposition,
        errno_code,
        env,
        binding_generation,
    )
    return AlsaDsdProbeEvidence(
        stable_device_id=stable_device_id,
        requested=requested,
        negotiated=negotiated,
        supported=supported,
        disposition=disposition,
        errno_code=errno_code,
        environment_fingerprint=env,
        binding_generation=binding_generation,
        evidence_ref=ref,
        detail=detail,
    )


class _ProbeAbortError(Exception):
    """Internal control-flow marker; never escapes the module."""


def _readback(
    lib: ctypes.CDLL,
    pcm: ctypes.c_void_p,
    params: ctypes.c_void_p,
    requested: AlsaDsdTuple,
) -> AlsaDsdTuple | None:
    raw_format = ctypes.c_int(-1)
    raw_rate = ctypes.c_uint(0)
    raw_dir = ctypes.c_int(0)
    raw_channels = ctypes.c_uint(0)
    if lib.snd_pcm_hw_params_get_format(params, ctypes.byref(raw_format)) < 0:
        return None
    if (
        lib.snd_pcm_hw_params_get_rate(
            params, ctypes.byref(raw_rate), ctypes.byref(raw_dir)
        )
        < 0
    ):
        return None
    if lib.snd_pcm_hw_params_get_channels(params, ctypes.byref(raw_channels)) < 0:
        return None
    grouping = _ALSA_ID_TO_GROUPING.get(int(raw_format.value))
    if grouping is None:
        return None
    width = grouping.bits_per_alsa_sample
    source_bits = int(raw_rate.value) * width
    if (
        int(raw_channels.value) != requested.channels
        or source_bits != requested.source_bits_per_second_per_channel
    ):
        return None
    return AlsaDsdTuple(
        format_name=grouping.alsa_format_name,
        frame_rate_hz=int(raw_rate.value),
        channels=int(raw_channels.value),
        sample_width_bits=width,
        source_bits_per_second_per_channel=source_bits,
    )


def _strerror(lib: ctypes.CDLL, rc: int) -> str:
    try:
        raw = lib.snd_strerror(rc)
        return raw.decode("utf-8", "replace") if raw else f"error {rc}"
    except Exception:  # noqa: BLE001 - diagnostic only
        return f"error {rc}"
