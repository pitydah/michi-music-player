# ruff: noqa: N802 - Qt Property getters intentionally use camelCase names.
"""F11 Signal Truth presentation projection.

This bridge is deliberately read-only. It joins the canonical
``SignalTruthRecorder`` snapshot, the committed processing truth and the
output bridge projection into the five disclosure stages. It never classifies
audio, never parses labels to infer HD/bit-perfect and never creates a second
recorder.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from michi.domain.signal_truth import (
    SignalTruthRecorder,
    signal_truth_snapshot_diagnostics,
)

logger = logging.getLogger(__name__)

_VERDICT_HEADLINES = {
    "direct": "Direct path",
    "direct_container_adapted": "Direct · container adapted",
    "resampled": "Resampled",
    "remixed": "Channel remix",
    "dsp": "Processing active",
    "contradicted": "Output mismatch",
    "unknown": "Not verified",
}

_CONFIG_ACTIONS = {
    "NONE",
    "OPEN_ENGINE",
    "OPEN_PROCESSING",
    "OPEN_OUTPUT",
    "OPEN_DEVICE_SETUP",
}

_LOSSY_TOKENS = ("mp3", "aac", "vorbis", "opus", "wma", "lossy")
_DSD_TOKENS = ("dsd", "dsf", "dff")


def _quality_class(source: dict[str, Any] | None) -> str:
    """Classify the nominal source quality from structured facts only."""
    if not source:
        return "unknown"
    codec = str(source.get("codec") or "").casefold()
    container = str(source.get("container") or "").casefold()
    nominal = source.get("nominal_pcm") or {}
    transport = str(nominal.get("format") or "").casefold()
    token = f"{codec} {container} {transport}"
    if any(item in token for item in _DSD_TOKENS):
        return "dsd"
    if any(item in token for item in _LOSSY_TOKENS):
        return "lossy"
    if nominal:
        bits = int(nominal.get("significant_bits") or 0)
        rate = int(nominal.get("rate_hz") or 0)
        if bits > 16 or rate > 48_000:
            return "pcm_hires"
        return "pcm_standard"
    return "unknown"


def _quality_format_label(
    source: dict[str, Any] | None, path: str, quality_class: str
) -> str:
    if quality_class == "dsd":
        token = " ".join(
            str((source or {}).get(key) or "").casefold()
            for key in ("codec", "container")
        )
        for family in ("dsd256", "dsd128", "dsd64"):
            if family in token:
                return family.upper()
        return "DSD"
    source = source or {}
    codec = str(source.get("codec") or "").strip()
    container = str(source.get("container") or "").strip()
    if container and (not codec or codec.casefold().startswith("pcm_")):
        return container.upper()
    if codec:
        return codec.upper()
    if container:
        return container.upper()
    suffix = path.rsplit(".", 1)[-1].strip() if "." in path else ""
    return suffix.upper() if suffix else "NO TRACK"


def _quality_rate_depth_label(source: dict[str, Any] | None, quality_class: str) -> str:
    if not source:
        return "format unknown"
    nominal = source.get("nominal_pcm") or {}
    if quality_class == "dsd" and not nominal:
        return "1-bit"
    rate = int(nominal.get("rate_hz") or 0)
    bits = int(nominal.get("significant_bits") or 0)
    parts: list[str] = []
    if bits > 0:
        parts.append(f"{bits}-bit")
    if rate > 0:
        parts.append(f"{rate / 1000:g} kHz")
    if parts:
        return " · ".join(parts)
    if quality_class == "lossy":
        return "lossy"
    return "format unknown"


def _path_proof_state(
    *,
    temporal_status: str,
    verdict_state: str,
    tone: str,
    proof_parts: list[str],
    processing_verified: bool,
) -> str:
    if temporal_status == "NONE":
        return "no_path"
    if temporal_status == "PENDING":
        return "pending"
    if temporal_status == "HISTORICAL":
        return "historical"
    if verdict_state == "contradicted" or tone == "error":
        return "contradicted"
    expected = {"Source", "host", "transport", "device"}
    # Having four IDs/formats is not proof of a verified path if the canonical
    # verdict remains unknown. This prevents "Verified path / Not verified".
    verified_verdict = verdict_state in {
        "direct",
        "direct_container_adapted",
        "resampled",
        "remixed",
        "dsp",
    }
    if verified_verdict and expected.issubset(set(proof_parts)):
        if not processing_verified:
            return "partially_verified"
        return "verified"
    if proof_parts:
        return "partially_verified"
    return "no_path"


def _path_proof_label(state: str) -> str:
    return {
        "no_path": "No verified path",
        "pending": "Preparing path",
        "historical": "Last playback",
        "verified": "Verified path",
        "partially_verified": "Partially verified",
        "contradicted": "Output mismatch",
    }.get(state, "No verified path")


def _pcm_label(item: dict[str, Any] | None) -> str:
    if not item:
        return "Not observed"
    rate = item.get("rate_hz")
    fmt = item.get("format") or "PCM"
    bits = item.get("significant_bits")
    channels = item.get("channels")
    if isinstance(rate, (int, float)) and rate > 0:
        rate_text = f"{rate / 1000:g} kHz"
    else:
        rate_text = "rate unknown"
    bits_text = f" · {bits}-bit" if isinstance(bits, int) and bits > 0 else ""
    channel_text = f" · {channels} ch" if isinstance(channels, int) and channels else ""
    return f"{fmt}{bits_text} · {rate_text}{channel_text}"


class SignalPathBridge(QObject):
    """Truthful five-stage Signal Truth read model for QML."""

    state_changed = Signal()
    configuration_action_requested = Signal(str)

    def __init__(
        self,
        recorder: SignalTruthRecorder,
        output_bridge: object,
        processing_bridge: object,
        *,
        playback_path_provider: Callable[[], str] | None = None,
        playback_status_provider: Callable[[], str] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._recorder = recorder
        self._output = output_bridge
        self._processing = processing_bridge
        self._playback_path_provider = playback_path_provider
        self._playback_status_provider = playback_status_provider
        self._disposed = False
        self._generation = 0
        self._projection: dict[str, Any] = {}
        recorder.subscribe(self._on_source_changed)
        output_changed = getattr(output_bridge, "state_changed", None)
        if output_changed is not None:
            output_changed.connect(self._on_source_changed)
        processing_changed = getattr(processing_bridge, "state_changed", None)
        if processing_changed is not None:
            processing_changed.connect(self._on_source_changed)
        self._rebuild()

    def dispose(self) -> None:
        if self._disposed:
            return
        self._disposed = True
        self._recorder.unsubscribe(self._on_source_changed)

    def _on_source_changed(self) -> None:
        if self._disposed:
            return
        self._generation += 1
        self._rebuild()
        self.state_changed.emit()

    # ------------------------------------------------------------------
    # projection
    # ------------------------------------------------------------------
    def _snapshot_diagnostics(self, snapshot) -> dict[str, Any] | None:
        if snapshot is None:
            return None
        try:
            diagnostics = signal_truth_snapshot_diagnostics(snapshot)
        except Exception:  # noqa: BLE001 - projection failure is not runtime truth
            logger.debug("signal truth projection failed", exc_info=True)
            return None
        source = getattr(snapshot, "source_file_facts", None)
        if source is not None:
            nominal = getattr(source, "nominal_pcm", None)
            diagnostics["source"] = {
                "container": getattr(source, "container", None),
                "codec": getattr(source, "codec", None),
                "nominal_pcm": (
                    {
                        "format": nominal.transport_format,
                        "rate_hz": nominal.rate_hz,
                        "channels": nominal.channels,
                        "significant_bits": nominal.significant_bits,
                    }
                    if nominal is not None
                    else None
                ),
            }
        return diagnostics

    def _snapshot_choice(self):
        """Choose ONE evidence source and label its temporal status.

        ACTIVE and HISTORICAL are mutually exclusive. A candidate is PENDING:
        it is not a completed execution and can never publish ACTIVE proof.
        """
        active = self._recorder.active_snapshot
        if active is not None:
            transport = self._transport_status()
            if transport in {"stopped", "idle", "no_media"}:
                return active, "HISTORICAL"
            return active, "ACTIVE"
        try:
            candidate = self._recorder.candidate_snapshot
        except RuntimeError:
            candidate = None
        if candidate is not None:
            return candidate, "PENDING"
        last = self._recorder.last_snapshot
        if last is not None:
            return last, "HISTORICAL"
        return None, "NONE"

    def _transport_status(self) -> str:
        if self._playback_status_provider is None:
            return ""
        try:
            return str(self._playback_status_provider() or "").casefold()
        except Exception:  # noqa: BLE001 - presentation stays truthful
            return ""

    def _processing_truth(self) -> dict[str, Any]:
        try:
            return self._processing.truth
        except Exception:  # noqa: BLE001
            return {}

    def _processing_event_for(
        self,
        identity: dict[str, Any],
        effective_plan_id: str,
    ) -> tuple[bool, object | None]:
        """Correlate the processing receipt with this exact output pipeline.

        The processing plan id and the output plan id belong to different
        authorities and are never equal. The durable link is the pipeline
        generation the processing child observed when it committed. Return
        ``(events_available, event)`` so callers can distinguish "no evidence
        stream" (legacy/test doubles) from "a receipt that belongs elsewhere".
        """
        try:
            events = tuple(self._recorder.processing_events)
        except Exception:  # noqa: BLE001 - projection failure is not runtime truth
            return False, None
        if not events:
            return False, None
        port_generation = int(
            identity.get("port_generation") or identity.get("execution_generation") or 0
        )
        if port_generation <= 0:
            return True, None
        for event in reversed(events):
            state = getattr(event, "state", None)
            state_value = str(getattr(state, "value", state) or "")
            if state_value != "effective":
                continue
            if not bool(getattr(event, "readback_proven", False)):
                continue
            if str(getattr(event, "plan_id", None) or "") != effective_plan_id:
                continue
            pipeline_generation = int(getattr(event, "pipeline_generation", 0) or 0)
            if pipeline_generation == port_generation:
                return True, event
        return True, None

    def _device_display_name(self, stable_device_id: str) -> str:
        devices = self._output_value("devices", []) or []
        try:
            rows = list(devices)
        except TypeError:
            return "Audio device"
        for row in rows:
            if not isinstance(row, dict):
                continue
            identity = str(
                row.get("stableDeviceId") or row.get("stable_device_id") or ""
            )
            if identity != stable_device_id:
                continue
            name = str(row.get("displayName") or row.get("display_name") or "")
            if name:
                return name
        return "Audio device" if stable_device_id else "Device not selected"

    def _output_value(self, name: str, fallback: Any = None) -> Any:
        try:
            return self._output.property(name)
        except Exception:  # noqa: BLE001
            return fallback

    def _stage(
        self,
        stage_id: str,
        title: str,
        summary: str,
        *,
        detail: str = "",
        config_action: str = "NONE",
        state: str = "observed",
        detail_rows: tuple[tuple[str, str], ...] = (),
    ) -> dict[str, Any]:
        allowed = {
            "unknown",
            "pending",
            "observed",
            "transformed",
            "historical",
            "error",
        }
        return {
            "id": stage_id,
            "title": title,
            "summary": summary,
            "detail": detail,
            "configAction": config_action
            if config_action in _CONFIG_ACTIONS
            else "NONE",
            "state": state if state in allowed else "unknown",
            "detailRows": [list(row) for row in detail_rows],
            "expanded": False,
        }

    def _decorate_stages(
        self, stages: list[dict[str, Any]], *, historical: bool = False
    ) -> list[dict[str, Any]]:
        count = len(stages)
        decorated: list[dict[str, Any]] = []
        for index, stage in enumerate(stages):
            row = dict(stage)
            # Historical is a property of the whole capture, not of every
            # stage. One global badge prevents five repeated "Historical"
            # labels while the observed facts remain readable.
            row["historical"] = historical
            row["index"] = index
            row["count"] = count
            row["first"] = index == 0
            row["last"] = index == count - 1
            row["expandable"] = bool(row.get("detail") or row.get("detailRows"))
            decorated.append(row)
        return decorated

    def _rebuild(self) -> None:
        snapshot, temporal_status = self._snapshot_choice()
        diagnostics = self._snapshot_diagnostics(snapshot)
        truth = self._processing_truth()
        output_label = str(self._output_value("signalTruthLabel", "") or "")
        path = (
            self._playback_path_provider()
            if self._playback_path_provider is not None
            else ""
        )
        if diagnostics is None:
            has_media = bool(path)
            headline = (
                output_label or "Signal path not verified"
                if has_media
                else "No active path"
            )
            tone = "warning" if has_media else "neutral"
            stages = [
                self._stage(
                    "source",
                    "Source",
                    path.rsplit("/", 1)[-1] if path else "No active media",
                    detail="No verified execution" if has_media else "Idle",
                    state="unknown",
                ),
                self._stage(
                    "decode",
                    "Decode",
                    "Not observed",
                    detail="No active engine evidence",
                    config_action="OPEN_ENGINE",
                    state="unknown",
                ),
                self._stage(
                    "processing",
                    "Processing",
                    "Not verified",
                    detail=str(truth.get("effective_state", "unknown")),
                    config_action="OPEN_PROCESSING",
                    state="unknown",
                ),
                self._stage(
                    "output",
                    "Output",
                    str(self._output_value("currentFormat", "") or "Not observed"),
                    detail=str(self._output_value("signalTruthSummary", "") or ""),
                    config_action="OPEN_OUTPUT",
                    state="unknown",
                ),
                self._stage(
                    "device",
                    "DAC / Device",
                    str(self._output_value("activeDeviceId", "") or "Not selected"),
                    detail="No negotiated device evidence",
                    config_action="OPEN_DEVICE_SETUP",
                    state="unknown",
                ),
            ]
            quality_class = "unknown"
            format_label = _quality_format_label(None, path, quality_class)
            rate_depth_label = _quality_rate_depth_label(None, quality_class)
            proof_state = "no_path"
            proof_label = _path_proof_label(proof_state)
            self._projection = {
                "headline": headline,
                "proofLevel": "Not verified",
                "generation": self._generation,
                "sourceIdentity": path,
                "sourceQualityClass": quality_class,
                "sourceFormatLabel": format_label,
                "sourceRateDepthLabel": rate_depth_label,
                "pathProofState": proof_state,
                "pathProofLabel": proof_label,
                "qualityAccessibleText": (
                    f"Nominal quality: {format_label}. Path: {proof_label}"
                ),
                "stages": self._decorate_stages(stages),
                "reasonCodes": list(
                    self._output_value("signalTruthReasonCodes", []) or []
                ),
                "headlineTone": tone,
                "active": False,
                "historical": False,
                "status": "NOT_ACTIVE",
                "statusLabel": "No active path" if not has_media else "Pending",
                "pathVerdict": "unknown",
                "indicatorState": "none" if not has_media else "unknown",
                "indicatorTooltip": (
                    "Signal Truth: no active playback"
                    if not has_media
                    else "Signal Truth: path not verified"
                ),
                "identity": {},
                "configurationActions": [
                    "OPEN_ENGINE",
                    "OPEN_PROCESSING",
                    "OPEN_OUTPUT",
                    "OPEN_DEVICE_SETUP",
                ],
            }
            return

        verdict = diagnostics.get("verdict", {})
        verdict_state = str(verdict.get("state", "unknown"))
        canonical_headline = _VERDICT_HEADLINES.get(verdict_state, "Not verified")
        headline = (
            canonical_headline
            if verdict_state in _VERDICT_HEADLINES and verdict_state != "unknown"
            else (output_label or canonical_headline)
        )
        source = diagnostics.get("source") or {}
        quality_class = _quality_class(source)
        format_label = _quality_format_label(source, str(path or ""), quality_class)
        rate_depth_label = _quality_rate_depth_label(source, quality_class)
        decoded = diagnostics.get("decoded")
        engine = diagnostics.get("engine") or {}
        alsa = diagnostics.get("alsa")
        transform = diagnostics.get("transform") or {}
        plan = diagnostics.get("plan") or {}
        identity = diagnostics.get("identity") or {}
        reasons = list(verdict.get("reason_codes", []))
        tone = "neutral"
        if verdict_state == "contradicted":
            tone = "error"
        elif verdict_state == "unknown":
            tone = "warning"

        source_container = str(source.get("container") or "").strip()
        source_codec = str(source.get("codec") or "").strip()
        source_name = format_label
        nominal = source.get("nominal_pcm")
        source_detail = rate_depth_label if source else "Nominal format unknown"
        source_rows: list[tuple[str, str]] = []
        if source_container:
            source_rows.append(("Container", source_container))
        if source_codec:
            source_rows.append(("Codec", source_codec))
        if nominal:
            source_rows.append(("Nominal", _pcm_label(nominal)))

        decode_action = "OPEN_ENGINE" if decoded is None else "NONE"
        decode_state = "observed" if decoded is not None else "unknown"
        decode_rows: list[tuple[str, str]] = []
        if decoded:
            decode_rows.append(("Decoded", _pcm_label(decoded)))
            decode_rows.append(
                ("Port generation", str(identity.get("port_generation", "unknown")))
            )

        effective_state = str(truth.get("effective_state", "unknown"))
        effective_plan_id = str(truth.get("effective_plan_id") or "")
        snapshot_plan_id = str(identity.get("plan_id") or "")
        events_available, processing_event = self._processing_event_for(
            identity, effective_plan_id
        )
        if events_available:
            processing_matches = bool(
                effective_state == "effective" and processing_event is not None
            )
        else:
            # Compatibility for read-model doubles that publish the processing
            # truth without a recorder event stream.
            processing_matches = bool(
                effective_state == "effective"
                and effective_plan_id
                and snapshot_plan_id
                and effective_plan_id == snapshot_plan_id
            )
        engine_graph_factories = [
            str(item) for item in engine.get("graph_factories", []) or []
        ]
        has_engine_dsp = any(
            keyword in factory.casefold()
            for factory in engine_graph_factories
            for keyword in (
                "equalizer",
                "peq",
                "parametric",
                "preamp",
                "fir",
                "convolution",
                "dsp",
            )
        )
        processing_rows: list[tuple[str, str]] = []
        if processing_matches:
            processing_summary = "DSP active"
            processing_detail = "Readback confirmed for this signal path"
            processing_state = "transformed"
            event_plan = str(getattr(processing_event, "plan_id", "") or "")
            event_revision = getattr(processing_event, "processing_generation", 0)
            event_pipeline = getattr(processing_event, "pipeline_generation", 0)
            processing_rows.extend(
                (
                    ("Plan", event_plan or effective_plan_id),
                    (
                        "Revision",
                        str(
                            event_revision
                            if event_revision
                            else truth.get("effective_revision", 0)
                        ),
                    ),
                    ("Readback", "confirmed"),
                )
            )
            if event_pipeline:
                processing_rows.append(("Pipeline generation", str(event_pipeline)))
        elif effective_state == "effective":
            processing_summary = "Processing active · identity unverified"
            processing_detail = (
                "The effective processing runtime does not match this signal path"
            )
            processing_state = "unknown"
            processing_rows.append(("Effective plan", effective_plan_id or "unknown"))
            processing_rows.append(("Signal plan", snapshot_plan_id or "unknown"))
        elif effective_state == "bypassed":
            processing_summary = "Bypassed"
            processing_detail = "Processing is bypassed"
            processing_state = "observed"
            processing_rows.append(
                ("Revision", str(truth.get("effective_revision", 0)))
            )
        elif effective_state == "unavailable":
            processing_summary = "Unavailable"
            processing_detail = "No effective processing authority"
            processing_state = "unknown"
        else:
            processing_summary = "Not verified"
            processing_detail = "No processing receipt for this path"
            processing_state = "unknown"
        if not processing_matches and has_engine_dsp:
            processing_summary = "DSP observed · identity unverified"
            processing_detail = (
                "The engine reports DSP graph nodes but no matching receipt "
                "was found for this execution"
            )
            processing_state = "unknown"
            processing_rows.append(
                ("Graph factories", ", ".join(engine_graph_factories))
            )

        if verdict_state == "dsp" and processing_state == "unknown":
            headline = "DSP detected · identity unverified"
            tone = "warning"
        elif processing_matches and verdict_state in {
            "direct",
            "direct_container_adapted",
        }:
            # The DAC snapshot is captured before the live graph gains its DSP
            # filter. A readback-proven processing event bound to the same
            # pipeline generation is the authority for the processing stage.
            headline = "Processing active"
            tone = "neutral"

        requested = plan.get("requested") or {}
        output_observed = alsa or engine or None
        output_format = _pcm_label(output_observed)
        output_state = "observed" if output_observed else "unknown"
        output_detail = (
            "Negotiated device format"
            if alsa is not None
            else "Engine output format"
            if output_observed
            else "No negotiated evidence"
        )
        output_rows: list[tuple[str, str]] = []
        if requested:
            # Display the negotiated/observed format as the concise headline;
            # keep the complete requested vs actual tuple in expanded evidence.
            output_rows.append(("Requested", _pcm_label(requested)))
        if alsa is not None:
            output_rows.append(("Negotiated", _pcm_label(alsa)))
        if plan.get("sink_factory"):
            output_rows.append(("Sink", str(plan.get("sink_factory"))))
        if plan.get("sink_device"):
            output_rows.append(("Sink device", str(plan.get("sink_device"))))
        output_action = "OPEN_OUTPUT"

        snapshot_device = str(identity.get("stable_device_id") or "")
        selected_device = str(self._output_value("activeDeviceId", "") or "")
        device_summary = self._device_display_name(snapshot_device or selected_device)
        device_detail = str(self._output_value("signalTruthSummary", "") or "")
        device_action = "OPEN_DEVICE_SETUP"
        device_state = "observed" if snapshot_device else "unknown"
        device_rows: list[tuple[str, str]] = []
        if snapshot_device:
            device_rows.append(("Stable ID", snapshot_device))
        if selected_device:
            device_rows.append(("Active selection", selected_device))
        if snapshot_device and selected_device and snapshot_device != selected_device:
            device_state = "error"
            device_detail = "Observed device identity differs from the active selection"
        elif "ST_BINDING_MISMATCH" in reasons or "ST_DEVICE_MISMATCH" in reasons:
            device_state = "error"
            device_detail = "Runtime report contradicts the device binding"
        if identity.get("binding_generation") is not None:
            device_rows.append(
                ("Binding generation", str(identity.get("binding_generation")))
            )
        if identity.get("port_generation") is not None:
            device_rows.append(
                ("Port generation", str(identity.get("port_generation")))
            )

        stages = [
            self._stage(
                "source",
                "Source",
                source_name,
                detail=source_detail,
                state="observed" if source else "unknown",
                detail_rows=tuple(source_rows),
            ),
            self._stage(
                "decode",
                "Decode",
                _pcm_label(decoded),
                detail="Runtime decoder evidence" if decoded else "Not observed",
                config_action=decode_action,
                state=decode_state,
                detail_rows=tuple(decode_rows),
            ),
            self._stage(
                "processing",
                "Processing",
                processing_summary,
                detail=processing_detail,
                config_action="OPEN_PROCESSING",
                state=processing_state,
                detail_rows=tuple(processing_rows),
            ),
        ]

        if transform.get("resampler_transforming"):
            input_rate = (decoded or {}).get("rate_hz") if decoded else None
            output_rate = (alsa or {}).get("rate_hz") if alsa else None
            if input_rate and output_rate:
                resample_summary = (
                    f"{float(input_rate) / 1000:g} kHz → "
                    f"{float(output_rate) / 1000:g} kHz"
                )
            else:
                resample_summary = "Resampling observed"
            stages.append(
                self._stage(
                    "resample",
                    "Sample rate conversion",
                    resample_summary,
                    detail="Observed resampler transform",
                    config_action="OPEN_OUTPUT",
                    state="transformed",
                )
            )
        if transform.get("remix_transforming"):
            stages.append(
                self._stage(
                    "channel-remap",
                    "Channel remap",
                    "Channel layout changed",
                    detail="Observed channel remap",
                    config_action="OPEN_OUTPUT",
                    state="transformed",
                )
            )
        if any(
            "fir" in factory.casefold() or "convolution" in factory.casefold()
            for factory in engine_graph_factories
        ):
            stages.append(
                self._stage(
                    "fir",
                    "Convolution / FIR",
                    "FIR graph observed",
                    detail="Runtime graph factory reported FIR; latency is not measured",
                    config_action="OPEN_PROCESSING",
                    state="transformed",
                )
            )

        stages.extend(
            [
                self._stage(
                    "output",
                    "Output",
                    output_format,
                    detail=output_detail,
                    config_action=output_action,
                    state=output_state,
                    detail_rows=tuple(output_rows),
                ),
                self._stage(
                    "device",
                    "DAC / Device",
                    device_summary,
                    detail=device_detail or "Observed route",
                    config_action=device_action,
                    state=device_state,
                    detail_rows=tuple(device_rows),
                ),
            ]
        )

        historical = temporal_status == "HISTORICAL"
        pending = temporal_status == "PENDING"
        if historical:
            headline = "Last playback · historical"
            tone = "neutral"
            stages = self._decorate_stages(stages, historical=True)
        elif pending:
            headline = "Preparing signal path"
            tone = "neutral"
            for stage in stages:
                if stage["state"] in {"observed", "transformed"}:
                    stage["state"] = "pending"
            stages = self._decorate_stages(stages)
        else:
            stages = self._decorate_stages(stages)

        actions: list[str] = []
        for stage in stages:
            action = stage["configAction"]
            if action != "NONE" and action not in actions:
                actions.append(action)
        proof_parts: list[str] = []
        if source:
            proof_parts.append("Source")
        if decoded is not None or engine:
            proof_parts.append("host")
        if alsa is not None:
            proof_parts.append("transport")
        if snapshot_device:
            proof_parts.append("device")
        proof_level = " · ".join(proof_parts) or "Not verified"
        processing_verified = not (
            effective_state == "effective" and not processing_matches
        )
        proof_state = _path_proof_state(
            temporal_status=temporal_status,
            verdict_state=str(verdict_state),
            tone=tone,
            proof_parts=proof_parts,
            processing_verified=processing_verified,
        )
        proof_label = _path_proof_label(proof_state)
        if historical:
            indicator_state = "historical"
            indicator_tooltip = "Signal Truth: last playback (historical)"
            status_label = "Last playback · historical"
        elif pending:
            indicator_state = "pending"
            indicator_tooltip = "Signal Truth: path in preparation"
            status_label = "Preparing"
        elif tone == "error":
            indicator_state = "error"
            indicator_tooltip = "Signal Truth: output mismatch"
            status_label = "Error"
        elif any(stage["state"] == "transformed" for stage in stages):
            indicator_state = "transformed"
            indicator_tooltip = "Signal Truth: processing observed"
            status_label = "Active"
        elif verdict_state in {"direct", "direct_container_adapted"}:
            indicator_state = "observed"
            indicator_tooltip = "Signal Truth: path observed"
            status_label = "Active"
        else:
            indicator_state = "unknown"
            indicator_tooltip = "Signal Truth: path not verified"
            status_label = "Active"
        self._projection = {
            "headline": headline,
            "proofLevel": proof_level,
            "generation": self._generation,
            "sourceIdentity": str(path or ""),
            "sourceQualityClass": quality_class,
            "sourceFormatLabel": format_label,
            "sourceRateDepthLabel": rate_depth_label,
            "pathProofState": proof_state,
            "pathProofLabel": proof_label,
            "qualityAccessibleText": (
                f"Nominal quality: {format_label} {rate_depth_label}. "
                f"Path: {proof_label}"
            ).strip(),
            "stages": stages,
            "reasonCodes": reasons,
            "headlineTone": tone,
            "active": temporal_status == "ACTIVE",
            "historical": historical,
            "status": temporal_status,
            "statusLabel": status_label,
            "pathVerdict": verdict_state,
            "indicatorState": indicator_state,
            "indicatorTooltip": indicator_tooltip,
            "identity": identity,
            "configurationActions": actions,
        }

    # ------------------------------------------------------------------
    # QML properties / slots
    # ------------------------------------------------------------------
    def _get(self, key: str, fallback: Any = None) -> Any:
        return self._projection.get(key, fallback)

    @Property(str, notify=state_changed)
    def headline(self) -> str:
        return str(self._get("headline", "Not verified"))

    @Property(str, notify=state_changed)
    def proofLevel(self) -> str:
        return str(self._get("proofLevel", "Not verified"))

    @Property(int, notify=state_changed)
    def generation(self) -> int:
        return int(self._get("generation", 0))

    @Property(str, notify=state_changed)
    def sourceIdentity(self) -> str:
        return str(self._get("sourceIdentity", ""))

    @Property("QVariantList", notify=state_changed)
    def stages(self) -> list[dict[str, Any]]:
        return list(self._get("stages", []))

    @Property("QVariantList", notify=state_changed)
    def reasonCodes(self) -> list[str]:
        return list(self._get("reasonCodes", []))

    @Property(str, notify=state_changed)
    def headlineTone(self) -> str:
        return str(self._get("headlineTone", "neutral"))

    @Property(bool, notify=state_changed)
    def active(self) -> bool:
        return bool(self._get("active", False))

    @Property(bool, notify=state_changed)
    def historical(self) -> bool:
        return bool(self._get("historical", False))

    @Property(str, notify=state_changed)
    def status(self) -> str:
        return str(self._get("status", "NONE"))

    @Property(str, notify=state_changed)
    def statusLabel(self) -> str:
        return str(self._get("statusLabel", "No active path"))

    @Property(str, notify=state_changed)
    def pathVerdict(self) -> str:
        return str(self._get("pathVerdict", "unknown"))

    @Property(str, notify=state_changed)
    def sourceQualityClass(self) -> str:
        return str(self._get("sourceQualityClass", "unknown"))

    @Property(str, notify=state_changed)
    def sourceFormatLabel(self) -> str:
        return str(self._get("sourceFormatLabel", "NO TRACK"))

    @Property(str, notify=state_changed)
    def sourceRateDepthLabel(self) -> str:
        return str(self._get("sourceRateDepthLabel", "format unknown"))

    @Property(str, notify=state_changed)
    def pathProofState(self) -> str:
        return str(self._get("pathProofState", "no_path"))

    @Property(str, notify=state_changed)
    def pathProofLabel(self) -> str:
        return str(self._get("pathProofLabel", "No verified path"))

    @Property(str, notify=state_changed)
    def qualityAccessibleText(self) -> str:
        return str(self._get("qualityAccessibleText", "Nominal quality unknown"))

    @Property(str, notify=state_changed)
    def indicatorState(self) -> str:
        return str(self._get("indicatorState", "none"))

    @Property(str, notify=state_changed)
    def indicatorTooltip(self) -> str:
        return str(self._get("indicatorTooltip", "Signal Truth: no active playback"))

    @Property("QVariantMap", notify=state_changed)
    def identity(self) -> dict[str, Any]:
        return dict(self._get("identity", {}) or {})

    @Property("QVariantList", notify=state_changed)
    def configurationActions(self) -> list[str]:
        return list(self._get("configurationActions", []))

    @Slot(str)
    def request_configuration(self, action: str) -> None:
        if action in _CONFIG_ACTIONS and action != "NONE":
            self.configuration_action_requested.emit(action)


__all__ = ["SignalPathBridge"]
