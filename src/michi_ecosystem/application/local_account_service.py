"""Local account application service (E11.5-A)."""

from __future__ import annotations

import sqlite3
import threading
import time
from collections.abc import Callable

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from michi_ecosystem.domain.account import (
    AccountDomainError,
    LocalAccount,
    LocalSession,
)
from michi_ecosystem.ports.account import LocalAccountRepositoryPort


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class LocalAccountError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class LocalAccountService:
    """Single-owner local account service; sessions exist only in memory."""

    def __init__(
        self,
        repository: LocalAccountRepositoryPort,
        *,
        clock: Callable[[], str] | None = None,
        home_unlocked_provider: Callable[[], bool] | None = None,
        home_unlocker: Callable[[str], object] | None = None,
        home_id_provider: Callable[[], str | None] | None = None,
        password_hasher: PasswordHasher | None = None,
        monotonic_clock: Callable[[], float] | None = None,
        session_idle_seconds: int = 1800,
        max_failed_attempts: int = 5,
        auth_cooldown_seconds: int = 60,
    ) -> None:
        self._repository = repository
        self._clock = clock or _now_iso
        self._home_unlocked_provider = home_unlocked_provider
        self._home_unlocker = home_unlocker
        self._home_id_provider = home_id_provider
        self._hasher = password_hasher or PasswordHasher(
            time_cost=3,
            memory_cost=65536,
            parallelism=2,
            hash_len=32,
            salt_len=16,
            type=Type.ID,
        )
        if (
            session_idle_seconds <= 0
            or max_failed_attempts <= 0
            or auth_cooldown_seconds <= 0
        ):
            raise ValueError("security intervals and attempt limits must be positive")
        self._session: LocalSession | None = None
        self._monotonic = monotonic_clock or time.monotonic
        self._session_idle_seconds = session_idle_seconds
        self._session_last_used: float | None = None
        self._max_failed_attempts = max_failed_attempts
        self._auth_cooldown_seconds = auth_cooldown_seconds
        self._failed_auth_count = 0
        self._locked_until = 0.0
        self._state_lock = threading.RLock()

    @staticmethod
    def _validate_password(password: str) -> None:
        if not isinstance(password, str) or len(password) < 8:
            raise LocalAccountError(
                "WEAK_PASSWORD", "la contraseña debe tener al menos 8 caracteres"
            )

    @property
    def session(self) -> LocalSession | None:
        return self._session

    @property
    def authenticated(self) -> bool:
        with self._state_lock:
            if (
                self._session is not None
                and self._session_last_used is not None
                and self._monotonic() - self._session_last_used
                >= self._session_idle_seconds
            ):
                self._session = None
                self._session_last_used = None
            return self._session is not None and self._session.authenticated

    def _check_auth_rate_limit(self) -> None:
        if self._monotonic() < self._locked_until:
            raise LocalAccountError(
                "AUTH_THROTTLED", "demasiados intentos; prueba más tarde"
            )
        if self._locked_until:
            self._locked_until = 0.0
            self._failed_auth_count = 0

    def _auth_failed(self) -> None:
        self._failed_auth_count += 1
        if self._failed_auth_count >= self._max_failed_attempts:
            self._locked_until = self._monotonic() + self._auth_cooldown_seconds
        raise LocalAccountError("AUTH_FAILED", "usuario o contraseña incorrectos")

    def has_account(self) -> bool:
        return self._repository.count_accounts() > 0

    def create_account(
        self, *, username: str, display_name: str, password: str
    ) -> LocalAccount:
        if self.has_account():
            raise LocalAccountError(
                "ACCOUNT_EXISTS", "ya existe una cuenta local OWNER"
            )
        self._validate_password(password)
        now = self._clock()
        verifier = self._hasher.hash(password)
        try:
            account = LocalAccount.new(
                username=username.strip(),
                display_name=display_name,
                password_verifier=verifier,
                created_at=now,
            )
            self._repository.create(account)
        except AccountDomainError as exc:
            raise LocalAccountError("INVALID_ACCOUNT", str(exc)) from exc
        except sqlite3.IntegrityError as exc:
            raise LocalAccountError(
                "ACCOUNT_EXISTS", "ya existe una cuenta local OWNER"
            ) from exc
        with self._state_lock:
            self._session = LocalSession(
                account_id=account.account_id,
                created_at=now,
                last_activity=now,
                authenticated=True,
                unlocked_home=False,
            )
            self._session_last_used = self._monotonic()
        return account

    def authenticate(self, username: str, password: str) -> LocalAccount:
        # Serialize authentication attempts so concurrent worker threads cannot
        # bypass the cooldown. This is process-local; no persistent credential
        # or session state is introduced.
        with self._state_lock:
            self._check_auth_rate_limit()
            normalized = username.strip() if isinstance(username, str) else ""
            account = (
                self._repository.get_by_username(normalized) if normalized else None
            )
            if account is None or not isinstance(password, str):
                self._auth_failed()
            try:
                verified = self._hasher.verify(account.password_verifier, password)
            except (VerifyMismatchError, InvalidHashError, VerificationError):
                self._auth_failed()
            if not verified:
                self._auth_failed()
            now = self._clock()
            if self._hasher.check_needs_rehash(account.password_verifier):
                replacement = self._hasher.hash(password)
                self._repository.update_verifier(account.account_id, replacement, now)
                account = self._repository.get_by_id(account.account_id) or account
            self._failed_auth_count = 0
            self._locked_until = 0.0
            self._session = LocalSession(
                account_id=account.account_id,
                created_at=now,
                last_activity=now,
                authenticated=True,
                unlocked_home=False,
            )
            self._session_last_used = self._monotonic()
            return account

    def lock(self) -> None:
        with self._state_lock:
            self._session = None
            self._session_last_used = None

    def account_summary(self) -> LocalAccount | None:
        """Return non-secret OWNER metadata even while the session is locked."""
        return self._repository.first_account()

    def current_account(self) -> LocalAccount | None:
        with self._state_lock:
            if not self.authenticated or self._session is None:
                return None
            return self._repository.get_by_id(self._session.account_id)

    def change_password(self, current_password: str, new_password: str) -> None:
        with self._state_lock:
            self._check_auth_rate_limit()
            account = self._require_account()
            self._validate_password(new_password)
            try:
                verified = self._hasher.verify(
                    account.password_verifier, current_password
                )
            except (VerifyMismatchError, InvalidHashError, VerificationError):
                self._auth_failed()
            if not verified:
                self._auth_failed()
            now = self._clock()
            self._repository.update_verifier(
                account.account_id, self._hasher.hash(new_password), now
            )
            self._failed_auth_count = 0
            self._locked_until = 0.0
            self._touch(
                unlocked_home=self._session.unlocked_home if self._session else False
            )

    def bind_home_owner(self, michi_home_id: str) -> None:
        account = self._require_account()
        if (
            self._home_unlocked_provider is not None
            and not self._home_unlocked_provider()
        ):
            raise LocalAccountError(
                "HOME_LOCKED", "desbloquea Michi Home antes de cambiar su propiedad"
            )
        if not isinstance(michi_home_id, str) or not michi_home_id.strip():
            raise LocalAccountError(
                "INVALID_HOME", "michi_home_id no puede estar vacío"
            )
        requested_home_id = michi_home_id.strip()
        if self._home_id_provider is not None:
            active_home_id = self._home_id_provider()
            if not active_home_id:
                raise LocalAccountError(
                    "HOME_UNAVAILABLE", "no encontramos un Michi Home activo"
                )
            if requested_home_id != active_home_id:
                raise LocalAccountError(
                    "HOME_MISMATCH",
                    "la cuenta local sólo puede reclamar el Michi Home activo",
                )
        self._repository.bind_home_owner(account.account_id, requested_home_id)
        self._touch(unlocked_home=True)

    def bind_existing_home(self, home_password: str) -> str:
        """Verify an existing Home once and bind the authenticated OWNER.

        The Home Root, home id, roster, memberships and revocations are not
        regenerated.  The callback only performs the existing Home unlock.
        """
        account = self._require_account()
        if self._home_unlocker is None or self._home_id_provider is None:
            raise LocalAccountError(
                "HOME_UNAVAILABLE", "Michi Home no está disponible en este host"
            )
        if not isinstance(home_password, str) or not home_password:
            raise LocalAccountError(
                "HOME_PASSWORD_REQUIRED", "ingresá la contraseña actual de Michi Home"
            )
        try:
            self._home_unlocker(home_password)
        except Exception as exc:
            raise LocalAccountError(
                "HOME_AUTH_FAILED", "la contraseña de Michi Home es incorrecta"
            ) from exc
        home_id = self._home_id_provider()
        if not home_id:
            raise LocalAccountError(
                "HOME_UNAVAILABLE", "no encontramos un Michi Home existente"
            )
        self._repository.bind_home_owner(account.account_id, home_id)
        self._touch(unlocked_home=True)
        return home_id

    def owner_for_home(self, michi_home_id: str) -> str | None:
        return self._repository.owner_for_home(michi_home_id)

    def owned_home_id(self) -> str | None:
        account = self.current_account() or self.account_summary()
        if account is None:
            return None
        return self._repository.home_for_owner(account.account_id)

    def _require_account(self) -> LocalAccount:
        account = self.current_account()
        if account is None:
            raise LocalAccountError(
                "AUTH_REQUIRED", "esta operación requiere la cuenta local desbloqueada"
            )
        return account

    def _touch(self, *, unlocked_home: bool) -> None:
        with self._state_lock:
            if not self.authenticated or self._session is None:
                return
            self._session = LocalSession(
                account_id=self._session.account_id,
                created_at=self._session.created_at,
                last_activity=self._clock(),
                authenticated=True,
                unlocked_home=unlocked_home,
            )
            self._session_last_used = self._monotonic()
