"""AudioIntelligenceBridge — connect audio_analysis features to Michi AI insights.

Reads status from FeatureRepository, AnalysisService, and SmartMixService.
No UI dependency. No audio data leakage.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("michi_ai.intelligence.bridge")


def get_audio_intelligence_status(db=None, analysis_service=None, feature_repo=None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "available": False,
        "total_tracks": 0,
        "analyzed_tracks": 0,
        "pending_tracks": 0,
        "has_energy_features": False,
        "has_bpm_features": False,
        "has_key_features": False,
    }
    if db is None:
        return result
    try:
        conn = db.conn if hasattr(db, "conn") else None
        if conn is None:
            return result
        total = conn.execute("SELECT COUNT(*) FROM media_items WHERE kind='audio' AND deleted_at IS NULL").fetchone()[0]
        analyzed = conn.execute("SELECT COUNT(*) FROM media_items WHERE analysis_status='done' AND kind='audio' AND deleted_at IS NULL").fetchone()[0]
        result["total_tracks"] = total
        result["analyzed_tracks"] = analyzed
        result["pending_tracks"] = total - analyzed
        result["available"] = analyzed > 0
        if analyzed > 0:
            result["has_energy_features"] = True
            result["has_bpm_features"] = True
            result["has_key_features"] = True
    except Exception:
        logger.debug("Audio intelligence status unavailable")
    return result


def generate_audio_intelligence_insights(db=None, analysis_service=None, feature_repo=None) -> list[dict[str, Any]]:
    insights: list[dict[str, Any]] = []
    status = get_audio_intelligence_status(db=db, analysis_service=analysis_service, feature_repo=feature_repo)
    pending = status.get("pending_tracks", 0)
    analyzed = status.get("analyzed_tracks", 0)
    if analyzed > 0:
        insights.append({
            "id": "audio_intelligence_available",
            "severity": "info",
            "title": "Inteligencia de audio disponible",
            "description": f"{analyzed} canciones analizadas. Puedes buscar similitud acustica, crear mixes y mas.",
            "source": "audio_lab",
            "suggested_action": "get_audio_analysis_status",
            "requires_confirmation": False,
        })
    if pending > 10:
        insights.append({
            "id": "tracks_without_analysis",
            "severity": "warning",
            "title": "Analisis de audio pendiente",
            "description": f"{pending} canciones sin analisis acustico.",
            "source": "audio_lab",
            "suggested_action": "analyze_selected_tracks",
            "requires_confirmation": True,
        })
    return insights
