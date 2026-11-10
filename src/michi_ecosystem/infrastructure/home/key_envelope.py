"""Encrypted Home envelopes (R2): Argon2id + AES-256-GCM, versioned.

No custom cryptography: Argon2id comes from ``argon2-cffi`` and AEAD from
``cryptography``. The envelope carries its KDF parameters so they remain
upgradeable. A wrong password and a corrupted envelope fail identically
(authenticated decryption) — never partial plaintext.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass

from argon2.low_level import Type, hash_secret_raw
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ENVELOPE_VERSION = 1
_AAD = b"michi-home-envelope-v1"
_SALT_BYTES = 16
_NONCE_BYTES = 12
_KEY_BYTES = 32

# Never trust KDF parameters loaded from disk (unbounded allocation defense).
MIN_TIME_COST, MAX_TIME_COST = 1, 10
MIN_MEMORY_COST, MAX_MEMORY_COST = 8 * 1024, 256 * 1024  # KiB (8 MiB .. 256 MiB)
MIN_PARALLELISM, MAX_PARALLELISM = 1, 8
MAX_CIPHERTEXT_BYTES = 16 * 1024
MAX_ENVELOPE_BYTES = 64 * 1024


class EnvelopeError(RuntimeError):
    code = "ENVELOPE_OPEN_FAILED"


@dataclass(frozen=True)
class KdfParams:
    """Desktop-practical Argon2id parameters (versioned by the envelope)."""

    time_cost: int = 3
    memory_cost: int = 65536  # 64 MiB
    parallelism: int = 2


DEFAULT_KDF = KdfParams()


def _b64e(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64d(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"), validate=True)


def derive_key(password: str, salt: bytes, params: KdfParams) -> bytes:
    return hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt,
        time_cost=params.time_cost,
        memory_cost=params.memory_cost,
        parallelism=params.parallelism,
        hash_len=_KEY_BYTES,
        type=Type.ID,
    )


def seal(plaintext: bytes, password: str, *, params: KdfParams = DEFAULT_KDF) -> bytes:
    salt = os.urandom(_SALT_BYTES)
    nonce = os.urandom(_NONCE_BYTES)
    key = derive_key(password, salt, params)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, _AAD)
    envelope = {
        "version": ENVELOPE_VERSION,
        "kdf": "argon2id",
        "salt": _b64e(salt),
        "time_cost": params.time_cost,
        "memory_cost": params.memory_cost,
        "parallelism": params.parallelism,
        "nonce": _b64e(nonce),
        "ciphertext": _b64e(ciphertext),
    }
    return json.dumps(envelope, separators=(",", ":")).encode("utf-8")


def open_sealed(envelope: bytes, password: str) -> bytes:
    if len(envelope) > MAX_ENVELOPE_BYTES:
        raise EnvelopeError("envelope demasiado grande")
    try:
        data = json.loads(envelope.decode("utf-8"))
        if data.get("version") != ENVELOPE_VERSION:
            raise EnvelopeError("versión de envelope no soportada")
        if data.get("kdf") != "argon2id":
            raise EnvelopeError("KDF no soportado")
        params = KdfParams(
            time_cost=int(data["time_cost"]),
            memory_cost=int(data["memory_cost"]),
            parallelism=int(data["parallelism"]),
        )
        salt = _b64d(data["salt"])
        nonce = _b64d(data["nonce"])
        ciphertext = _b64d(data["ciphertext"])
    except EnvelopeError:
        raise
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise EnvelopeError("envelope dañado") from exc

    if not (MIN_TIME_COST <= params.time_cost <= MAX_TIME_COST):
        raise EnvelopeError("time_cost fuera de límites")
    if not (MIN_MEMORY_COST <= params.memory_cost <= MAX_MEMORY_COST):
        raise EnvelopeError("memory_cost fuera de límites")
    if not (MIN_PARALLELISM <= params.parallelism <= MAX_PARALLELISM):
        raise EnvelopeError("parallelism fuera de límites")
    if len(salt) != _SALT_BYTES:
        raise EnvelopeError("salt de tamaño inválido")
    if len(nonce) != _NONCE_BYTES:
        raise EnvelopeError("nonce de tamaño inválido")
    if len(ciphertext) > MAX_CIPHERTEXT_BYTES:
        raise EnvelopeError("ciphertext demasiado grande")

    key = derive_key(password, salt, params)
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, _AAD)
    except InvalidTag as exc:
        raise EnvelopeError("contraseña incorrecta o envelope dañado") from exc
