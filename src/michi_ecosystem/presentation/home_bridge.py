"""Michi Home product bridge (C1): safe QML surface for Home management.

Exposes product state and actions; NEVER exposes secrets (no password, no
private material, no envelope bytes). Slow crypto (Argon2id on create /
unlock / backup / restore) runs on a worker thread; state is mutated only on
the owning thread via queued signal delivery (A2 pattern).
"""

from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import Property, QObject, Qt, Signal, Slot

from michi_ecosystem.application.home_authority import (
    HomeAuthorityService,
    HomeSecurityError,
)
from michi_ecosystem.application.home_backup import BackupError, HomeBackupService

_STATUS_LABELS = {
    "pending": "Esperando confirmación",
    "active": "Activo",
    "revoked": "Revocado",
    "replacement_pending": "Reemplazo en curso",
    "replaced": "Reemplazado",
    "aborted": "Cancelado",
    "recovery_required": "Recuperación requerida",
}


_HOME_ERROR_UX = {
    "OWNER_REQUIRED": (
        "Cuenta propietaria bloqueada",
        "Desbloquea la cuenta local OWNER para administrar Michi Home.",
    ),
    "HOME_REHYDRATION_FAILED": (
        "No pudimos activar el Home actualizado",
        "El Home se guardó en disco; reintenta (o reinicia) para activarlo.",
    ),
    "HOME_BUSY": (
        "Operación de fábrica en curso",
        "Espera a que termine el trabajo de Fábrica y reintenta.",
    ),
    "HOME_MISSING": (
        "Todavía no hay un Michi Home",
        "Crea un Home nuevo o restaura una copia de seguridad.",
    ),
    "HOME_LOCKED": (
        "El Home está bloqueado",
        "Desbloquea tu Michi Home para continuar.",
    ),
    "WEAK_PASSWORD": (
        "Contraseña demasiado corta",
        "Usa al menos 8 caracteres.",
    ),
    "ENVELOPE_OPEN_FAILED": (
        "No pudimos desbloquear el Home",
        "Revisa la contraseña. Si no la recordás, restaura una copia de seguridad.",
    ),
    "HOME_CONFLICT": (
        "Ya existe un Home distinto",
        "Restaura en un destino limpio o revocá el Home actual primero.",
    ),
    "INVALID_PATH": (
        "Archivo inválido",
        "Elige un archivo local .michi-home válido.",
    ),
    "BACKUP_HOME_MISMATCH": (
        "La copia pertenece a otro Home",
        "Usa una copia del Home actual o restaurada en un destino limpio.",
    ),
    "BACKUP_TOO_LARGE": (
        "La copia es demasiado grande",
        "Verificá que el archivo sea una copia de Michi Home legítima.",
    ),
    "RESTORE_FAILED": (
        "La restauración no se completó",
        "El Home actual quedó intacto; reintenta con una copia válida.",
    ),
    "REVOKE_FAILED": (
        "No pudimos revocar el dispositivo",
        "Reintenta; si persiste, revisa los permisos del archivo de datos.",
    ),
    "INTERNAL_HOME_ERROR": (
        "Algo salió mal",
        "Reintenta. Si persiste, reinicia la aplicación.",
    ),
}


_EXCLUSIVE_OPERATIONS = (
    "create",
    "restore_backup",
    "export_backup",
    "revoke",
)


class HomeBridge(QObject):
    stateChanged = Signal()
    operationFinished = Signal(str, bool, str)  # operation, ok, message
    _completed = Signal(str, bool, str, str, object)  # op, ok, msg, code, payload

    def __init__(
        self,
        *,
        authority: HomeAuthorityService | None = None,
        profiles=None,
        backup: HomeBackupService | None = None,
        roster=None,
        revocations=None,
        context_changed=None,
        empty_restore=None,
        operation_busy_provider=None,
        structural_begin=None,
        structural_end=None,
        privileged_authorizer=None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._authority = authority
        self._profiles = profiles
        self._backup = backup
        self._roster = roster
        self._revocations = revocations
        self._context_changed = context_changed
        self._empty_restore = empty_restore
        self._operation_busy_provider = operation_busy_provider
        self._structural_begin = structural_begin
        self._structural_end = structural_end
        # Optional host policy. Legacy standalone Home keeps its own unlock
        # authority; E11.5 hosts add an authenticated OWNER gate.
        self._privileged_authorizer = privileged_authorizer
        self._busy = False
        self._error = ""
        self._error_code = ""
        self._last_operation = ""
        self._profile = None
        self._devices: list[dict] = []
        self._backup_preview: dict = {}
        self._completed.connect(self._on_completed, Qt.ConnectionType.QueuedConnection)
        self._refresh_state()

    # ── properties (never secrets) ──────────────────────────────────────

    @staticmethod
    def _local_path(path: str):
        """Robust local file path from QML (QUrl string or plain path, §18)."""
        from PySide6.QtCore import QUrl

        text = (path or "").strip()
        if not text:
            raise BackupError("INVALID_PATH", "Elige un archivo.")
        if text.startswith("file:"):
            local = QUrl(text).toLocalFile()
            if not local:
                raise BackupError("INVALID_PATH", "Ruta local inválida.")
            return Path(local)
        if "://" in text:
            raise BackupError("INVALID_PATH", "Solo se permiten archivos locales.")
        return Path(text).expanduser()

    @staticmethod
    def _resolve(value):
        """Instances or zero-arg providers (dynamic Home lifecycle)."""
        return value() if callable(value) else value

    def _refresh_state(self) -> None:
        self._profile = (
            self._authority.home_summary() if self._authority is not None else None
        )
        roster = self._resolve(self._roster)
        self._devices = self._load_devices(roster) if roster is not None else []

    def _load_devices(self, roster) -> list[dict]:
        if roster is None:
            return []
        return [_device_dict(entry) for entry in roster.list_entries()]

    @Property(bool, notify=stateChanged)
    def configured(self) -> bool:
        return self._profile is not None

    @Property(bool, notify=stateChanged)
    def locked(self) -> bool:
        return self._profile is not None and (
            self._authority is None or not self._authority.is_unlocked()
        )

    @Property(str, notify=stateChanged)
    def homeName(self) -> str:
        return self._profile.name if self._profile is not None else ""

    @Property(str, notify=stateChanged)
    def homeId(self) -> str:
        return self._profile.home_id.value if self._profile is not None else ""

    @Property(str, notify=stateChanged)
    def homeRootKey(self) -> str:
        if self._profile is None:
            return ""
        key = self._profile.root.public_key
        return f"{key[:11]}…{key[-6:]}" if len(key) > 20 else key

    @Property("QVariantList", notify=stateChanged)
    def devices(self) -> list[dict]:
        return self._devices

    @Property(int, notify=stateChanged)
    def deviceCount(self) -> int:
        return len(self._devices)

    @Property(int, notify=stateChanged)
    def activeDeviceCount(self) -> int:
        return sum(1 for item in self._devices if item["status"] == "active")

    @Property(int, notify=stateChanged)
    def pendingDeviceCount(self) -> int:
        return sum(
            1
            for item in self._devices
            if item["status"] in ("pending", "replacement_pending")
        )

    @Property(bool, notify=stateChanged)
    def backupSupported(self) -> bool:
        return self._resolve(self._backup) is not None

    @Property(bool, notify=stateChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=stateChanged)
    def errorMessage(self) -> str:
        return self._error

    @Property(str, notify=stateChanged)
    def errorCode(self) -> str:
        return self._error_code

    @Property(str, notify=stateChanged)
    def errorTitle(self) -> str:
        entry = _HOME_ERROR_UX.get(self._error_code)
        return entry[0] if entry else ""

    @Property(str, notify=stateChanged)
    def errorHelp(self) -> str:
        entry = _HOME_ERROR_UX.get(self._error_code)
        return entry[1] if entry else ""

    @Property(str, notify=stateChanged)
    def lastOperation(self) -> str:
        return self._last_operation

    @Property("QVariantMap", notify=stateChanged)
    def backupPreview(self) -> dict:
        return self._backup_preview

    # ── actions ─────────────────────────────────────────────────────────

    def _reserve_structural(self) -> bool:
        """Atomically reserve the exclusive slot BEFORE the worker starts."""
        if self._structural_begin is None:
            return True
        try:
            self._structural_begin()
            return True
        except HomeSecurityError as exc:
            self._fail_sync(exc.code, exc.message)
            return False

    def _factory_busy(self) -> bool:
        if self._operation_busy_provider is None:
            return False
        value = self._resolve(self._operation_busy_provider)
        return bool(value() if callable(value) else value)

    def set_privileged_authorizer(self, authorizer) -> None:
        """Install OWNER authorization after the local account is composed."""
        self._privileged_authorizer = authorizer

    def _require_owner(self, operation: str) -> bool:
        if self._privileged_authorizer is None:
            return True
        try:
            allowed = bool(self._privileged_authorizer(operation))
        except Exception:
            allowed = False
        if not allowed:
            self._fail_sync(
                "OWNER_REQUIRED",
                "Desbloquea la cuenta propietaria para administrar Michi Home.",
            )
        return allowed

    @Slot(str, str)
    def createHome(self, name: str, password: str) -> None:
        if not self._require_owner("create"):
            return
        if self._authority is None:
            self._fail_sync("HOME_MISSING", "Todavía no hay un Home.")
            return
        if self._factory_busy() or self._busy:
            self._fail_sync(
                "HOME_BUSY",
                "Hay una operación de fábrica en curso; espera a que termine.",
            )
            return
        if not self._reserve_structural():
            return
        if not name.strip():
            self._fail_sync("INVALID_NAME", "Poné un nombre para tu Home.")
            self._release_structural("create")
            return
        self._start(
            "create",
            lambda: (
                self._authority.create_home(name=name.strip(), password=password)
                and f"Home «{name.strip()}» creado"
            ),
        )

    @Slot(str)
    def unlockHome(self, password: str) -> None:
        if self._authority is None:
            self._fail_sync("HOME_MISSING", "Todavía no hay un Home.")
            return
        self._start("unlock", lambda: self._unlock(password))

    @Slot()
    def lockHome(self) -> None:
        self._authority.lock_home()
        self._refresh_state()
        self.stateChanged.emit()

    @Slot(str, str)
    def exportBackup(self, path: str, password: str) -> None:
        if not self._require_owner("export_backup"):
            return
        if self._factory_busy():
            # A snapshot taken mid-recreate would persist transient roster
            # states without their transaction (not cleanly restorable).
            self._fail_sync(
                "HOME_BUSY",
                "Hay una operación de fábrica en curso; espera a que termine "
                "para crear la copia.",
            )
            return

        def run() -> str:
            target = self._local_path(path)
            self._resolve(self._backup).create_backup(target, password)
            return f"Copia de seguridad guardada en {target}"

        if not self._reserve_structural():
            return
        self._start("export_backup", run)

    @Slot(str)
    def previewBackup(self, path: str) -> None:
        """Inspect backup metadata for the restore preview (no secrets)."""
        self._backup_preview = {}
        self.stateChanged.emit()

        def run() -> str:
            source = self._local_path(path)
            if not source.is_file():
                raise BackupError(
                    "INVALID_PATH", "No encontramos un archivo de copia ahí."
                )
            metadata = self._resolve(self._backup).inspect_backup(source)
            preview = {
                "homeId": metadata.home_id.value,
                "createdAt": metadata.created_at,
                "formatVersion": metadata.format_version,
                "includesRoster": metadata.includes_roster,
            }
            return "", preview

        self._start("inspect_backup", run)

    @Slot(str, str)
    def restoreBackup(self, path: str, password: str) -> None:
        if not self._require_owner("restore_backup"):
            return
        if self._factory_busy() or self._busy:
            self._fail_sync(
                "HOME_BUSY",
                "Hay una operación de fábrica en curso; espera a que termine.",
            )
            return
        if not self._reserve_structural():
            return

        def run() -> str:
            source = self._local_path(path)
            if not source.is_file():
                raise BackupError(
                    "INVALID_PATH", "No encontramos un archivo de copia ahí."
                )
            if (
                self._authority.home_summary() is None
                and self._empty_restore is not None
            ):
                # P0: restore into an EMPTY runtime (no Home exists yet).
                return self._empty_restore(source, password)
            self._resolve(self._backup).restore_backup(source, password)
            return "Home restaurado desde la copia de seguridad"

        self._start("restore_backup", run)

    @Slot(str, str)
    def revokeDevice(self, device_id: str, reason: str = "") -> None:
        if not self._require_owner("revoke"):
            return
        if self._resolve(self._roster) is None:
            self._fail_sync("HOME_MISSING", "Todavía no hay un Home.")
            return
        if self._factory_busy():
            # A revoke mid-recreate would contaminate the replacement state
            # machine (the old device must stay REPLACEMENT_PENDING until the
            # transaction settles).
            self._fail_sync(
                "HOME_BUSY",
                "Hay una operación de fábrica en curso; espera a que termine.",
            )
            return
        roster = self._resolve(self._roster)
        if not self._reserve_structural():
            return
        # Validation lives INSIDE the worker: the reservation is released by
        # _on_completed on EVERY path (including DB exceptions raised here
        # before the write), so no pre-worker exception can strand it.
        # Factory cannot turn the device into REPLACEMENT_PENDING between
        # the check and the write because the reservation blocks Factory.

        def run() -> str:
            entry = roster.get(device_id) if hasattr(roster, "get") else None
            if entry is not None and entry.status.value in (
                "replacement_pending",
                "recovery_required",
            ):
                raise BackupError(
                    "REVOKE_NOT_ALLOWED",
                    "Este dispositivo está en medio de una reconstrucción; "
                    "espera a que termine antes de revocarlo.",
                )
            try:
                roster.revoke(device_id, reason or "revocado desde Ecosystem")
            except BackupError:
                raise
            except Exception as exc:  # domain/DB errors must not kill the UI
                raise BackupError(
                    "REVOKE_FAILED",
                    f"No se pudo revocar ({type(exc).__name__}).",
                ) from exc
            return "Dispositivo revocado"

        self._start("revoke", run)

    @Slot()
    def refresh(self) -> None:
        self._refresh_state()
        self.stateChanged.emit()

    # ── worker plumbing ─────────────────────────────────────────────────

    def _unlock(self, password: str) -> str:
        profile = self._authority.unlock_home(password)
        return f"Home «{profile.name}» desbloqueado"

    def _start(self, operation: str, fn) -> None:
        if self._busy:
            self._release_structural(operation)
            return
        self._busy = True
        self._error = ""
        self._error_code = ""
        self._last_operation = operation
        self.stateChanged.emit()

        def worker() -> None:
            try:
                result = fn()
                message, payload = (
                    result if isinstance(result, tuple) else (result, None)
                )
                self._completed.emit(operation, True, message or "", "", payload)
            except HomeSecurityError as exc:
                self._completed.emit(operation, False, exc.message, exc.code, None)
            except BackupError as exc:
                self._completed.emit(operation, False, exc.message, exc.code, None)
            except Exception as exc:  # sanitized: type only
                self._completed.emit(
                    operation,
                    False,
                    f"Error interno ({type(exc).__name__}).",
                    "INTERNAL_HOME_ERROR",
                    None,
                )

        try:
            threading.Thread(target=worker, daemon=True).start()
        except Exception:
            # Thread creation failure (e.g. resource exhaustion): restore the
            # state exactly as if the operation never started.
            self._busy = False
            self._release_structural(operation)
            self._fail_sync(
                "INTERNAL_HOME_ERROR",
                "No pudimos iniciar la operación; reintenta.",
            )

    def _release_structural(self, operation: str) -> None:
        """Release the exclusive Home slot (idempotent, safe)."""
        if operation in _EXCLUSIVE_OPERATIONS and (self._structural_end is not None):
            self._structural_end()

    @Slot(str, bool, str, str, object)
    def _on_completed(
        self,
        operation: str,
        ok: bool,
        message: str,
        code: str,
        payload: object,
    ) -> None:
        self._busy = False
        self._last_operation = operation
        effective_ok = ok
        effective_message = message
        try:
            if not ok:
                self._error = message
                self._error_code = code
            else:
                self._error = ""
                self._error_code = ""
                # QObject state is mutated ONLY here (owning thread, A2).
                if operation == "inspect_backup":
                    self._backup_preview = payload if isinstance(payload, dict) else {}
                if self._context_changed is not None and operation in (
                    "create",
                    "restore_backup",
                ):
                    # Structural hydration ONLY on create/restore (§10-11):
                    # lock/unlock/backup never rebuild repositories.
                    try:
                        self._context_changed()
                    except Exception:
                        # The Home is on disk but not active: surface it and
                        # NEVER leave the exclusive slot stuck (finally).
                        self._error = (
                            "El Home se guardó, pero no pudimos activar el "
                            "contexto; reintenta."
                        )
                        self._error_code = "HOME_REHYDRATION_FAILED"
                        effective_ok = False
                        effective_message = self._error
                self._refresh_state()
        except Exception:
            self._error = (
                "El Home se guardó, pero no pudimos activar el contexto; reintenta."
            )
            self._error_code = "HOME_REHYDRATION_FAILED"
            effective_ok = False
            effective_message = self._error
        finally:
            # The exclusive slot is RELEASED on EVERY path: a hydration
            # failure must never deadlock Factory/create/restore/backup/revoke.
            self._release_structural(operation)
            self.stateChanged.emit()
            self.operationFinished.emit(operation, effective_ok, effective_message)

    def _fail_sync(self, code: str, message: str) -> None:
        self._error = message
        self._error_code = code
        self.stateChanged.emit()
        self.operationFinished.emit("", False, message)


def _device_dict(entry) -> dict:
    roles = ", ".join(role.value for role in entry.roles)
    return {
        "id": entry.device_michi_id,
        "name": entry.device_name,
        "status": entry.status.value,
        "statusLabel": _STATUS_LABELS.get(entry.status.value, entry.status.value),
        "roles": roles,
        "serial": entry.membership_serial,
    }
