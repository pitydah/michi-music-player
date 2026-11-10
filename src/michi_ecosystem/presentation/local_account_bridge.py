"""QML bridge for the local OWNER account (E11.5-A).

Argon2id is intentionally expensive.  All create/auth/change-password/migration
operations therefore run off the GUI thread and are delivered back through a
queued signal, mirroring the Home bridge threading pattern.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import Property, QObject, Qt, Signal, Slot

from michi_ecosystem.application.local_account_service import (
    LocalAccountError,
    LocalAccountService,
)

_ACCOUNT_ERROR_UX = {
    "WEAK_PASSWORD": "Usa una contraseña de al menos 8 caracteres.",
    "AUTH_FAILED": "Usuario o contraseña incorrectos.",
    "AUTH_THROTTLED": "Demasiados intentos. Vuelve a intentarlo en un minuto.",
    "AUTH_REQUIRED": "Desbloquea la cuenta local para continuar.",
    "ACCOUNT_EXISTS": "Ya existe un propietario local en este equipo.",
    "INVALID_ACCOUNT": "Revisa el nombre de usuario y el nombre visible.",
    "HOME_AUTH_FAILED": "La contraseña actual de Michi Home es incorrecta.",
    "HOME_PASSWORD_REQUIRED": "Ingresá la contraseña actual de Michi Home.",
    "HOME_UNAVAILABLE": "No encontramos un Michi Home disponible.",
    "HOME_LOCKED": "Desbloquea Michi Home antes de cambiar su propiedad.",
    "INVALID_HOME": "El identificador de Michi Home no es válido.",
    "HOME_MISMATCH": "La cuenta sólo puede reclamar el Michi Home activo en este equipo.",
}


class LocalAccountBridge(QObject):
    accountChanged = Signal()
    errorOccurred = Signal(str, str)
    operationFinished = Signal(str, bool, str)
    _completed = Signal(str, bool, str, str)

    def __init__(
        self, service: LocalAccountService, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._busy = False
        self._error = ""
        self._error_code = ""
        self._completed.connect(self._on_completed, Qt.ConnectionType.QueuedConnection)

    @Property(bool, notify=accountChanged)
    def hasAccount(self) -> bool:
        return self._service.has_account()

    @Property(bool, notify=accountChanged)
    def authenticated(self) -> bool:
        return self._service.authenticated

    @Property(bool, notify=accountChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=accountChanged)
    def username(self) -> str:
        account = self._service.current_account() or self._service.account_summary()
        return account.username if account is not None else ""

    @Property(str, notify=accountChanged)
    def displayName(self) -> str:
        account = self._service.current_account() or self._service.account_summary()
        return account.display_name if account is not None else ""

    @Property(str, notify=accountChanged)
    def ownedHomeId(self) -> str:
        return self._service.owned_home_id() or ""

    @Property(str, notify=accountChanged)
    def errorMessage(self) -> str:
        return self._error

    @Property(str, notify=accountChanged)
    def errorCode(self) -> str:
        return self._error_code

    @Slot(str, str, str)
    def createAccount(self, username: str, display_name: str, password: str) -> None:
        self._start(
            "create",
            lambda: self._service.create_account(
                username=username, display_name=display_name, password=password
            ),
        )

    @Slot(str, str)
    def authenticate(self, username: str, password: str) -> None:
        self._start(
            "authenticate", lambda: self._service.authenticate(username, password)
        )

    @Slot()
    def lock(self) -> None:
        if self._busy:
            return
        self._service.lock()
        self._error = ""
        self._error_code = ""
        self.accountChanged.emit()

    @Slot(str, str)
    def changePassword(self, current_password: str, new_password: str) -> None:
        self._start(
            "change_password",
            lambda: self._service.change_password(current_password, new_password),
        )

    @Slot(str)
    def bindHomeOwner(self, michi_home_id: str) -> None:
        self._start("bind_home", lambda: self._service.bind_home_owner(michi_home_id))

    @Slot(str)
    def bindExistingHome(self, home_password: str) -> None:
        self._start(
            "bind_existing_home",
            lambda: self._service.bind_existing_home(home_password),
        )

    def _start(self, operation: str, work) -> None:
        if self._busy:
            self.errorOccurred.emit("ACCOUNT_BUSY", "Ya hay una operación en curso")
            return
        self._busy = True
        self._error = ""
        self._error_code = ""
        self.accountChanged.emit()

        def run() -> None:
            try:
                work()
            except LocalAccountError as exc:
                message = _ACCOUNT_ERROR_UX.get(
                    exc.code, "No pudimos completar la operación."
                )
                self._completed.emit(operation, False, message, exc.code)
            except Exception:
                self._completed.emit(
                    operation,
                    False,
                    "No pudimos completar la operación.",
                    "INTERNAL_ACCOUNT_ERROR",
                )
            else:
                messages = {
                    "create": "Cuenta local creada",
                    "authenticate": "Cuenta desbloqueada",
                    "change_password": "Contraseña actualizada",
                    "bind_home": "Propiedad de Michi Home vinculada",
                    "bind_existing_home": "Michi Home existente vinculado al propietario local",
                }
                self._completed.emit(
                    operation, True, messages.get(operation, "Listo"), ""
                )

        threading.Thread(
            target=run, name=f"michi-account-{operation}", daemon=True
        ).start()

    @Slot(str, bool, str, str)
    def _on_completed(self, operation: str, ok: bool, message: str, code: str) -> None:
        self._busy = False
        self._error = "" if ok else message
        self._error_code = "" if ok else code
        self.accountChanged.emit()
        if not ok:
            self.errorOccurred.emit(code, message)
        self.operationFinished.emit(operation, ok, message)
