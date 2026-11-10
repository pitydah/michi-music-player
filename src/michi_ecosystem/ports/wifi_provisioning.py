"""Wi-Fi provisioning port: transient credential source for the wizard.

Credentials live only between the UX field and the bounded MICHI-F1 blob; they
never persist, never enter navigation state and never reach logs (master plan
§137–§138).
"""

from __future__ import annotations

from typing import Protocol

from michi_ecosystem.domain.flashing import ProvisioningRequest


class WifiProvisioningPort(Protocol):
    def request(self) -> ProvisioningRequest | None: ...
