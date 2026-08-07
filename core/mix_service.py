"""MixService — real mix generation using recommendation and rule engines.
Single facade for the mix domain (ADR-002): SmartMixService (generator),
MixQueryService (SQL queries), MixRuleEngine + MixRepository (custom mixes),
RecommendationService (scoring).  Generation returns explicit
MixGenerationStatus outcomes — an empty result is never presented as a
generated mix.
"""
from __future__ import annotations

import contextlib
import json
import logging
from typing import Any

from core.mix.models import KNOWN_STRATEGIES, MixGenerationStatus
from core.mix_rules import MixRuleEngine
from core.mix.repository import MixRepository
from core.mix_rules import MixDefinition as MixEngineDef, MixRuleGroup, MixRule
from core.mix.repository import MixDefinition as PersistedMix

logger = logging.getLogger("michi.mix_service")

# Query-backed strategies: generated through MixQueryService with the same
# explicit-outcome semantics as smart strategies (S10): an empty result is
# NO_MATCHES / EMPTY_LIBRARY with ok=False, never a fake success.
QUERY_STRATEGIES = frozenset({
    "favorites", "most_played", "unplayed", "rediscovery",
    "by_artist", "by_genre", "by_album", "by_decade", "by_year",
    "high_quality", "custom",
})

# Smart strategy aliases: QML category ids that map onto SmartMixService
# strategy names (business mapping lives in the service, not the bridge).
SMART_ALIASES = {
    "daily_mix": "daily",
}

REASON_LABELS = {
    "favorites": "Favoritos",
    "most_played": "Más escuchadas",
    "unplayed": "No escuchadas",
    "rediscovery": "Redescubrimiento",
    "by_artist": "Por artista",
    "by_genre": "Por género",
    "by_album": "Por álbum",
    "by_decade": "Por década",
    "by_year": "Por año",
    "high_quality": "Alta calidad",
    "custom": "Mix personalizado",
}


class MixService:
    def __init__(self, db=None, recommendation_service=None, smart_mix_service=None,
                 library_query_service=None, playlist_service=None, event_bus=None,
                 mix_query_service=None):
        self._db = db
        self._event_bus = event_bus
        self._recommendation = recommendation_service
        self._smart_mix = smart_mix_service
        self._library_query = library_query_service
        self._playlist_service = playlist_service
        self._rule_engine = MixRuleEngine(library_query_service)
        self._repo = MixRepository(db) if db else None
        self._cancelled = False
        self._last_result: dict | None = None
        if mix_query_service is not None:
            self._queries = mix_query_service
        elif db is not None:
            from core.mix_query_service import MixQueryService
            self._queries = MixQueryService(db)
        else:
            self._queries = None

    @property
    def available(self) -> bool:
        return self._smart_mix is not None or self._library_query is not None

    # ── Generation ────────────────────────────────────────────────────────

    def generate(self, strategy: str = "daily", seed: dict | None = None,
                 limit: int = 30) -> dict:
        """Generate a mix with an explicit outcome status (MixGenerationStatus).

        Single entry point for EVERY strategy: smart strategies
        (SmartMixService), the "recent" history strategy, the QML query
        categories (favorites, by_artist, custom, ...) and the
        "daily_mix" alias.  ``ok`` is True only for
        COMPLETED_WITH_TRACKS / PARTIAL_RECOMMENDATION; NO_MATCHES /
        EMPTY_LIBRARY / INVALID_STRATEGY / GENERATOR_UNAVAILABLE return
        ``ok=False`` with the status that explains why.
        """
        self._cancelled = False
        if strategy not in KNOWN_STRATEGIES:
            return self._outcome(
                ok=False, status=MixGenerationStatus.INVALID_STRATEGY,
                message=f"Estrategia desconocida: {strategy}", strategy=strategy,
            )
        result = self._generate_impl(strategy, seed, limit)
        self._last_result = result
        return result

    def _generate_impl(self, strategy: str, seed: dict | None,
                       limit: int) -> dict:
        strategy = SMART_ALIASES.get(strategy, strategy)
        if strategy in QUERY_STRATEGIES:
            return self._generate_from_queries(strategy, seed, limit)
        if strategy == "recent":
            return self._generate_recent(limit)
        if self._smart_mix is None:
            return self._outcome(
                ok=False, status=MixGenerationStatus.GENERATOR_UNAVAILABLE,
                message="Generador de mixes no disponible", strategy=strategy,
            )
        try:
            mix = self._smart_mix.create_mix(strategy=strategy, seed=seed, limit=limit)
        except Exception as e:
            logger.error("SmartMix error: %s", e)
            return self._outcome(
                ok=False, status=MixGenerationStatus.GENERATOR_UNAVAILABLE,
                message="El generador de mixes falló", strategy=strategy, error=str(e),
            )

        tracks = list(getattr(mix, "tracks", []) or [])
        if not tracks:
            status = (
                MixGenerationStatus.EMPTY_LIBRARY
                if self._library_empty()
                else MixGenerationStatus.NO_MATCHES
            )
            return self._outcome(
                ok=False, status=status,
                message=("La biblioteca no tiene canciones"
                         if status == MixGenerationStatus.EMPTY_LIBRARY
                         else "Ninguna canción coincide con el criterio del mix"),
                strategy=strategy, mix_id=getattr(mix, "mix_id", ""),
            )

        warnings = list(getattr(mix, "warnings", []) or [])
        status = (
            MixGenerationStatus.PARTIAL_RECOMMENDATION
            if warnings
            else MixGenerationStatus.COMPLETED_WITH_TRACKS
        )
        return self._format_mix(mix, status=status, warnings=warnings)

    def _generate_from_queries(self, strategy: str, seed: dict | None,
                               limit: int) -> dict:
        """Generate a query-backed category mix with explicit outcomes.

        Empty results are honest NO_MATCHES / EMPTY_LIBRARY (ok=False) —
        never an empty success.  Tracks are built as fresh copies, so the
        reason label never mutates the query service's dicts.
        """
        if self._queries is None:
            return self._outcome(
                ok=False, status=MixGenerationStatus.GENERATOR_UNAVAILABLE,
                message="Servicio de consultas de mix no disponible",
                strategy=strategy,
            )
        try:
            items = self._query_items(strategy, seed, limit)
        except Exception as e:
            logger.error("Mix query %s error: %s", strategy, e)
            return self._outcome(
                ok=False, status=MixGenerationStatus.GENERATOR_UNAVAILABLE,
                message="Fallo al consultar canciones", strategy=strategy,
                error=str(e),
            )
        if not items:
            status = (
                MixGenerationStatus.EMPTY_LIBRARY
                if self._library_empty()
                else MixGenerationStatus.NO_MATCHES
            )
            return self._outcome(
                ok=False, status=status,
                message=("La biblioteca no tiene canciones"
                         if status == MixGenerationStatus.EMPTY_LIBRARY
                         else "Ninguna canción coincide con el criterio del mix"),
                strategy=strategy, mix_id=f"query:{strategy}",
            )
        tracks = self._normalize_query_tracks(items, strategy)
        return self._outcome(
            ok=True, status=MixGenerationStatus.COMPLETED_WITH_TRACKS,
            message="Mix generado", strategy=strategy,
            mix_id=f"query:{strategy}", tracks=tracks, count=len(tracks),
        )

    def _query_items(self, strategy: str, seed: dict | None,
                     limit: int) -> list[dict]:
        seed = seed or {}
        if strategy == "favorites":
            return self._queries.favorites(limit)
        if strategy == "most_played":
            return self._queries.most_played(limit)
        if strategy == "unplayed":
            return self._queries.unplayed(limit)
        if strategy == "rediscovery":
            return self._queries.rediscovery(limit)
        if strategy == "by_artist":
            return self._queries.by_field("artist", value=seed.get("artist", ""),
                                          limit=limit)
        if strategy == "by_genre":
            return self._queries.by_field("genre", value=seed.get("genre", ""),
                                          limit=limit)
        if strategy == "by_album":
            return self._queries.by_field("album", value=seed.get("album", ""),
                                          limit=limit)
        if strategy == "custom":
            if seed.get("artist"):
                return self._queries.by_field("artist", value=seed["artist"],
                                              limit=limit)
            if seed.get("genre"):
                return self._queries.by_field("genre", value=seed["genre"],
                                              limit=limit)
            return self._queries.by_field("artist", limit=limit)
        if strategy == "by_decade":
            return self._queries.by_decade(decade=int(seed.get("year") or 0),
                                           limit=limit)
        if strategy == "by_year":
            return self._queries.by_year(year=int(seed.get("year") or 0),
                                         limit=limit)
        if strategy == "high_quality":
            return self._queries.high_quality(limit=limit)
        return []

    def _normalize_query_tracks(self, items: list[dict],
                                strategy: str) -> list[dict]:
        """Normalize query rows into canonical track dicts (copies only)."""
        tracks = []
        for item in items:
            track_id = item.get("track_id") or item.get("id", 0)
            track = dict(item)
            track["id"] = track_id
            track["track_id"] = track_id
            track.setdefault("score", 0.0)
            track["reason"] = REASON_LABELS.get(strategy, "")
            tracks.append(track)
        return tracks

    def _generate_recent(self, limit: int) -> dict:
        if self._library_query is None:
            return self._outcome(
                ok=False, status=MixGenerationStatus.GENERATOR_UNAVAILABLE,
                message="Servicio de biblioteca no disponible", strategy="recent",
            )
        try:
            items = self._library_query.recently_played(limit=limit) or []
        except Exception as e:
            return self._outcome(
                ok=False, status=MixGenerationStatus.GENERATOR_UNAVAILABLE,
                message="Fallo al consultar recientes", strategy="recent", error=str(e),
            )
        if not items:
            status = (
                MixGenerationStatus.EMPTY_LIBRARY
                if self._library_empty()
                else MixGenerationStatus.NO_MATCHES
            )
            return self._outcome(
                ok=False, status=status,
                message=("La biblioteca no tiene canciones"
                         if status == MixGenerationStatus.EMPTY_LIBRARY
                         else "Sin canciones reproducidas recientemente"),
                strategy="recent",
            )
        tracks = [
            {
                "id": t.get("track_id") or t.get("id", 0),
                "track_id": t.get("track_id") or t.get("id", 0),
                "title": t.get("title", ""), "artist": t.get("artist", ""),
                "album": t.get("album", ""), "score": 0.0,
                "reason": "Escuchadas recientemente",
            }
            for t in items
        ]
        return self._outcome(
            ok=True, status=MixGenerationStatus.COMPLETED_WITH_TRACKS,
            message="Mix de recientes generado", strategy="recent",
            mix_id="query:recent", tracks=tracks, count=len(tracks),
        )

    def _outcome(self, ok: bool, status: MixGenerationStatus, message: str,
                 strategy: str = "", mix_id: str = "", tracks: list | None = None,
                 count: int = 0, error: str = "", warnings: list | None = None) -> dict:
        result = {
            "ok": ok,
            "status": status.value if isinstance(status, MixGenerationStatus) else status,
            "code": status.value if isinstance(status, MixGenerationStatus) else status,
            "message": message,
            "strategy": strategy,
            "mix_id": mix_id,
            "tracks": tracks or [],
            "count": count,
            "warnings": warnings or [],
        }
        if error:
            result["error"] = error
        return result

    def _library_empty(self) -> bool:
        if self._library_query is not None and hasattr(self._library_query, "count_tracks"):
            try:
                return self._library_query.count_tracks() == 0
            except Exception:
                pass
        if self._db is not None and hasattr(self._db, "get_all"):
            try:
                return not self._db.get_all()
            except Exception:
                pass
        return False

    def _format_mix(self, mix, status: MixGenerationStatus | None = None,
                    warnings: list | None = None) -> dict:
        tracks = []
        for t in getattr(mix, "tracks", []) or []:
            track = {
                "id": getattr(t, "track_id", 0) or getattr(t, "id", 0),
                "track_id": getattr(t, "track_id", 0) or getattr(t, "id", 0),
                "title": getattr(t, "title", ""),
                "artist": getattr(t, "artist", ""),
                "album": getattr(t, "album", ""),
                "score": getattr(t, "score", 0.0),
            }
            reasons = list(getattr(t, "reasons", []) or [])
            if reasons:
                track["reasons"] = reasons
                track["reason"] = "; ".join(str(r) for r in reasons)
            explanation = self._explain_track(t, reasons)
            if explanation is not None:
                track["explanation"] = explanation
            tracks.append(track)
        return self._outcome(
            ok=True,
            status=status or MixGenerationStatus.COMPLETED_WITH_TRACKS,
            message="Mix generado",
            strategy=getattr(mix, "strategy", "unknown"),
            mix_id=getattr(mix, "mix_id", ""),
            tracks=tracks, count=len(tracks),
            warnings=warnings or [],
        )

    def _explain_track(self, track: Any, reasons: list[str]) -> dict | None:
        try:
            from recommendation.recommendation_explainer import explain
            exp = explain(track)
            return {
                "reason_summary": exp.reason_summary,
                "detailed_reasons": list(exp.detailed_reasons or reasons),
            }
        except Exception:
            return None

    # ── Save-as-playlist ──────────────────────────────────────────────────

    def save_mix_as_playlist(self, mix_id: str, name: str) -> dict:
        """Persist the last generated mix (matched by *mix_id*) as a playlist.

        Uses the REAL playlist id from ``playlist_service.create()["id"]`` —
        never a dict — and reports PARTIAL_SUCCESS with counts when some
        tracks fail; an empty save is never reported as a full success.
        """
        if self._playlist_service is None:
            return {"ok": False, "status": "FAILED",
                    "error_code": "NO_PLAYLIST_SERVICE"}
        result = self._last_result or {}
        if not result or result.get("mix_id") != mix_id:
            return {"ok": False, "status": "FAILED",
                    "error_code": "NO_MIX_CONTENT",
                    "detail": "El mix no está disponible para guardar"}
        track_ids = [
            t.get("id") or t.get("track_id")
            for t in (result.get("tracks") or [])
            if t.get("id") or t.get("track_id")
        ]
        if not track_ids:
            return {"ok": False, "status": "FAILED", "error_code": "EMPTY_MIX",
                    "detail": "El mix no tiene canciones para guardar"}
        try:
            create_result = self._playlist_service.create(name)
        except Exception as e:
            return {"ok": False, "status": "FAILED",
                    "error_code": "CREATE_FAILED", "detail": str(e)}
        if not isinstance(create_result, dict) or not create_result.get("ok"):
            return {"ok": False, "status": "FAILED",
                    "error_code": "CREATE_FAILED",
                    "detail": "No se pudo crear la playlist"}
        playlist_id = create_result.get("id")
        if playlist_id is None or isinstance(playlist_id, dict):
            return {"ok": False, "status": "FAILED",
                    "error_code": "CREATE_FAILED",
                    "detail": "Id de playlist inválido"}
        added = 0
        failed = 0
        for track_id in track_ids:
            try:
                add_result = self._playlist_service.add_track(playlist_id, track_id)
                if isinstance(add_result, dict) and not add_result.get("ok"):
                    failed += 1
                else:
                    added += 1
            except Exception:
                failed += 1
        if added == 0:
            return {"ok": False, "status": "FAILED",
                    "error_code": "SAVE_FAILED",
                    "requested": len(track_ids), "added": 0,
                    "failed": len(track_ids),
                    "detail": "No se pudo agregar ninguna canción"}
        status = "PARTIAL_SUCCESS" if failed else "COMPLETED"
        return {"ok": True, "status": status, "playlist_id": playlist_id,
                "requested": len(track_ids), "added": added, "failed": failed}

    # ── Mix query facade (MixQueryService delegation, bridge contract) ────

    def favorites(self, limit: int = 50) -> list[dict]:
        return self._queries.favorites(limit) if self._queries else []

    def recent(self, limit: int = 50) -> list[dict]:
        return self._queries.recent(limit) if self._queries else []

    def most_played(self, limit: int = 50) -> list[dict]:
        return self._queries.most_played(limit) if self._queries else []

    def unplayed(self, limit: int = 50) -> list[dict]:
        return self._queries.unplayed(limit) if self._queries else []

    def rediscovery(self, limit: int = 50) -> list[dict]:
        return self._queries.rediscovery(limit) if self._queries else []

    def by_field(self, field: str, value: str = "", limit: int = 30) -> list[dict]:
        return self._queries.by_field(field, value=value, limit=limit) if self._queries else []

    def by_decade(self, limit: int = 30) -> list[dict]:
        return self._queries.by_decade(limit=limit) if self._queries else []

    def by_year(self, limit: int = 30) -> list[dict]:
        return self._queries.by_year(limit=limit) if self._queries else []

    def high_quality(self, limit: int = 30) -> list[dict]:
        return self._queries.high_quality(limit=limit) if self._queries else []

    # ── Custom rule mixes ─────────────────────────────────────────────────

    def save_rules(self, mix_id: str, rules_json: str) -> dict:
        try:
            data = json.loads(rules_json)
            definition = MixEngineDef(
                name=data.get("name", mix_id),
                groups=[MixRuleGroup(
                    rules=[MixRule(**r) for r in g.get("rules", [])],
                    logic=g.get("logic", "AND"))
                    for g in data.get("groups", [])],
                limit=data.get("limit", 30),
                sort_by=data.get("sort_by", "random"),
                seed=data.get("seed", 0),
            )
            new_id = self._rule_engine.generate_id(definition)

            if self._repo:
                persisted = PersistedMix(
                    mix_id=new_id, name=definition.name, rules_json=rules_json,
                    limit=definition.limit, sort_by=definition.sort_by, seed=definition.seed,
                )
                self._repo.save(persisted)

            return {"ok": True, "mix_id": new_id}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def load_rules(self, mix_id: str) -> dict:
        if not self._repo:
            return {"ok": False, "error": "REPOSITORY_UNAVAILABLE"}
        definition = self._repo.load(mix_id)
        if not definition:
            return {"ok": False, "error": "NOT_FOUND"}
        return {
            "ok": True, "mix_id": definition.mix_id, "name": definition.name,
            "rules_json": definition.rules_json, "limit": definition.limit,
            "sort_by": definition.sort_by, "seed": definition.seed,
            "created_at": definition.created_at, "updated_at": definition.updated_at,
            "play_count": definition.play_count,
        }

    def list_rules(self) -> dict:
        if not self._repo:
            return {"ok": False, "error": "REPOSITORY_UNAVAILABLE", "mixes": []}
        mixes = self._repo.list_all()
        return {"ok": True, "mixes": [{
            "mix_id": m.mix_id, "name": m.name,
            "updated_at": m.updated_at, "play_count": m.play_count,
        } for m in mixes]}

    def delete_rules(self, mix_id: str) -> dict:
        if not self._repo:
            return {"ok": False, "error": "REPOSITORY_UNAVAILABLE"}
        return self._repo.delete(mix_id)

    def preview_rules(self, rules_json: str, limit: int = 10) -> dict:
        try:
            data = json.loads(rules_json)
            definition = MixEngineDef(
                name=data.get("name", "preview"),
                groups=[MixRuleGroup(rules=[MixRule(**r) for r in g.get("rules", [])],
                                     logic=g.get("logic", "AND"))
                        for g in data.get("groups", [])],
                limit=limit, sort_by=data.get("sort_by", "random"),
                seed=data.get("seed", 0),
            )
            if not self._library_query:
                return {"ok": False, "error": "LIBRARY_UNAVAILABLE", "tracks": []}
            scanned = self._library_query.fetch_tracks(offset=0, limit=500)
            matched = self._rule_engine.filter(scanned, definition)
            total = len(scanned)
            if hasattr(self._library_query, "count_tracks"):
                with contextlib.suppress(Exception):
                    total = self._library_query.count_tracks()
            return {"ok": True, "matched": len(matched),
                    "tracks": matched[:limit],
                    "total_scanned": len(scanned),
                    "total_in_library": total}
        except json.JSONDecodeError as e:
            return {"ok": False, "error": f"Invalid JSON: {e}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}
