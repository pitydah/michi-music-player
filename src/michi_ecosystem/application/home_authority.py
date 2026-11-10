"""Home Authority service (R2): create / unlock / lock / sign.

Ed25519 Home Root with its private material persisted ONLY inside the
Argon2id+AES-GCM envelope. The unlocked key lives in memory only;
``lock_home()`` clears the reference. Python cannot guarantee secure memory
zeroing — documented limitation, no false claims.
"""

from __future__ import annotations

import base64
import time
from collections.abc import Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from michi_ecosystem.domain.home import (
    HomeRootPublicIdentity,
    MichiHomeId,
    MichiHomeProfile,
)
from michi_ecosystem.infrastructure.home.key_envelope import (
    EnvelopeError,
    open_sealed,
    seal,
)
from michi_ecosystem.ports.home import HomeKeyStorePort, HomeRepositoryPort


class HomeSecurityError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class HomeAuthorityService:
    def __init__(
        self,
        *,
        keystore: HomeKeyStorePort,
        profiles: HomeRepositoryPort,
        clock: Callable[[], str] | None = None,
    ) -> None:
        self._keystore = keystore
        self._profiles = profiles
        self._clock = clock or _now_iso
        self._unlocked_key: bytes | None = None

    # ── lifecycle ───────────────────────────────────────────────────────

    def create_home(self, *, name: str, password: str) -> MichiHomeProfile:
        if self._keystore.exists():
            raise HomeSecurityError(
                "HOME_EXISTS", "ya existe un Home en este dispositivo"
            )
        if not isinstance(password, str) or len(password) < 8:
            raise HomeSecurityError(
                "WEAK_PASSWORD", "la contraseña debe tener al menos 8 caracteres"
            )
        private = Ed25519PrivateKey.generate()
        private_raw = private.private_bytes(
            Encoding.Raw, PrivateFormat.Raw, NoEncryption()
        )
        public_raw = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        profile = MichiHomeProfile(
            home_id=MichiHomeId.generate(),
            name=name,
            root=HomeRootPublicIdentity(public_key=_b64url(public_raw)),
            created_at=self._clock(),
        )
        # Fail-safe order: the PUBLIC profile first, the SECRET envelope last.
        # If the profile write fails first, nothing was written at all. If
        # the envelope write fails, 100% closure: the orphan profile is
        # REMOVED (no reliance on "ignored orphan" semantics).
        self._profiles.save_profile(profile)
        try:
            self._keystore.save_envelope(seal(private_raw, password))
        except Exception:
            self._profiles.delete_profile()
            raise
        self._unlocked_key = private_raw
        return profile

    def unlock_home(self, password: str) -> MichiHomeProfile:
        envelope = self._keystore.load_envelope()
        if envelope is None:
            raise HomeSecurityError(
                "HOME_MISSING", "no hay un Home en este dispositivo"
            )
        try:
            private_raw = open_sealed(envelope, password)
        except EnvelopeError as exc:
            raise HomeSecurityError("ENVELOPE_OPEN_FAILED", str(exc)) from exc
        profile = self._profiles.load_profile()
        if profile is None:
            raise HomeSecurityError("HOME_MISSING", "falta el perfil público del Home")
        if profile.root.key_scheme != "ed25519":
            raise HomeSecurityError(
                "HOME_ROOT_PROFILE_MISMATCH",
                f"esquema de clave no soportado: {profile.root.key_scheme}",
            )
        derived_public = (
            Ed25519PrivateKey.from_private_bytes(private_raw)
            .public_key()
            .public_bytes(Encoding.Raw, PublicFormat.Raw)
        )
        if _b64url(derived_public) != profile.root.public_key:
            raise HomeSecurityError(
                "HOME_ROOT_PROFILE_MISMATCH",
                "la clave privada no corresponde a la identidad pública",
            )
        self._unlocked_key = private_raw
        return profile

    def lock_home(self) -> None:
        # Best effort: Python cannot guarantee memory zeroing (documented).
        self._unlocked_key = None

    def is_unlocked(self) -> bool:
        return self._unlocked_key is not None

    # ── operations ──────────────────────────────────────────────────────

    def sign(self, message: bytes) -> bytes:
        if self._unlocked_key is None:
            raise HomeSecurityError("HOME_LOCKED", "el Home está bloqueado")
        key = Ed25519PrivateKey.from_private_bytes(self._unlocked_key)
        return key.sign(message)

    def home_summary(self) -> MichiHomeProfile | None:
        """Public profile — readable without unlocking (contains no secrets).

        Guarded: an orphan profile without its envelope is NOT a Home.
        """
        if not self._keystore.exists():
            return None
        return self._profiles.load_profile()
