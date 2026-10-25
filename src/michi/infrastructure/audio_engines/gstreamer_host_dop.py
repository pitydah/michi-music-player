"""AP2-F09 — dedicated DoP pipeline inside the supervised GStreamer host.

M13 Gate A evaluation only: the Rust ``michidop`` element is loaded from an
isolated plugin prefix. The pipeline is explicit; no playbin3, no DSD-to-PCM
conversion and no DSP:

    filesrc -> avdemux_dsf|avdemux_dsdiff -> dsdconvert
            -> capsfilter(audio/x-dsd, format=DSDU8)
            -> michidop -> capsfilter(audio/x-raw, carrier)
            -> alsasink|fakesink

The parent owns plan/binding/execution authority; this child runtime only
executes one immutable request and reports primitive pad observations.
"""

from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class DopHostError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class _DopRequest:
    path: str
    plan_id: str
    execution_id: str
    host_generation: int
    binding_generation: int
    stable_device_id: str
    locator: str
    source_family: str
    source_rate_hz: int
    carrier_rate_hz: int
    carrier_format: str
    channels: int
    reverse_payload_bits: bool
    sink_factory: str


def _str(payload: dict[str, Any], name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value.strip():
        raise DopHostError("DOP_HOST_PAYLOAD_INVALID", f"{name} required")
    return value


def _int(payload: dict[str, Any], name: str, *, zero: bool = False) -> int:
    value = payload.get(name)
    minimum = 0 if zero else 1
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise DopHostError("DOP_HOST_PAYLOAD_INVALID", f"{name} must be >= {minimum}")
    return value


def _bool(payload: dict[str, Any], name: str) -> bool:
    value = payload.get(name)
    if not isinstance(value, bool):
        raise DopHostError("DOP_HOST_PAYLOAD_INVALID", f"{name} must be boolean")
    return value


def parse_request(payload: dict[str, Any]) -> _DopRequest:
    if not isinstance(payload, dict):
        raise DopHostError("DOP_HOST_PAYLOAD_INVALID", "payload must be an object")
    request = _DopRequest(
        path=_str(payload, "path"),
        plan_id=_str(payload, "plan_id"),
        execution_id=_str(payload, "execution_id"),
        host_generation=_int(payload, "host_generation", zero=True),
        binding_generation=_int(payload, "binding_generation", zero=True),
        stable_device_id=_str(payload, "stable_device_id"),
        locator=_str(payload, "locator"),
        source_family=_str(payload, "source_family"),
        source_rate_hz=_int(payload, "source_rate_hz"),
        carrier_rate_hz=_int(payload, "carrier_rate_hz"),
        carrier_format=_str(payload, "carrier_format"),
        channels=_int(payload, "channels"),
        reverse_payload_bits=_bool(payload, "reverse_payload_bits"),
        sink_factory=_str(payload, "sink_factory"),
    )
    if request.source_family not in ("dsf", "dff"):
        raise DopHostError("DOP_HOST_FAMILY_INVALID", request.source_family)
    if request.source_rate_hz not in (352_800, 705_600, 1_411_200):
        raise DopHostError("DOP_HOST_SOURCE_RATE_INVALID", str(request.source_rate_hz))
    if request.carrier_rate_hz * 2 != request.source_rate_hz:
        raise DopHostError(
            "DOP_HOST_CARRIER_RATE_INVALID",
            "carrier rate must be GStreamer DSD-byte rate / 2",
        )
    if request.carrier_format == "S32_LE":
        request = dataclasses.replace(request, carrier_format="S32LE")
    if request.carrier_format not in ("S24_3LE", "S32LE"):
        raise DopHostError("DOP_HOST_FORMAT_INVALID", request.carrier_format)
    if request.channels != 2:
        raise DopHostError("DOP_HOST_CHANNELS_INVALID", "DoP evaluation is stereo")
    if request.sink_factory not in ("alsasink", "fakesink"):
        raise DopHostError("DOP_HOST_SINK_INVALID", request.sink_factory)
    if (
        request.sink_factory == "fakesink"
        and os.environ.get("MICHI_GST_LAB_SINK") != "fakesink"
    ):
        raise DopHostError(
            "DOP_HOST_SINK_FORBIDDEN",
            "fakesink is only allowed under the explicit lab switch",
        )
    return request


class DopHostRuntime:
    """One explicit DoP carrier pipeline owned by the child process."""

    def __init__(self) -> None:
        self._gst = None
        self._pipeline = None
        self._request: _DopRequest | None = None
        self._identity: dict[str, Any] | None = None
        self._committed = False
        self._errors: list[dict[str, str]] = []
        self._eos = False

    def _ensure_gst(self):
        if self._gst is not None:
            return self._gst
        import gi

        gi.require_version("Gst", "1.0")
        import gi.repository
        from gi.repository import Gst

        gst = Gst
        gst.init(None)
        self._gst = gst
        return gst

    def _plugin(self, gst) -> Any:
        from michi.infrastructure.audio_output.dop_plugin import resolve_dop_prefix

        try:
            root = resolve_dop_prefix()
        except RuntimeError as exc:
            raise DopHostError("DOP_RUNTIME_UNAVAILABLE", str(exc)) from exc
        factory = gst.ElementFactory.find("michidop")
        if factory is None:
            registry = gst.Registry.get()
            for candidate in (root, root / "lib/gstreamer-1.0"):
                if candidate.is_dir():
                    registry.scan_path(str(candidate))
            factory = gst.ElementFactory.find("michidop")
        if factory is None:
            raise DopHostError(
                "DOP_PLUGIN_UNAVAILABLE",
                "michidop is not registered in the host plugin registry",
            )
        from michi.infrastructure.audio_output.dop_plugin import resolve_dop_prefix

        try:
            root = resolve_dop_prefix()
        except RuntimeError as exc:
            raise DopHostError("DOP_RUNTIME_UNAVAILABLE", str(exc)) from exc
        plugin = factory.get_plugin()
        filename = plugin.get_filename() if plugin is not None else None
        if not filename:
            raise DopHostError("DOP_PLUGIN_PATH_MISSING", "plugin has no filename")
        path = Path(filename).resolve()
        if not path.is_relative_to(root):
            raise DopHostError(
                "DOP_PLUGIN_NOT_PRIVATE",
                f"michidop loaded outside the Gate A prefix: {path}",
            )
        manifest = (root / "michidop.manifest.json").resolve()
        if not manifest.is_file():
            manifest = (root / "lib/gstreamer-1.0/michidop.manifest.json").resolve()
        if not manifest.is_relative_to(root) or not manifest.is_file():
            raise DopHostError(
                "DOP_PLUGIN_MANIFEST_REQUIRED",
                f"missing Gate A manifest: {manifest}",
            )
        try:
            declared = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise DopHostError(
                "DOP_PLUGIN_MANIFEST_INVALID", f"manifest unreadable: {exc}"
            ) from exc
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if (
            not isinstance(declared, dict)
            or declared.get("name") != "michidop"
            or declared.get("revision") != "michidop-rust-0.1.0"
            or declared.get("sha256") != actual
        ):
            raise DopHostError(
                "DOP_PLUGIN_IDENTITY_MISMATCH",
                f"plugin manifest/artifact mismatch: {declared}",
            )
        return factory

    def prepare(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = parse_request(payload)
        if self._identity is not None:
            raise DopHostError(
                "DOP_HOST_SUPERSESSION_UNAUTHORIZED",
                "release the active DoP execution before preparing another",
            )
        self.close()
        gst = self._ensure_gst()
        factory = self._plugin(gst)
        self._request = request
        pipeline = gst.Pipeline.new("michi-dop")
        if pipeline is None:
            raise DopHostError("DOP_HOST_PIPELINE_FAILED", "pipeline creation failed")
        filesrc = gst.ElementFactory.make("filesrc", "src")
        demux_name = (
            "avdemux_dsf" if request.source_family == "dsf" else "avdemux_dsdiff"
        )
        demux = gst.ElementFactory.make(demux_name, "demux")
        dsdconvert = gst.ElementFactory.make("dsdconvert", "dsdconvert")
        capsfilter_in = gst.ElementFactory.make("capsfilter", "dsd_caps")
        dop = gst.ElementFactory.make("michidop", "dop")
        capsfilter_out = gst.ElementFactory.make("capsfilter", "carrier_caps")
        sink = gst.ElementFactory.make(request.sink_factory, "sink")
        missing = [
            name
            for name, element in (
                ("filesrc", filesrc),
                (demux_name, demux),
                ("dsdconvert", dsdconvert),
                ("capsfilter", capsfilter_in),
                ("michidop", dop),
                ("capsfilter", capsfilter_out),
                (request.sink_factory, sink),
            )
            if element is None
        ]
        if missing:
            self.close()
            raise DopHostError("DOP_HOST_FACTORY_UNAVAILABLE", f"missing {missing}")
        if factory is None:
            self.close()
            raise DopHostError("DOP_PLUGIN_UNAVAILABLE", "michidop")
        filesrc.set_property("location", request.path)
        dsd_caps = gst.Caps.from_string(
            "audio/x-dsd,format=DSDU8,layout=interleaved,"
            f"rate={request.source_rate_hz},channels=2,reversed-bytes=false"
        )
        carrier_caps = gst.Caps.from_string(
            "audio/x-raw,layout=interleaved,"
            f"format={request.carrier_format},rate={request.carrier_rate_hz},"
            "channels=2"
        )
        if dsd_caps is None or carrier_caps is None:
            self.close()
            raise DopHostError("DOP_HOST_CAPS_INVALID", "caps creation failed")
        capsfilter_in.set_property("caps", dsd_caps)
        capsfilter_out.set_property("caps", carrier_caps)
        dop.set_property("reverse-payload-bits", request.reverse_payload_bits)
        if request.sink_factory == "alsasink":
            sink.set_property("device", request.locator)
        elements = [
            filesrc,
            demux,
            dsdconvert,
            capsfilter_in,
            dop,
            capsfilter_out,
            sink,
        ]
        for element in elements:
            if not pipeline.add(element):
                self.close()
                raise DopHostError(
                    "DOP_HOST_PIPELINE_FAILED", f"cannot add {element.get_name()}"
                )
        if not filesrc.link(demux):
            self.close()
            raise DopHostError("DOP_HOST_LINK_FAILED", "filesrc -> demux")

        def _on_pad_added(_demux, pad) -> None:
            if not pad.get_name().startswith("audio_"):
                return
            sinkpad = dsdconvert.get_static_pad("sink")
            if sinkpad is None or pad.is_linked() or sinkpad.is_linked():
                return
            result = pad.link(sinkpad)
            if result != gst.PadLinkReturn.OK:
                self._errors.append(
                    {
                        "code": "DOP_HOST_DYNAMIC_LINK_FAILED",
                        "detail": f"{pad.get_name()} -> dsdconvert",
                    }
                )

        demux.connect("pad-added", _on_pad_added)
        for upper, lower, label in (
            (dsdconvert, capsfilter_in, "dsdconvert -> dsd_caps"),
            (capsfilter_in, dop, "dsd_caps -> michidop"),
            (dop, capsfilter_out, "michidop -> carrier_caps"),
            (capsfilter_out, sink, "carrier_caps -> sink"),
        ):
            if not upper.link(lower):
                self.close()
                raise DopHostError("DOP_HOST_LINK_FAILED", label)
        self._pipeline = pipeline
        pipeline.set_state(gst.State.PAUSED)
        ret, state, _pending = pipeline.get_state(10 * gst.SECOND)
        if ret == gst.StateChangeReturn.FAILURE or state != gst.State.PAUSED:
            detail = self._bus_error() or f"state={state.value_name}"
            self.close()
            raise DopHostError("DOP_HOST_PREROLL_FAILED", detail)
        if self._errors:
            detail = self._errors[0]["detail"]
            self.close()
            raise DopHostError("DOP_HOST_LINK_FAILED", detail)
        observations = self._observe(
            filesrc, demux, dsdconvert, capsfilter_in, dop, capsfilter_out, sink
        )
        self._identity = {
            "dop": True,
            "plan_id": request.plan_id,
            "execution_id": request.execution_id,
            "host_generation": request.host_generation,
            "binding_generation": request.binding_generation,
            "stable_device_id": request.stable_device_id,
            "device": request.locator,
            "source_family": request.source_family,
            "source_rate_hz": request.source_rate_hz,
            "carrier_rate_hz": request.carrier_rate_hz,
            "carrier_format": request.carrier_format,
            "channels": request.channels,
            "reverse_payload_bits": request.reverse_payload_bits,
            "sink_factory": request.sink_factory,
            "lab_sink": request.sink_factory == "fakesink",
            "plugin_filename": factory.get_plugin().get_filename(),
            "plugin_revision": "michidop-rust-0.1.0",
            "observations": observations,
            "prerolled": True,
            "path": request.path,
        }
        return dict(self._identity)

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

    def _pad_observation(
        self, pad, element, role: str, direction: str
    ) -> dict[str, Any]:
        current = pad.get_current_caps() if pad is not None else None
        template = pad.get_pad_template_caps() if pad is not None else None
        if current is not None and current.get_size() > 0:
            caps, state = current, "NEGOTIATED_CURRENT"
        elif template is not None and template.get_size() > 0:
            caps, state = template, "TEMPLATE_CAPABILITY"
        else:
            caps, state = None, "UNAVAILABLE"
        structure = caps.get_structure(0) if caps is not None else None
        fields: list[list[str]] = []
        if structure is not None:
            for index in range(structure.n_fields()):
                name = structure.nth_field_name(index)
                with contextlib.suppress(Exception):
                    fields.append([str(name), str(structure.get_value(name))])
        factory = element.get_factory()
        request = self._request
        return {
            "element_name": element.get_name(),
            "factory": factory.get_name() if factory is not None else "",
            "pad_name": pad.get_name() if pad is not None else "",
            "direction": direction,
            "role": role,
            "media_type": structure.get_name() if structure is not None else "",
            "fields": fields,
            "caps_state": state,
            "caps": caps.to_string() if caps is not None else "",
            "linked": bool(pad.is_linked()) if pad is not None else False,
            "selected_device": request.locator if request is not None else "",
            "execution_id": request.execution_id if request is not None else "",
            "binding_generation": request.binding_generation
            if request is not None
            else 0,
        }

    def _observe(
        self, filesrc, demux, dsdconvert, capsfilter_in, dop, capsfilter_out, sink
    ):
        observations = []
        for pad in demux.srcpads:
            observations.append(self._pad_observation(pad, demux, "demux", "src"))
            break
        for element, role in (
            (dsdconvert, "dsdconvert"),
            (capsfilter_in, "dsd_caps"),
            (dop, "michidop"),
            (capsfilter_out, "carrier_caps"),
            (sink, "sink"),
        ):
            observations.append(
                self._pad_observation(
                    element.get_static_pad("src" if element is not sink else "sink"),
                    element,
                    role,
                    "sink" if element is sink else "src",
                )
            )
        return observations

    def commit(self, expected: dict[str, Any]) -> dict[str, Any]:
        self._require_expected(expected)
        self._committed = True
        return {"committed": True, "identity": dict(self._identity or {})}

    def start(self) -> dict[str, Any]:
        if not self._committed or self._pipeline is None:
            raise DopHostError("DOP_HOST_NOT_COMMITTED", "commit before start")
        if self._errors:
            raise DopHostError("DOP_HOST_LINK_FAILED", self._errors[0]["detail"])
        self._pipeline.set_state(self._gst.State.PLAYING)
        confirmed = self._confirm(self._gst.State.PLAYING, "PLAYING")
        self._drain_bus()
        if self._errors:
            raise DopHostError("DOP_HOST_BUS_ERROR", self._errors[0]["detail"])
        return {
            "state": "PLAYING",
            "confirmed": confirmed,
            "eos": self._eos,
            "errors": list(self._errors),
        }

    def _confirm(self, target, label: str) -> bool:
        _ret, state, _pending = self._pipeline.get_state(5 * self._gst.SECOND)
        if state != target:
            raise DopHostError(
                "DOP_HOST_STATE_NOT_CONFIRMED",
                f"requested {label}, observed {state.value_name}",
            )
        return True

    def pause(self) -> dict[str, Any]:
        if self._pipeline is None:
            raise DopHostError("DOP_HOST_NOT_PREPARED", "no DoP pipeline")
        self._pipeline.set_state(self._gst.State.PAUSED)
        return {
            "state": "PAUSED",
            "confirmed": self._confirm(self._gst.State.PAUSED, "PAUSED"),
        }

    def resume(self) -> dict[str, Any]:
        if not self._committed or self._pipeline is None:
            raise DopHostError("DOP_HOST_NOT_COMMITTED", "commit before resume")
        self._pipeline.set_state(self._gst.State.PLAYING)
        return {
            "state": "PLAYING",
            "confirmed": self._confirm(self._gst.State.PLAYING, "PLAYING"),
        }

    def stop(self, expected: dict[str, Any]) -> dict[str, Any]:
        self._require_expected(expected)
        self.close()
        return {"stopped": True, "stale": False}

    def abort(self, expected: dict[str, Any]) -> dict[str, Any]:
        self._require_expected(expected)
        self.close()
        return {"aborted": True, "stale": False}

    def query_identity(self) -> dict[str, Any]:
        self._drain_bus()
        if self._identity is None:
            return {"dop": False}
        payload = dict(self._identity)
        payload.update(
            {
                "dop": True,
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
                    {"code": "DOP_HOST_BUS_ERROR", "detail": f"{err}: {debug}"}
                )

    def _state_name(self) -> str:
        if self._pipeline is None:
            return "NULL"
        _ret, state, _pending = self._pipeline.get_state(0)
        return state.value_name

    def _require_expected(self, expected: dict[str, Any] | None) -> None:
        if not isinstance(expected, dict) or not expected:
            raise DopHostError("DOP_HOST_IDENTITY_REQUIRED", "identity required")
        identity = self._identity
        if identity is None:
            raise DopHostError("DOP_HOST_NOT_PREPARED", "no DoP pipeline")
        for field in (
            "plan_id",
            "execution_id",
            "stable_device_id",
            "device",
            "binding_generation",
            "host_generation",
        ):
            value = expected.get(field)
            if value is None or value == "" or str(value) != str(identity.get(field)):
                raise DopHostError(
                    "DOP_HOST_IDENTITY_MISMATCH", f"{field} does not match"
                )

    def close(self) -> None:
        if self._pipeline is not None:
            with contextlib.suppress(Exception):
                self._pipeline.set_state(self._gst.State.NULL)
        self._pipeline = None
        self._request = None
        self._identity = None
        self._committed = False
        self._errors = []
        self._eos = False
