"""V1 bootstrap encoder: MICHI-F1 as shipped today (network + device only).

Home/identity material belongs to the V2 semantics (STREAM-REQ-007); trying to
encode it here fails closed instead of silently dropping fields.
"""

from __future__ import annotations

from michi_ecosystem.domain.bootstrap import FactoryBootstrapPayload
from michi_ecosystem.domain.flashing import ProvisioningRequest
from michi_ecosystem.infrastructure.flashing.provisioning_blob import (
    build_provisioning_blob,
)
from michi_ecosystem.ports.bootstrap_encoder import BootstrapEncodingError


class V1BootstrapEncoder:
    def encode(self, payload: FactoryBootstrapPayload) -> bytes:
        if payload.requires_v2():
            raise BootstrapEncodingError(
                "V1_CANNOT_CARRY_HOME",
                "identidad/Home requieren el importer MICHI-F1 v2 (STREAM-REQ-007)",
            )
        if payload.network is None:
            raise BootstrapEncodingError("V1_REQUIRES_NETWORK", "falta la red")
        return build_provisioning_blob(
            ProvisioningRequest(
                ssid=payload.network.ssid,
                password=payload.network.password,
                region=payload.network.region,
                device_name=payload.device_name,
            )
        )
