"""LibrarySource and LibraryScope — music source and scope models for multi-source libraries."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LibrarySource:
    id: str = ""
    name: str = ""
    source_type: str = "local_file"
    connection_profile_id: str | None = None
    base_url: str | None = None
    enabled: bool = True
    visible: bool = True
    color: str | None = None
    icon: str | None = None
    priority: int = 100
    last_sync_at: str | None = None
    status: str = "unknown"


@dataclass
class LibraryScope:
    id: str = ""
    name: str = ""
    mode: str = "single_source"
    source_ids: list[str] = field(default_factory=list)
    allow_cross_source: bool = False


def build_default_sources(db=None) -> list[LibrarySource]:
    sources: list[LibrarySource] = [
        LibrarySource(
            id="local_music", name="Musica local",
            source_type="local_file", priority=10, status="available",
            icon="sidebar_library",
        ),
    ]

    try:
        import json
        import os
        path = os.path.expanduser("~/.local/share/michi-music-player/subsonic_servers.json")
        if os.path.exists(path):
            with open(path) as f:
                servers = json.load(f)
            for srv in servers:
                sname = srv.get("name", "Servidor")
                stype = srv.get("stype", "navidrome")
                sid = f"{stype}_{sname.lower().replace(' ', '_')}"
                sources.append(LibrarySource(
                    id=sid, name=sname, source_type=stype,
                    connection_profile_id=sid,
                    base_url=srv.get("url", ""), priority=50,
                    status="configured",
                    icon="sidebar_navidrome" if stype == "navidrome" else "sidebar_jellyfin",
                ))
    except Exception:
        pass

    return sources


def build_default_scopes(sources: list[LibrarySource]) -> list[LibraryScope]:
    scopes: list[LibraryScope] = [
        LibraryScope(
            id="local_music", name="Musica local",
            mode="single_source", source_ids=["local_music"],
            allow_cross_source=False,
        ),
    ]

    for s in sources:
        if s.source_type in ("navidrome", "jellyfin") and s.enabled:
            scopes.append(LibraryScope(
                id=s.id, name=s.name,
                mode="single_source", source_ids=[s.id],
                allow_cross_source=False,
            ))

    remote_ids = [s.id for s in sources if s.source_type in ("navidrome", "jellyfin") and s.enabled]
    if remote_ids:
        scopes.append(LibraryScope(
            id="smart_mix", name="Mix inteligente",
            mode="mixed_sources",
            source_ids=["local_music"] + remote_ids,
            allow_cross_source=True,
        ))

    return scopes
