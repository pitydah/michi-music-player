"""Map technical events to human-readable Michi AI events."""

EVENT_MAP: dict[str, str] = {
    "sync_started": "Michi Sync iniciado",
    "sync_stopped": "Michi Sync detenido",
    "client_connected": "Dispositivo conectado",
    "peer_found": "Servidor o dispositivo encontrado",
    "peer_lost": "Dispositivo perdido",
    "micro_server_discovered": "Micro Server detectado",
    "micro_server_paired": "Micro Server emparejado",
    "micro_server_pairing_started": "Emparejamiento con Micro Server iniciado",
    "micro_server_import_started": "Importacion a Micro Server iniciada",
    "micro_server_import_finished": "Importacion a Micro Server finalizada",
    "continue_on_server_started": "Continuar reproduccion en servidor iniciado",
    "continue_on_server_confirmed": "Reproduccion transferida al servidor",
    "audio_analysis_started": "Analisis de audio iniciado",
    "audio_analysis_finished": "Analisis de audio finalizado",
    "audio_analysis_failed": "Analisis de audio fallo",
    "audio_lab_warning_detected": "Advertencia de Audio Lab detectada",
    "michi_ai_opened": "Michi AI abierto",
    "michi_ai_insight_generated": "Insight generado",
    "michi_ai_plan_created": "Plan creado",
    "michi_ai_plan_applied": "Plan aplicado",
    "michi_ai_tool_executed": "Herramienta ejecutada",
    "michi_ai_tool_failed": "Error al ejecutar herramienta",
    "michi_ai_confirmation_required": "Confirmacion requerida",
}


def map_event(event_type: str) -> str:
    return EVENT_MAP.get(event_type, event_type)
