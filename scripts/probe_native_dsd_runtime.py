#!/usr/bin/env python
"""AP2-F08 isolated Native DSD runtime branch probe.

Runs in a FRESH process (the caller is the supervisor) and observes real
GStreamer caps. It is a qualification probe, not a second productive engine:
no application authority, no playback state and no Signal Truth are touched.

Default sink is ``fakesink`` (no hardware). ``--sink alsasink`` performs a
PAUSED negotiation/readback on the exact device and then goes to NULL; it
does not PLAY. The JSON output records the observed caps and factories so a
caller can classify the branch with ``dsd_runtime_inspector``.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
import time
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Isolated Native DSD branch probe")
    parser.add_argument("--path", required=True)
    parser.add_argument("--sink", choices=("fakesink", "alsasink"), default="fakesink")
    parser.add_argument("--device", default="")
    parser.add_argument("--convert", action="store_true")
    parser.add_argument("--format", default="DSDU32BE")
    parser.add_argument("--rate", type=int, default=352_800)
    parser.add_argument("--channels", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--execution-id", default="probe:1")
    parser.add_argument("--binding-generation", type=int, default=1)
    parser.add_argument("--json-out", default="")
    args = parser.parse_args(argv)
    if args.sink == "alsasink" and not args.device.strip():
        parser.error("--sink alsasink requires --device")

    result: dict = {
        "schema_version": 1,
        "probe": "native_dsd_runtime",
        "path": str(Path(args.path)),
        "sink": args.sink,
        "device": args.device,
        "execution_id": args.execution_id,
        "binding_generation": args.binding_generation,
        "observed_caps": [],
        "factories": [],
        "errors": [],
        "eos": False,
        "prerolled": False,
        "duration_ms": 0,
    }
    started = time.monotonic()
    gst = None
    pipeline = None
    try:
        import gi

        gi.require_version("Gst", "1.0")
        from gi.repository import Gst

        gst = Gst
        Gst.init(None)
        pipeline = Gst.Pipeline.new("michi-native-dsd-probe")
        filesrc = Gst.ElementFactory.make("filesrc", "src")
        demux = Gst.ElementFactory.make("avdemux_dsf", "demux")
        if pipeline is None or filesrc is None or demux is None:
            raise RuntimeError("filesrc/avdemux_dsf unavailable")
        filesrc.set_property("location", str(Path(args.path).resolve()))
        elements = [filesrc, demux]

        dsdconvert = None
        if args.convert:
            dsdconvert = Gst.ElementFactory.make("dsdconvert", "dsdconvert")
            if dsdconvert is None:
                raise RuntimeError("dsdconvert unavailable")
            elements.append(dsdconvert)

        capsfilter = None
        sink = None
        if args.sink == "alsasink":
            capsfilter = Gst.ElementFactory.make("capsfilter", "dsd_caps")
            sink = Gst.ElementFactory.make("alsasink", "alsa")
            if capsfilter is None or sink is None:
                raise RuntimeError("capsfilter/alsasink unavailable")
            caps = Gst.Caps.from_string(
                "audio/x-dsd,"
                f"format={args.format},"
                f"rate={args.rate},"
                f"channels={args.channels},"
                "layout=interleaved,reversed-bytes=false"
            )
            if caps is None or caps.get_size() == 0:
                raise RuntimeError("invalid DSD caps")
            capsfilter.set_property("caps", caps)
            sink.set_property("device", args.device)
            elements.extend([capsfilter, sink])
        else:
            sink = Gst.ElementFactory.make("fakesink", "fake")
            if sink is None:
                raise RuntimeError("fakesink unavailable")
            sink.set_property("sync", False)
            elements.append(sink)

        for element in elements:
            if not pipeline.add(element):
                raise RuntimeError(f"cannot add {element.get_name()}")
        result["factories"] = [element.get_factory().get_name() for element in elements]

        # Link the static head; demux src pads are dynamic.
        if not filesrc.link(demux):
            raise RuntimeError("filesrc -> avdemux_dsf link failed")
        static_chain = elements[2:]
        for upstream, downstream in zip(static_chain, static_chain[1:], strict=False):
            if not upstream.link(downstream):
                raise RuntimeError(
                    f"{upstream.get_name()} -> {downstream.get_name()} link failed"
                )

        seen_caps: set[tuple] = set()

        def _record(pad: object, element: object, role: str, direction: str) -> None:
            if len(result["observed_caps"]) >= 64:
                return
            current = pad.get_current_caps()
            template = pad.get_pad_template_caps()
            if current is not None and current.get_size() > 0:
                caps = current
                caps_state = "NEGOTIATED_CURRENT"
            elif template is not None and template.get_size() > 0:
                caps = template
                caps_state = "TEMPLATE_CAPABILITY"
            else:
                caps = None
                caps_state = "UNAVAILABLE"
            structure = caps.get_structure(0) if caps is not None else None
            media_type = structure.get_name() if structure is not None else ""
            fields: list[list[str]] = []
            if structure is not None:
                for index in range(structure.n_fields()):
                    name = structure.nth_field_name(index)
                    try:
                        value = structure.get_value(name)
                    except Exception:  # noqa: BLE001 - e.g. GstBitmask is opaque
                        continue
                    fields.append([str(name), str(value)])
            factory = element.get_factory()
            observation = {
                "element_name": element.get_name(),
                "factory": factory.get_name() if factory is not None else "",
                "pad_name": pad.get_name(),
                "direction": direction,
                "role": role,
                "media_type": media_type,
                "fields": fields,
                "caps_state": caps_state,
                "caps": caps.to_string() if caps is not None else "",
                "linked": bool(pad.is_linked()),
                "selected_device": args.device,
                "execution_id": args.execution_id,
                "binding_generation": args.binding_generation,
            }
            key = (
                observation["element_name"],
                observation["pad_name"],
                role,
                direction,
                media_type,
                tuple((str(k), str(v)) for k, v in fields),
                caps_state,
                observation["linked"],
            )
            if key in seen_caps:
                return
            seen_caps.add(key)
            result["observed_caps"].append(observation)

        def _probe_for(element: object, role: str, direction: str):
            def _probe(pad: object, _info: object):
                _record(pad, element, role, direction)
                return Gst.PadProbeReturn.OK

            return _probe

        def _on_pad_added(demux_element: object, pad: object) -> None:
            pad.add_probe(
                Gst.PadProbeType.BUFFER,
                _probe_for(demux_element, "source", "src"),
            )
            target = static_chain[0] if static_chain else None
            if target is None:
                return
            sinkpad = target.get_static_pad("sink")
            if sinkpad is not None and not pad.is_linked():
                pad.link(sinkpad)

        demux.connect("pad-added", _on_pad_added)
        for element, role, direction in (
            (dsdconvert, "dsdconvert", "src"),
            (capsfilter, "capsfilter", "src"),
            (sink, "sink", "sink"),
        ):
            if element is None:
                continue
            pad = element.get_static_pad(direction)
            if pad is not None:
                pad.add_probe(
                    Gst.PadProbeType.BUFFER,
                    _probe_for(element, role, direction),
                )

        state = Gst.State.PAUSED if args.sink == "alsasink" else Gst.State.PLAYING
        pipeline.set_state(state)
        deadline = time.monotonic() + float(args.timeout)
        bus = pipeline.get_bus()
        while time.monotonic() < deadline:
            message = bus.timed_pop_filtered(
                50 * Gst.MSECOND,
                Gst.MessageType.ERROR
                | Gst.MessageType.EOS
                | Gst.MessageType.ASYNC_DONE,
            )
            if message is None:
                continue
            if message.type == Gst.MessageType.ERROR:
                err, debug = message.parse_error()
                result["errors"].append({"error": str(err), "debug": str(debug)})
                break
            if message.type == Gst.MessageType.EOS:
                result["eos"] = True
                break
            if message.type == Gst.MessageType.ASYNC_DONE:
                result["prerolled"] = True
                if args.sink == "alsasink":
                    break
        if args.sink == "alsasink" and not result["prerolled"] and not result["errors"]:
            result["errors"].append(
                {"error": "probe timeout before preroll", "debug": ""}
            )
    except Exception as exc:  # noqa: BLE001 - probe reports, never crashes silently
        result["errors"].append({"error": f"{type(exc).__name__}: {exc}", "debug": ""})
    finally:
        if pipeline is not None and gst is not None:
            with contextlib.suppress(Exception):
                pipeline.set_state(gst.State.NULL)

    result["duration_ms"] = int((time.monotonic() - started) * 1000)
    encoded = json.dumps(result, indent=1, ensure_ascii=False)
    if args.json_out:
        Path(args.json_out).write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
