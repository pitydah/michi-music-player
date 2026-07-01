# Michi AI — Unified Contextual Intelligence Layer

## Decisión de Producto

A partir de ahora todo se llama visiblemente **Michi AI**. Michi Assistant deja de ser una marca visible separada. Puede seguir existiendo como concepto interno o compatibilidad técnica, pero la UI, documentación, rutas nuevas y experiencia del usuario se consolidan bajo Michi AI.

## Arquitectura

```
michi_ai/
├── context/
│   ├── ai_event_mapper.py       → Mapeo de eventos técnicos a legibles
│   ├── ai_context_bridge.py     → Bridge SyncManager → ContextService
│   ├── ai_snapshot_service.py   → Snapshot unificado sanitizado
│   └── ai_insight_service.py    → Insights determinísticos sin LLM
├── tools/
│   ├── tool_result.py           → ToolResult dataclass
│   ├── tool_permissions.py      → 8 niveles de permiso
│   ├── tool_registry.py         → Register, list, execute con confirmación
│   ├── library_tools.py         → 4 tools
│   ├── playlist_tools.py        → 2 tools
│   ├── audio_lab_tools.py       → 2 tools
│   ├── sync_tools.py            → 2 tools
│   ├── michi_link_tools.py      → 2 tools
│   └── config_tools.py          → 2 tools
├── planner/
│   ├── action_plan.py           → ActionPlan + PlanStep
│   ├── plan_builder.py          → 6 planes predefinidos
│   ├── plan_executor.py         → Preview + execute con validación
│   └── confirmation_policy.py   → Política de confirmación
└── ui/
    └── michi_ai_page.py         → Dashboard con insights + acciones
```

## Servicios Reutilizados

- ContextService (core/context/)
- DiagnosticsService (integrations/michi_link/services/)
- MicroServerService
- PlayerMicroCompatibilityReport
- SyncManager
- SettingsManager

## Privacidad

- No se envían filepaths al LLM
- No se envían tokens
- No se envían contraseñas
- No se envía la biblioteca completa
- Ollama solo en localhost si offline_strict=True
- Snapshots sanitizados automáticamente
