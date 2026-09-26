"""DAC-V35-020 — DacQualificationService (spec §401).

Decide si un ExactProbeResult puede producir capability evidence:

    exact open + exact readback       -> supported=True,  OPENED
    rechazo exacto format/rate        -> supported=False, PROBED
    BUSY / REMOVED / TIMEOUT          -> supported=None
    permission/runtime/protocol error -> supported=None
    requested != negotiated           -> supported=None (negotiation_failed)

Nunca brute-force de matrices al startup (§14).
"""

from __future__ import annotations

import hashlib
import json
import platform
import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass

from michi.application.audio_output_ports import QualificationCachePort
from michi.domain.audio_device import AudioDeviceBinding
from michi.domain.audio_evidence import (
    CapabilityEvidence,
    EvidenceStrength,
    ExactProbeResult,
    PcmTuple,
)

SOURCE = "michi-alsa-probe"
ENVIRONMENT_FINGERPRINT_SCHEMA_VERSION = 2
QUALIFICATION_PROFILE_VERSION = "dac-v35-exact-open-v1"

_NEGATIVE_DISPOSITIONS = {"unsupported_format"}
# BUSY/REMOVED/TIMEOUT y fallos de entorno NUNCA son negativos (§12).


def _exact_match(requested: PcmTuple, negotiated: PcmTuple | None) -> bool:
    """El readback prueba el tuple exacto (rate/format/channels).

    significant_bits es diagnóstico del readback (sbits), no parte del
    pedido; compararlo contra None del requested sería falso negativo.
    """
    if negotiated is None:
        return False
    return (
        negotiated.rate_hz == requested.rate_hz
        and negotiated.transport_format == requested.transport_format
        and negotiated.channels == requested.channels
    )


@dataclass(frozen=True, slots=True)
class QualificationEnvironmentContext:
    """Canonical inputs that decide whether exact-open evidence is current."""

    stable_device_id: str
    usb_vendor_id: str | None
    usb_product_id: str | None
    usb_bcd_device: str | None
    usb_descriptor_sha256: str | None
    kernel_release: str
    snd_usb_audio_identity: str | None
    alsa_library_version: str | None
    gstreamer_version: str | None
    binding_topology_fingerprint: str
    qualification_profile_version: str = QUALIFICATION_PROFILE_VERSION

    @property
    def complete_for_current_evidence(self) -> bool:
        required = (
            self.stable_device_id,
            self.usb_vendor_id,
            self.usb_product_id,
            self.usb_bcd_device,
            self.usb_descriptor_sha256,
            self.kernel_release,
            self.snd_usb_audio_identity,
            self.alsa_library_version,
            self.gstreamer_version,
            self.binding_topology_fingerprint,
            self.qualification_profile_version,
        )
        return all(value is not None and value != "" for value in required)


@dataclass(frozen=True, slots=True)
class ExactQualificationOutcome:
    evidence: CapabilityEvidence
    disposition: str
    detail: str | None


def default_environment_context(
    stable_device_id: str = "environment:unbound",
) -> QualificationEnvironmentContext:
    """Best available host context when no device registry is supplied."""
    return QualificationEnvironmentContext(
        stable_device_id=stable_device_id,
        usb_vendor_id=None,
        usb_product_id=None,
        usb_bcd_device=None,
        usb_descriptor_sha256=None,
        kernel_release=platform.release(),
        snd_usb_audio_identity=None,
        alsa_library_version=None,
        gstreamer_version=None,
        binding_topology_fingerprint="topology:unbound",
    )


def default_environment_fingerprint(
    context: QualificationEnvironmentContext | None = None,
) -> str:
    """Versioned SHA-256 over canonical JSON; legacy strings never match."""
    material = asdict(context or default_environment_context())
    material["schema_version"] = ENVIRONMENT_FINGERPRINT_SCHEMA_VERSION
    canonical = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"qenv:v{ENVIRONMENT_FINGERPRINT_SCHEMA_VERSION}:sha256:{digest}"


def binding_topology_fingerprint(
    bindings: tuple[AudioDeviceBinding, ...],
) -> str:
    """Canonical endpoint-set hash; card renumber is ignored only with proof."""
    endpoints: list[dict[str, object]] = []
    for binding in bindings:
        endpoint: dict[str, object] = {"kind": binding.kind.value}
        if binding.stable_endpoint_signature is not None:
            endpoint["stable_endpoint_signature"] = binding.stable_endpoint_signature
        else:
            # Without a superior signature, retain all runtime identity inputs;
            # a renumber must invalidate rather than be guessed equivalent.
            endpoint.update(
                {
                    "locator": binding.locator,
                    "card_index": binding.card_index,
                    "pcm_device": binding.pcm_device,
                    "pcm_subdevice": binding.pcm_subdevice,
                }
            )
        endpoints.append(endpoint)
    canonical = json.dumps(
        sorted(endpoints, key=lambda item: json.dumps(item, sort_keys=True)),
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"topology:v1:sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"


class QualificationSingleFlightTimeoutError(RuntimeError):
    """A coalesced follower exceeded its wait while the leader is still alive.

    R1.3.1 §10/§12: a follower timeout must NEVER launch a second physical
    probe. The consumer receives a typed inconclusive timeout instead, and
    nothing is cached as capability.
    """

    code = "EXACT_QUALIFICATION_TIMEOUT"

    def __init__(self, key: tuple[object, ...]) -> None:
        super().__init__(
            "exact qualification is already running for this endpoint and tuple"
        )
        self.key = key


class QualificationSingleFlightIncompleteError(RuntimeError):
    """A coalesced flight ended without a result or a failure.

    R1.3.2 §24: a flight terminates in exactly SUCCESS(result) or
    FAILURE(error). An accidental ``None`` must never reach a consumer.
    """

    code = "EXACT_QUALIFICATION_INCONCLUSIVE"

    def __init__(self, key: tuple[object, ...]) -> None:
        super().__init__("exact qualification produced no terminal outcome")
        self.key = key


class _Flight:
    """One in-flight qualification shared by equivalent concurrent callers.

    The terminal outcome is exactly one of: a result, or the leader's failure.
    Followers observe the SAME semantic failure — never an accidental ``None``.
    """

    __slots__ = ("event", "result", "error", "waiters")

    def __init__(self) -> None:
        self.event = threading.Event()
        self.result: object | None = None
        self.error: BaseException | None = None
        self.waiters = 0


class DacQualificationService:
    def __init__(
        self,
        adapter: object,
        *,
        cache: QualificationCachePort | None = None,
        environment_fingerprint: Callable[[], str] | None = None,
        environment_context: (
            Callable[[str], QualificationEnvironmentContext] | None
        ) = None,
        clock: Callable[[], int] = time.monotonic_ns,
        single_flight_timeout_s: float = 30.0,
    ) -> None:
        if environment_fingerprint is not None and environment_context is not None:
            raise ValueError(
                "environment_fingerprint and environment_context are mutually exclusive"
            )
        self._adapter = adapter
        self._cache = cache
        self._environment_fingerprint = environment_fingerprint
        self._environment_context = environment_context
        self._clock = clock
        self._single_flight_timeout_s = single_flight_timeout_s
        # DAC-V35-100R1.3 §11: equivalent concurrent qualifications coalesce
        # into exactly ONE physical probe. No thread is killed and no ALSA
        # call is cancelled; only duplicate consumers are merged.
        self._flight_lock = threading.Lock()
        self._flights: dict[tuple[object, ...], _Flight] = {}

    def _single_flight(self, key: tuple[object, ...], probe: Callable[[], object]):
        """Run ``probe`` once for every equivalent concurrent caller.

        Invariant (R1.3.1 §10): AT MOST ONE physical probe may be running for
        one key. A follower whose wait expires receives a typed timeout — it
        never becomes a second physical leader while the original probe is
        still alive, and no thread is killed or cancelled.
        """
        with self._flight_lock:
            flight = self._flights.get(key)
            if flight is None:
                flight = _Flight()
                self._flights[key] = flight
                leader = True
            else:
                flight.waiters += 1
                leader = False
        if leader:
            try:
                result = probe()
            except BaseException as exc:
                # R1.3.2 §25: the leader's failure is the flight's terminal
                # outcome, so every joined consumer observes it coherently.
                with self._flight_lock:
                    flight.error = exc
                    flight.event.set()
                    if flight.waiters == 0:
                        self._flights.pop(key, None)
                raise
            if result is None:
                incomplete = QualificationSingleFlightIncompleteError(key)
                with self._flight_lock:
                    flight.error = incomplete
                    flight.event.set()
                    if flight.waiters == 0:
                        self._flights.pop(key, None)
                raise incomplete
            with self._flight_lock:
                flight.result = result
                flight.event.set()
                if flight.waiters == 0:
                    self._flights.pop(key, None)
            return result
        if not flight.event.wait(timeout=self._single_flight_timeout_s):
            with self._flight_lock:
                flight.waiters -= 1
                if flight.waiters == 0 and flight.result is None:
                    # The leader is still alive: keep the flight registered so
                    # a future consumer still coalesces onto it.
                    pass
            raise QualificationSingleFlightTimeoutError(key)
        with self._flight_lock:
            result = flight.result
            error = flight.error
            flight.waiters -= 1
            if flight.waiters == 0:
                self._flights.pop(key, None)
        if error is not None:
            raise error
        if result is None:
            # Defensive: a flight must never publish an accidental None.
            raise QualificationSingleFlightIncompleteError(key)
        return result

    # ── C07: la mutación de la cache es autoridad de ESTE servicio ────
    def cache_evidence(
        self, stable_device_id: str, evidence: tuple[CapabilityEvidence, ...]
    ) -> None:
        if self._cache is None:
            raise RuntimeError("qualification cache no configurada")
        self._cache.replace_qualification_cache(stable_device_id, evidence)

    def cached_evidence(self, stable_device_id: str) -> tuple[CapabilityEvidence, ...]:
        if self._cache is None:
            return ()
        return self._cache.load_qualification_cache(stable_device_id)

    def cached_evidence_current(
        self, stable_device_id: str
    ) -> tuple[CapabilityEvidence, ...]:
        """Return only cache evidence valid for the current environment."""
        if self._environment_fingerprint is None:
            context = (
                self._environment_context(stable_device_id)
                if self._environment_context is not None
                else default_environment_context(stable_device_id)
            )
            if not context.complete_for_current_evidence:
                return ()
            fingerprint = default_environment_fingerprint(context)
        else:
            fingerprint = self.current_environment_fingerprint(stable_device_id)
        return tuple(
            item
            for item in self.cached_evidence(stable_device_id)
            if item.environment_fingerprint == fingerprint
        )

    def current_environment_context(
        self, stable_device_id: str
    ) -> QualificationEnvironmentContext:
        """Return the exact context used for environment-scoped qualification.

        Evidence tooling must never call ``default_environment_fingerprint()``
        without this device-bound context and then label the result physical.
        """
        if self._environment_context is not None:
            return self._environment_context(stable_device_id)
        return default_environment_context(stable_device_id)

    def current_environment_fingerprint(self, stable_device_id: str) -> str:
        if self._environment_fingerprint is not None:
            return self._environment_fingerprint()
        return default_environment_fingerprint(
            self.current_environment_context(stable_device_id)
        )

    def qualify_and_cache(
        self,
        *,
        stable_device_id: str,
        locator: str,
        rate_hz: int,
        transport_format: str,
        channels: int,
    ) -> CapabilityEvidence:
        """Probe exacto + cache SOLO de resultados concluyentes.

        La ambigüedad (BUSY/REMOVED/TIMEOUT/entorno) nunca se cachea como
        claim (§0I/§12).
        """
        return self.qualify_for_play(
            stable_device_id=stable_device_id,
            locator=locator,
            rate_hz=rate_hz,
            transport_format=transport_format,
            channels=channels,
        ).evidence

    def qualify_for_play(
        self,
        *,
        stable_device_id: str,
        locator: str,
        rate_hz: int,
        transport_format: str,
        channels: int,
    ) -> ExactQualificationOutcome:
        """Qualify and cache one current Play tuple."""
        outcome = self.probe_for_play(
            stable_device_id=stable_device_id,
            locator=locator,
            rate_hz=rate_hz,
            transport_format=transport_format,
            channels=channels,
        )
        self.cache_conclusive_evidence(outcome.evidence)
        return outcome

    def probe_for_play(
        self,
        *,
        stable_device_id: str,
        locator: str,
        rate_hz: int,
        transport_format: str,
        channels: int,
        binding_generation: int | None = None,
    ) -> ExactQualificationOutcome:
        """Probe without cache mutation; owner revalidation decides commit.

        Equivalent concurrent requests coalesce into ONE physical probe. The
        flight key represents the exact endpoint AND request (R1.3.1 §11):
        device + binding generation + locator + environment + exact tuple.
        """
        environment_before = self.current_environment_fingerprint(stable_device_id)
        key = (
            stable_device_id,
            binding_generation,
            locator,
            environment_before,
            rate_hz,
            transport_format,
            channels,
        )

        def probe() -> ExactQualificationOutcome:
            result: ExactProbeResult = self._adapter.probe_exact(
                locator=locator,
                rate_hz=rate_hz,
                transport_format=transport_format,
                channels=channels,
            )
            evidence = self.evidence_from(result, stable_device_id=stable_device_id)
            environment_after = self.current_environment_fingerprint(stable_device_id)
            if environment_after != environment_before:
                evidence = CapabilityEvidence(
                    stable_device_id=evidence.stable_device_id,
                    tuple=evidence.tuple,
                    supported=None,
                    strength=EvidenceStrength.PROBED,
                    source=evidence.source,
                    observed_at_ns=evidence.observed_at_ns,
                    environment_fingerprint=environment_after,
                    evidence_refs=(
                        *evidence.evidence_refs,
                        "environment_changed",
                    ),
                )
            return ExactQualificationOutcome(
                evidence, result.disposition, result.detail
            )

        return self._single_flight(key, probe)

    def cache_conclusive_evidence(self, evidence: CapabilityEvidence) -> None:
        """Merge one conclusive tuple after its continuation is current."""
        if evidence.supported is not None and self._cache is not None:
            key = (
                evidence.environment_fingerprint,
                evidence.tuple.rate_hz,
                evidence.tuple.transport_format,
                evidence.tuple.channels,
            )
            retained = tuple(
                item
                for item in self.cached_evidence(evidence.stable_device_id)
                if (
                    item.environment_fingerprint,
                    item.tuple.rate_hz,
                    item.tuple.transport_format,
                    item.tuple.channels,
                )
                != key
            )
            self._cache.replace_qualification_cache(
                evidence.stable_device_id, (*retained, evidence)
            )

    def qualify_exact(
        self,
        *,
        stable_device_id: str,
        locator: str,
        rate_hz: int,
        transport_format: str,
        channels: int,
    ) -> CapabilityEvidence:
        result: ExactProbeResult = self._adapter.probe_exact(
            locator=locator,
            rate_hz=rate_hz,
            transport_format=transport_format,
            channels=channels,
        )
        return self.evidence_from(result, stable_device_id=stable_device_id)

    def evidence_from(
        self, result: ExactProbeResult, *, stable_device_id: str
    ) -> CapabilityEvidence:
        requested = result.requested
        exact = _exact_match(requested, result.negotiated)
        if result.disposition == "OPENED" and exact:
            # C05: se preserva el sbits NEGOCIADO (readback real), no el pedido.
            proven = PcmTuple(
                rate_hz=requested.rate_hz,
                transport_format=requested.transport_format,
                channels=requested.channels,
                significant_bits=(
                    result.negotiated.significant_bits
                    if result.negotiated is not None
                    else None
                ),
            )
            return self._evidence(
                stable_device_id,
                proven,
                supported=True,
                strength=EvidenceStrength.OPENED,
                evidence_ref=result.evidence_ref,
            )
        if result.disposition in _NEGATIVE_DISPOSITIONS:
            # Solo un rechazo exacto documentado produce evidencia negativa.
            return self._evidence(
                stable_device_id,
                requested,
                supported=False,
                strength=EvidenceStrength.PROBED,
                evidence_ref=result.evidence_ref,
            )
        # BUSY/REMOVED/TIMEOUT/permission/runtime/protocol: sin claim.
        return self._evidence(
            stable_device_id,
            requested,
            supported=None,
            strength=EvidenceStrength.PROBED,
            evidence_ref=result.evidence_ref,
        )

    def _evidence(
        self,
        stable_device_id: str,
        pcm_tuple: PcmTuple,
        *,
        supported: bool | None,
        strength: EvidenceStrength,
        evidence_ref: str,
    ) -> CapabilityEvidence:
        return CapabilityEvidence(
            stable_device_id=stable_device_id,
            tuple=pcm_tuple,
            supported=supported,
            strength=strength,
            source=SOURCE,
            observed_at_ns=self._clock(),
            environment_fingerprint=self.current_environment_fingerprint(
                stable_device_id
            ),
            evidence_refs=(evidence_ref,),
        )
