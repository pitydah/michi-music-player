"""Local human account domain (E11.5-A).

The account identifies a *person on this installation*.  It is deliberately
separate from ``michi_home_id`` (Home) and ``michi_id`` (device).  Passwords
are never represented by the domain; only an Argon2id verifier may be stored.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from enum import StrEnum

_USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{3,64}$")


class AccountDomainError(ValueError):
    pass


class LocalAccountRole(StrEnum):
    OWNER = "OWNER"


@dataclass(frozen=True)
class LocalAccount:
    account_id: str
    username: str
    display_name: str
    password_verifier: str = field(repr=False)
    created_at: str = ""
    updated_at: str = ""
    role: LocalAccountRole = LocalAccountRole.OWNER

    def __post_init__(self) -> None:
        if not self.account_id or not isinstance(self.account_id, str):
            raise AccountDomainError("account_id must not be empty")
        if not isinstance(self.username, str) or not _USERNAME_RE.fullmatch(
            self.username
        ):
            raise AccountDomainError("username must be 3-64 characters [A-Za-z0-9._-]")
        if not isinstance(self.display_name, str) or not self.display_name.strip():
            raise AccountDomainError("display_name must not be empty")
        if not isinstance(self.password_verifier, str) or not self.password_verifier:
            raise AccountDomainError("password verifier must not be empty")

    @classmethod
    def new(
        cls,
        *,
        username: str,
        display_name: str,
        password_verifier: str,
        created_at: str,
    ) -> LocalAccount:
        return cls(
            account_id=uuid.uuid4().hex,
            username=username,
            display_name=display_name.strip(),
            password_verifier=password_verifier,
            created_at=created_at,
            updated_at=created_at,
        )


@dataclass(frozen=True)
class LocalSession:
    account_id: str
    created_at: str
    last_activity: str
    authenticated: bool = True
    unlocked_home: bool = False
