"""DAC-V35-010 — AudioDeviceRegistry (spec §10 + §400).

Responsabilidades: recolectar observaciones, correlacionarlas, mantener
identidad estable, actualizar bindings, trackear availability,
re-scan generation-safe y preservar el intent seleccionado a través de
desconexiones.

NO es responsabilidad: probar formatos, elegir output profile, abrir
PCM, decidir GStreamer ni gestionar Queue.

Reglas §400:
- replug del mismo DAC -> mismo stable id cuando la evidencia lo permite;
- dos devices simultáneos idénticos (VID/PID) NO se fusionan sin
  evidencia de identidad confiable;
- renumber de card -> stable id preservado, binding actualizado;
- remove -> unavailable SIN borrar el intent seleccionado;
- observación/probe tardío con generation vieja -> STALE, descartado.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from michi.domain.audio_device import (
    AudioDeviceBinding,
    AudioDeviceIdentity,
    BindingKind,
    DeviceObservation,
    IdentityConfidence,
)


class AudioDeviceRegistryPort(Protocol):
    def snapshot(self) -> tuple[AudioDeviceIdentity, ...]: ...

    def binding_for(
        self, stable_device_id: str, kind: BindingKind
    ) -> AudioDeviceBinding | None: ...


def _useful_serial(serial: str | None) -> str | None:
    """Seriales vacíos/genéricos no identifican (§7)."""
    if serial is None:
        return None
    value = serial.strip()
    if not value:
        return None
    if set(value) <= {"0"}:  # 00000000
        return None
    if len(set(value)) <= 1:  # aaaa, 1111
        return None
    return value


@dataclass
class _DeviceRecord:
    stable_device_id: str
    identity: AudioDeviceIdentity
    available: bool
    generation: int
    binding: AudioDeviceBinding | None = None


class AudioDeviceRegistry:
    """Registry canónico de devices de audio físicos."""

    def __init__(self) -> None:
        self._records: dict[str, _DeviceRecord] = {}
        self._generation = 0
        self._selected_device_id: str | None = None

    # ── lectura ───────────────────────────────────────────────────────
    @property
    def generation(self) -> int:
        return self._generation

    @property
    def selected_device_id(self) -> str | None:
        return self._selected_device_id

    def select_device(self, stable_device_id: str) -> None:
        """El intent seleccionado es SEPARADO de la availability (§400)."""
        self._selected_device_id = stable_device_id

    def snapshot(self) -> tuple[AudioDeviceIdentity, ...]:
        return tuple(
            record.identity
            for record in sorted(
                self._records.values(), key=lambda r: r.stable_device_id
            )
            if record.available
        )

    def binding_for(
        self, stable_device_id: str, kind: BindingKind
    ) -> AudioDeviceBinding | None:
        record = self._records.get(stable_device_id)
        if record is None or not record.available or record.binding is None:
            return None
        if record.binding.kind is not kind:
            return None
        return record.binding

    def available_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(r.stable_device_id for r in self._records.values() if r.available)
        )

    # ── observaciones ─────────────────────────────────────────────────
    def ingest(self, observations: tuple[DeviceObservation, ...]) -> None:
        """Re-scan completo: correlaciona USB y ALSA y publica identidad.

        La identidad se decide SOLO aquí, con la evidencia de TODOS los
        device simultáneos (nunca por un serial duplicado, §7). Los
        devices antes observados que ya no aparecen quedan unavailable
        (reconcile generation-safe).
        """
        usb = [o for o in observations if o.vendor_id and o.product_id]
        alsa = [o for o in observations if o.binding is not None]

        # seriales "útiles": los duplicados simultáneos dejan de serlo.
        serial_counts: dict[str, int] = {}
        for observation in usb:
            serial = _useful_serial(observation.serial)
            if serial is not None:
                serial_counts[serial] = serial_counts.get(serial, 0) + 1

        seen_ids: set[str] = set()
        seen_paths: set[str] = set()
        for observation in usb:
            if observation.physical_path:
                seen_paths.add(observation.physical_path)
            stable_id = self._identity_for(observation, serial_counts, seen_ids)
            self._records[stable_id] = self._publish(
                stable_id,
                observation,
                self._confidence_for(stable_id, observation, serial_counts),
                alsa,
            )

        # cards ALSA huérfanas (sin ancestro USB observado): identidad local.
        for observation in alsa:
            correlated = any(
                record.binding is not None
                and record.binding.locator == observation.binding.locator
                for record in self._records.values()
            )
            if correlated:
                continue
            stable_id = f"local:{observation.binding.locator}"
            self._records[stable_id] = self._publish(
                stable_id, observation, IdentityConfidence.LOW, ()
            )

        # Reconcile: USB records que ya no se observan -> unavailable.
        for record in self._records.values():
            identity = record.identity
            if (
                identity.bus == "usb"
                and record.available
                and identity.physical_path not in seen_paths
            ):
                record.available = False
                record.generation = self._next_generation()
                if record.binding is not None:
                    record.binding = self._binding_state(
                        record.binding, record.generation, available=False
                    )

    def _identity_for(
        self,
        observation: DeviceObservation,
        serial_counts: dict[str, int],
        seen_ids: set[str],
    ) -> str:
        serial = _useful_serial(observation.serial)
        if serial is not None and serial_counts.get(serial, 0) > 1:
            serial = None  # serial duplicado simultáneo: no identifica
        if serial is not None:
            stable_id = f"usb:{observation.vendor_id}:{observation.product_id}:{serial}"
        elif observation.physical_path:
            stable_id = (
                f"usb:{observation.vendor_id}:{observation.product_id}:"
                f"{observation.physical_path}"
            )
        else:
            stable_id = f"sysfs:{observation.product or 'usb'}"
        if stable_id in seen_ids:
            # colisión (p.ej. mismo path reciclado): determinístico.
            stable_id = f"{stable_id}#{len(seen_ids)}"
        seen_ids.add(stable_id)
        return stable_id

    def _confidence_for(
        self,
        stable_id: str,
        observation: DeviceObservation,
        serial_counts: dict[str, int],
    ) -> IdentityConfidence:
        serial = _useful_serial(observation.serial)
        if serial is not None and serial_counts.get(serial, 0) <= 1:
            return IdentityConfidence.HIGH
        if "#" in stable_id:
            return IdentityConfidence.AMBIGUOUS
        if observation.physical_path:
            return IdentityConfidence.MEDIUM
        return IdentityConfidence.LOW

    def _publish(
        self,
        stable_id: str,
        observation: DeviceObservation,
        confidence: IdentityConfidence,
        alsa: list[DeviceObservation],
    ) -> _DeviceRecord:
        previous = self._records.get(stable_id)
        generation = previous.generation if previous else self._next_generation()
        binding: AudioDeviceBinding | None = None
        if observation.binding is not None:
            binding = self._bind(observation.binding, generation)
        elif observation.physical_path:
            for card in alsa:
                if card.physical_path == observation.physical_path:
                    binding = self._bind(card.binding, generation)
                    break
        if (
            previous is not None
            and previous.binding is not None
            and binding is not None
        ):
            old, new = previous.binding, binding
            if (
                old.locator != new.locator
                or old.card_index != new.card_index
                or old.pcm_device != new.pcm_device
            ):
                # Rebind (p.ej. renumber de card): generation nueva (§400).
                generation = self._next_generation()
                binding = self._bind(binding, generation)
        identity = AudioDeviceIdentity(
            stable_device_id=stable_id,
            vendor_id=observation.vendor_id,
            product_id=observation.product_id,
            serial=_useful_serial(observation.serial),
            manufacturer=observation.manufacturer,
            product=observation.product,
            physical_path=observation.physical_path,
            bus="usb" if observation.vendor_id else None,
            confidence=confidence,
        )
        return _DeviceRecord(
            stable_device_id=stable_id,
            identity=identity,
            available=True,
            generation=generation,
            binding=binding,
        )

    def _bind(self, binding: AudioDeviceBinding, generation: int) -> AudioDeviceBinding:
        return self._binding_state(binding, generation, available=True)

    def _binding_state(
        self,
        binding: AudioDeviceBinding,
        generation: int,
        *,
        available: bool,
    ) -> AudioDeviceBinding:
        return AudioDeviceBinding(
            kind=binding.kind,
            locator=binding.locator,
            generation=generation,
            currently_available=available,
            card_index=binding.card_index,
            pcm_device=binding.pcm_device,
            pcm_subdevice=binding.pcm_subdevice,
        )

    def _next_generation(self) -> int:
        self._generation += 1
        return self._generation

    # ── topología ─────────────────────────────────────────────────────
    def handle_removed(self, physical_path: str) -> None:
        """Remove físico: unavailable, generation++, intent PRESERVADO."""
        for record in self._records.values():
            identity = record.identity
            if identity.physical_path == physical_path and record.available:
                record.available = False
                record.generation = self._next_generation()
                if record.binding is not None:
                    record.binding = self._binding_state(
                        record.binding, record.generation, available=False
                    )

    def handle_added(self, observation: DeviceObservation) -> None:
        """Re-add: la identidad se re-resuelve (mismo id si la evidencia
        lo permite) con generation nueva. Sin reconcile de terceros."""
        serial_counts: dict[str, int] = {}
        serial = _useful_serial(observation.serial)
        if serial is not None:
            serial_counts[serial] = 1
        seen_ids: set[str] = set(self._records)
        stable_id = self._identity_for(observation, serial_counts, seen_ids)
        self._records[stable_id] = self._publish(
            stable_id,
            observation,
            self._confidence_for(stable_id, observation, serial_counts),
            [],
        )

    # ── generation-safety ─────────────────────────────────────────────
    def apply_probe_result(
        self, stable_device_id: str, generation: int, *, payload: object = None
    ) -> bool:
        """Callback async: si la generation cambió, se descarta (STALE) y
        NO se muta estado. Devuelve True si fue aceptado."""
        record = self._records.get(stable_device_id)
        if record is None:
            return False
        # El probe en sí pertenece a DAC-V35-020; aquí solo la guardia.
        return generation == record.generation
