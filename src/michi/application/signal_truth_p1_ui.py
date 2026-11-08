"""AP2-F11 A48: pure, optional inspector labels from existing read models.

No second renderer/recorder, no Qt dependency and no verdict recalculation.
Never uses source metadata or visual badges to create evidence.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

_STATUS = {
    "ACTIVE": ("LIVE", "Ruta activa"),
    "PENDING": ("PREPARING", "Ruta en preparación, aún no confirmada"),
    "HISTORICAL": ("LAST PLAYBACK", "Última reproducción; datos históricos"),
    "NOT_ACTIVE": ("NOT ACTIVE", "Sin ruta de reproducción activa"),
    "NONE": ("NOT ACTIVE", "Sin ruta de reproducción activa"),
}
_PROOF = {
    "verified": "Ruta observada hasta la frontera declarada",
    "partially_verified": "Verificación parcial; quedan tramos sin observar",
    "contradicted": "Contradicción entre evidencias de salida",
    "pending": "Ruta todavía en preparación",
    "no_path": "Sin evidencia de ruta actual",
}


@dataclass(frozen=True, slots=True)
class InspectorLabels:
    temporal_badge: str
    temporal_description: str
    path_description: str
    fidelity_description: str
    operations_description: str
    accessible_summary: str

    def to_qml(self) -> dict[str, str]:
        return {
            "temporalBadge": self.temporal_badge,
            "temporalDescription": self.temporal_description,
            "pathDescription": self.path_description,
            "fidelityDescription": self.fidelity_description,
            "operationsDescription": self.operations_description,
            "accessibleSummary": self.accessible_summary,
        }


def inspector_labels(frame: Mapping[str, object]) -> InspectorLabels:
    if not isinstance(frame, Mapping):
        raise TypeError("read-only frame mapping required")
    scope = frame.get("status")
    badge, temporal = _STATUS.get(scope, _STATUS["NOT_ACTIVE"])
    proof = frame.get("pathProofState")
    path = _PROOF.get(proof, "Ruta no certificada con las evidencias disponibles")
    if proof == "verified" and frame.get("lastProvenBoundary") not in {
        "ALSA",
        "USB_SUBMITTED",
        "DIGITAL_TAP",
        "PROCESSING_HOST",
        "REMOTE_REPORTED",
    }:
        path = "Verificación de ruta sin frontera certificada"
    # Any historical/pending path proof describes old/pending evidence only.
    if scope != "ACTIVE":
        path = "Sin verificación de ejecución activa"
    fidelity = "La fuente y la ruta no constituyen una prueba física de fidelidad"
    if frame.get("fidelityClaim") == "MATCHED_COMPLETE" and scope == "ACTIVE":
        # A48 doesn't read M11.5 signed/boundary proof; never elevate the claim.
        fidelity = (
            "Comparación declarada; revisar frontera, cobertura y autoridad M11.5"
        )
    order = (
        "Orden causal confirmado por recibo"
        if frame.get("operationOrderVerified") is True
        and frame.get("operationOrderProof") == "OWNER_ATTESTED"
        and scope == "ACTIVE"
        else "Operaciones observadas; orden causal no acreditado"
    )
    accessible = ". ".join((temporal, path, fidelity, order))
    return InspectorLabels(badge, temporal, path, fidelity, order, accessible)
