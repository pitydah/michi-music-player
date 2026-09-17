"""Truthful QML projection of the canonical audio-output authorities."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from michi.application.audio_output_selection_coordinator import (
    AudioOutputSelectionCoordinator,
    AudioOutputSelectionError,
)
from michi.application.playback_service import PlaybackService
from michi.application.volume_policy_service import VolumePolicyService
from michi.domain.audio_engine import AudioEngineId
from michi.domain.audio_output import OutputPathPreference, OutputSessionState
from michi.domain.playback import PlaybackStatus
from michi.domain.signal_truth import SignalTruthRecorder

_VERDICT_LABELS = {
    "direct": "Direct path",
    "direct_container_adapted": "Direct · container adapted",
    "resampled": "Resampled",
    "remixed": "Channel remix",
    "dsp": "Processing active",
    "contradicted": "Output mismatch",
    "unknown": "Not verified",
}


def signal_truth_label(verdict: str) -> str:
    """Map a canonical verdict to normal-mode copy without overclaiming."""
    return _VERDICT_LABELS.get(verdict.casefold(), "Not verified")


def failure_copy(code: str | None) -> tuple[str, str]:
    """Return presentation-only title/explanation for one typed code."""
    normalized = (code or "").upper()
    if "BUSY" in normalized:
        return "Device busy", "Another application is currently using this DAC."
    if normalized in {"DEVICE_LOST", "OUTPUT_DEVICE_LOST", "DEVICE_UNAVAILABLE"}:
        return (
            "Device disconnected",
            "The selected DAC is no longer available.",
        )
    if normalized in {"ENGINE_UNSUPPORTED_FOR_DIRECT", "ENGINE_NOT_GSTREAMER"}:
        return (
            "Direct requires GStreamer",
            "Select GStreamer explicitly to use Direct output.",
        )
    if normalized in {"EXACT_TUPLE_UNKNOWN", "SIGNIFICANT_BITS_UNPROVEN"}:
        return (
            "Format not verified",
            "Michi has not confirmed this format for the current DAC connection.",
        )
    if "FIXED" in normalized or "LOCKED" in normalized:
        return (
            "Output locked at fixed level",
            "Digital attenuation is disabled for this output.",
        )
    if "CONTRADICT" in normalized or normalized == "OUTPUT_MISMATCH":
        return (
            "Output mismatch",
            "The runtime output does not match the expected Direct plan.",
        )
    if normalized in {"OUTPUT_DEVICE_UNKNOWN", "OUTPUT_PROFILE_UNKNOWN"}:
        return (
            "Output unavailable",
            "The requested output is no longer known to Michi.",
        )
    if normalized in {"SELECTED_DEVICE_MISSING", "DIRECT_PROFILE_REQUIRED"}:
        return "Select a DAC", "Choose an available physical DAC first."
    if normalized == "OUTPUT_PROFILE_DEVICE_MISMATCH":
        return "Profile mismatch", "This output profile belongs to another DAC."
    if normalized in {"VOLUME_MODE_UNAVAILABLE", "RESYNC_DELAY_INVALID"}:
        return (
            "Setting unavailable",
            "This setting is not qualified for the selected output.",
        )
    if normalized == "OUTPUT_PATH_MODE_UNKNOWN":
        return "Output path unavailable", "Choose Shared or Direct output."
    if not normalized:
        return "", ""
    return "Output unavailable", "Michi could not activate the selected output."


def _display_name(identity) -> str:
    manufacturer = (identity.manufacturer or "").strip()
    product = (identity.product or "").strip()
    if manufacturer and product:
        if product.casefold().startswith(manufacturer.casefold()):
            return product
        return f"{manufacturer} {product}"
    return (
        product
        or manufacturer
        or ("USB Audio Device" if identity.bus == "usb" else "Audio Output")
    )


def _short_id(stable_device_id: str) -> str:
    if len(stable_device_id) <= 24:
        return stable_device_id
    return f"{stable_device_id[:16]}…{stable_device_id[-6:]}"


def _bounded_suffix(value: str, *, width: int = 6) -> str:
    """Return a stable, bounded presentation hint without exposing raw identity."""
    return f"…{value[-width:]}"


def _identity_presentations(snapshots: tuple) -> dict[str, tuple[str, str]]:
    """Build collision-only human labels shared by device and profile rows."""
    grouped: dict[str, list] = {}
    for snapshot in snapshots:
        grouped.setdefault(_display_name(snapshot.identity), []).append(snapshot)

    presentations: dict[str, tuple[str, str]] = {}
    for base_name, group in grouped.items():
        if len(group) == 1:
            identity = group[0].identity
            presentations[identity.stable_device_id] = (base_name, "")
            continue

        serial_suffixes = {
            snapshot.identity.stable_device_id: _bounded_suffix(
                snapshot.identity.serial.strip()
            )
            for snapshot in group
            if snapshot.identity.serial and snapshot.identity.serial.strip()
        }
        if len(serial_suffixes) == len(group) and len(
            set(serial_suffixes.values())
        ) == len(group):
            suffixes = serial_suffixes
        else:
            stable_ids = [snapshot.identity.stable_device_id for snapshot in group]
            suffixes = {}
            for width in range(6, 13):
                candidate = {
                    stable_id: _bounded_suffix(stable_id, width=width)
                    for stable_id in stable_ids
                }
                if len(set(candidate.values())) == len(stable_ids):
                    suffixes = candidate
                    break
            if not suffixes:
                digests = {
                    stable_id: hashlib.sha256(stable_id.encode("utf-8")).hexdigest()
                    for stable_id in stable_ids
                }
                for width in range(8, 65, 4):
                    candidate = {
                        stable_id: f"…{digest[:width]}"
                        for stable_id, digest in digests.items()
                    }
                    if len(set(candidate.values())) == len(stable_ids):
                        suffixes = candidate
                        break

        for snapshot in group:
            stable_id = snapshot.identity.stable_device_id
            presentations[stable_id] = (base_name, f" · {suffixes[stable_id]}")
    return presentations


def _rate_label(rate_hz: int) -> str:
    if rate_hz <= 0:
        return "—"
    if rate_hz % 1000 == 0:
        return f"{rate_hz // 1000} kHz"
    return f"{rate_hz / 1000:.1f} kHz"


class AudioOutputBridge(QObject):
    """Render existing output truth and delegate explicit selection intents."""

    state_changed = Signal()
    action_failed = Signal(str, str, str)  # typed code, friendly title, explanation
    diagnostics_requested = Signal()

    def __init__(
        self,
        volume_policy: VolumePolicyService,
        playback: PlaybackService,
        signal_truth: SignalTruthRecorder | None = None,
        parent: QObject | None = None,
        *,
        devices=None,
        profiles=None,
        output_session=None,
        engines=None,
        selection_coordinator: AudioOutputSelectionCoordinator | None = None,
        qualification=None,
        refresh_devices: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._volume_policy = volume_policy
        self._playback = playback
        self._signal_truth = signal_truth
        self._devices = devices
        self._profiles = profiles
        self._output_session = output_session
        self._engines = engines
        self._selection_coordinator = selection_coordinator
        self._qualification = qualification
        self._refresh_devices = refresh_devices
        self._disposed = False
        self._projection: dict[str, Any] = {}
        self._last_action_failure: tuple[str, str, str] | None = None

        playback.subscribe_changed(self._on_source_changed)
        if signal_truth is not None:
            signal_truth.subscribe(self._on_source_changed)
        if devices is not None:
            devices.subscribe_topology_changed(self._on_topology_changed)
        if profiles is not None:
            profiles.subscribe_changed(self._on_source_changed)
        if output_session is not None:
            output_session.subscribe_changed(self._on_source_changed)
        if engines is not None:
            engines.subscribe_changed(self._on_source_changed)
        self._rebuild()

    def dispose(self) -> None:
        if self._disposed:
            return
        self._disposed = True
        self._playback.unsubscribe_changed(self._on_source_changed)
        if self._signal_truth is not None:
            self._signal_truth.unsubscribe(self._on_source_changed)
        if self._devices is not None:
            self._devices.unsubscribe_topology_changed(self._on_topology_changed)
        if self._profiles is not None:
            self._profiles.unsubscribe_changed(self._on_source_changed)
        if self._output_session is not None:
            self._output_session.unsubscribe_changed(self._on_source_changed)
        if self._engines is not None:
            self._engines.unsubscribe_changed(self._on_source_changed)

    def _on_topology_changed(self, _change) -> None:
        if self._last_action_failure is not None and self._last_action_failure[0] in {
            "DEVICE_UNAVAILABLE",
            "DEVICE_LOST",
            "OUTPUT_DEVICE_LOST",
        }:
            self._last_action_failure = None
        self._on_source_changed()

    def _on_source_changed(self) -> None:
        if self._disposed:
            return
        self._rebuild()
        self.state_changed.emit()

    def _selection(self):
        return self._profiles.load_selection() if self._profiles is not None else None

    def _profiles_snapshot(self) -> tuple:
        return self._profiles.load_profiles() if self._profiles is not None else ()

    def _active_truth(self, session_state):
        truth = self._signal_truth.active_snapshot if self._signal_truth else None
        if truth is None or session_state is None:
            return truth
        if (
            session_state.active_plan_id is None
            or session_state.active_device_id is None
            or truth.identity.plan_id != session_state.active_plan_id
            or truth.identity.stable_device_id != session_state.active_device_id
        ):
            return None
        return truth

    def _rebuild(self) -> None:
        selection = self._selection()
        selected_device_id = (
            selection.selected_device_id if selection is not None else None
        )
        selected_profile_id = (
            selection.selected_profile_id if selection is not None else None
        )
        profiles = self._profiles_snapshot()
        selected_profile = next(
            (item for item in profiles if item.profile_id == selected_profile_id), None
        )
        session_state = (
            self._output_session.selection_state()
            if self._output_session is not None
            else None
        )
        active_device_id = (
            session_state.active_device_id if session_state is not None else None
        )
        output_state = (
            session_state.session_state.value if session_state is not None else "idle"
        )
        transport_mode = (
            self._output_session.mode if self._output_session is not None else "shared"
        )
        selected_path_mode = (
            "direct"
            if selected_profile is not None
            and selected_profile.path is OutputPathPreference.HARDWARE_DIRECT
            else "shared"
        )
        reconnecting = output_state == OutputSessionState.RECOVERING.value
        session_failure_code = (
            session_state.error_code if session_state is not None else None
        )
        if self._last_action_failure is not None:
            (
                last_failure_code,
                last_failure_title,
                last_failure_display,
            ) = self._last_action_failure
        else:
            last_failure_code = session_failure_code
            last_failure_title, last_failure_display = failure_copy(last_failure_code)
        truth = self._active_truth(session_state)
        verdict = truth.verdict.value if truth is not None else "unknown"
        truth_label = signal_truth_label(verdict)
        signal_path = self._signal_path(truth)
        can_use_direct = bool(
            self._engines is not None
            and self._engines.state.active_engine_id is AudioEngineId.GSTREAMER
        )

        snapshots = (
            self._devices.device_snapshots() if self._devices is not None else ()
        )
        snapshots_by_id = {
            snapshot.identity.stable_device_id: snapshot for snapshot in snapshots
        }
        identity_presentations = _identity_presentations(snapshots)
        profile_rows = [
            self._profile_row(
                item,
                snapshot=snapshots_by_id.get(item.stable_device_id or ""),
                selected=item.profile_id == selected_profile_id,
                identity_presentation=identity_presentations.get(
                    item.stable_device_id or "", ("Audio device", "")
                ),
            )
            for item in profiles
        ]
        profile_rows.sort(
            key=lambda row: (
                not row["selected"],
                not row["available"],
                row["displayName"].casefold(),
            )
        )
        physical_rows = []
        for snapshot in snapshots:
            physical_rows.append(
                self._device_row(
                    snapshot,
                    profiles=profiles,
                    selected_device_id=selected_device_id,
                    selected_profile_id=selected_profile_id,
                    active_device_id=active_device_id,
                    reconnecting=reconnecting,
                    truth=truth,
                    truth_label=truth_label,
                    last_failure_code=last_failure_code or "",
                    identity_presentation=identity_presentations[
                        snapshot.identity.stable_device_id
                    ],
                )
            )
        physical_rows.sort(
            key=lambda row: (
                not row["selected"],
                not row["active"],
                not row["available"],
                row["displayName"].casefold(),
                row["stableDeviceId"],
            )
        )
        shared_active = self._shared_is_active(transport_mode)
        shared_row = self._shared_row(
            selected=selected_device_id is None,
            active=shared_active,
            truth_label=truth_label if shared_active else "Not verified",
        )
        device_rows = [shared_row, *physical_rows]
        selected_name = next(
            (row["displayName"] for row in device_rows if row["selected"]),
            "System Output" if selected_device_id is None else "Audio Output",
        )
        active_row = next((row for row in device_rows if row["active"]), None)
        selected_row = next((row for row in device_rows if row["selected"]), None)
        if selected_device_id and not any(
            row["stableDeviceId"] == selected_device_id and row["available"]
            for row in physical_rows
        ):
            output_tooltip = "Selected output unavailable"
        elif active_row is not None:
            output_tooltip = (
                f"Output: {active_row['displayName']} · {active_row['transportLabel']}"
            )
        elif selected_device_id is None:
            output_tooltip = "Shared system output"
        else:
            output_tooltip = f"Output: {selected_name}"

        self._projection = {
            "devices": device_rows,
            "profiles": profile_rows,
            "selectedDeviceId": selected_device_id or "",
            "activeDeviceId": active_device_id or "",
            "selectedProfileId": selected_profile_id or "",
            "transportMode": transport_mode,
            "selectedPathMode": selected_path_mode,
            "pathMode": selected_path_mode,
            "availability": bool(selected_row and selected_row["available"]),
            "availabilityReason": (
                selected_row["connectionLabel"] if selected_row else "Unknown"
            ),
            "outputState": output_state,
            "volumeMode": self._volume_policy.authority.value,
            "volumeAdjustable": self._volume_policy.volume_adjustable,
            "volumeLabel": self._volume_policy.volume_label,
            "signalTruthVerdict": verdict,
            "signalTruthLabel": truth_label,
            "signalTruthSummary": truth_label,
            "signalTruthReasonCodes": (
                [reason.value for reason in truth.reasons] if truth is not None else []
            ),
            "currentSourceRate": (
                truth.decoded_runtime.pcm.rate_hz
                if truth is not None and truth.decoded_runtime is not None
                else 0
            ),
            "currentDeviceRate": (
                truth.device_negotiated.negotiated_pcm.rate_hz
                if truth is not None and truth.device_negotiated is not None
                else 0
            ),
            "currentRateHz": (
                truth.device_negotiated.negotiated_pcm.rate_hz
                if truth is not None and truth.device_negotiated is not None
                else 0
            ),
            "currentFormat": (
                truth.device_negotiated.negotiated_pcm.transport_format
                if truth is not None and truth.device_negotiated is not None
                else ""
            ),
            "currentChannels": (
                truth.device_negotiated.negotiated_pcm.channels
                if truth is not None and truth.device_negotiated is not None
                else 0
            ),
            "significantBits": (
                truth.device_negotiated.negotiated_pcm.significant_bits or 0
                if truth is not None and truth.device_negotiated is not None
                else 0
            ),
            "isDirect": bool(active_device_id and transport_mode == "direct"),
            "isExclusiveObserved": False,
            "isBusy": "BUSY" in (last_failure_code or "").upper(),
            "isReconnecting": reconnecting,
            "signalPath": signal_path,
            "reconnecting": reconnecting,
            "lastFailureCode": last_failure_code or "",
            "lastFailureTitle": last_failure_title,
            "lastFailureDisplay": last_failure_display,
            "canSelectDevice": self._selection_coordinator is not None,
            "canUseDirect": can_use_direct,
            "outputTooltip": output_tooltip,
            "diagnosticsAvailable": bool(physical_rows or last_failure_code or truth),
        }

    def _shared_is_active(self, transport_mode: str) -> bool:
        state = getattr(self._playback, "state", None)
        if state is None:
            return False
        return bool(
            transport_mode == "shared"
            and state.file_path is not None
            and state.status in {PlaybackStatus.PLAYING, PlaybackStatus.PAUSED}
        )

    @staticmethod
    def _profile_row(
        profile,
        *,
        snapshot,
        selected: bool,
        identity_presentation: tuple[str, str],
    ) -> dict[str, Any]:
        direct = profile.path is OutputPathPreference.HARDWARE_DIRECT
        path_label = "Direct" if direct else "Shared"
        available = bool(snapshot is not None and snapshot.available)
        base_device_name, identity_suffix = identity_presentation
        device_name = f"{base_device_name}{identity_suffix}"
        status = (
            "Selected · available"
            if selected and available
            else "Selected · unavailable"
            if selected
            else "Available"
            if available
            else "Unavailable"
        )
        return {
            "profileId": profile.profile_id,
            "stableDeviceId": profile.stable_device_id or "",
            "profileName": path_label,
            "displayName": f"{base_device_name} — {path_label}{identity_suffix}",
            "deviceName": device_name,
            "pathLabel": path_label,
            "transportMode": "direct" if direct else "shared",
            "volumeMode": profile.volume_policy.value,
            "resyncDelayMs": profile.resync_delay_ms,
            "available": available,
            "selected": selected,
            "actionEnabled": available,
            "statusLabel": status,
        }

    def _device_row(
        self,
        snapshot,
        *,
        profiles: tuple,
        selected_device_id: str | None,
        selected_profile_id: str | None,
        active_device_id: str | None,
        reconnecting: bool,
        truth,
        truth_label: str,
        last_failure_code: str,
        identity_presentation: tuple[str, str],
    ) -> dict[str, Any]:
        identity = snapshot.identity
        stable_id = identity.stable_device_id
        selected = stable_id == selected_device_id
        active = stable_id == active_device_id
        device_profiles = sorted(
            (item for item in profiles if item.stable_device_id == stable_id),
            key=lambda item: item.profile_id,
        )
        profile = next(
            (
                item
                for item in device_profiles
                if item.profile_id == selected_profile_id
            ),
            device_profiles[0] if device_profiles else None,
        )
        direct = bool(
            profile is not None and profile.path is OutputPathPreference.HARDWARE_DIRECT
        )
        alsa = next(
            (
                binding
                for binding in snapshot.bindings
                if snapshot.available
                and binding.currently_available
                and binding.kind.value == "alsa_pcm"
            ),
            None,
        )
        if selected and reconnecting:
            status = "Selected · reconnecting"
        elif selected and not snapshot.available:
            status = "Selected · unavailable"
        elif selected and active:
            status = "Selected · Active"
        elif active:
            status = "In use"
        elif selected:
            status = "Selected · inactive"
        elif snapshot.available:
            status = "Available"
        else:
            status = "Disconnected"
        connection = "Available" if snapshot.available else "Disconnected"
        evidence = ()
        evidence_failed = False
        if self._qualification is not None and snapshot.available:
            try:
                evidence = self._qualification.cached_evidence_current(stable_id)
            except Exception:  # Diagnostics must not interrupt output state changes.
                evidence_failed = True
        if evidence_failed:
            evidence_label = "Evidence unavailable"
        elif any(item.supported is True for item in evidence):
            evidence_label = "Qualified"
        elif any(item.supported is False for item in evidence):
            evidence_label = "Unavailable"
        else:
            evidence_label = "Unknown" if snapshot.available else "Removed"
        environment = ""
        if self._qualification is not None and snapshot.available:
            try:
                environment = self._qualification.current_environment_fingerprint(
                    stable_id
                )
            except Exception:  # Diagnostics must never break the normal card.
                environment = ""
        active_truth = truth if active else None
        source_rate = (
            active_truth.decoded_runtime.pcm.rate_hz
            if active_truth is not None and active_truth.decoded_runtime is not None
            else 0
        )
        device_rate = (
            active_truth.device_negotiated.negotiated_pcm.rate_hz
            if active_truth is not None and active_truth.device_negotiated is not None
            else 0
        )
        graph = (
            active_truth.engine_effective.graph_factories
            if active_truth is not None and active_truth.engine_effective is not None
            else ()
        )
        return {
            "stableDeviceId": stable_id,
            "shortenedStableDeviceId": _short_id(stable_id),
            "displayName": "".join(identity_presentation),
            "manufacturer": identity.manufacturer or "",
            "product": identity.product or "",
            "available": snapshot.available,
            "selected": selected,
            "active": active,
            "reconnecting": selected and reconnecting,
            "connectionLabel": connection,
            "statusLabel": status,
            "identityConfidence": identity.confidence.value,
            "alsaLocator": alsa.locator if alsa is not None else "",
            "vendorId": identity.vendor_id or "",
            "productId": identity.product_id or "",
            "bcdDevice": identity.bcd_device or "",
            "generation": snapshot.generation,
            "bindingAvailable": alsa is not None,
            "profileId": profile.profile_id if profile is not None else "",
            "profileName": "Direct" if direct else ("Shared" if profile else ""),
            "transportMode": "direct" if direct else "shared",
            "transportLabel": "Direct" if direct else "Shared",
            "volumeLabel": self._volume_policy.volume_label if active else "",
            "signalTruthLabel": truth_label if active else "Not verified",
            "sourceRateLabel": _rate_label(source_rate),
            "deviceRateLabel": _rate_label(device_rate),
            "capabilityEvidenceLabel": evidence_label,
            "environmentFingerprint": environment,
            "runtimeSinkSummary": " → ".join(graph),
            "lastFailureCode": last_failure_code if selected else "",
            "lastFailureDetail": (
                self._output_session.last_cleanup_diagnostic.detail
                if selected
                and self._output_session is not None
                and self._output_session.last_cleanup_diagnostic is not None
                else ""
            ),
            "canSelect": snapshot.available,
            "isShared": False,
        }

    def _shared_row(self, *, selected: bool, active: bool, truth_label: str) -> dict:
        status = (
            "Selected · Active"
            if selected and active
            else "In use"
            if active
            else "Selected · inactive"
            if selected
            else "Available"
        )
        return {
            "stableDeviceId": "",
            "shortenedStableDeviceId": "",
            "displayName": "System Output",
            "manufacturer": "",
            "product": "",
            "available": True,
            "selected": selected,
            "active": active,
            "reconnecting": False,
            "connectionLabel": "Available",
            "statusLabel": status,
            "identityConfidence": "",
            "alsaLocator": "",
            "vendorId": "",
            "productId": "",
            "bcdDevice": "",
            "generation": 0,
            "bindingAvailable": True,
            "profileId": "",
            "profileName": "Shared",
            "transportMode": "shared",
            "transportLabel": "Shared",
            "volumeLabel": self._volume_policy.volume_label if active else "",
            "signalTruthLabel": truth_label,
            "sourceRateLabel": "—",
            "deviceRateLabel": "—",
            "capabilityEvidenceLabel": "Not applicable",
            "environmentFingerprint": "",
            "runtimeSinkSummary": "",
            "lastFailureCode": "",
            "lastFailureDetail": "",
            "canSelect": True,
            "isShared": True,
        }

    @staticmethod
    def _pcm_stage(title: str, pcm, *, detail: str = "") -> dict[str, Any]:
        if pcm is None:
            return {
                "title": title,
                "observed": False,
                "summary": "Not observed",
                "rateHz": 0,
                "format": "",
                "channels": 0,
                "significantBits": 0,
                "detail": detail,
            }
        summary = f"{pcm.transport_format or 'PCM'} · {_rate_label(pcm.rate_hz)}"
        return {
            "title": title,
            "observed": True,
            "summary": summary,
            "rateHz": pcm.rate_hz,
            "format": pcm.transport_format,
            "channels": pcm.channels,
            "significantBits": pcm.significant_bits or 0,
            "detail": detail,
        }

    def _signal_path(self, truth) -> list[dict[str, Any]]:
        if truth is None:
            return [
                self._pcm_stage(title, None)
                for title in ("Source", "Decoded", "Engine", "Device")
            ]
        source = truth.source_file_facts
        source_stage = self._pcm_stage(
            "Source",
            source.nominal_pcm if source is not None else None,
            detail=(
                " · ".join(
                    value
                    for value in (
                        source.container if source is not None else None,
                        source.codec if source is not None else None,
                    )
                    if value
                )
            ),
        )
        decoded_stage = self._pcm_stage(
            "Decoded",
            truth.decoded_runtime.pcm if truth.decoded_runtime is not None else None,
        )
        engine_stage = self._pcm_stage(
            "Engine",
            (
                truth.engine_effective.effective_pcm
                if truth.engine_effective is not None
                else None
            ),
            detail=(
                truth.engine_effective.sink_factory
                if truth.engine_effective is not None
                else ""
            ),
        )
        device_stage = self._pcm_stage(
            "Device",
            (
                truth.device_negotiated.negotiated_pcm
                if truth.device_negotiated is not None
                else None
            ),
            detail=(
                truth.device_negotiated.locator or ""
                if truth.device_negotiated is not None
                else ""
            ),
        )
        return [source_stage, decoded_stage, engine_stage, device_stage]

    @Slot()
    def refresh_devices(self) -> None:
        if self._refresh_devices is not None:
            self._refresh_devices()

    @Slot(str)
    def select_device(self, stable_device_id: str) -> None:
        self._run_action(
            lambda: (
                self._selection_coordinator.select_device(stable_device_id)
                if self._selection_coordinator is not None
                else self._missing_action()
            )
        )

    @Slot(str)
    def select_profile(self, profile_id: str) -> None:
        self._run_action(
            lambda: (
                self._selection_coordinator.select_profile(profile_id)
                if self._selection_coordinator is not None
                else self._missing_action()
            )
        )

    @Slot(str)
    def select_path_mode(self, mode: str) -> None:
        self._run_action(
            lambda: (
                self._selection_coordinator.select_path_mode(mode)
                if self._selection_coordinator is not None
                else self._missing_action()
            )
        )

    @Slot(str)
    def select_volume_mode(self, mode: str) -> None:
        self._run_action(
            lambda: (
                self._selection_coordinator.select_volume_mode(mode)
                if self._selection_coordinator is not None
                else self._missing_action()
            )
        )

    @Slot(int)
    def set_resync_delay_ms(self, value: int) -> None:
        self._run_action(
            lambda: (
                self._selection_coordinator.set_resync_delay_ms(value)
                if self._selection_coordinator is not None
                else self._missing_action()
            )
        )

    @Slot()
    def open_diagnostics(self) -> None:
        self.diagnostics_requested.emit()

    @Slot()
    def select_shared_output(self) -> None:
        self._run_action(
            lambda: (
                self._selection_coordinator.select_shared_output()
                if self._selection_coordinator is not None
                else self._missing_action()
            )
        )

    @staticmethod
    def _missing_action() -> None:
        raise AudioOutputSelectionError(
            "OUTPUT_SELECTION_UNAVAILABLE", "Output selection is unavailable."
        )

    def _run_action(self, action: Callable[[], None]) -> None:
        try:
            action()
        except AudioOutputSelectionError as exc:
            title, detail = failure_copy(exc.code)
            if not title:
                title, detail = "Output unavailable", exc.detail
            self._last_action_failure = (exc.code, title, detail)
            self._rebuild()
            self.state_changed.emit()
            self.action_failed.emit(exc.code, title, detail)
        else:
            if self._last_action_failure is not None:
                self._last_action_failure = None
                self._rebuild()
                self.state_changed.emit()

    def _get(self, key: str, fallback=None):
        return self._projection.get(key, fallback)

    devices = Property(
        list, lambda self: self._get("devices", []), notify=state_changed
    )
    profiles = Property(
        list, lambda self: self._get("profiles", []), notify=state_changed
    )
    selectedDeviceId = Property(
        str, lambda self: self._get("selectedDeviceId", ""), notify=state_changed
    )
    activeDeviceId = Property(
        str, lambda self: self._get("activeDeviceId", ""), notify=state_changed
    )
    selectedProfileId = Property(
        str, lambda self: self._get("selectedProfileId", ""), notify=state_changed
    )
    transportMode = Property(
        str, lambda self: self._get("transportMode", "shared"), notify=state_changed
    )
    selectedPathMode = Property(
        str, lambda self: self._get("selectedPathMode", "shared"), notify=state_changed
    )
    pathMode = Property(
        str, lambda self: self._get("pathMode", "shared"), notify=state_changed
    )
    availability = Property(
        bool, lambda self: self._get("availability", False), notify=state_changed
    )
    availabilityReason = Property(
        str,
        lambda self: self._get("availabilityReason", "Unknown"),
        notify=state_changed,
    )
    outputState = Property(
        str, lambda self: self._get("outputState", "idle"), notify=state_changed
    )
    volumeMode = Property(
        str, lambda self: self._get("volumeMode", "unknown"), notify=state_changed
    )
    volumeAdjustable = Property(
        bool, lambda self: self._get("volumeAdjustable", False), notify=state_changed
    )
    volumeLabel = Property(
        str,
        lambda self: self._get("volumeLabel", "Volume unavailable"),
        notify=state_changed,
    )
    signalTruthVerdict = Property(
        str,
        lambda self: self._get("signalTruthVerdict", "unknown"),
        notify=state_changed,
    )
    signalTruthLabel = Property(
        str,
        lambda self: self._get("signalTruthLabel", "Not verified"),
        notify=state_changed,
    )
    signalTruthSummary = Property(
        str,
        lambda self: self._get("signalTruthSummary", "Not verified"),
        notify=state_changed,
    )
    signalTruthReasonCodes = Property(
        list, lambda self: self._get("signalTruthReasonCodes", []), notify=state_changed
    )
    currentSourceRate = Property(
        int, lambda self: self._get("currentSourceRate", 0), notify=state_changed
    )
    currentDeviceRate = Property(
        int, lambda self: self._get("currentDeviceRate", 0), notify=state_changed
    )
    currentRateHz = Property(
        int, lambda self: self._get("currentRateHz", 0), notify=state_changed
    )
    currentFormat = Property(
        str, lambda self: self._get("currentFormat", ""), notify=state_changed
    )
    currentChannels = Property(
        int, lambda self: self._get("currentChannels", 0), notify=state_changed
    )
    significantBits = Property(
        int, lambda self: self._get("significantBits", 0), notify=state_changed
    )
    isDirect = Property(
        bool, lambda self: self._get("isDirect", False), notify=state_changed
    )
    isExclusiveObserved = Property(
        bool,
        lambda self: self._get("isExclusiveObserved", False),
        notify=state_changed,
    )
    isBusy = Property(
        bool, lambda self: self._get("isBusy", False), notify=state_changed
    )
    isReconnecting = Property(
        bool, lambda self: self._get("isReconnecting", False), notify=state_changed
    )
    signalPath = Property(
        list, lambda self: self._get("signalPath", []), notify=state_changed
    )
    reconnecting = Property(
        bool, lambda self: self._get("reconnecting", False), notify=state_changed
    )
    lastFailureCode = Property(
        str, lambda self: self._get("lastFailureCode", ""), notify=state_changed
    )
    lastFailureTitle = Property(
        str, lambda self: self._get("lastFailureTitle", ""), notify=state_changed
    )
    lastFailureDisplay = Property(
        str, lambda self: self._get("lastFailureDisplay", ""), notify=state_changed
    )
    canSelectDevice = Property(
        bool, lambda self: self._get("canSelectDevice", False), notify=state_changed
    )
    canUseDirect = Property(
        bool, lambda self: self._get("canUseDirect", False), notify=state_changed
    )
    outputTooltip = Property(
        str,
        lambda self: self._get("outputTooltip", "Audio output"),
        notify=state_changed,
    )
    diagnosticsAvailable = Property(
        bool,
        lambda self: self._get("diagnosticsAvailable", False),
        notify=state_changed,
    )
