"""DAC-V35-010 — AudioDeviceRegistry (spec §10 + §400).

Responsabilidades: recolectar observaciones, correlacionarlas, mantener
identidad estable, actualizar bindings, trackear availability,
re-scan generation-safe y preservar el intent seleccionado a través de
desconexiones.

NO es responsabilidad: probar formatos, elegir output profile, abrir
PCM, decidir GStreamer ni gestionar Queue.

Reglas §400 (seal pre-050):
- un DAC físico puede poseer CERO-O-MÁS endpoints ALSA actuales: la
  autoridad canónica los preserva TODOS (`bindings_for`), nunca trunca
  al primero;
- replug del mismo DAC -> mismo stable id cuando la evidencia lo permite;
- dos devices simultáneos idénticos (VID/PID) NO se fusionan sin
  evidencia de identidad confiable;
- la generation representa el SET canónico de bindings: cambia cuando el
  conjunto cambia (A->(), ()->A, A->B, (A)->(A,B), ...) y NO cambia si
  sólo cambia el orden incidental o nada cambia;
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

    def bindings_for(
        self, stable_device_id: str, kind: BindingKind | None = None
    ) -> tuple[AudioDeviceBinding, ...]: ...


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


def _binding_key(binding: AudioDeviceBinding) -> tuple:
    """Key semántico/determinista de un binding (nunca identidad de
    objeto)."""
    return (
        binding.kind.value,
        binding.locator,
        -1 if binding.card_index is None else binding.card_index,
        -1 if binding.pcm_device is None else binding.pcm_device,
        -1 if binding.pcm_subdevice is None else binding.pcm_subdevice,
        binding.currently_available,
    )


def _bindings_key(bindings: tuple[AudioDeviceBinding, ...]) -> tuple:
    """Key del SET canónico: el orden incidental no importa."""
    return tuple(sorted(_binding_key(b) for b in bindings))


@dataclass
class _DeviceRecord:
    stable_device_id: str
    identity: AudioDeviceIdentity
    available: bool
    generation: int
    bindings: tuple[AudioDeviceBinding, ...] = ()


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

    def generation_for(self, stable_device_id: str) -> int | None:
        record = self._records.get(stable_device_id)
        return record.generation if record is not None else None

    def bindings_for(
        self, stable_device_id: str, kind: BindingKind | None = None
    ) -> tuple[AudioDeviceBinding, ...]:
        """TODOS los bindings actuales del device (API canónica).

        Determinista: orden estable por kind/locator/card/pcm/subdevice.
        """
        record = self._records.get(stable_device_id)
        if record is None or not record.available:
            return ()
        if kind is None:
            return record.bindings
        return tuple(b for b in record.bindings if b.kind is kind)

    def binding_for(
        self, stable_device_id: str, kind: BindingKind
    ) -> AudioDeviceBinding | None:
        """Compatibilidad determinista: el PRIMER binding del kind.

        La API canónica que preserva TODOS los endpoints es
        `bindings_for()`.
        """
        bindings = self.bindings_for(stable_device_id, kind)
        return bindings[0] if bindings else None

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
        self._apply_observations(observations, reconcile=True)

    def handle_added(self, observation: DeviceObservation) -> None:
        """Re-add: comparte EXACTAMENTE la resolución canónica de ingest
        (mismo algoritmo de identidad), sin reconciliar terceros."""
        self._apply_observations((observation,), reconcile=False)

    def _apply_observations(
        self,
        observations: tuple[DeviceObservation, ...],
        *,
        reconcile: bool,
    ) -> None:
        usb = [o for o in observations if o.vendor_id and o.product_id]
        alsa = [o for o in observations if o.binding is not None]

        # seriales "útiles": los duplicados simultáneos dejan de serlo.
        serial_counts: dict[str, int] = {}
        for observation in usb:
            serial = _useful_serial(observation.serial)
            if serial is not None:
                serial_counts[serial] = serial_counts.get(serial, 0) + 1

        batch_ids: set[str] = set()
        seen_paths: set[str] = set()
        for observation in usb:
            if observation.physical_path:
                seen_paths.add(observation.physical_path)
            stable_id = self._identity_for(observation, serial_counts, batch_ids)
            self._records[stable_id] = self._publish(
                stable_id,
                observation,
                self._confidence_for(stable_id, observation, serial_counts),
                alsa,
            )

        # cards ALSA huérfanas (sin ancestro USB observado): identidad local.
        for observation in alsa:
            correlated = any(
                binding.locator == observation.binding.locator
                for record in self._records.values()
                for binding in record.bindings
            )
            if correlated:
                continue
            stable_id = f"local:{observation.binding.locator}"
            self._records[stable_id] = self._publish(
                stable_id, observation, IdentityConfidence.LOW, ()
            )

        if not reconcile:
            return
        # Reconcile: USB records que ya no se observan -> unavailable.
        for record in self._records.values():
            identity = record.identity
            if (
                identity.bus == "usb"
                and record.available
                and identity.physical_path not in seen_paths
            ):
                record.available = False
                if record.bindings:
                    record.bindings = ()
                    record.generation = self._next_generation()

    def _identity_for(
        self,
        observation: DeviceObservation,
        serial_counts: dict[str, int],
        batch_ids: set[str],
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
        if stable_id in batch_ids:
            # colisión DENTRO del batch (p.ej. mismo path reciclado).
            stable_id = f"{stable_id}#{len(batch_ids)}"
        batch_ids.add(stable_id)
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
        # TODOS los endpoints del mismo DAC físico (nunca break al primero).
        if observation.binding is not None:
            new_bindings: tuple[AudioDeviceBinding, ...] = (observation.binding,)
        elif observation.physical_path:
            new_bindings = tuple(
                card.binding
                for card in alsa
                if card.physical_path == observation.physical_path
            )
        else:
            new_bindings = ()
        new_bindings = tuple(sorted(new_bindings, key=_binding_key))

        # La generation representa el SET canónico de bindings.
        set_changed = previous is None or _bindings_key(
            previous.bindings
        ) != _bindings_key(new_bindings)
        generation = self._next_generation() if set_changed else previous.generation

        bindings = tuple(
            self._bindings_state(binding, generation) for binding in new_bindings
        )
        identity = AudioDeviceIdentity(
            stable_device_id=stable_id,
            vendor_id=observation.vendor_id,
            product_id=observation.product_id,
            serial=_useful_serial(observation.serial),
            manufacturer=observation.manufacturer,
            product=observation.product,
            physical_path=observation.physical_path,
            bus="usb" if observation.vendor_id else None,
            bcd_device=observation.bcd_device,
            confidence=confidence,
        )
        return _DeviceRecord(
            stable_device_id=stable_id,
            identity=identity,
            available=True,
            generation=generation,
            bindings=bindings,
        )

    def _bindings_state(
        self, binding: AudioDeviceBinding, generation: int
    ) -> AudioDeviceBinding:
        return AudioDeviceBinding(
            kind=binding.kind,
            locator=binding.locator,
            generation=generation,
            currently_available=True,
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
                record.bindings = ()
                record.generation = self._next_generation()

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
