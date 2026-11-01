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
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._recorder = recorder
        self._output = output_bridge
        self._processing = processing_bridge
        self._playback_path_provider = playback_path_provider
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
    def _snapshot_diagnostics(self) -> dict[str, Any] | None:
        snapshot = self._recorder.active_snapshot or self._recorder.last_snapshot
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

    def _processing_truth(self) -> dict[str, Any]:
        try:
            return self._processing.truth
        except Exception:  # noqa: BLE001
            return {}

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
    ) -> dict[str, Any]:
        return {
            "id": stage_id,
            "title": title,
            "summary": summary,
            "detail": detail,
            "configAction": config_action
            if config_action in _CONFIG_ACTIONS
            else "NONE",
            "state": state,
        }

    def _rebuild(self) -> None:
        diagnostics = self._snapshot_diagnostics()
        truth = self._processing_truth()
        output_label = str(self._output_value("signalTruthLabel", "") or "")
        path = (
            self._playback_path_provider()
            if self._playback_path_provider is not None
            else ""
        )
        if diagnostics is None:
            headline = output_label or "Not verified"
            tone = (
                "warning"
                if output_label in {"Output mismatch", "Not verified", ""}
                else "neutral"
            )
            stages = [
                self._stage(
                    "source",
                    "Source",
                    path.rsplit("/", 1)[-1] if path else "No active media",
                    detail="No verified execution",
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
            self._projection = {
                "headline": headline,
                "proofLevel": "Not verified",
                "generation": self._generation,
                "sourceIdentity": path,
                "stages": stages,
                "reasonCodes": list(
                    self._output_value("signalTruthReasonCodes", []) or []
                ),
                "headlineTone": tone,
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
        # The recorder is the authority. The output bridge label is only a
        # fallback when the canonical snapshot has no classified verdict.
        canonical_headline = _VERDICT_HEADLINES.get(verdict_state, "Not verified")
        headline = (
            canonical_headline
            if verdict_state in _VERDICT_HEADLINES and verdict_state != "unknown"
            else (output_label or canonical_headline)
        )
        source = diagnostics.get("source") or {}
        decoded = diagnostics.get("decoded")
        engine = diagnostics.get("engine") or {}
        alsa = diagnostics.get("alsa")
        transform = diagnostics.get("transform") or {}
        plan = diagnostics.get("plan") or {}
        reasons = list(verdict.get("reason_codes", []))
        tone = "neutral"
        if verdict_state == "contradicted":
            tone = "error"
        elif verdict_state == "unknown":
            tone = "warning"

        source_container = str(source.get("container") or "").strip()
        source_codec = str(source.get("codec") or "").strip()
        source_name = " · ".join(
            part for part in (source_codec, source_container) if part
        ) or (path.rsplit("/", 1)[-1] if path else "Source observed")
        nominal = source.get("nominal_pcm")
        source_detail = _pcm_label(nominal) if nominal else "Nominal format unknown"

        decode_action = "OPEN_ENGINE" if decoded is None else "NONE"
        decode_state = "observed" if decoded is not None else "unknown"

        effective_state = str(truth.get("effective_state", "unknown"))
        processing_bits: list[str] = []
        if effective_state == "effective":
            bands = getattr(self._processing, "bands", [])
            active = sum(
                1
                for band in bands
                if isinstance(band, dict) and float(band.get("gainDb", 0.0)) != 0.0
            )
            processing_bits.append(
                f"Graphic EQ · {active or len(bands)} bands" if bands else "Processing"
            )
        elif effective_state == "bypassed":
            processing_bits.append("Bypassed")
        elif effective_state == "unavailable":
            processing_bits.append("Unavailable")
        else:
            processing_bits.append("Not verified")
        preamp = getattr(self._processing, "preampDb", 0.0)
        if effective_state == "effective":
            processing_bits.append(f"Preamp {float(preamp):+.1f} dB")
        processing_summary = " · ".join(processing_bits)
        processing_state = (
            "observed" if effective_state in {"effective", "bypassed"} else "unknown"
        )

        requested = plan.get("requested") or {}
        output_format = _pcm_label(alsa or engine or None)
        if requested:
            requested_text = _pcm_label(requested)
            output_format = f"{requested_text} → {output_format}"
        output_action = "OPEN_OUTPUT"
        output_state = "observed" if alsa is not None else "unknown"
        if transform.get("resampler_transforming"):
            output_format = f"Resampled · {output_format}"

        device = str(self._output_value("activeDeviceId", "") or "")
        device_summary = device or "Device not selected"
        device_detail = str(self._output_value("signalTruthSummary", "") or "")
        device_action = "OPEN_DEVICE_SETUP" if not device else "NONE"
        device_state = "observed" if device else "unknown"
        if "ST_BINDING_MISMATCH" in reasons or "ST_DEVICE_MISMATCH" in reasons:
            device_state = "error"

        stages = [
            self._stage(
                "source",
                "Source",
                source_name,
                detail=source_detail,
                state="observed",
            ),
            self._stage(
                "decode",
                "Decode",
                _pcm_label(decoded),
                detail="Runtime decoder evidence" if decoded else "Not observed",
                config_action=decode_action,
                state=decode_state,
            ),
            self._stage(
                "processing",
                "Processing",
                processing_summary,
                detail=f"Revision {truth.get('effective_revision', 0)} · {effective_state}",
                config_action="OPEN_PROCESSING",
                state=processing_state,
            ),
            self._stage(
                "output",
                "Output",
                output_format,
                detail="Negotiated device format" if alsa else "No negotiated evidence",
                config_action=output_action,
                state=output_state,
            ),
            self._stage(
                "device",
                "DAC / Device",
                device_summary,
                detail=device_detail or "Observed route",
                config_action=device_action,
                state=device_state,
            ),
        ]
        actions: list[str] = []
        for stage in stages:
            action = stage["configAction"]
            if action != "NONE" and action not in actions:
                actions.append(action)
        self._projection = {
            "headline": headline,
            "proofLevel": "Source · host · transport",
            "generation": self._generation,
            "sourceIdentity": str(path or ""),
            "stages": stages,
            "reasonCodes": reasons,
            "headlineTone": tone,
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

    @Property("QVariantList", notify=state_changed)
    def configurationActions(self) -> list[str]:
        return list(self._get("configurationActions", []))

    @Slot(str)
    def request_configuration(self, action: str) -> None:
        if action in _CONFIG_ACTIONS and action != "NONE":
            self.configuration_action_requested.emit(action)


__all__ = ["SignalPathBridge"]
