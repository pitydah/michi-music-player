"""Player-facing composition root (C9/C10 + E).

ONE host-facing boundary: the host injects real adapters and receives
constructed runtime objects with explicit ownership. This module contains NO
Player imports, NO harness and NO repository-relative paths — the only
filesystem input is the host-provided Home state dir (XDG product path).

Ownership (E):

    EcosystemRuntime
        factory   -> FactoryRuntime(service, bridge, orchestrator)
                      (the bridge owns the QObject lifetime)
        home      -> HomeRuntime(keystore, profiles, authority, roster,
                                 revocations, backup, enrollment, recreate)
        registry  -> canonical Device Registry (one device, many evidence sources)
        account   -> local human OWNER (optional)
        home      -> Michi Home authority/runtime (optional)
        stream    -> normal Music Stream lifecycle, factory kept separate
        HA        -> opt-in external automation adapter (optional)
        discovery -> DiscoveryService | None
        playback  -> RemoteMicroServerPlaybackEndpoint | None

The host never manufactures internal repositories: the root owns the wiring.
"""

from __future__ import annotations

import contextlib
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from michi_ecosystem.application.capability_resolution import Operation
from michi_ecosystem.application.device_registry_service import (
    DeviceRegistryService,
    DeviceSource,
)
from michi_ecosystem.application.discovery_runner import DiscoveryRunner
from michi_ecosystem.application.discovery_service import DiscoveryService
from michi_ecosystem.application.ecosystem_doctor import EcosystemDoctor
from michi_ecosystem.application.ecosystem_service import EcosystemDashboardService
from michi_ecosystem.application.factory_recreate import FactoryRecreateService
from michi_ecosystem.application.home_assistant_service import HomeAssistantService
from michi_ecosystem.application.home_authority import (
    HomeAuthorityService,
    HomeSecurityError,
)
from michi_ecosystem.application.home_backup import HomeBackupService
from michi_ecosystem.application.home_enrollment import HomeEnrollmentService
from michi_ecosystem.application.local_account_service import (
    LocalAccountError,
    LocalAccountService,
)
from michi_ecosystem.application.operation_history import OperationHistory
from michi_ecosystem.application.spaces_service import SpacesService
from michi_ecosystem.application.stream_factory_orchestrator import (
    StreamFactoryOrchestrator,
)
from michi_ecosystem.application.stream_factory_service import (
    StreamFactoryService,
)
from michi_ecosystem.application.stream_management_service import (
    StreamManagementService,
)
from michi_ecosystem.domain.device_registry import (
    DeviceCapability,
    DeviceDescriptor,
    DeviceType,
    HomeMembershipState,
    canonical_id_for,
)
from michi_ecosystem.domain.home import MichiHomeProfile
from michi_ecosystem.infrastructure.account import SqliteLocalAccountRepository
from michi_ecosystem.infrastructure.home.keystore import (
    XdgHomeKeyStore,
    XdgHomeProfileRepository,
)
from michi_ecosystem.infrastructure.home.recreate_transaction import (
    FactoryRecreateStore,
)
from michi_ecosystem.infrastructure.home.roster import (
    SqliteDeviceRosterRepository,
    SqliteRevocationRepository,
)
from michi_ecosystem.infrastructure.micro_server.playback_endpoint import (
    RemoteMicroServerPlaybackEndpoint,
)
from michi_ecosystem.infrastructure.spaces import SqliteSpacesStore
from michi_ecosystem.ports.device_identity import DeviceIdentityProviderPort
from michi_ecosystem.ports.discovery import DiscoverySourcePort
from michi_ecosystem.ports.firmware_catalog import FirmwareCatalogPort
from michi_ecosystem.ports.flash_backend import FlashBackendPort
from michi_ecosystem.ports.home import MembershipIssuerPort
from michi_ecosystem.ports.home_automation import (
    HomeAutomationPort,
    HomeAutomationSettingsPort,
)
from michi_ecosystem.ports.installation_detector import InstallationDetectorPort
from michi_ecosystem.ports.serial_devices import SerialDevicesPort
from michi_ecosystem.ports.stream import StreamManagementCommandPort
from michi_ecosystem.presentation.ecosystem_bridge import EcosystemBridge
from michi_ecosystem.presentation.ecosystem_operations_bridge import (
    EcosystemOperationsBridge,
)
from michi_ecosystem.presentation.home_assistant_bridge import HomeAssistantBridge
from michi_ecosystem.presentation.home_bridge import HomeBridge
from michi_ecosystem.presentation.local_account_bridge import LocalAccountBridge
from michi_ecosystem.presentation.stream_device_bridge import StreamDeviceBridge
from michi_ecosystem.presentation.stream_factory_bridge import (
    StreamFactoryBridge,
)

HOME_STATE_DB = "home-state.db"


class EcosystemBusyError(RuntimeError):
    """Runtime shutdown refused: an operation is still active."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def _descriptor_from_roster(entry, home_id: str) -> DeviceDescriptor:
    """Project Home roster evidence into the neutral Device Registry model."""
    from michi_ecosystem.domain.home import DeviceRole, MembershipStatus

    roles = set(entry.roles)
    if DeviceRole.AUDIO_RECEIVER in roles:
        device_type = DeviceType.MUSIC_STREAM
    elif DeviceRole.MOBILE_PLAYER in roles or DeviceRole.SYNC_CLIENT in roles:
        device_type = DeviceType.MOBILE
    elif DeviceRole.MUSIC_SERVER in roles or DeviceRole.PLAYBACK_HOST in roles:
        device_type = DeviceType.MICRO_SERVER
    elif DeviceRole.DESKTOP_PLAYER in roles:
        device_type = DeviceType.DESKTOP_PLAYER
    else:
        device_type = DeviceType.UNKNOWN

    membership = {
        MembershipStatus.ACTIVE: HomeMembershipState.ACTIVE,
        MembershipStatus.REVOKED: HomeMembershipState.REVOKED,
        MembershipStatus.PENDING: HomeMembershipState.PENDING,
        MembershipStatus.REPLACEMENT_PENDING: HomeMembershipState.PENDING,
        MembershipStatus.REPLACED: HomeMembershipState.REVOKED,
        MembershipStatus.ABORTED: HomeMembershipState.REVOKED,
        MembershipStatus.EXPIRED: HomeMembershipState.REVOKED,
    }.get(entry.status, HomeMembershipState.NONE)

    capabilities: set[DeviceCapability] = {DeviceCapability.DIAGNOSTICS}
    if DeviceRole.AUDIO_RECEIVER in roles:
        capabilities.update(
            {
                DeviceCapability.PLAYBACK_ENDPOINT,
                DeviceCapability.FACTORY_RECREATE,
                DeviceCapability.HOME_ASSISTANT_EXPOSABLE,
            }
        )
    if DeviceRole.MOBILE_PLAYER in roles:
        capabilities.add(DeviceCapability.PLAYBACK_ENDPOINT)
    if DeviceRole.REMOTE_CONTROLLER in roles:
        capabilities.add(DeviceCapability.REMOTE_CONTROLLER)
    if DeviceRole.SYNC_CLIENT in roles:
        capabilities.update(
            {
                DeviceCapability.CONTENT_SYNC,
                DeviceCapability.STORAGE_TARGET,
            }
        )
    if DeviceRole.MUSIC_SERVER in roles or DeviceRole.PLAYBACK_HOST in roles:
        capabilities.update(
            {
                DeviceCapability.PLAYBACK_ENDPOINT,
                DeviceCapability.REMOTE_CONTROLLER,
                DeviceCapability.HOME_ASSISTANT_EXPOSABLE,
            }
        )

    return DeviceDescriptor(
        canonical_id=canonical_id_for(michi_id=entry.device_michi_id),
        michi_id=entry.device_michi_id,
        name=entry.device_name,
        type=device_type,
        michi_home_id=home_id,
        home_membership=membership,
        capabilities=frozenset(capabilities),
    )


def _active_stream_devices(roster) -> list[dict]:
    """ACTIVE Music Stream devices for the recreate picker (B3)."""
    from michi_ecosystem.domain.home import DeviceRole, MembershipStatus

    if roster is None:
        return []
    return [
        {"id": entry.device_michi_id, "name": entry.device_name}
        for entry in roster.list_entries()
        if entry.status is MembershipStatus.ACTIVE
        and DeviceRole.AUDIO_RECEIVER in entry.roles
    ]


@dataclass(frozen=True)
class FactoryEnvironment:
    """Real factory adapters supplied by the host."""

    serial: SerialDevicesPort
    catalog: FirmwareCatalogPort
    backend: FlashBackendPort
    installation_detector: InstallationDetectorPort
    acquisition: object | None = None
    developer_mode: bool = False  # explicit; never a product default
    # I2: MICHI-F1 v1 cannot carry identity/Home. Only an explicit lab flag
    # enables the partial Home bootstrap (never ACTIVE, pending confirmation).
    allow_partial_home_bootstrap: bool = False


@dataclass(frozen=True)
class HomeEnvironment:
    """Home runtime rooted at a host-provided (XDG product) path (E1).

    The composition root owns every internal repository; the host only
    provides the state directory and optional external ports (membership
    issuer waits for Michi Link v3; the identity provider is provisional).
    """

    state_dir: Path
    issuer: MembershipIssuerPort | None = None
    identity_provider: DeviceIdentityProviderPort | None = None


@dataclass(frozen=True)
class AccountEnvironment:
    """Local human account persistence rooted at $XDG_DATA_HOME/michi/account."""

    state_dir: Path


@dataclass(frozen=True)
class HomeContext:
    """Active Home wiring (P0): rebuilt by the manager, never stale."""

    profile: MichiHomeProfile | None
    roster: SqliteDeviceRosterRepository | None
    revocations: SqliteRevocationRepository | None
    backup: HomeBackupService
    enrollment: HomeEnrollmentService | None
    recreate: FactoryRecreateService | None
    recreate_store: FactoryRecreateStore | None = None

    def close(self) -> None:
        """Deterministic cleanup (§12): never rely on garbage collection."""
        for resource in (self.roster, self.revocations, self.recreate_store):
            if resource is not None:
                resource.close()


class HomeRuntimeManager:
    """Stable Home runtime surviving create/restore/lock/unlock (P0).

    Bridges and the factory orchestrator hold PROVIDERS into this manager,
    so a Home created or restored mid-session becomes visible without
    rebuilding the runtime or restarting the application.
    """

    def __init__(
        self,
        *,
        state_dir: Path,
        issuer: MembershipIssuerPort | None = None,
        identity_provider: DeviceIdentityProviderPort | None = None,
        registry: DeviceRegistryService | None = None,
    ) -> None:
        self._context_lock = threading.Lock()
        self._leases = 0
        self._structural_active = False
        self._retired: list[HomeContext] = []
        self._state_dir = Path(state_dir)
        self._issuer = issuer
        self._identity_provider = identity_provider
        self._registry = registry
        self.keystore = XdgHomeKeyStore(self._state_dir)
        self.profiles = XdgHomeProfileRepository(self._state_dir)
        self.authority = HomeAuthorityService(
            keystore=self.keystore, profiles=self.profiles
        )
        self._context = self._build_context()
        self.sync_registry()
        self.bridge = HomeBridge(
            authority=self.authority,
            profiles=self.profiles,
            backup=lambda: self._context.backup,
            roster=lambda: self._context.roster,
            revocations=lambda: self._context.revocations,
            context_changed=self.refresh,
            empty_restore=self.restore_into_empty,
            operation_busy_provider=lambda: self.has_active_leases,
            structural_begin=self.begin_structural_mutation,
            structural_end=self.end_structural_mutation,
        )

    @property
    def profile(self) -> MichiHomeProfile | None:
        return self._context.profile

    @property
    def roster(self) -> SqliteDeviceRosterRepository | None:
        return self._context.roster

    @property
    def revocations(self) -> SqliteRevocationRepository | None:
        return self._context.revocations

    @property
    def backup(self) -> HomeBackupService:
        return self._context.backup

    @property
    def enrollment(self) -> HomeEnrollmentService | None:
        return self._context.enrollment

    @property
    def recreate(self) -> FactoryRecreateService | None:
        return self._context.recreate

    def begin_structural_mutation(self) -> None:
        """Reserve the EXCLUSIVE Home slot atomically (kills TOCTOU).

        One shared exclusive reservation covers every Home mutation that
        must not interleave with Factory: structural create/restore, backup
        snapshots and device revocations. While reserved, no Factory
        operation can acquire a lease, and any refresh is part of the same
        mutation; the reserve happens in the same critical section as the
        busy check, so the check→mutate window does not exist.
        """
        with self._context_lock:
            if self._leases > 0 or self._structural_active:
                raise HomeSecurityError(
                    "HOME_BUSY",
                    "hay una operación de fábrica en curso; espera a que termine",
                )
            self._structural_active = True

    def end_structural_mutation(self) -> None:
        with self._context_lock:
            self._structural_active = False

    # Explicit alias for non-structural exclusive operations (backup
    # snapshot, revoke): same reservation, clearer call sites.
    begin_exclusive_operation = begin_structural_mutation
    end_exclusive_operation = end_structural_mutation

    @property
    def busy(self) -> bool:
        """True while a lease or structural mutation owns Home resources."""
        with self._context_lock:
            return self._leases > 0 or self._structural_active

    @property
    def has_active_leases(self) -> bool:
        """True while any Factory operation holds the context (§1)."""
        with self._context_lock:
            return self._leases > 0

    def operation_scope(self):
        """Lease the CURRENT context for an operation (§13: concurrency).

        Thread-safe: lease counters and the retired list are guarded by an
        explicit lock. Contexts retired during a lease are closed exactly
        when the last lease is released (never while in use).
        """
        from contextlib import contextmanager

        @contextmanager
        def _scope():
            with self._context_lock:
                if self._structural_active:
                    raise HomeSecurityError(
                        "HOME_BUSY",
                        "hay una creación o restauración de Home en curso; "
                        "espera a que termine",
                    )
                self._leases += 1
            try:
                yield
            finally:
                with self._context_lock:
                    self._leases -= 1
                    drained = []
                    if self._leases == 0 and self._retired:
                        drained = list(self._retired)
                        self._retired.clear()
                for context in drained:
                    context.close()

        return _scope()

    def refresh(self) -> None:
        """Structural rebuild ONLY after create/restore (§10-11).

        Blocked while a Factory operation holds a lease (§1): structural
        mutations never race an active operation's context.
        """
        with self._context_lock:
            if self._leases > 0:
                raise HomeSecurityError(
                    "HOME_BUSY",
                    "hay una operación de fábrica en curso; espera a que termine",
                )
            previous = self._context
            self._context = self._build_context()
        previous.close()
        self.sync_registry()

    def sync_registry(self) -> None:
        if self._registry is None:
            return
        profile = self._context.profile
        roster = self._context.roster
        # A Home refresh is one logical state transition.  Never expose the
        # transient clear/repopulate window to QML, AirCat or Home Assistant.
        with self._registry.batch():
            self._registry.clear_source(DeviceSource.HOME_ROSTER)
            if profile is None or roster is None:
                return
            for entry in roster.list_entries():
                self._registry.ingest(
                    DeviceSource.HOME_ROSTER,
                    _descriptor_from_roster(entry, profile.home_id.value),
                )

    def close(self, *, force: bool = False) -> None:
        """Deterministic runtime shutdown (§14).

        Refuses while an operation is active (Factory lease or structural
        mutation): Home resources are NEVER closed under a live operation.
        ``force`` is kept for API compatibility but no longer bypasses the
        barrier; callers must settle or cancel first.
        """
        with self._context_lock:
            if self._leases > 0 or self._structural_active:
                raise HomeSecurityError(
                    "HOME_BUSY",
                    "hay una operación activa; no se puede cerrar el runtime todavía",
                )
            drained = list(self._retired)
            self._retired.clear()
            current = self._context
            self._structural_active = False
        for context in drained:
            context.close()
        current.close()

    def restore_into_empty(self, path: Path, password: str) -> str:
        """P0: transactional restore when NO Home exists yet."""
        from michi_ecosystem.application.home_backup import BackupError

        if self.authority.home_summary() is not None:
            raise BackupError(
                "HOME_CONFLICT",
                "ya existe un Home; usa la restauración normal",
            )
        metadata = self._context.backup.inspect_backup(path)
        db = self._state_dir / HOME_STATE_DB
        db_existed = db.exists()
        roster = None
        revocations = None
        try:
            roster = SqliteDeviceRosterRepository(db, metadata.home_id)
            revocations = SqliteRevocationRepository(db, metadata.home_id)
            provisional = HomeBackupService(
                keystore=self.keystore,
                profiles=self.profiles,
                roster=roster,
                revocations=revocations,
            )
            provisional.restore_backup(path, password)
        except Exception:
            # §2 order: CLOSE the provisional connections first, then remove
            # only what this attempt created (no deletes over open handles).
            if roster is not None:
                roster.close()
            if revocations is not None:
                revocations.close()
            if not db_existed:
                for suffix in ("", "-wal", "-shm"):
                    artifact = Path(str(db) + suffix)
                    if artifact.exists():
                        artifact.unlink()
            raise
        # Success order: release the provisional handles, THEN rebuild the
        # context over the restored files.
        roster.close()
        revocations.close()
        self.refresh()
        return "Home restaurado desde la copia de seguridad"

    def _build_context(self) -> HomeContext:
        profile = self.authority.home_summary()
        roster = None
        revocations = None
        enrollment = None
        recreate = None
        recreate_store = None
        if profile is not None:
            db = self._state_dir / HOME_STATE_DB
            roster = SqliteDeviceRosterRepository(db, profile.home_id)
            revocations = SqliteRevocationRepository(db, profile.home_id)
            if self._issuer is not None and self._identity_provider is not None:
                enrollment = HomeEnrollmentService(
                    identity_provider=self._identity_provider,
                    issuer=self._issuer,
                    roster=roster,
                )
                recreate_store = FactoryRecreateStore(db, profile.home_id)
                recreate = FactoryRecreateService(store=recreate_store, roster=roster)
        backup = HomeBackupService(
            keystore=self.keystore,
            profiles=self.profiles,
            roster=roster,
            revocations=revocations,
        )
        return HomeContext(
            profile=profile,
            roster=roster,
            revocations=revocations,
            backup=backup,
            enrollment=enrollment,
            recreate=recreate,
            recreate_store=recreate_store,
        )


@dataclass(frozen=True)
class FactoryRuntime:
    service: StreamFactoryService
    bridge: StreamFactoryBridge
    orchestrator: StreamFactoryOrchestrator


@dataclass(frozen=True)
class AccountRuntime:
    repository: SqliteLocalAccountRepository
    service: LocalAccountService
    bridge: LocalAccountBridge

    def close(self) -> None:
        self.repository.close()


class ShutdownPhase(StrEnum):
    RUNNING = "running"
    QUIESCING = "quiescing"
    WAITING_FOR_OPERATIONS = "waiting_for_operations"
    SAFE_TO_CLOSE = "safe_to_close"
    CLOSED = "closed"


@dataclass
class RuntimeLifecycle:
    """Mutable shutdown state shared with the host (single instance)."""

    phase: ShutdownPhase = ShutdownPhase.RUNNING
    close_requested: bool = False
    closed: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def accepting_operations(self) -> bool:
        return not self.close_requested and not self.closed


class EcosystemShutdownError(RuntimeError):
    """One or more resources failed to close; the runtime stays retryable."""

    def __init__(self, errors: tuple[BaseException, ...]) -> None:
        self.errors = errors
        detail = "; ".join(type(item).__name__ for item in errors)
        super().__init__(f"ECOSYSTEM_SHUTDOWN_INCOMPLETE: {detail}")


@dataclass(frozen=True)
class EcosystemRuntime:
    ecosystem_bridge: EcosystemBridge
    factory: FactoryRuntime
    device_registry: DeviceRegistryService
    stream_management: StreamManagementService
    stream_bridge: StreamDeviceBridge
    home: HomeRuntimeManager | None = None
    home_bridge: HomeBridge | None = None
    account: AccountRuntime | None = None
    account_bridge: LocalAccountBridge | None = None
    home_assistant: HomeAssistantService | None = None
    home_assistant_bridge: HomeAssistantBridge | None = None
    discovery: DiscoveryService | None = None
    playback: RemoteMicroServerPlaybackEndpoint | None = None
    operations_bridge: EcosystemOperationsBridge | None = None
    spaces: SpacesService | None = None
    operation_history: OperationHistory | None = None
    discovery_runner: DiscoveryRunner | None = None
    lifecycle: RuntimeLifecycle = field(default_factory=RuntimeLifecycle)
    unsubscribers: tuple[Callable[[], None], ...] = ()

    # ── lifecycle ───────────────────────────────────────────────────────

    def start(self) -> bool:
        """Start background services; False when shutting down or absent."""
        if not self.lifecycle.accepting_operations:
            return False
        if self.discovery is None:
            return False
        try:
            # The source must be open before the worker starts polling it.
            self.discovery.start()
        except Exception:
            return False
        if self.discovery_runner is None:
            return True
        return self.discovery_runner.start()

    def _busy_reasons(self) -> tuple[tuple[str, str], ...]:
        reasons: list[tuple[str, str]] = []
        if self.factory.bridge.busy:
            reasons.append(("FACTORY_BUSY", "hay una operación de fábrica activa"))
        if self.account_bridge is not None and self.account_bridge.busy:
            reasons.append(("ACCOUNT_BUSY", "hay una operación de cuenta activa"))
        if self.home_assistant_bridge is not None and self.home_assistant_bridge.busy:
            reasons.append(("HOME_ASSISTANT_BUSY", "Home Assistant está operando"))
        if self.operations_bridge is not None and self.operations_bridge.busy:
            reasons.append(("SPACES_BUSY", "hay una operación de espacios activa"))
        if self.stream_bridge.busy:
            reasons.append(("STREAM_BUSY", "hay una operación de Music Stream activa"))
        if self.home is not None and self.home.busy:
            reasons.append(("HOME_BUSY", "hay una operación de Home activa"))
        return tuple(reasons)

    def availability(self) -> dict[str, object]:
        """Explicit availability for every optional module (no invented cabling)."""
        home_configured = self.home is not None and self.home.profile is not None
        return {
            "lifecycle": self.lifecycle.phase.value,
            "home": {
                "available": self.home is not None,
                "configured": home_configured,
            },
            "account": {"available": self.account is not None},
            "spaces": {"available": self.spaces is not None},
            "discovery": {
                "available": self.discovery is not None,
                "running": (
                    self.discovery_runner.running
                    if self.discovery_runner is not None
                    else False
                ),
                "health": (
                    self.discovery_runner.health()
                    if self.discovery_runner is not None
                    else None
                ),
            },
            "streamCommands": {"available": self.stream_management.commands_available},
            "homeAssistant": {
                "available": self.home_assistant is not None,
                "enabled": (
                    self.home_assistant.enabled
                    if self.home_assistant is not None
                    else False
                ),
                "connection": (
                    self.home_assistant.connection_state.value
                    if self.home_assistant is not None
                    else "disabled"
                ),
            },
            "microServer": {"available": self.playback is not None},
            "operationHistory": {"available": self.operation_history is not None},
        }

    def close(
        self,
        *,
        force: bool = False,
        timeout: float = 5.0,
        process_pending: Callable[[], None] | None = None,
        cancel_operations: Callable[[], None] | None = None,
    ) -> None:
        """Deterministic shutdown (§14): close persistent adapters.

        Propagates HOME_BUSY while an operation is active; the host must
        settle (or safe-cancel pre-destructive) before closing. When
        ``process_pending`` is supplied, the host keeps a valid event-dispatch
        path open while queued Qt completion slots clear their busy state.
        """
        with self.lifecycle.lock:
            if self.lifecycle.closed:
                return
        # Barrier FIRST: never close resources owned by a live operation.
        reasons = self._busy_reasons()
        if reasons:
            if not force and process_pending is None:
                code, message = reasons[0]
                raise EcosystemBusyError(
                    code, message + "; espera a que termine antes de cerrar"
                )
            with self.lifecycle.lock:
                self.lifecycle.close_requested = True
                self.lifecycle.phase = ShutdownPhase.WAITING_FOR_OPERATIONS
            if cancel_operations is not None:
                with contextlib.suppress(Exception):
                    cancel_operations()
            deadline = time.monotonic() + max(0.0, float(timeout))
            while reasons and time.monotonic() < deadline:
                if process_pending is not None:
                    process_pending()
                else:
                    time.sleep(0.02)
                reasons = self._busy_reasons()
            if reasons:
                with self.lifecycle.lock:
                    self.lifecycle.phase = ShutdownPhase.QUIESCING
                code, message = reasons[0]
                raise EcosystemBusyError(
                    code,
                    message + f"; el cierre esperó {timeout:.1f}s sin poder "
                    "cerrar recursos en uso",
                )
        with self.lifecycle.lock:
            self.lifecycle.close_requested = True
            self.lifecycle.phase = ShutdownPhase.QUIESCING
        # Background workers stop before persistent stores close.
        if self.discovery_runner is not None:
            self.discovery_runner.stop()
        with self.lifecycle.lock:
            self.lifecycle.phase = ShutdownPhase.SAFE_TO_CLOSE
        # Detach observers so late registry/discovery events cannot reach a
        # bridge whose resources are being released.
        for unsubscribe in self.unsubscribers:
            # An observer that already detached itself must not block shutdown.
            with contextlib.suppress(Exception):
                unsubscribe()
        errors: list[BaseException] = []

        def _attempt(action) -> None:
            try:
                action()
            except Exception as exc:  # keep closing the remaining resources
                errors.append(exc)

        if self.home_assistant is not None:
            # Internal teardown path: retained tombstones still publish; the
            # OWNER gate is reserved for user-initiated disable().
            _attempt(self.home_assistant.shutdown)
        if self.home is not None:
            _attempt(self.home.close)
        if self.account is not None:
            _attempt(self.account.close)
        if self.discovery is not None:
            _attempt(self.discovery.close)
        if self.spaces is not None:
            _attempt(self.spaces.close)
        if self.operation_history is not None:
            _attempt(self.operation_history.close)
        if errors:
            # Retryable: resources that did close are idempotent; the phase
            # stays SAFE_TO_CLOSE so the host can retry close().
            raise EcosystemShutdownError(tuple(errors))
        with self.lifecycle.lock:
            self.lifecycle.phase = ShutdownPhase.CLOSED
            self.lifecycle.closed = True


def build_ecosystem_runtime(
    *,
    dashboard_service,
    factory: FactoryEnvironment,
    board: str = "waveshare-esp32s3-lcd-2",
    firmware_reference: str = "",
    firmware_selection: str = "official_recommended",
    home: HomeEnvironment | None = None,
    account: AccountEnvironment | None = None,
    home_automation: HomeAutomationPort | None = None,
    home_automation_settings: HomeAutomationSettingsPort | None = None,
    stream_commands: StreamManagementCommandPort | None = None,
    discovery_source: DiscoverySourcePort | None = None,
    micro_client=None,
    operation_compatibility=None,
    devices_sync_navigation_available: bool = False,
    support_destination=None,
) -> EcosystemRuntime:
    """Assemble the ecosystem runtime from host-owned dependencies."""
    factory_service = StreamFactoryService(
        serial=factory.serial,
        catalog=factory.catalog,
        backend=factory.backend,
        installation_detector=factory.installation_detector,
    )
    device_registry = DeviceRegistryService()
    home_manager = (
        HomeRuntimeManager(
            state_dir=home.state_dir,
            issuer=home.issuer,
            identity_provider=home.identity_provider,
            registry=device_registry,
        )
        if home is not None
        else None
    )

    account_runtime = None
    if account is not None:
        account_repository = SqliteLocalAccountRepository(account.state_dir)
        account_service = LocalAccountService(
            account_repository,
            home_unlocked_provider=(
                (lambda: home_manager.authority.is_unlocked())
                if home_manager is not None
                else None
            ),
            home_unlocker=(
                (lambda password: home_manager.authority.unlock_home(password))
                if home_manager is not None
                else None
            ),
            home_id_provider=(
                (
                    lambda: (
                        home_manager.profile.home_id.value
                        if home_manager.profile is not None
                        else None
                    )
                )
                if home_manager is not None
                else None
            ),
        )
        account_runtime = AccountRuntime(
            repository=account_repository,
            service=account_service,
            bridge=LocalAccountBridge(account_service),
        )
        # First-run path: CreateLocalAccount and CreateMichiHome stay separate
        # operations, but a Home CREATED in this authenticated local session is
        # immediately assigned to its OWNER. Existing Homes are deliberately not
        # auto-bound; they use bind_existing_home() and verify the Home password.
        if home_manager is not None:

            def _bind_new_home_owner(operation: str, ok: bool, _message: str) -> None:
                if operation != "create" or not ok or not account_service.authenticated:
                    return
                profile = home_manager.profile
                if profile is None:
                    return
                try:
                    account_service.bind_home_owner(profile.home_id.value)
                except LocalAccountError:
                    account_runtime.bridge.errorOccurred.emit(
                        "HOME_OWNER_BIND_FAILED",
                        "El Home se creó, pero no pudimos asignar "
                        "su propietario local.",
                    )
                    return
                account_runtime.bridge.accountChanged.emit()

            home_manager.bridge.operationFinished.connect(_bind_new_home_owner)

    def _owner_authorized(operation: str = "manage") -> bool:
        # Preserve old standalone Home usage when Local Account is not enabled.
        if account_runtime is None:
            return True
        if not account_runtime.service.authenticated:
            return False
        if home_manager is None:
            return True
        profile = home_manager.profile
        if profile is None:
            return operation in {"create", "restore_backup"}
        account_summary = account_runtime.service.account_summary()
        if account_summary is None:
            return False
        return (
            account_runtime.repository.owner_for_home(profile.home_id.value)
            == account_summary.account_id
        )

    if home_manager is not None and account_runtime is not None:
        home_manager.bridge.set_privileged_authorizer(_owner_authorized)

    stream_management = StreamManagementService(
        device_registry,
        commands=stream_commands,
        privileged_authorizer=lambda: _owner_authorized("manage"),
    )
    stream_bridge = StreamDeviceBridge(stream_management)
    unsubscribers: list[Callable[[], None]] = []
    unsubscribers.append(device_registry.subscribe(stream_bridge.on_registry_changed))
    home_assistant_service = (
        HomeAssistantService(
            home_automation,
            settings=home_automation_settings,
            enabled=False,
            privileged_authorizer=lambda: _owner_authorized("manage"),
        )
        if home_automation is not None
        else None
    )
    home_assistant_bridge = HomeAssistantBridge(home_assistant_service)
    if home_assistant_service is not None:
        # Real connectivity (transport events) refreshes the QML status; the
        # bridge marshals it to the GUI thread. Never enable-only "connected".
        home_assistant_service.set_state_listener(
            home_assistant_bridge.notify_connection_changed
        )

    def _sync_home_assistant(devices) -> None:
        if home_assistant_service is None:
            return
        home_assistant_service.sync_devices(devices)
        if home_manager is None or home_manager.profile is None:
            home_assistant_service.clear_home_summary()
            return
        roster = home_manager.roster
        count = len(roster.list_entries()) if roster is not None else 0
        try:
            base = dashboard_service.dashboard_snapshot()
            health = (base.get("health") or {}) if isinstance(base, dict) else {}
            healthy = str(health.get("state", "unknown")) == "healthy"
        except Exception:
            healthy = False
        home_assistant_service.publish_home_summary(
            home_id=home_manager.profile.home_id.value,
            name=home_manager.profile.name,
            device_count=count,
            healthy=healthy,
        )

    if home_assistant_service is not None:
        unsubscribers.append(device_registry.subscribe(_sync_home_assistant))

    discovery_service = (
        DiscoveryService(
            source=discovery_source,
            # Publish each poll as one atomic registry snapshot; individual
            # frames must not make devices disappear/reappear between sources.
            on_snapshot=device_registry.sync_discovery_nodes,
        )
        if discovery_source is not None
        else None
    )
    spaces_service = (
        SpacesService(
            SqliteSpacesStore(home.state_dir / "ecosystem" / "spaces"),
            home_id=(
                lambda: (
                    home_manager.profile.home_id.value if home_manager.profile else None
                )
            ),
            owner_authorized=(lambda: _owner_authorized("manage")),
            device_lookup=device_registry.get,
        )
        if home_manager is not None and home is not None
        else None
    )
    history = OperationHistory(
        state_dir=(home.state_dir / "ecosystem" / "history")
        if home is not None
        else None
    )
    doctor = EcosystemDoctor()
    dashboard = EcosystemDashboardService(
        dashboard_service,
        registry=device_registry,
        discovery=discovery_service,
        account=(account_runtime.service if account_runtime is not None else None),
        home_assistant=home_assistant_service,
        doctor=doctor,
        spaces=spaces_service,
    )

    def _adapter_ready(device: DeviceDescriptor, operation: Operation) -> bool:
        # Never equate a capability flag with a functioning host adapter.
        if device.type is DeviceType.MUSIC_STREAM and operation in {
            Operation.DIAGNOSTICS,
            Operation.FIRMWARE_UPDATE,
            Operation.NETWORK_REPROVISION,
        }:
            return stream_commands is not None
        if operation is Operation.CONTENT_SYNC:
            # Only navigation into Michi Devices, never an AirCat executor here.
            return devices_sync_navigation_available and device.type in {
                DeviceType.MOBILE,
                DeviceType.GENERIC_DAP,
            }
        return False

    operations_bridge = EcosystemOperationsBridge(
        dashboard=dashboard,
        registry=device_registry,
        spaces=spaces_service,
        history=history,
        owner_authorized=lambda: _owner_authorized("manage"),
        adapter_ready=_adapter_ready,
        operation_compatibility=operation_compatibility,
        operation_busy=lambda: stream_bridge.busy,
        support_destination=support_destination,
    )
    operations_bridge.streamSelectionRequested.connect(stream_bridge.select)
    if spaces_service is not None:

        def _remove_revoked_assignments(_devices) -> None:
            # Deletion occurs only for explicit revoked/moved identities.
            # Missing discovery evidence must never purge a trusted location.
            if spaces_service.home_available:
                spaces_service.reconcile_revocations()

        unsubscribers.append(device_registry.subscribe(_remove_revoked_assignments))
    unsubscribers.append(
        device_registry.subscribe(operations_bridge.on_registry_changed)
    )
    ecosystem_bridge = EcosystemBridge(dashboard)
    # Reuse the Player's existing Ecosystem navigator rather than adding a
    # second unconnected route authority for E11.6 detail-page actions.
    operations_bridge.navigationRequested.connect(ecosystem_bridge.activate)
    unsubscribers.append(
        device_registry.subscribe(ecosystem_bridge.on_registry_changed)
    )
    if account_runtime is not None:
        account_runtime.bridge.accountChanged.connect(ecosystem_bridge.refresh)
        account_runtime.bridge.accountChanged.connect(operations_bridge.refresh)
    if home_manager is not None:
        home_manager.bridge.stateChanged.connect(operations_bridge.refresh)
    home_assistant_bridge.stateChanged.connect(ecosystem_bridge.refresh)

    stream_factory_bridge = StreamFactoryBridge(
        factory_service,
        board=board,
        firmware_reference=firmware_reference,
        developer_mode=factory.developer_mode,
        allow_partial_home_bootstrap=factory.allow_partial_home_bootstrap,
        acquisition=factory.acquisition,
        firmware_selection=firmware_selection,
        # P0 dynamic Home: providers query the CURRENT context per operation.
        enrollment=(lambda: home_manager.enrollment) if home_manager else None,
        home_provider=(lambda: home_manager.profile) if home_manager else None,
        recreate=(lambda: home_manager.recreate) if home_manager else None,
        recreate_devices_provider=(
            (lambda: _active_stream_devices(home_manager.roster))
            if home_manager is not None
            else None
        ),
        home_access_provider=(
            (
                lambda: (
                    home_manager.authority.is_unlocked() and _owner_authorized("manage")
                )
            )
            if home_manager is not None
            else None
        ),
        home_lease_provider=(
            (lambda: home_manager.operation_scope())
            if home_manager is not None
            else None
        ),
    )
    discovery_runner = (
        DiscoveryRunner(discovery_service, registry=device_registry)
        if discovery_service is not None
        else None
    )
    return EcosystemRuntime(
        ecosystem_bridge=ecosystem_bridge,
        operations_bridge=operations_bridge,
        spaces=spaces_service,
        operation_history=history,
        factory=FactoryRuntime(
            service=factory_service,
            bridge=stream_factory_bridge,
            orchestrator=stream_factory_bridge.orchestrator,
        ),
        device_registry=device_registry,
        stream_management=stream_management,
        stream_bridge=stream_bridge,
        home=home_manager,
        home_bridge=(home_manager.bridge if home_manager is not None else HomeBridge()),
        account=account_runtime,
        account_bridge=(
            account_runtime.bridge if account_runtime is not None else None
        ),
        home_assistant=home_assistant_service,
        home_assistant_bridge=home_assistant_bridge,
        discovery=discovery_service,
        discovery_runner=discovery_runner,
        unsubscribers=tuple(unsubscribers),
        playback=(
            RemoteMicroServerPlaybackEndpoint(micro_client)
            if micro_client is not None
            else None
        ),
    )
