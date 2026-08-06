"""ActionContext — explicit execution context for actions.

Actions executed through ``ActionRegistry`` must know their target explicitly
(ADR-003 transition): entity type/id, the selection version the action was
built for, the originating route/component, and any parameters. Silent lookup
of the global selection is deprecated; when a context is provided it is the
only source of truth for the action target.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ActionContext:
    entity_type: str = ""                 # track|album|artist|playlist|radio|genre|folder|source
    entity_id: str = ""                   # stable id (track_uid, album_key, ...)
    public_ref: str = ""                  # UI-facing reference (e.g. "track_42")
    selection_version: int = 0            # version of the selection the action targets
    source_route: str = ""                # QML route that requested the action
    source_component: str = ""            # QML component that requested the action
    selected_ids: tuple[int, ...] = ()    # secondary ids (bulk actions)
    parameters: dict[str, Any] = field(default_factory=dict)
    requested_at: float = field(default_factory=time.time)

    def command_hash(self, command: str = "") -> str:
        """Stable hash over the command and all context material.

        Confirmation is bound to this hash: confirming an action for one
        context never authorizes a different context (selection changed,
        different entity, different parameters).
        """
        material = json.dumps(
            [
                command or "",
                self.entity_type or "",
                self.entity_id or "",
                self.public_ref or "",
                int(self.selection_version or 0),
                sorted(int(i) for i in self.selected_ids),
                sorted((str(k), str(v)) for k, v in self.parameters.items()),
            ],
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict:
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "public_ref": self.public_ref,
            "selection_version": self.selection_version,
            "source_route": self.source_route,
            "source_component": self.source_component,
            "selected_ids": list(self.selected_ids),
            "parameters": dict(self.parameters),
            "requested_at": self.requested_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ActionContext":
        data = data or {}
        selected = data.get("selected_ids") or []
        try:
            selected_ids = tuple(int(i) for i in selected)
        except (TypeError, ValueError):
            selected_ids = ()
        parameters = data.get("parameters")
        if not isinstance(parameters, dict):
            parameters = {}
        return cls(
            entity_type=str(data.get("entity_type") or ""),
            entity_id=str(data.get("entity_id") or ""),
            public_ref=str(data.get("public_ref") or ""),
            selection_version=int(data.get("selection_version") or 0),
            source_route=str(data.get("source_route") or ""),
            source_component=str(data.get("source_component") or ""),
            selected_ids=selected_ids,
            parameters=parameters,
            requested_at=float(data.get("requested_at") or time.time()),
        )
