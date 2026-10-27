"""AP2-F10 — explicit DSD→PCM pipeline inside the supervised GStreamer host.

This child runtime owns exactly one DSD→PCM execution. It never auto-plugs a
decoder and never falls back to PCM playback of a DSD bitstream:

    filesrc -> avdemux_dsf|avdemux_dsdiff -> dsdconvert
            -> capsfilter(audio/x-dsd, DSDU8, interleaved, reversed)
            -> avdec_dsd_lsbf|avdec_dsd_msbf -> audioconvert
            -> [audioresample] -> capsfilter(audio/x-raw, F32LE)
            -> fakesink|alsasink

The parent keeps policy, plan and output ownership. This module only executes
one immutable request and reports identity/caps evidence.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import Any


class DsdPcmHostError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class _DsdPcmRequest:
    path: str
    plan_id: str
    execution_id: str
    host_generation: int
    binding_generation: int
    stable_device_id: str
    locator: str
    source_family: str
    source_rate_hz: int
    source_bits: int
    bit_order: str
    channels: int
    decoder_factory: str
    target_rate_hz: int
    output_format: str
    quality_profile: str
    resampler_policy: tuple[tuple[str, Any], ...]
    sink_factory: str


def _str(payload: dict[str, Any], name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value.strip():
        raise DsdPcmHostError("DSD_PCM_HOST_PAYLOAD_INVALID", f"{name} required")
    return value


def _int(payload: dict[str, Any], name: str) -> int:
    value = payload.get(name)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise DsdPcmHostError("DSD_PCM_HOST_PAYLOAD_INVALID", f"{name} must be > 0")
    return value


def _bool_str(value: Any) -> str:
    return "true" if value is True else "false"


def parse_request(payload: dict[str, Any]) -> _DsdPcmRequest:
    if not isinstance(payload, dict):
        raise DsdPcmHostError("DSD_PCM_HOST_PAYLOAD_INVALID", "payload must be object")
    raw_policy = payload.get("resampler_policy") or ()
    if not isinstance(raw_policy, (list, tuple)):
        raise DsdPcmHostError(
            "DSD_PCM_HOST_PAYLOAD_INVALID", "resampler_policy must be a sequence"
        )
    policy: list[tuple[str, Any]] = []
    for item in raw_policy:
        if (
            not isinstance(item, (list, tuple))
            or len(item) != 2
            or not isinstance(item[0], str)
        ):
            raise DsdPcmHostError(
                "DSD_PCM_HOST_PAYLOAD_INVALID", "resampler_policy entry invalid"
            )
        policy.append((item[0], item[1]))
    return _DsdPcmRequest(
        path=_str(payload, "path"),
        plan_id=_str(payload, "plan_id"),
        execution_id=_str(payload, "execution_id"),
        host_generation=_int(payload, "host_generation"),
        binding_generation=_int(payload, "binding_generation"),
        stable_device_id=_str(payload, "stable_device_id"),
        locator=_str(payload, "locator"),
        source_family=_str(payload, "source_family"),
        source_rate_hz=_int(payload, "source_rate_hz"),
        source_bits=_int(payload, "source_bits"),
        bit_order=_str(payload, "bit_order"),
        channels=_int(payload, "channels"),
        decoder_factory=_str(payload, "decoder_factory"),
        target_rate_hz=_int(payload, "target_rate_hz"),
        output_format=_str(payload, "output_format"),
        quality_profile=_str(payload, "quality_profile"),
        resampler_policy=tuple(policy),
        sink_factory=_str(payload, "sink_factory"),
    )


class DsdPcmHostRuntime:
    """One explicit DSD→PCM pipeline owned by the host child."""

    _IDENTITY_FIELDS = (
        "plan_id",
        "execution_id",
        "stable_device_id",
        "device",
        "binding_generation",
        "host_generation",
    )

    def __init__(self) -> None:
        self._gst = None
        self._pipeline = None
        self._request: _DsdPcmRequest | None = None
        self._identity: dict[str, Any] | None = None
        self._last_receipt: dict[str, Any] | None = None
        self._committed = False
        self._errors: list[dict[str, str]] = []
        self._eos = False

    def _ensure_gst(self):
        if self._gst is not None:
            return self._gst
        import gi

        gi.require_version("Gst", "1.0")
        from gi.repository import Gst

        gst = Gst
        gst.init(None)
        self._gst = gst
        return gst

    def prepare(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = parse_request(payload)
        if self._identity is not None:
            raise DsdPcmHostError(
                "DSD_PCM_HOST_SUPERSESSION_UNAUTHORIZED",
                "release the active DSD→PCM execution first",
            )
        self.close()
        gst = self._ensure_gst()
        self._request = request
        pipeline = gst.Pipeline.new("michi-dsd-pcm")
        if pipeline is None:
            raise DsdPcmHostError(
                "DSD_PCM_HOST_PIPELINE_FAILED", "pipeline creation failed"
            )
        demux_name = (
            "avdemux_dsf" if request.source_family == "dsf" else "avdemux_dsdiff"
        )
        filesrc = gst.ElementFactory.make("filesrc", "src")
        demux = gst.ElementFactory.make(demux_name, "demux")
        dsdconvert = gst.ElementFactory.make("dsdconvert", "dsdconvert")
        dsd_caps = gst.ElementFactory.make("capsfilter", "dsd_caps")
        decoder = gst.ElementFactory.make(request.decoder_factory, "decoder")
        audioconvert = gst.ElementFactory.make("audioconvert", "audioconvert")
        pcm_caps = gst.ElementFactory.make("capsfilter", "pcm_caps")
        sink = gst.ElementFactory.make(request.sink_factory, "sink")
        missing = [
            name
            for name, element in (
                ("filesrc", filesrc),
                (demux_name, demux),
                ("dsdconvert", dsdconvert),
                ("capsfilter", dsd_caps),
                (request.decoder_factory, decoder),
                ("audioconvert", audioconvert),
                ("capsfilter", pcm_caps),
                (request.sink_factory, sink),
            )
            if element is None
        ]
        if missing:
            self.close()
            raise DsdPcmHostError(
                "DSD_PCM_HOST_FACTORY_UNAVAILABLE", f"missing {missing}"
            )
        filesrc.set_property("location", request.path)
        reversed_bytes = request.bit_order.upper() == "LSBF"
        dsd_caps_obj = gst.Caps.from_string(
            "audio/x-dsd,format=DSDU8,layout=interleaved,"
            f"rate={request.source_rate_hz // 8},channels={request.channels},"
            f"reversed-bytes={'true' if reversed_bytes else 'false'}"
        )
        pcm_caps_obj = gst.Caps.from_string(
            "audio/x-raw,layout=interleaved,"
            f"format={request.output_format},rate={request.target_rate_hz},"
            f"channels={request.channels}"
        )
        if dsd_caps_obj is None or pcm_caps_obj is None:
            self.close()
            raise DsdPcmHostError("DSD_PCM_HOST_CAPS_INVALID", "caps creation failed")
        dsd_caps.set_property("caps", dsd_caps_obj)
        pcm_caps.set_property("caps", pcm_caps_obj)
        if request.sink_factory == "alsasink":
            sink.set_property("device", request.locator)
        elements = [filesrc, demux, dsdconvert, dsd_caps, decoder, audioconvert]
        resampler = None
        native_rate = request.source_bits // 8
        if request.target_rate_hz != native_rate:
            resampler = gst.ElementFactory.make("audioresample", "resampler")
            if resampler is None:
                self.close()
                raise DsdPcmHostError(
                    "DSD_PCM_HOST_RESAMPLER_UNAVAILABLE", "audioresample missing"
                )
            for prop, value in request.resampler_policy:
                try:
                    resampler.set_property(prop, value)
                    actual = resampler.get_property(prop)
                except Exception as exc:  # noqa: BLE001
                    self.close()
                    raise DsdPcmHostError(
                        "DSD_PCM_HOST_RESAMPLER_CONTRACT_UNAVAILABLE",
                        f"{prop}: {exc}",
                    ) from exc
                actual_value = getattr(actual, "value_nick", actual)
                if str(actual_value) != str(value):
                    self.close()
                    raise DsdPcmHostError(
                        "DSD_PCM_HOST_RESAMPLER_CONTRACT_UNAVAILABLE",
                        f"{prop} readback {actual!r} != {value!r}",
                    )
            elements.append(resampler)
        elements.extend([pcm_caps, sink])
        for element in elements:
            if not pipeline.add(element):
                self.close()
                raise DsdPcmHostError(
                    "DSD_PCM_HOST_PIPELINE_FAILED",
                    f"cannot add {element.get_name()}",
                )
        if not filesrc.link(demux):
            self.close()
            raise DsdPcmHostError("DSD_PCM_HOST_LINK_FAILED", "filesrc -> demux")

        def _on_pad_added(_demux, pad) -> None:
            if not pad.get_name().startswith("audio_"):
                return
            sinkpad = dsdconvert.get_static_pad("sink")
            if sinkpad is None or sinkpad.is_linked():
                return
            if pad.link(sinkpad) != gst.PadLinkReturn.OK:
                self._errors.append(
                    {
                        "code": "DSD_PCM_HOST_DYNAMIC_LINK_FAILED",
                        "detail": f"{pad.get_name()} -> dsdconvert",
                    }
                )

        demux.connect("pad-added", _on_pad_added)
        chain = [dsdconvert, dsd_caps, decoder, audioconvert]
        if resampler is not None:
            chain.append(resampler)
        chain.extend([pcm_caps, sink])
        for upper, lower in zip(chain, chain[1:], strict=False):
            if not upper.link(lower):
                self.close()
                raise DsdPcmHostError(
                    "DSD_PCM_HOST_LINK_FAILED",
                    f"{upper.get_name()} -> {lower.get_name()}",
                )
        self._pipeline = pipeline
        pipeline.set_state(gst.State.PAUSED)
        ret, state, _pending = pipeline.get_state(10 * gst.SECOND)
        if ret == gst.StateChangeReturn.FAILURE or state != gst.State.PAUSED:
            detail = self._bus_error() or f"state={state.value_name}"
            self.close()
            raise DsdPcmHostError("DSD_PCM_HOST_PREROLL_FAILED", detail)
        if self._errors:
            detail = self._errors[0].get("detail", "link failure")
            self.close()
            raise DsdPcmHostError("DSD_PCM_HOST_LINK_FAILED", detail)
        self._identity = {
            "dsd_pcm": True,
            "plan_id": request.plan_id,
            "execution_id": request.execution_id,
            "host_generation": request.host_generation,
            "binding_generation": request.binding_generation,
            "stable_device_id": request.stable_device_id,
            "device": request.locator,
            "source_family": request.source_family,
            "source_rate_hz": request.source_rate_hz,
            "source_bits": request.source_bits,
            "bit_order": request.bit_order,
            "channels": request.channels,
            "decoder_factory": request.decoder_factory,
            "native_rate_hz": native_rate,
            "target_rate_hz": request.target_rate_hz,
            "output_format": request.output_format,
            "quality_profile": request.quality_profile,
            "resampler": resampler is not None,
            "sink_factory": request.sink_factory,
            "lab_sink": request.sink_factory == "fakesink",
            "decoder_caps": self._caps_text(decoder.get_static_pad("sink")),
            "output_caps": self._caps_text(sink.get_static_pad("sink")),
            "prerolled": True,
            "path": request.path,
        }
        self._last_receipt = None
        return dict(self._identity)

    def _caps_text(self, pad) -> str:
        try:
            caps = pad.get_current_caps() if pad is not None else None
            return caps.to_string() if caps is not None else ""
        except Exception:
            return ""

    def _bus_error(self) -> str:
        if self._pipeline is None:
            return ""
        bus = self._pipeline.get_bus()
        if bus is None:
            return ""
        message = bus.timed_pop_filtered(0, self._gst.MessageType.ERROR)
        if message is None:
            return ""
        err, debug = message.parse_error()
        return f"{err}: {debug}"

    def commit(self, expected: dict[str, Any]) -> dict[str, Any]:
        self._require_expected(expected)
        self._committed = True
        return {"committed": True, "identity": dict(self._identity or {})}

    def start(self, expected: dict[str, Any] | None) -> dict[str, Any]:
        self._require_expected(expected)
        if not self._committed or self._pipeline is None:
            raise DsdPcmHostError("DSD_PCM_HOST_NOT_COMMITTED", "commit before start")
        self._pipeline.set_state(self._gst.State.PLAYING)
        self._confirm(self._gst.State.PLAYING, "PLAYING")
        self._drain_bus()
        if self._errors:
            raise DsdPcmHostError("DSD_PCM_HOST_BUS_ERROR", self._errors[0]["detail"])
        return {
            "state": "PLAYING",
            "confirmed": True,
            "eos": self._eos,
            "errors": list(self._errors),
        }

    def _confirm(self, target, label: str) -> bool:
        _ret, state, _pending = self._pipeline.get_state(5 * self._gst.SECOND)
        if state != target:
            raise DsdPcmHostError(
                "DSD_PCM_HOST_STATE_NOT_CONFIRMED",
                f"requested {label}, observed {state.value_name}",
            )
        return True

    def pause(self, expected: dict[str, Any] | None) -> dict[str, Any]:
        self._require_expected(expected)
        if self._pipeline is None:
            raise DsdPcmHostError("DSD_PCM_HOST_NOT_PREPARED", "no pipeline")
        self._pipeline.set_state(self._gst.State.PAUSED)
        return {
            "state": "PAUSED",
            "confirmed": self._confirm(self._gst.State.PAUSED, "PAUSED"),
        }

    def resume(self, expected: dict[str, Any] | None) -> dict[str, Any]:
        self._require_expected(expected)
        if not self._committed or self._pipeline is None:
            raise DsdPcmHostError("DSD_PCM_HOST_NOT_COMMITTED", "commit before resume")
        self._pipeline.set_state(self._gst.State.PLAYING)
        return {
            "state": "PLAYING",
            "confirmed": self._confirm(self._gst.State.PLAYING, "PLAYING"),
        }

    def stop(self, expected: dict[str, Any]) -> dict[str, Any]:
        receipt = self._repeat_release(expected)
        if receipt is not None:
            return {
                "stopped": True,
                "already": True,
                "stale": False,
                "release": receipt,
            }
        self._require_expected(expected)
        receipt = self._release_receipt("stop")
        if not self._release_route():
            raise DsdPcmHostError(
                "DSD_PCM_HOST_RELEASE_UNCONFIRMED", "pipeline did not confirm NULL"
            )
        self._last_receipt = receipt
        return {"stopped": True, "stale": False, "release": receipt}

    def abort(self, expected: dict[str, Any]) -> dict[str, Any]:
        receipt = self._repeat_release(expected)
        if receipt is not None:
            return {
                "aborted": True,
                "already": True,
                "stale": False,
                "release": receipt,
            }
        self._require_expected(expected)
        receipt = self._release_receipt("abort")
        if not self._release_route():
            raise DsdPcmHostError(
                "DSD_PCM_HOST_RELEASE_UNCONFIRMED", "pipeline did not confirm NULL"
            )
        self._last_receipt = receipt
        return {"aborted": True, "stale": False, "release": receipt}

    def _repeat_release(self, expected: dict[str, Any]) -> dict[str, Any] | None:
        if self._identity is not None or self._pipeline is not None:
            return None
        receipt = self._last_receipt
        if not isinstance(receipt, dict) or not expected:
            return None
        for field in self._IDENTITY_FIELDS:
            if str(expected.get(field)) != str(receipt.get(field)):
                return None
        if (
            receipt.get("confirmed") is not True
            or receipt.get("terminal_state") != "RELEASED"
            or receipt.get("provenance") != "SUPERVISED_HOST"
        ):
            return None
        return dict(receipt)

    def _release_receipt(self, operation: str) -> dict[str, Any]:
        identity = self._identity or {}
        return {
            "confirmed": True,
            "operation": operation,
            "plan_id": str(identity.get("plan_id") or ""),
            "execution_id": str(identity.get("execution_id") or ""),
            "stable_device_id": str(identity.get("stable_device_id") or ""),
            "device": str(identity.get("device") or ""),
            "binding_generation": int(identity.get("binding_generation") or 0),
            "host_generation": int(identity.get("host_generation") or 0),
            "terminal_state": "RELEASED",
            "provenance": "SUPERVISED_HOST",
        }

    def _release_route(self) -> bool:
        pipeline = self._pipeline
        if pipeline is None:
            return False
        try:
            result = pipeline.set_state(self._gst.State.NULL)
            if result == self._gst.StateChangeReturn.FAILURE:
                return False
            _result, state, _pending = pipeline.get_state(self._gst.SECOND)
            if state != self._gst.State.NULL:
                return False
        except Exception:
            return False
        self._pipeline = None
        self._request = None
        self._identity = None
        self._committed = False
        self._errors = []
        self._eos = False
        return True

    def query_identity(self) -> dict[str, Any]:
        self._drain_bus()
        if self._identity is None:
            return {"dsd_pcm": False}
        payload = dict(self._identity)
        payload.update(
            {
                "dsd_pcm": True,
                "committed": self._committed,
                "eos": self._eos,
                "errors": list(self._errors),
                "state": self._state_name(),
            }
        )
        return payload

    def query_evidence(self) -> dict[str, Any]:
        return self.query_identity()

    def _drain_bus(self) -> None:
        if self._pipeline is None:
            return
        bus = self._pipeline.get_bus()
        if bus is None:
            return
        while True:
            message = bus.timed_pop_filtered(
                0, self._gst.MessageType.ERROR | self._gst.MessageType.EOS
            )
            if message is None:
                return
            if message.type == self._gst.MessageType.EOS:
                self._eos = True
            elif message.type == self._gst.MessageType.ERROR:
                err, debug = message.parse_error()
                self._errors.append(
                    {"code": "DSD_PCM_HOST_BUS_ERROR", "detail": f"{err}: {debug}"}
                )

    def _state_name(self) -> str:
        if self._pipeline is None:
            return "NULL"
        _ret, state, _pending = self._pipeline.get_state(0)
        return state.value_name

    def _require_expected(self, expected: dict[str, Any] | None) -> None:
        if not isinstance(expected, dict) or not expected:
            raise DsdPcmHostError("DSD_PCM_HOST_IDENTITY_REQUIRED", "identity required")
        identity = self._identity
        if identity is None:
            raise DsdPcmHostError("DSD_PCM_HOST_NOT_PREPARED", "no DSD→PCM pipeline")
        for field in self._IDENTITY_FIELDS:
            if str(expected.get(field)) != str(identity.get(field)):
                raise DsdPcmHostError(
                    "DSD_PCM_HOST_IDENTITY_MISMATCH", f"{field} does not match"
                )

    def close(self) -> None:
        if self._pipeline is not None:
            with contextlib.suppress(Exception):
                self._pipeline.set_state(self._gst.State.NULL)
        self._pipeline = None
        self._request = None
        self._identity = None
        self._last_receipt = None
        self._committed = False
        self._errors = []
        self._eos = False
