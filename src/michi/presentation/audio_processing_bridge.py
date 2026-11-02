# ruff: noqa: N802 - Qt Property getters intentionally use camelCase names.
"""F11 audio-processing presentation bridge.

The bridge owns DRAFT presentation state for the quick 10-band equalizer and
delegates every runtime effect to the canonical ``AudioProcessingService``.
It never compiles a graph, never touches GStreamer and never declares a
processing state that the service did not commit.

Basic EQ mapping (F11 contract): ``PreampNode`` + ``ParametricEqNode`` with
ten PEAK bands at the MICHI_10 centers and Q = sqrt(2). A slider drag edits
the local draft only; Apply performs one owner-safe service transaction and
publishes EFFECTIVE only from the service truth.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from michi.application.audio_processing_service import AudioProcessingService
from michi.domain.audio_processing import (
    BiquadType,
    ParametricEqNode,
    PeqBand,
    PreampNode,
    ProcessingGraph,
)
from michi.domain.audio_signal import PcmSignalFormat

logger = logging.getLogger(__name__)

MICHI_10_CENTERS_HZ: tuple[float, ...] = (
    31.25,
    62.5,
    125.0,
    250.0,
    500.0,
    1_000.0,
    2_000.0,
    4_000.0,
    8_000.0,
    16_000.0,
)
MICHI_10_LABELS: tuple[str, ...] = (
    "31",
    "62",
    "125",
    "250",
    "500",
    "1K",
    "2K",
    "4K",
    "8K",
    "16K",
)
MICHI_10_Q = 2.0**0.5
_GAIN_MIN = -12.0
_GAIN_MAX = 12.0
_PREAMP_MIN = -24.0
_PREAMP_MAX = 24.0
_PRESET_ASSET = (
    Path(__file__).resolve().parents[1]
    / "resources"
    / "audio"
    / "factory_eq_presets_v1.json"
)


def _round_half_db(value: object) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    numeric = max(_GAIN_MIN, min(_GAIN_MAX, numeric))
    return round(numeric * 2.0) / 2.0


def _typed_code(exc: Exception, fallback: str) -> str:
    code = getattr(exc, "code", None)
    return str(code) if isinstance(code, str) and code else fallback


class AudioProcessingBridge(QObject):
    """QML projection of the canonical processing authority and draft EQ."""

    state_changed = Signal()
    open_advanced_requested = Signal()

    def __init__(
        self,
        service: AudioProcessingService,
        *,
        signal_provider: Callable[[], PcmSignalFormat | None] | None = None,
        source_family_provider: Callable[[], str] | None = None,
        async_submit: Callable[[Callable, Callable], None] | None = None,
        profiles: object | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._signal_provider = signal_provider
        self._source_family_provider = source_family_provider or (lambda: "pcm")
        self._async_submit = async_submit
        self._profiles = profiles
        self._disposed = False
        self._busy = False
        self._bands: list[dict[str, Any]] = self._flat_bands()
        self._preamp_db = 0.0
        self._bypass_requested = False
        self._preset_id = "flat"
        self._draft_graph_id = "f11:quick-eq"
        self._error_code = ""
        self._error_message = ""
        self._committed_bands = self._flat_bands()
        self._committed_preamp = 0.0
        self._committed_bypass = True
        self._factory_presets = self._load_factory_presets()

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------
    def dispose(self) -> None:
        self._disposed = True

    # ------------------------------------------------------------------
    # projections
    # ------------------------------------------------------------------
    @staticmethod
    def _flat_bands() -> list[dict[str, Any]]:
        return [
            {
                "id": f"band-{index + 1}",
                "label": MICHI_10_LABELS[index],
                "centerHz": center,
                "gainDb": 0.0,
                "enabled": True,
                "inactiveReason": "",
            }
            for index, center in enumerate(MICHI_10_CENTERS_HZ)
        ]

    def _signal(self) -> PcmSignalFormat | None:
        if self._signal_provider is None:
            return None
        try:
            return self._signal_provider()
        except Exception:  # noqa: BLE001 - a provider failure is a typed state
            logger.debug("processing signal provider failed", exc_info=True)
            return None

    def _truth(self) -> dict[str, Any]:
        try:
            return self._service.processing_truth()
        except Exception:  # noqa: BLE001 - presentation must stay truthful
            return {
                "capability_state": "unavailable",
                "requested_revision": 0,
                "effective_revision": 0,
                "effective_state": "unavailable",
                "runtime_identity": None,
            }

    def _strategies(self) -> set[str]:
        return {str(item) for item in self._truth().get("strategies", [])}

    @Property(bool, notify=state_changed)
    def available(self) -> bool:
        if self._source_family() in {"dsd", "dop", "native_dsd"}:
            return False
        return self._truth().get("capability_state") != "unavailable"

    @Property(str, notify=state_changed)
    def capabilityReason(self) -> str:
        if self._source_family() in {"dsd", "dop", "native_dsd"}:
            return "DSP requires explicit DSD-to-PCM conversion"
        state = str(self._truth().get("capability_state", "unknown"))
        if state == "unknown":
            strategies = self._strategies()
            if not strategies:
                return "Audio processing capabilities have not been queried yet"
        if state == "unavailable":
            return "Audio processing is unavailable for the current output"
        return ""

    @Property(str, notify=state_changed)
    def sourceFamily(self) -> str:
        return self._source_family()

    def _source_family(self) -> str:
        try:
            value = str(self._source_family_provider() or "pcm").casefold()
        except Exception:  # noqa: BLE001
            return "pcm"
        allowed = {
            "pcm",
            "pcm_direct",
            "pcm_managed",
            "dsd",
            "dsd_to_pcm",
            "dop",
            "native_dsd",
        }
        return value if value in allowed else "pcm"

    @Property(bool, notify=state_changed)
    def busy(self) -> bool:
        return self._busy

    @Property(bool, notify=state_changed)
    def enabledDraft(self) -> bool:
        return not self._bypass_requested

    @Property(bool, notify=state_changed)
    def enabledEffective(self) -> bool:
        return self._truth().get("effective_state") == "effective"

    @Property(bool, notify=state_changed)
    def bypassRequested(self) -> bool:
        return self._bypass_requested

    @Property(bool, notify=state_changed)
    def bypassEffective(self) -> bool:
        return self._truth().get("effective_state") == "bypassed"

    @Property(str, notify=state_changed)
    def effectiveState(self) -> str:
        return str(self._truth().get("effective_state", "unavailable"))

    @Property(int, notify=state_changed)
    def requestRevision(self) -> int:
        return int(self._truth().get("requested_revision", 0) or 0)

    @Property(int, notify=state_changed)
    def committedRevision(self) -> int:
        return int(self._truth().get("effective_revision", 0) or 0)

    @Property("QVariantList", notify=state_changed)
    def bands(self) -> list[dict[str, Any]]:
        signal = self._signal()
        nyquist = signal.rate_hz / 2.0 if signal is not None else None
        projected: list[dict[str, Any]] = []
        for item in self._bands:
            row = dict(item)
            if nyquist is not None and float(row["centerHz"]) >= nyquist:
                row["enabled"] = False
                row["inactiveReason"] = "Unavailable at current sample rate"
            projected.append(row)
        return projected

    @Property(float, notify=state_changed)
    def preampDb(self) -> float:
        return self._preamp_db

    @Property(str, notify=state_changed)
    def presetId(self) -> str:
        return self._preset_id

    @Property("QVariantList", notify=state_changed)
    def factoryPresets(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._factory_presets]

    @Property(str, notify=state_changed)
    def headroomLabel(self) -> str:
        return "Headroom · not measured"

    @Property(bool, notify=state_changed)
    def canPreview(self) -> bool:
        return False

    @Property(bool, notify=state_changed)
    def canApply(self) -> bool:
        if self._busy or not self.available:
            return False
        if self._signal() is None:
            return False
        strategies = self._strategies()
        return {"BIQUAD_CASCADE", "GAIN"}.issubset(strategies) or not strategies

    @Property(str, notify=state_changed)
    def errorCode(self) -> str:
        return self._error_code

    @Property(str, notify=state_changed)
    def errorMessage(self) -> str:
        return self._error_message

    @Property("QVariantMap", notify=state_changed)
    def truth(self) -> dict[str, Any]:
        return self._truth()

    # ------------------------------------------------------------------
    # draft edits (presentation only)
    # ------------------------------------------------------------------
    @Slot(int, float)
    def set_draft_band(self, index: int, gain_db: float) -> None:
        if self._busy or index < 0 or index >= len(self._bands):
            return
        self._bands[index]["gainDb"] = _round_half_db(gain_db)
        self._preset_id = "custom"
        self._clear_error()
        self.state_changed.emit()

    @Slot(float)
    def set_draft_preamp(self, value: float) -> None:
        if self._busy:
            return
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return
        self._preamp_db = round(max(_PREAMP_MIN, min(_PREAMP_MAX, numeric)) * 2.0) / 2.0
        self._preset_id = "custom"
        self._clear_error()
        self.state_changed.emit()

    @Slot(str)
    def select_preset(self, preset_id: str) -> None:
        if self._busy:
            return
        preset = next(
            (
                item
                for item in self._factory_presets
                if item.get("id") == preset_id and item.get("gainsDb")
            ),
            None,
        )
        if preset is None:
            return
        gains = list(preset.get("gainsDb", []))
        if len(gains) != len(self._bands):
            return
        for index, gain in enumerate(gains):
            self._bands[index]["gainDb"] = _round_half_db(gain)
        self._preset_id = preset_id
        self._clear_error()
        self.state_changed.emit()

    @Slot()
    def reset_draft(self) -> None:
        if self._busy:
            return
        self._bands = self._flat_bands()
        self._preamp_db = 0.0
        self._preset_id = "flat"
        self._clear_error()
        self.state_changed.emit()

    @Slot()
    def discard_draft(self) -> None:
        if self._busy:
            return
        self._bands = [dict(item) for item in self._committed_bands]
        self._preamp_db = self._committed_preamp
        self._bypass_requested = self._committed_bypass
        self._preset_id = "custom" if not self._is_flat() else "flat"
        self._clear_error()
        self.state_changed.emit()

    @Slot(bool)
    def set_bypass_requested(self, bypassed: bool) -> None:
        if self._busy:
            return
        self._bypass_requested = bool(bypassed)
        self._clear_error()
        self.state_changed.emit()

    @Slot()
    def open_advanced(self) -> None:
        self.open_advanced_requested.emit()

    @Slot()
    def refresh(self) -> None:
        """Re-read the canonical truth after an external state change."""
        self.state_changed.emit()

    # ------------------------------------------------------------------
    # runtime transactions
    # ------------------------------------------------------------------
    @Slot()
    def validate_draft(self) -> bool:
        for index, band in enumerate(self._bands):
            gain = band.get("gainDb")
            if not isinstance(gain, (int, float)) or not (
                _GAIN_MIN <= float(gain) <= _GAIN_MAX
            ):
                self._set_error("DSP_EQ_GAIN_INVALID", f"Band {index + 1} is invalid")
                return False
        if not (_PREAMP_MIN <= self._preamp_db <= _PREAMP_MAX):
            self._set_error("DSP_EQ_PREAMP_INVALID", "Preamp is outside its range")
            return False
        self._clear_error()
        return True

    def _build_graph(self) -> ProcessingGraph:
        bands = tuple(
            PeqBand(
                band_id=f"f11-band-{index + 1}",
                filter_type=BiquadType.PEAK,
                frequency_hz=center,
                q=MICHI_10_Q,
                gain_db=float(self._bands[index]["gainDb"]),
                enabled=True,
            )
            for index, center in enumerate(MICHI_10_CENTERS_HZ)
        )
        return ProcessingGraph(
            graph_id=self._draft_graph_id,
            revision=max(1, self.committedRevision + 1),
            nodes=(
                PreampNode(node_id="f11-preamp", gain_db=self._preamp_db),
                ParametricEqNode(node_id="f11-peq", bands=bands),
            ),
            bypassed=False,
        )

    @Slot()
    def apply_draft_async(self) -> None:
        if self._busy:
            return
        if not self.validate_draft():
            return
        signal = self._signal()
        if signal is None:
            self._set_error(
                "DSP_SIGNAL_UNKNOWN",
                "No decoded PCM signal is available for processing",
            )
            return
        if self._source_family() in {"dsd", "dop", "native_dsd"}:
            self._set_error(
                "DSP_REQUIRES_DSD_PCM_CONVERSION",
                "DSP requires explicit DSD-to-PCM conversion",
            )
            return
        self._busy = True
        self._clear_error()
        self.state_changed.emit()
        if self._bypass_requested:
            self._service.disable_processing_async(
                on_done=self._on_bypass_done,
                on_failed=self._on_async_failed,
                async_submit=self._async_submit,
            )
            return
        graph = self._build_graph()
        self._service.apply_processing_async(
            graph,
            signal,
            assets=(),
            on_done=self._on_apply_done,
            on_failed=self._on_async_failed,
            async_submit=self._async_submit,
        )

    def _on_apply_done(self, result: dict[str, Any]) -> None:
        if self._disposed:
            return
        self._busy = False
        self._committed_bands = [dict(item) for item in self._bands]
        self._committed_preamp = self._preamp_db
        self._committed_bypass = False
        if not self._is_flat():
            self._preset_id = "custom"
        self._clear_error()
        logger.debug("F11 quick EQ committed: %s", result.get("plan_id"))
        self.state_changed.emit()

    def _on_bypass_done(self, bypassed: bool) -> None:
        if self._disposed:
            return
        self._busy = False
        if bypassed:
            self._committed_bands = [dict(item) for item in self._bands]
            self._committed_preamp = self._preamp_db
            self._committed_bypass = True
            self._clear_error()
        else:
            self._set_error(
                "DSP_BYPASS_UNCONFIRMED",
                "The host did not confirm the processing bypass",
            )
        self.state_changed.emit()

    def _on_async_failed(self, exc: Exception) -> None:
        if self._disposed:
            return
        self._busy = False
        self._set_error(
            _typed_code(exc, "DSP_APPLY_FAILED"),
            str(exc) or "Audio processing could not be applied",
        )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _is_flat(self) -> bool:
        return all(float(item.get("gainDb", 0.0)) == 0.0 for item in self._bands) and (
            self._preamp_db == 0.0
        )

    def _set_error(self, code: str, message: str) -> None:
        self._error_code = code
        self._error_message = message
        self.state_changed.emit()

    def _clear_error(self) -> None:
        self._error_code = ""
        self._error_message = ""

    def _load_factory_presets(self) -> list[dict[str, Any]]:
        presets: list[dict[str, Any]] = [
            {
                "id": "flat",
                "displayName": "Flat",
                "gainsDb": [0.0] * len(MICHI_10_CENTERS_HZ),
                "provenance": "factory/flat",
                "reviewState": "reviewed",
            }
        ]
        try:
            payload = json.loads(_PRESET_ASSET.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return presets
        known_ids = {str(item["id"]) for item in presets}
        for item in payload.get("presets", []):
            if not isinstance(item, dict):
                continue
            if item.get("reviewState") != "reviewed":
                continue
            gains = item.get("gainsDb")
            if not isinstance(gains, list) or len(gains) != len(MICHI_10_CENTERS_HZ):
                continue
            if not all(isinstance(value, (int, float)) for value in gains):
                continue
            preset_id = str(item.get("id", "")).strip()
            display = str(item.get("displayName", "")).strip()
            if not preset_id or not display or preset_id in known_ids:
                continue
            known_ids.add(preset_id)
            presets.append(
                {
                    "id": preset_id,
                    "displayName": display,
                    "gainsDb": [float(value) for value in gains],
                    "provenance": str(item.get("provenance", "")),
                    "reviewState": "reviewed",
                }
            )
        return presets


__all__ = [
    "AudioProcessingBridge",
    "MICHI_10_CENTERS_HZ",
    "MICHI_10_LABELS",
    "MICHI_10_Q",
]
