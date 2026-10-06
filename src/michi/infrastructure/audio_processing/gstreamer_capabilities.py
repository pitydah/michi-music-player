"""CHILD-NATIVE processing capability probe (AP2-F05).

Runs ONLY inside the supervised GStreamer Output Host. It instantiates and
inspects real factories in the real environment and returns primitive facts;
it never decides strategy availability (the parent owns that semantic
decision) and it never crosses a Gst object over IPC.

Missing plugins are reported, never fatal: the host must stay alive to answer
the parent with typed evidence.
"""

from __future__ import annotations

from typing import Any

#: Factories the canonical F05 plan may use, with the properties this slice
#: actually needs. Factory presence alone is never enough.
REQUIRED_FACTORIES: dict[str, tuple[str, ...]] = {
    "equalizer-nbands": ("num-bands", "band0-freq", "band0-gain", "band0-bandwidth"),
    "audioiirfilter": ("a", "b"),
    "audiofirfilter": ("kernel",),
    "audioconvert": ("dithering", "noise-shaping"),
    "audioresample": ("quality",),
    "volume": ("volume",),
}


def probe_processing_capabilities() -> dict[str, Any]:
    """Primitive capability facts from the REAL environment in this process."""
    facts: dict[str, Any] = {
        "schema_version": 1,
        "gstreamer_version": None,
        "runtime_failure": None,
        "factories": {},
    }
    try:
        import gi

        gi.require_version("Gst", "1.0")
        from gi.repository import Gst

        if not Gst.is_initialized():
            Gst.init(None)
        facts["gstreamer_version"] = str(Gst.version_string())
        for factory_name, required in REQUIRED_FACTORIES.items():
            facts["factories"][factory_name] = _probe_factory(
                Gst, factory_name, required
            )
    except Exception as exc:  # noqa: BLE001 - reported, never fatal
        facts["runtime_failure"] = f"{type(exc).__name__}: {exc}"
    return facts


#: Working precision the F05 runtime requires from processing factories.
_REQUIRED_WORKING_FORMATS = ("F64LE", "F32LE")


def _caps_accept_working_precision(gst, element: Any) -> bool:
    """True when the element sink template accepts the working precision."""
    template = element.get_pad_template("sink")
    if template is None:
        return False
    caps = template.get_caps()
    if caps is None:
        return False
    for fmt in _REQUIRED_WORKING_FORMATS:
        probe = gst.Caps.from_string(f"audio/x-raw,format={fmt}")
        if caps.can_intersect(probe):
            return True
    return False


def _probe_factory(gst, factory_name: str, required: tuple[str, ...]) -> dict:
    factory = gst.ElementFactory.find(factory_name)
    if factory is None:
        return {
            "available": False,
            "properties": {},
            "missing_properties": list(required),
        }
    element = gst.ElementFactory.make(factory_name, None)
    if element is None:
        return {
            "available": False,
            "properties": {},
            "missing_properties": list(required),
            "detail": "factory found but element could not be created",
        }
    try:
        missing: list[str] = []
        present: dict[str, bool] = {}
        for prop in required:
            # Only property EXISTENCE is probed here: presence of a writable
            # property with the right type is what strategy support needs.
            spec = element.find_property(prop)
            writable = bool(spec is not None and spec.flags & spec.flags.WRITABLE)
            present[prop] = spec is not None
            if spec is None or not writable:
                missing.append(prop)
        element.set_property(
            "num-bands", 1
        ) if factory_name == "equalizer-nbands" else None
        caps_ok = _caps_accept_working_precision(gst, element)
        if not caps_ok:
            missing.append("working-precision-caps")
        return {
            "available": not missing,
            "properties": present,
            "missing_properties": missing,
            "working_precision_caps": caps_ok,
        }
    finally:
        del element
