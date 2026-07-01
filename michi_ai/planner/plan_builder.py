"""PlanBuilder — create ActionPlan from snapshot, insight, or plan_type."""

from __future__ import annotations

import uuid
from typing import Any

from michi_ai.planner.action_plan import ActionPlan, PlanStep

_PLAN_DEFS: dict[str, dict[str, Any]] = {
    "prepare_mobile_sync": {
        "title": "Preparar sincronizacion movil",
        "description": "Activa la sincronizacion y prepara el perfil para dispositivos moviles.",
        "steps": [PlanStep(tool="start_sync", description="Activar Sync")],
        "risks": ["Bajo"],
        "tests": ["Verificar Sync activo"],
    },
    "prepare_micro_server_remote": {
        "title": "Preparar Micro Server remoto",
        "description": "Configura perfil de streaming liviano para conexion remota.",
        "steps": [PlanStep(tool="create_config_plan", params={"plan_type": "setup_micro_server_remote"}, description="Crear plan de configuracion Micro Server")],
        "risks": ["Bajo"],
        "tests": [],
    },
    "prepare_space_saver_mobile": {
        "title": "Perfil de ahorro de espacio para Mobile",
        "description": "Configura perfil de conversion ligero (Opus 128k).",
        "steps": [PlanStep(tool="create_config_plan", params={"plan_type": "setup_mobile_space_saver_profile"}, description="Crear plan space saver")],
        "risks": ["Bajo"],
        "tests": [],
    },
    "prepare_hifi_profile": {
        "title": "Configurar perfil Hi-Fi",
        "description": "Configura salida bit-perfect para reproduccion Hi-Fi.",
        "steps": [PlanStep(tool="create_config_plan", params={"plan_type": "setup_hifi_profile"}, description="Crear plan Hi-Fi")],
        "risks": ["Bajo"],
        "tests": [],
    },
    "prepare_home_audio": {
        "title": "Configurar Home Audio",
        "description": "Activa Home Audio, Snapcast y API de Michi.",
        "steps": [PlanStep(tool="create_config_plan", params={"plan_type": "setup_home_audio"}, description="Crear plan Home Audio")],
        "risks": ["Bajo"],
        "tests": [],
    },
    "clean_library_metadata": {
        "title": "Limpiar metadatos de biblioteca",
        "description": "Revisa canciones con metadatos incompletos.",
        "steps": [PlanStep(tool="list_missing_metadata", description="Identificar metadatos incompletos")],
        "risks": ["Ninguno"],
        "tests": [],
    },
}


class PlanBuilder:
    def create_plan(self, plan_type: str, context: dict[str, Any] | None = None) -> ActionPlan:
        definition = _PLAN_DEFS.get(plan_type)
        if definition is None:
            raise ValueError(f"Unknown plan type: {plan_type}")
        return ActionPlan(
            plan_id=str(uuid.uuid4())[:8],
            title=definition["title"],
            description=definition["description"],
            steps=list(definition.get("steps", [])),
            risks=list(definition.get("risks", [])),
            tests=list(definition.get("tests", [])),
            requires_confirmation=True,
            rollback_available=True,
        )

    def list_plan_types(self) -> list[dict[str, str]]:
        return [{"type": k, "title": v["title"], "description": v["description"]} for k, v in _PLAN_DEFS.items()]
