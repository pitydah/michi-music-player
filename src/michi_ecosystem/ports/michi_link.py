"""Michi Link contract port: bundle metadata and payload validation.

Phase: E2. Implementations wrap the vendored ``receiver-v1-lite`` bundle
(``infrastructure.michi_link.contracts.ContractBundle``); live transports and
event adapters arrive with E3/E4.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol


class MichiLinkContractPort(Protocol):
    """Consumer view of the vendored Michi Link contract bundle."""

    @property
    def version(self) -> str: ...

    def schema_names(self) -> Sequence[str]: ...

    def validate(self, schema_name: str, payload: Mapping[str, Any]) -> None: ...
