from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from michi_ai.v2.core.models import (
    ActionPlan, ParsedIntent,
    PlanStep,
)
from michi_ai.v2.intent.capability_resolver import CapabilityResolver
from michi_ai.v2.tools.tool_registry_v2 import ToolRegistryV2


class PlanBuilderV2:
    _ALIAS_MAP: dict[str, str] = {
        "create_smart_mix": "create_mix",
        "cancel_mix_generation": "cancel_mix",
    }

    def __init__(self, tool_registry: ToolRegistryV2, capability_resolver: CapabilityResolver | None = None) -> None:
        self._tool_registry = tool_registry
        self._capability_resolver = capability_resolver or tool_registry.capability_resolver

        self._plan_templates: dict[str, dict[str, Any]] = {
            "play_track": {
                "title": "Reproducir canción",
                "steps": [{"tool": "play_track", "depends_on": []}],
                "risks": [],
            },
            "play_album": {
                "title": "Reproducir álbum",
                "steps": [{"tool": "play_album", "depends_on": []}],
                "risks": [],
            },
            "play_artist": {
                "title": "Reproducir artista",
                "steps": [{"tool": "play_artist", "depends_on": []}],
                "risks": [],
            },
            "play_playlist": {
                "title": "Reproducir playlist",
                "steps": [{"tool": "play_playlist", "depends_on": []}],
                "risks": [],
            },
            "create_mix": {
                "title": "Crear mix inteligente",
                "steps": [{"tool": "create_smart_mix", "depends_on": []}],
                "risks": [],
            },
            "create_playlist": {
                "title": "Crear playlist",
                "steps": [
                    {"tool": "create_playlist", "depends_on": []},
                ],
                "risks": [],
            },
            "start_conversion": {
                "title": "Convertir archivos de audio",
                "steps": [
                    {"tool": "recommend_conversion_profile", "depends_on": []},
                    {"tool": "preview_conversion", "depends_on": ["step_0"]},
                    {"tool": "start_conversion", "depends_on": ["step_1"]},
                ],
                "risks": ["Conversión irreversible sin backup"],
                "confirmation_mode": "PER_DESTRUCTIVE_STEP",
            },
            "scan_library_health": {
                "title": "Diagnosticar biblioteca",
                "steps": [
                    {"tool": "scan_library_health", "depends_on": []},
                ],
                "risks": [],
            },
            "apply_library_repair": {
                "title": "Reparar biblioteca",
                "steps": [
                    {"tool": "scan_library_health", "depends_on": []},
                    {"tool": "preview_library_repair", "depends_on": ["step_0"]},
                    {"tool": "apply_library_repair", "depends_on": ["step_1"]},
                ],
                "risks": ["Modificación masiva de metadatos"],
                "confirmation_mode": "ONCE_PER_PLAN",
            },
            "plan_device_sync": {
                "title": "Sincronizar con dispositivo",
                "steps": [
                    {"tool": "plan_device_sync", "depends_on": []},
                    {"tool": "start_device_sync", "depends_on": ["step_0"]},
                ],
                "risks": ["Posible pérdida de datos en destino"],
                "confirmation_mode": "ONCE_PER_PLAN",
            },
            "general_query": {
                "title": "Consulta general",
                "steps": [],
                "risks": [],
            },
        }

    def build_plan(self, intent: ParsedIntent, context: dict[str, Any] | None = None, session_id: str = "") -> ActionPlan:
        ctx = context or {}
        intent_id = intent.intent_id

        resolved_id = self._ALIAS_MAP.get(intent_id, intent_id)
        template = self._plan_templates.get(resolved_id)
        if template is None:
            return self._build_fallback_plan(intent, session_id)

        steps: list[PlanStep] = []
        for i, step_def in enumerate(template.get("steps", [])):
            tool_name = step_def["tool"]
            tool_defn = self._tool_registry.get(tool_name)
            tool_args = self._build_args_for_tool(tool_name, intent, ctx)
            steps.append(PlanStep(
                step_id=f"step_{i}",
                tool=tool_name,
                arguments=tool_args,
                depends_on=tuple(step_def.get("depends_on", [])),
                on_failure=step_def.get("on_failure", "STOP"),
                rollback=step_def.get("rollback", ""),
                timeout=tool_defn.timeout_seconds if tool_defn else 30,
                cancellable=tool_defn.cancellable if tool_defn else False,
            ))

        requires_confirmation = template.get("confirmation_mode") in (
            "ONCE_PER_PLAN", "PER_DESTRUCTIVE_STEP"
        )

        plan_id = uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc)
        return ActionPlan(
            plan_id=plan_id,
            session_id=session_id,
            title=template.get("title", intent_id),
            description=f"Plan para: {intent.reasoning_summary}",
            intent=intent_id,
            steps=tuple(steps),
            risks=tuple(template.get("risks", [])),
            warnings=intent.negated_actions,
            requires_confirmation=requires_confirmation,
            confirmation_scope=template.get("confirmation_mode", "NONE"),
            rollback_strategy="STOP",
            created_at=now.isoformat(),
            expires_at=(now + timedelta(minutes=5)).isoformat(),
        )

    def _build_args_for_tool(self, tool_name: str, intent: ParsedIntent, context: dict[str, Any]) -> dict[str, Any]:
        args: dict[str, Any] = {}

        if tool_name in ("play_track", "play_album", "play_artist", "play_playlist"):
            if "artist" in intent.entities:
                args["artist"] = intent.entities["artist"]
            if "album" in intent.entities:
                args["album"] = intent.entities["album"]
            if "track" in intent.entities:
                args["track"] = intent.entities["track"]
            if "playlist" in intent.entities:
                args["playlist_name"] = intent.entities["playlist"]

        if tool_name == "add_to_queue" and "selection" in context and context["selection"]:
            args["track_ids"] = context["selection"].get("track_ids", [])

        if tool_name == "create_smart_mix":
            if "genre" in intent.entities:
                args["genre"] = intent.entities["genre"]
            if "decade" in intent.entities:
                args["decade"] = intent.entities["decade"]
            if "year" in intent.entities:
                args["year"] = intent.entities["year"]

        if tool_name in ("recommend_conversion_profile", "start_conversion") and "format" in intent.entities:
            args["target_format"] = intent.entities["format"]

        if tool_name in ("set_volume",):
            m = __import__("re").search(r"(\d+)", str(intent.entities))
            if m:
                args["level"] = int(m.group(1))

        if intent.constraints:
            args["constraints"] = intent.constraints

        return args

    def _build_fallback_plan(self, intent: ParsedIntent, session_id: str) -> ActionPlan:
        plan_id = uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc)
        return ActionPlan(
            plan_id=plan_id,
            session_id=session_id,
            title="Consulta",
            description=intent.reasoning_summary,
            intent=intent.intent_id,
            created_at=now.isoformat(),
            expires_at=(now + timedelta(minutes=2)).isoformat(),
        )
