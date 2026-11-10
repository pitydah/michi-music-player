"""Semantic factory bootstrap model (R7 — semantics only, no frozen bytes).

The FINAL MICHI-F1 v2 wire format, signature canonicalization and exact
encoding remain open (STREAM-REQ-007). This model only describes what the
bootstrap conceptually carries so host-side orchestration can advance.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BootstrapNetwork:
    ssid: str
    password: str = field(repr=False)
    region: str = ""

    def __repr__(self) -> str:
        return (
            f"BootstrapNetwork(ssid={self.ssid!r}, password=<redacted>, "
            f"region={self.region!r})"
        )


@dataclass(frozen=True)
class BootstrapCandidateIdentity:
    """Candidate device identity metadata (private material NEVER here)."""

    michi_id: str
    public_key: str
    scheme: str = "ed25519-blake3-v1"


@dataclass(frozen=True)
class BootstrapHomeReference:
    """Home reference for enrollment (public identity only)."""

    home_id: str
    home_root_public_key: str


@dataclass(frozen=True)
class BootstrapIssue:
    code: str
    message: str


@dataclass(frozen=True)
class FactoryBootstrapPayload:
    """What a factory bootstrap conceptually carries (semantic, wire-neutral)."""

    network: BootstrapNetwork | None = None
    device_name: str = ""
    identity: BootstrapCandidateIdentity | None = None
    home: BootstrapHomeReference | None = None
    membership_token: str | None = field(default=None, repr=False)

    def requires_v2(self) -> bool:
        """Home/identity material cannot ride the V1 blob."""
        return self.identity is not None or self.home is not None

    def validate(self) -> tuple[BootstrapIssue, ...]:
        """Semantic validation (C3) — wire-neutral, no encoding decisions.

        Home-aware bootstrap requires identity + home + membership together;
        network fields follow 802.11/WPA2 bounds. UPDATE flows must not
        carry a bootstrap at all (enforced by the caller, not here).
        """
        issues: list[BootstrapIssue] = []
        if self.network is not None:
            ssid = self.network.ssid
            if not 1 <= len(ssid) <= 32:
                issues.append(
                    BootstrapIssue(
                        "BOOTSTRAP_SSID_BOUNDS",
                        "el SSID debe tener entre 1 y 32 caracteres",
                    )
                )
            password = self.network.password
            if not 8 <= len(password) <= 63:
                issues.append(
                    BootstrapIssue(
                        "BOOTSTRAP_PASSWORD_BOUNDS",
                        "la contraseña WPA2 debe tener entre 8 y 63 caracteres",
                    )
                )
            region = self.network.region
            if region and len(region) > 8:
                issues.append(
                    BootstrapIssue(
                        "BOOTSTRAP_REGION_BOUNDS",
                        "la región debe tener 8 caracteres o menos",
                    )
                )
        if len(self.device_name) > 64:
            issues.append(
                BootstrapIssue(
                    "BOOTSTRAP_DEVICE_NAME_BOUNDS",
                    "el nombre del dispositivo supera 64 caracteres",
                )
            )

        home_aware = (
            self.identity is not None
            or self.home is not None
            or self.membership_token is not None
        )
        if home_aware:
            identity = self.identity
            if (
                identity is None
                or not identity.michi_id
                or not identity.public_key
                or not identity.scheme
            ):
                issues.append(
                    BootstrapIssue(
                        "BOOTSTRAP_IDENTITY_REQUIRED",
                        "un bootstrap con Home requiere identidad candidata",
                    )
                )
            home = self.home
            if home is None or not home.home_id or not home.home_root_public_key:
                issues.append(
                    BootstrapIssue(
                        "BOOTSTRAP_HOME_REQUIRED",
                        "un bootstrap con identidad requiere la referencia Home",
                    )
                )
            if not self.membership_token:
                issues.append(
                    BootstrapIssue(
                        "BOOTSTRAP_MEMBERSHIP_REQUIRED",
                        "un bootstrap con Home requiere el token de membresía",
                    )
                )
        return tuple(issues)
