"""AP2-F09 — exact ALSA PCM-carrier qualification for DoP.

This probes the PCM-compatible carrier (S24_3LE or S32_LE) at the DoP rate,
with exact-open/readback. It never claims that the DAC interprets DoP: the
result is DOP_CARRIER_QUALIFIED only, separate from interpretation evidence.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import errno
import hashlib
import json
import platform
from dataclasses import dataclass

from michi.domain.dop import (
    DopCarrierLayout,
    DopCarrierSupport,
    memory_contract_for,
)

SND_PCM_STREAM_PLAYBACK = 0
SND_PCM_ACCESS_RW_INTERLEAVED = 3
_ALSA_PCM_FORMAT_IDS = {"S24_3LE": 32, "S32_LE": 10}
_UNKNOWN_ERRNOS = frozenset(
    {errno.EBUSY, errno.ENODEV, errno.EAGAIN, errno.EINTR, errno.ETIMEDOUT}
)


class AlsaDopProbeError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DopCarrierProbeRequest:
    layout: DopCarrierLayout
    alsa_format: str
    rate_hz: int
    channels: int = 2

    def __post_init__(self) -> None:
        try:
            contract = memory_contract_for(self.layout)
        except Exception as exc:
            raise AlsaDopProbeError(str(exc)) from exc
        if self.alsa_format != contract.alsa_format:
            raise AlsaDopProbeError("DOP_CARRIER_FORMAT_MISMATCH")
        if self.alsa_format not in _ALSA_PCM_FORMAT_IDS:
            raise AlsaDopProbeError("DOP_CARRIER_FORMAT_UNSUPPORTED")
        if self.rate_hz <= 0 or self.channels != 2:
            raise AlsaDopProbeError("DOP_CARRIER_TUPLE_INVALID")


@dataclass(frozen=True, slots=True)
class DopCarrierProbeEvidence:
    stable_device_id: str
    binding_locator: str
    binding_generation: int
    request: DopCarrierProbeRequest
    negotiated_rate_hz: int | None
    negotiated_format: str | None
    negotiated_channels: int | None
    support: DopCarrierSupport
    disposition: str
    errno_code: int | None
    environment_fingerprint: str
    evidence_ref: str
    carrier_bytes_verified: bool = False
    dac_mode_verified: bool = False
    provenance: str = "ALSA_LAB_DIRECT"

    def as_dict(self) -> dict:
        return {
            "stable_device_id": self.stable_device_id,
            "binding_locator": self.binding_locator,
            "binding_generation": self.binding_generation,
            "layout": self.request.layout.value,
            "alsa_format": self.request.alsa_format,
            "requested_rate_hz": self.request.rate_hz,
            "negotiated_rate_hz": self.negotiated_rate_hz,
            "negotiated_format": self.negotiated_format,
            "negotiated_channels": self.negotiated_channels,
            "support": self.support.value,
            "disposition": self.disposition,
            "errno": self.errno_code,
            "environment_fingerprint": self.environment_fingerprint,
            "evidence_ref": self.evidence_ref,
            "carrier_bytes_verified": self.carrier_bytes_verified,
            "dac_mode_verified": self.dac_mode_verified,
        }


def classify_dop_probe_result(
    request: DopCarrierProbeRequest,
    negotiated_rate: int | None,
    negotiated_format: str | None,
    negotiated_channels: int | None,
    errno_code: int | None,
) -> tuple[DopCarrierSupport, str]:
    if errno_code is None or errno_code == 0:
        if (
            negotiated_rate == request.rate_hz
            and negotiated_format == request.alsa_format
            and negotiated_channels == request.channels
        ):
            return DopCarrierSupport.QUALIFIED, "DOP_CARRIER_EXACT_NEGOTIATED"
        return DopCarrierSupport.UNSUPPORTED, "DOP_CARRIER_READBACK_MISMATCH"
    if errno_code == errno.EINVAL:
        return DopCarrierSupport.UNSUPPORTED, "DOP_CARRIER_EXACT_TUPLE_REJECTED"
    if errno_code in _UNKNOWN_ERRNOS:
        return DopCarrierSupport.UNKNOWN, "DOP_CARRIER_PROBE_UNKNOWN"
    return DopCarrierSupport.INCONCLUSIVE, "DOP_CARRIER_PROBE_ERROR"


def environment_fingerprint() -> str:
    try:
        lib = _load_library()
        raw = lib.snd_asoundlib_version()
        alsa = raw.decode("ascii", "replace") if raw else "?"
    except Exception:  # noqa: BLE001 - explicit degraded fingerprint
        alsa = "alsa-runtime-missing"
    payload = {"platform": platform.platform(), "alsa": alsa}
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _load_library() -> ctypes.CDLL:
    name = ctypes.util.find_library("asound") or "libasound.so.2"
    try:
        lib = ctypes.CDLL(name)
    except OSError as exc:
        raise AlsaDopProbeError(f"libasound unavailable: {exc}") from exc
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
    lib.snd_pcm_hw_params_malloc.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
    lib.snd_pcm_hw_params_free.argtypes = [ctypes.c_void_p]
    lib.snd_pcm_hw_params_any.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    lib.snd_pcm_hw_params_set_rate_resample.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint,
    ]
    lib.snd_pcm_hw_params_set_access.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_int,
    ]
    lib.snd_pcm_hw_params_set_channels.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint,
    ]
    lib.snd_pcm_hw_params_set_format.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_int,
    ]
    lib.snd_pcm_hw_params_set_rate.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.c_int,
    ]
    lib.snd_pcm_hw_params.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    lib.snd_pcm_hw_params_get_format.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    lib.snd_pcm_hw_params_get_rate.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_uint),
        ctypes.POINTER(ctypes.c_int),
    ]
    lib.snd_pcm_hw_params_get_channels.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_uint),
    ]
    for name in (
        "snd_pcm_hw_params_malloc",
        "snd_pcm_hw_params_free",
        "snd_pcm_hw_params_any",
        "snd_pcm_hw_params_set_rate_resample",
        "snd_pcm_hw_params_set_access",
        "snd_pcm_hw_params_set_channels",
        "snd_pcm_hw_params_set_format",
        "snd_pcm_hw_params_set_rate",
        "snd_pcm_hw_params",
        "snd_pcm_hw_params_get_format",
        "snd_pcm_hw_params_get_rate",
        "snd_pcm_hw_params_get_channels",
    ):
        getattr(lib, name).restype = ctypes.c_int


def probe_dop_carrier(
    stable_device_id: str,
    binding_locator: str,
    binding_generation: int,
    request: DopCarrierProbeRequest,
    *,
    environment: str | None = None,
    library: ctypes.CDLL | None = None,
) -> DopCarrierProbeEvidence:
    if not stable_device_id.strip() or not binding_locator.strip():
        raise AlsaDopProbeError("device identity and locator are required")
    if binding_generation < 0:
        raise AlsaDopProbeError("binding generation must be non-negative")
    env = environment or environment_fingerprint()
    lib = library if library is not None else _load_library()
    handle = ctypes.c_void_p()
    params = ctypes.c_void_p()
    negotiated_rate = negotiated_format = negotiated_channels = None
    errno_code: int | None = None
    pcm = None

    class _AbortError(Exception):
        pass

    try:
        rc = lib.snd_pcm_open(
            ctypes.byref(handle), binding_locator.encode(), SND_PCM_STREAM_PLAYBACK, 0
        )
        if rc < 0:
            errno_code = -rc
            raise _AbortError
        pcm = handle
        rc = lib.snd_pcm_hw_params_malloc(ctypes.byref(params))
        if rc < 0:
            errno_code = -rc
            raise _AbortError

        def _step(rc: int) -> None:
            nonlocal errno_code
            if rc < 0:
                errno_code = -rc
                raise _AbortError

        _step(lib.snd_pcm_hw_params_any(pcm, params))
        _step(lib.snd_pcm_hw_params_set_rate_resample(pcm, params, 0))
        _step(
            lib.snd_pcm_hw_params_set_access(pcm, params, SND_PCM_ACCESS_RW_INTERLEAVED)
        )
        _step(lib.snd_pcm_hw_params_set_channels(pcm, params, request.channels))
        _step(
            lib.snd_pcm_hw_params_set_format(
                pcm, params, _ALSA_PCM_FORMAT_IDS[request.alsa_format]
            )
        )
        _step(lib.snd_pcm_hw_params_set_rate(pcm, params, request.rate_hz, 0))
        _step(lib.snd_pcm_hw_params(pcm, params))
        raw_format = ctypes.c_int(-1)
        raw_rate = ctypes.c_uint(0)
        raw_dir = ctypes.c_int(0)
        raw_channels = ctypes.c_uint(0)
        if lib.snd_pcm_hw_params_get_format(params, ctypes.byref(raw_format)) >= 0:
            negotiated_format = next(
                (
                    name
                    for name, value in _ALSA_PCM_FORMAT_IDS.items()
                    if value == raw_format.value
                ),
                None,
            )
        if (
            lib.snd_pcm_hw_params_get_rate(
                params, ctypes.byref(raw_rate), ctypes.byref(raw_dir)
            )
            >= 0
        ):
            negotiated_rate = int(raw_rate.value)
        if lib.snd_pcm_hw_params_get_channels(params, ctypes.byref(raw_channels)) >= 0:
            negotiated_channels = int(raw_channels.value)
    except _AbortError:
        pass
    finally:
        if params:
            lib.snd_pcm_hw_params_free(params)
        if pcm:
            lib.snd_pcm_close(pcm)

    support, disposition = classify_dop_probe_result(
        request, negotiated_rate, negotiated_format, negotiated_channels, errno_code
    )
    ref = (
        "alsa-dop:"
        + hashlib.sha256(
            json.dumps(
                {
                    "device": stable_device_id,
                    "locator": binding_locator,
                    "generation": binding_generation,
                    "layout": request.layout.value,
                    "format": request.alsa_format,
                    "rate": request.rate_hz,
                    "support": support.value,
                    "env": env,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
    )
    return DopCarrierProbeEvidence(
        stable_device_id=stable_device_id,
        binding_locator=binding_locator,
        binding_generation=binding_generation,
        request=request,
        negotiated_rate_hz=negotiated_rate,
        negotiated_format=negotiated_format,
        negotiated_channels=negotiated_channels,
        support=support,
        disposition=disposition,
        errno_code=errno_code,
        environment_fingerprint=env,
        evidence_ref=ref,
        provenance="ALSA_LAB_DIRECT",
    )
