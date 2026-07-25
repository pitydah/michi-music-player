"""Canonical hierarchical route registry with sidebar metadata, icons, and aliases.

RouteSpec structure (all keys):
  - route: str               canonical route key
  - parent: str | None       parent route for hierarchy (None = top-level section)
  - title: str               display title
  - breadcrumb_title: str    short title for breadcrumbs (defaults to title)
  - source: str              QML file path relative to shell/
  - icon: str                icon key (filename without .svg in icons/sidebar/)
  - order: int               display order within parent group
  - sidebar_visible: bool    whether this route appears in sidebar
  - sidebar_group: str       group label shown as section header
  - status: str              functional|partial|experimental|planned|configuration_required|dependency_missing|hardware_validation_pending|unavailable|deprecated
  - capability: str | None   capability key required for this route
  - aliases: list[str]       legacy route keys that redirect here
  - keywords: list[str]      search keywords
  - placeholder_state: str   state shown in FeatureStatePage when status != functional
  - params: dict | None      route parameter specifications
  - expandable: bool         whether this section can be expanded/collapsed in sidebar
  - category: str            legacy category (core/library/detail/tools/settings/experimental)
"""

from __future__ import annotations

ROUTES: dict[str, dict] = {
    # ═══════════════════════════════════════════════════════════════════
    # 1. HOME
    # ═══════════════════════════════════════════════════════════════════
    "home": {
        "route": "home", "parent": None, "title": "Inicio",
        "breadcrumb_title": "Inicio",
        "source": "../pages/home/HomePage.qml",
        "icon": "home", "order": 10, "sidebar_visible": True,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [], "keywords": ["inicio", "dashboard", "home"],
        "placeholder_state": None,
        "params": None, "category": "core",
    },

    # ═══════════════════════════════════════════════════════════════════
    # 2. LIBRARY
    # ═══════════════════════════════════════════════════════════════════
    "library": {
        "route": "library", "parent": None, "title": "Biblioteca",
        "breadcrumb_title": "Biblioteca",
        "source": "../pages/library/LibraryPage.qml",
        "icon": "library", "order": 20, "sidebar_visible": True,
        "sidebar_group": None, "expandable": True,
        "status": "functional", "capability": None,
        "aliases": [], "keywords": ["biblioteca", "library", "canciones", "albums", "artistas"],
        "placeholder_state": None,
        "params": None, "category": "core",
    },
    "library.songs": {
        "route": "library.songs", "parent": "library", "title": "Canciones",
        "breadcrumb_title": "Canciones",
        "source": "../pages/library/tracks/TracksPage.qml",
        "icon": "songs", "order": 10, "sidebar_visible": True,
        "sidebar_group": "library", "expandable": False,
        "status": "functional", "capability": None,
        "aliases": ["library.tracks"],
        "keywords": ["canciones", "tracks", "songs", "pistas"],
        "placeholder_state": None,
        "params": None, "category": "library",
    },
    "library.albums": {
        "route": "library.albums", "parent": "library", "title": "Álbumes",
        "breadcrumb_title": "Álbumes",
        "source": "../pages/library/AlbumGridPage.qml",
        "icon": "albums", "order": 20, "sidebar_visible": True,
        "sidebar_group": "library", "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": ["álbumes", "albums", "discos"],
        "placeholder_state": None,
        "params": None, "category": "library",
    },
    "library.album_detail": {
        "route": "library.album_detail", "parent": "library.albums",
        "title": "Álbum", "breadcrumb_title": "Álbum",
        "source": "../pages/library/AlbumDetailPage.qml",
        "icon": "albums", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": ["album_detail"],
        "keywords": [],
        "placeholder_state": None,
        "params": {"album_key": {"required": True, "type": "string"}},
        "category": "detail",
    },
    "library.artists": {
        "route": "library.artists", "parent": "library", "title": "Artistas",
        "breadcrumb_title": "Artistas",
        "source": "../pages/library/ArtistGridPage.qml",
        "icon": "artists", "order": 30, "sidebar_visible": True,
        "sidebar_group": "library", "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": ["artistas", "artists", "intérpretes"],
        "placeholder_state": None,
        "params": None, "category": "library",
    },
    "library.artist_detail": {
        "route": "library.artist_detail", "parent": "library.artists",
        "title": "Artista", "breadcrumb_title": "Artista",
        "source": "../pages/library/ArtistDetailPage.qml",
        "icon": "artists", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": ["artist_detail"],
        "keywords": [],
        "placeholder_state": None,
        "params": {"artist": {"required": True, "type": "string"}},
        "category": "detail",
    },
    "library.folders": {
        "route": "library.folders", "parent": "library", "title": "Carpetas",
        "breadcrumb_title": "Carpetas",
        "source": "../pages/library/FolderBrowserPage.qml",
        "icon": "folders", "order": 40, "sidebar_visible": True,
        "sidebar_group": "library", "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": ["carpetas", "folders", "fuentes", "directorios"],
        "placeholder_state": None,
        "params": None, "category": "library",
    },
    "library.collections": {
        "route": "library.collections", "parent": "library", "title": "Colecciones",
        "breadcrumb_title": "Colecciones",
        "source": "../pages/library/CollectionsPage.qml",
        "icon": "library", "order": 60, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": ["colecciones", "favoritos", "recientes", "años"],
        "placeholder_state": None,
        "params": None, "category": "library",
    },
    "library.folder_detail": {
        "route": "library.folder_detail", "parent": "library.folders",
        "title": "Carpeta", "breadcrumb_title": "Carpeta",
        "source": "../pages/library/FolderBrowserPage.qml",
        "icon": "folders", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": {"folder_id": {"required": True, "type": "string"}},
        "category": "detail",
    },
    "library.sources": {
        "route": "library.sources", "parent": "library.folders",
        "title": "Fuentes", "breadcrumb_title": "Fuentes",
        "source": "../pages/library/SourcesPage.qml",
        "icon": "folders", "order": 10, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "library",
    },
    "library.source_detail": {
        "route": "library.source_detail", "parent": "library.folders",
        "title": "Detalle de fuente", "breadcrumb_title": "Fuente",
        "source": "../pages/library/SourceDetailPage.qml",
        "icon": "folders", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": {"source_id": {"required": True, "type": "int"}},
        "category": "detail",
    },
    # Legacy library sub-routes (available as filters, not sidebar top-level)
    "library.favorites": {
        "route": "library.favorites", "parent": "library.songs",
        "title": "Favoritos", "breadcrumb_title": "Favoritos",
        "source": "../pages/library/FavoritesPage.qml",
        "icon": "songs", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": ["favoritos", "favorites"],
        "placeholder_state": None,
        "params": None, "category": "library",
    },
    "library.recent": {
        "route": "library.recent", "parent": "library.songs",
        "title": "Recientes", "breadcrumb_title": "Recientes",
        "source": "../pages/library/RecentPage.qml",
        "icon": "songs", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": ["recientes", "recent"],
        "placeholder_state": None,
        "params": None, "category": "library",
    },
    "library.genres": {
        "route": "library.genres", "parent": "library",
        "title": "Géneros", "breadcrumb_title": "Géneros",
        "source": "../pages/library/GenresPage.qml",
        "icon": "songs", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": ["géneros", "genres"],
        "placeholder_state": None,
        "params": None, "category": "library",
    },
    "library.genre_detail": {
        "route": "library.genre_detail", "parent": "library.genres",
        "title": "Género", "breadcrumb_title": "Género",
        "source": "../pages/library/GenreDetailPage.qml",
        "icon": "songs", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": {"genre": {"required": True, "type": "string"}},
        "category": "detail",
    },
    "library.composers": {
        "route": "library.composers", "parent": "library.artists",
        "title": "Compositores", "breadcrumb_title": "Compositores",
        "source": "../pages/library/ComposersPage.qml",
        "icon": "artists", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": ["compositores", "composers"],
        "placeholder_state": None,
        "params": None, "category": "library",
    },
    "library.composer_detail": {
        "route": "library.composer_detail", "parent": "library.composers",
        "title": "Compositor", "breadcrumb_title": "Compositor",
        "source": "../pages/library/ComposerDetailPage.qml",
        "icon": "artists", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": {"composer": {"required": True, "type": "string"}},
        "category": "detail",
    },
    "library.years": {
        "route": "library.years", "parent": "library",
        "title": "Años", "breadcrumb_title": "Años",
        "source": "../pages/library/YearsPage.qml",
        "icon": "songs", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": ["años", "years", "décadas"],
        "placeholder_state": None,
        "params": None, "category": "library",
    },
    "library.most_played": {
        "route": "library.most_played", "parent": "library.songs",
        "title": "Más reproducidas", "breadcrumb_title": "Más reproducidas",
        "source": "../pages/library/MostPlayedPage.qml",
        "icon": "songs", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": ["más reproducidas", "most played", "top"],
        "placeholder_state": None,
        "params": None, "category": "library",
    },
    "library.unplayed": {
        "route": "library.unplayed", "parent": "library.songs",
        "title": "Sin reproducir", "breadcrumb_title": "Sin reproducir",
        "source": "../pages/library/UnplayedPage.qml",
        "icon": "songs", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": ["sin reproducir", "unplayed", "no escuchadas"],
        "placeholder_state": None,
        "params": None, "category": "library",
    },
    "library.missing": {
        "route": "library.missing", "parent": "library",
        "title": "Archivos faltantes", "breadcrumb_title": "Faltantes",
        "source": "../pages/library/MissingPage.qml",
        "icon": "songs", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": ["faltantes", "missing", "perdidos"],
        "placeholder_state": None,
        "params": None, "category": "library",
    },
    "library.track_detail": {
        "route": "library.track_detail", "parent": "library.songs",
        "title": "Canción", "breadcrumb_title": "Canción",
        "source": "../pages/library/tracks/TracksPage.qml",
        "icon": "songs", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": ["track_detail"],
        "keywords": [],
        "placeholder_state": None,
        "params": {"track_id": {"required": True, "type": "int"}},
        "category": "detail",
    },

    # ═══════════════════════════════════════════════════════════════════
    # 3. MIX
    # ═══════════════════════════════════════════════════════════════════
    "mix": {
        "route": "mix", "parent": None, "title": "Mix",
        "breadcrumb_title": "Mix",
        "source": "../pages/mix/MixHubPage.qml",
        "icon": "mix", "order": 30, "sidebar_visible": True,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": ["mix", "descubrir", "discover", "recomendaciones", "daily mix"],
        "placeholder_state": None,
        "params": None, "category": "core",
    },
    "mix_detail": {
        "route": "mix_detail", "parent": "mix",
        "title": "Mix", "breadcrumb_title": "Mix",
        "source": "../pages/mix/MixDetailPage.qml",
        "icon": "mix", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": {"mix_id": {"required": True, "type": "string"}},
        "category": "detail",
    },
    "mix_generator": {
        "route": "mix_generator", "parent": "mix",
        "title": "Generar Mix", "breadcrumb_title": "Generar Mix",
        "source": "../pages/mix/MixGeneratorPage.qml",
        "icon": "mix", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "detail",
    },
    "mix_result": {
        "route": "mix_result", "parent": "mix",
        "title": "Resultado Mix", "breadcrumb_title": "Mix",
        "source": "../pages/mix/MixResultPage.qml",
        "icon": "mix", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "detail",
    },
    "mix_rule_editor": {
        "route": "mix_rule_editor", "parent": "mix",
        "title": "Editor de Reglas", "breadcrumb_title": "Reglas",
        "source": "../pages/mix/MixRuleEditorPage.qml",
        "icon": "mix", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "detail",
    },

    # ═══════════════════════════════════════════════════════════════════
    # 4. STREAMING
    # ═══════════════════════════════════════════════════════════════════
    "streaming": {
        "route": "streaming", "parent": None, "title": "Streaming",
        "breadcrumb_title": "Streaming",
        "source": "../pages/streaming/StreamingHubPage.qml",
        "icon": "streaming", "order": 40, "sidebar_visible": True,
        "sidebar_group": None, "expandable": True,
        "status": "partial", "capability": None,
        "aliases": [],
        "keywords": ["streaming", "radio", "podcasts", "transmisión"],
        "placeholder_state": None,
        "params": None, "category": "core",
    },
    "streaming.radio": {
        "route": "streaming.radio", "parent": "streaming", "title": "Radio",
        "breadcrumb_title": "Radio",
        "source": "../pages/radio/RadioPage.qml",
        "icon": "radio", "order": 10, "sidebar_visible": True,
        "sidebar_group": "streaming", "expandable": False,
        "status": "functional", "capability": None,
        "aliases": ["radio"],
        "keywords": ["radio", "emisoras", "stations", "stream"],
        "placeholder_state": None,
        "params": None, "category": "core",
    },
    "streaming.podcasts": {
        "route": "streaming.podcasts", "parent": "streaming", "title": "Podcasts",
        "breadcrumb_title": "Podcasts",
        "source": "../pages/streaming/PodcastsPlaceholderPage.qml",
        "icon": "podcasts", "order": 20, "sidebar_visible": True,
        "sidebar_group": "streaming", "expandable": False,
        "status": "planned",
        "capability": "podcasts",
        "aliases": [],
        "keywords": ["podcasts", "podcast", "episodios", "audio"],
        "placeholder_state": "planned",
        "params": None, "category": "experimental",
    },

    # ═══════════════════════════════════════════════════════════════════
    # 5. PLAYLISTS
    # ═══════════════════════════════════════════════════════════════════
    "playlists": {
        "route": "playlists", "parent": None, "title": "Playlists",
        "breadcrumb_title": "Playlists",
        "source": "../pages/playlists/PlaylistsPage.qml",
        "icon": "playlists", "order": 50, "sidebar_visible": True,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": ["playlists", "listas", "reproducción"],
        "placeholder_state": None,
        "params": None, "category": "core",
    },
    "playlist_detail": {
        "route": "playlist_detail", "parent": "playlists",
        "title": "Playlist", "breadcrumb_title": "Playlist",
        "source": "../pages/playlists/PlaylistDetailPage.qml",
        "icon": "playlists", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": {"playlist_id": {"required": True, "type": "int"}},
        "category": "detail",
    },
    "smart_playlist_editor": {
        "route": "smart_playlist_editor", "parent": "playlists",
        "title": "Smart Playlist", "breadcrumb_title": "Smart Playlist",
        "source": "../pages/playlists/SmartPlaylistEditorPage.qml",
        "icon": "playlists", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "detail",
    },

    # ═══════════════════════════════════════════════════════════════════
    # 6. CONNECTIONS
    # ═══════════════════════════════════════════════════════════════════
    "connections": {
        "route": "connections", "parent": None, "title": "Conexiones",
        "breadcrumb_title": "Conexiones",
        "source": "../pages/connections/ConnectionsPage.qml",
        "icon": "connections", "order": 60, "sidebar_visible": True,
        "sidebar_group": None, "expandable": True,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": ["conexiones", "connections", "servidores"],
        "placeholder_state": None,
        "params": None, "category": "core",
    },
    "connections.micro_server": {
        "route": "connections.micro_server", "parent": "connections",
        "title": "Michi Micro Server", "breadcrumb_title": "Micro Server",
        "source": "../pages/connections/ConnectionDiscoveryPage.qml",
        "icon": "micro_server", "order": 10, "sidebar_visible": True,
        "sidebar_group": "connections", "expandable": False,
        "status": "functional", "capability": "connections",
        "aliases": [],
        "keywords": ["micro server", "michi link", "servidor local"],
        "placeholder_state": None,
        "params": None, "category": "core",
    },
    "connections.big_server": {
        "route": "connections.big_server", "parent": "connections",
        "title": "Michi Big Server", "breadcrumb_title": "Big Server",
        "source": "../pages/connections/BigServerPlaceholderPage.qml",
        "icon": "big_server", "order": 20, "sidebar_visible": True,
        "sidebar_group": "connections", "expandable": False,
        "status": "planned",
        "capability": "big_server",
        "aliases": [],
        "keywords": ["big server", "servidor grande", "futuro"],
        "placeholder_state": "planned",
        "params": None, "category": "experimental",
    },
    "connections.navidrome": {
        "route": "connections.navidrome", "parent": "connections",
        "title": "Navidrome", "breadcrumb_title": "Navidrome",
        "source": "../pages/connections/NavidromePlaceholderPage.qml",
        "icon": "navidrome", "order": 30, "sidebar_visible": True,
        "sidebar_group": "connections", "expandable": False,
        "status": "planned",
        "capability": "navidrome",
        "aliases": [],
        "keywords": ["navidrome", "subsonic", "servidor"],
        "placeholder_state": "planned",
        "params": None, "category": "experimental",
    },
    "connections.jellyfin": {
        "route": "connections.jellyfin", "parent": "connections",
        "title": "Jellyfin", "breadcrumb_title": "Jellyfin",
        "source": "../pages/connections/JellyfinPlaceholderPage.qml",
        "icon": "jellyfin", "order": 40, "sidebar_visible": True,
        "sidebar_group": "connections", "expandable": False,
        "status": "planned",
        "capability": "jellyfin",
        "aliases": [],
        "keywords": ["jellyfin", "servidor", "streaming"],
        "placeholder_state": "planned",
        "params": None, "category": "experimental",
    },
    "connections.home_assistant": {
        "route": "connections.home_assistant", "parent": "connections",
        "title": "Home Assistant", "breadcrumb_title": "Home Assistant",
        "source": "../pages/connections/HomeAssistantPlaceholderPage.qml",
        "icon": "home_assistant", "order": 50, "sidebar_visible": True,
        "sidebar_group": "connections", "expandable": False,
        "status": "configuration_required",
        "capability": "home_assistant",
        "aliases": [],
        "keywords": ["home assistant", "ha", "automatización", "iot"],
        "placeholder_state": "configuration_required",
        "params": None, "category": "experimental",
    },
    "connections.detail": {
        "route": "connections.detail", "parent": "connections",
        "title": "Conexión", "breadcrumb_title": "Conexión",
        "source": "../pages/connections/ConnectionDetailPage.qml",
        "icon": "connections", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": {"connection_id": {"required": True, "type": "string"}},
        "category": "detail",
    },

    # ═══════════════════════════════════════════════════════════════════
    # 7. AUDIO LAB
    # ═══════════════════════════════════════════════════════════════════
    "audio_lab": {
        "route": "audio_lab", "parent": None, "title": "Audio Lab",
        "breadcrumb_title": "Audio Lab",
        "source": "../pages/audio_lab/AudioLabHubPage.qml",
        "icon": "audio_lab", "order": 70, "sidebar_visible": True,
        "sidebar_group": None, "expandable": True,
        "status": "functional", "capability": None,
        "aliases": ["audio_lab.overview"],
        "keywords": ["audio lab", "análisis", "procesamiento", "metadatos", "captura"],
        "placeholder_state": None,
        "params": None, "category": "tools",
    },
    "audio_lab.analysis": {
        "route": "audio_lab.analysis", "parent": "audio_lab",
        "title": "Análisis", "breadcrumb_title": "Análisis",
        "source": "../pages/audio_lab/AudioAnalysisPage.qml",
        "icon": "analysis", "order": 10, "sidebar_visible": True,
        "sidebar_group": "audio_lab", "expandable": False,
        "status": "functional", "capability": "audio_lab",
        "aliases": [],
        "keywords": ["análisis", "analysis", "técnico", "formato", "códec", "espectro"],
        "placeholder_state": None,
        "params": None, "category": "tools",
    },
    "audio_lab.processing": {
        "route": "audio_lab.processing", "parent": "audio_lab",
        "title": "Procesamiento", "breadcrumb_title": "Procesamiento",
        "source": "../pages/audio_lab/AudioProcessingHubPage.qml",
        "icon": "processing", "order": 20, "sidebar_visible": True,
        "sidebar_group": "audio_lab", "expandable": False,
        "status": "functional", "capability": "audio_lab",
        "aliases": ["outputs"],
        "keywords": ["procesamiento", "ecualizador", "dsp", "perfiles", "normalización", "conversión"],
        "placeholder_state": None,
        "params": None, "category": "tools",
    },
    "audio_lab.metadata": {
        "route": "audio_lab.metadata", "parent": "audio_lab",
        "title": "Metadatos", "breadcrumb_title": "Metadatos",
        "source": "../pages/metadata/MetadataInspectorPage.qml",
        "icon": "metadata", "order": 30, "sidebar_visible": True,
        "sidebar_group": "audio_lab", "expandable": False,
        "status": "functional", "capability": "audio_lab",
        "aliases": ["metadata.inspector", "metadata.editor", "metadata_editor", "metadata_inspector"],
        "keywords": ["metadatos", "metadata", "tags", "editor", "inspector", "carátulas"],
        "placeholder_state": None,
        "params": None, "category": "tools",
    },
    "audio_lab.capture": {
        "route": "audio_lab.capture", "parent": "audio_lab",
        "title": "Captura", "breadcrumb_title": "Captura",
        "source": "../pages/audio_lab/AudioCaptureHubPage.qml",
        "icon": "capture", "order": 40, "sidebar_visible": True,
        "sidebar_group": "audio_lab", "expandable": False,
        "status": "experimental", "capability": "audio_lab",
        "aliases": ["disc_lab"],
        "keywords": ["captura", "ripeo", "cd", "adc", "grabación", "digitalización"],
        "placeholder_state": None,
        "params": None, "category": "tools",
    },
    "audio_lab.library_health": {
        "route": "audio_lab.library_health", "parent": "audio_lab",
        "title": "Salud de biblioteca", "breadcrumb_title": "Salud",
        "source": "../pages/library_doctor/LibraryDoctorPage.qml",
        "icon": "library_health", "order": 50, "sidebar_visible": True,
        "sidebar_group": "audio_lab", "expandable": False,
        "status": "functional", "capability": "audio_lab",
        "aliases": ["library_doctor"],
        "keywords": ["salud", "biblioteca", "doctor", "reparación", "duplicados", "faltantes"],
        "placeholder_state": None,
        "params": None, "category": "tools",
    },

    # Audio Lab legacy sub-routes (not sidebar-visible, accessible from hub)
    "metadata.single": {
        "route": "metadata.single", "parent": "audio_lab.metadata",
        "title": "Editar metadatos", "breadcrumb_title": "Editar",
        "source": "../pages/metadata/MetadataSingleEditor.qml",
        "icon": "metadata", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": ["metadata_single"],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "tools",
    },
    "metadata.batch": {
        "route": "metadata.batch", "parent": "audio_lab.metadata",
        "title": "Edición por lotes", "breadcrumb_title": "Lotes",
        "source": "../pages/metadata/MetadataBatchEditor.qml",
        "icon": "metadata", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": ["metadata_batch"],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "tools",
    },
    "audio_lab.conversion": {
        "route": "audio_lab.conversion", "parent": "audio_lab.processing",
        "title": "Conversión", "breadcrumb_title": "Conversión",
        "source": "../pages/audio_lab/AudioConversionPage.qml",
        "icon": "processing", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "tools",
    },
    "audio_lab.normalization": {
        "route": "audio_lab.normalization", "parent": "audio_lab.processing",
        "title": "Normalización", "breadcrumb_title": "Normalización",
        "source": "../pages/audio_lab/AudioNormalizationPage.qml",
        "icon": "processing", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "tools",
    },
    "audio_lab.replaygain": {
        "route": "audio_lab.replaygain", "parent": "audio_lab.processing",
        "title": "ReplayGain", "breadcrumb_title": "ReplayGain",
        "source": "../pages/audio_lab/ReplayGainPage.qml",
        "icon": "processing", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "tools",
    },
    "audio_lab.integrity": {
        "route": "audio_lab.integrity", "parent": "audio_lab.analysis",
        "title": "Integridad", "breadcrumb_title": "Integridad",
        "source": "../pages/audio_lab/AudioIntegrityPage.qml",
        "icon": "analysis", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "tools",
    },
    "audio_lab.comparison": {
        "route": "audio_lab.comparison", "parent": "audio_lab.analysis",
        "title": "Comparación", "breadcrumb_title": "Comparación",
        "source": "../pages/audio_lab/AudioComparisonPage.qml",
        "icon": "analysis", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "tools",
    },
    "audio_lab.jobs": {
        "route": "audio_lab.jobs", "parent": "audio_lab",
        "title": "Trabajos", "breadcrumb_title": "Trabajos",
        "source": "../pages/audio_lab/AudioBatchJobsPage.qml",
        "icon": "audio_lab", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "tools",
    },
    "audio_lab.profiles": {
        "route": "audio_lab.profiles", "parent": "audio_lab.processing",
        "title": "Perfiles", "breadcrumb_title": "Perfiles",
        "source": "../pages/audio_lab/AudioConversionProfileEditor.qml",
        "icon": "processing", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "tools",
    },
    "audio_lab_job_detail": {
        "route": "audio_lab_job_detail", "parent": "audio_lab",
        "title": "Detalle de trabajo", "breadcrumb_title": "Trabajo",
        "source": "../pages/audio_lab/AudioJobDetail.qml",
        "icon": "audio_lab", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": {"job": {"required": True, "type": "object"}},
        "category": "detail",
    },
    "audio_lab.cd_ripper": {
        "route": "audio_lab.cd_ripper", "parent": "audio_lab",
        "title": "Ripeo de CD", "breadcrumb_title": "CD",
        "source": "../pages/audio_lab/AudioBackupPage.qml",
        "icon": "capture", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "experimental", "capability": "audio_lab",
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": {"tab": {"required": False, "type": "string"}}, "category": "tools",
    },
    "audio_lab.adc_recorder": {
        "route": "audio_lab.adc_recorder", "parent": "audio_lab",
        "title": "Grabación ADC", "breadcrumb_title": "ADC",
        "source": "../pages/audio_lab/AudioBackupPage.qml",
        "icon": "capture", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "experimental", "capability": "audio_lab",
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": {"tab": {"required": False, "type": "string"}}, "category": "tools",
    },

    # ═══════════════════════════════════════════════════════════════════
    # 8. HOME AUDIO
    # ═══════════════════════════════════════════════════════════════════
    "home_audio": {
        "route": "home_audio", "parent": None, "title": "Home Audio",
        "breadcrumb_title": "Home Audio",
        "source": "../pages/home_audio/HomeAudioHubPage.qml",
        "icon": "home_audio", "order": 80, "sidebar_visible": True,
        "sidebar_group": None, "expandable": True,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": ["home audio", "hogar", "multiroom", "stream", "cadena"],
        "placeholder_state": None,
        "params": None, "category": "core",
    },
    "home_audio.stream": {
        "route": "home_audio.stream", "parent": "home_audio",
        "title": "Michi Music Stream", "breadcrumb_title": "Stream",
        "source": "../pages/home_audio/HomeAudioPage.qml",
        "icon": "michi_stream", "order": 10, "sidebar_visible": True,
        "sidebar_group": "home_audio", "expandable": False,
        "status": "functional", "capability": "home_audio",
        "aliases": [],
        "keywords": ["stream", "transmisión", "michi music stream", "wifi audio"],
        "placeholder_state": None,
        "params": None, "category": "core",
    },
    "home_audio.rooms": {
        "route": "home_audio.rooms", "parent": "home_audio",
        "title": "Habitaciones y zonas", "breadcrumb_title": "Zonas",
        "source": "../pages/home_audio/RoomsHubPage.qml",
        "icon": "rooms", "order": 20, "sidebar_visible": True,
        "sidebar_group": "home_audio", "expandable": False,
        "status": "partial", "capability": "home_audio",
        "aliases": [],
        "keywords": ["habitaciones", "rooms", "zonas", "multiroom", "receptores"],
        "placeholder_state": None,
        "params": None, "category": "core",
    },
    "home_audio.distribution": {
        "route": "home_audio.distribution", "parent": "home_audio",
        "title": "Distribución de audio", "breadcrumb_title": "Distribución",
        "source": "../pages/home_audio/DistributionHubPage.qml",
        "icon": "distribution", "order": 30, "sidebar_visible": True,
        "sidebar_group": "home_audio", "expandable": False,
        "status": "partial", "capability": "home_audio",
        "aliases": [],
        "keywords": ["distribución", "distribution", "routing", "fuentes", "destinos"],
        "placeholder_state": None,
        "params": None, "category": "core",
    },
    "home_audio.chain_planner": {
        "route": "home_audio.chain_planner", "parent": "home_audio",
        "title": "Planificador de cadenas", "breadcrumb_title": "Cadenas",
        "source": "../pages/home_audio/ChainPlannerPlaceholderPage.qml",
        "icon": "chain_planner", "order": 40, "sidebar_visible": True,
        "sidebar_group": "home_audio", "expandable": False,
        "status": "planned",
        "capability": "home_audio",
        "aliases": [],
        "keywords": ["cadena", "chain", "planificador", "dac", "amplificador", "parlantes"],
        "placeholder_state": "planned",
        "params": None, "category": "experimental",
    },
    "group_editor": {
        "route": "group_editor", "parent": "home_audio.rooms",
        "title": "Editor de grupos", "breadcrumb_title": "Grupos",
        "source": "../pages/home_audio/GroupEditorPage.qml",
        "icon": "rooms", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "detail",
    },
    "zone_detail": {
        "route": "zone_detail", "parent": "home_audio.rooms",
        "title": "Zona", "breadcrumb_title": "Zona",
        "source": "../pages/home_audio/ZoneDetailPage.qml",
        "icon": "rooms", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": {"zone_id": {"required": True, "type": "string"}},
        "category": "detail",
    },

    # ═══════════════════════════════════════════════════════════════════
    # 9. MICHI AI
    # ═══════════════════════════════════════════════════════════════════
    "michi_ai": {
        "route": "michi_ai", "parent": None, "title": "Michi AI",
        "breadcrumb_title": "Michi AI",
        "source": "../pages/assistant/AssistantPage.qml",
        "icon": "michi_ai", "order": 90, "sidebar_visible": True,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": ["assistant", "ai"],
        "keywords": ["michi ai", "asistente", "ai", "chat", "consultas", "recomendaciones"],
        "placeholder_state": None,
        "params": None, "category": "core",
    },
    "ai.settings": {
        "route": "ai.settings", "parent": "michi_ai",
        "title": "Configuración de Michi AI", "breadcrumb_title": "Config. AI",
        "source": "../pages/assistant/AISettingsPage.qml",
        "icon": "michi_ai", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "settings",
    },

    # ═══════════════════════════════════════════════════════════════════
    # 10. MICHI SYNC SUITE
    # ═══════════════════════════════════════════════════════════════════
    "sync": {
        "route": "sync", "parent": None, "title": "Michi Sync Suite",
        "breadcrumb_title": "Sync Suite",
        "source": "../pages/sync/SyncHubPage.qml",
        "icon": "sync", "order": 100, "sidebar_visible": True,
        "sidebar_group": None, "expandable": True,
        "status": "partial", "capability": None,
        "aliases": ["devices", "devices.list"],
        "keywords": ["sync", "sincronización", "dispositivos", "sync suite"],
        "placeholder_state": None,
        "params": None, "category": "core",
    },
    "sync.mobile": {
        "route": "sync.mobile", "parent": "sync",
        "title": "Dispositivos móviles", "breadcrumb_title": "Móviles",
        "source": "../pages/devices/MobilePairingPage.qml",
        "icon": "mobile", "order": 10, "sidebar_visible": True,
        "sidebar_group": "sync", "expandable": False,
        "status": "functional", "capability": "sync",
        "aliases": ["devices.mobile_pairing", "devices.pairing"],
        "keywords": ["móviles", "mobile", "android", "pairing", "emparejar"],
        "placeholder_state": None,
        "params": None, "category": "tools",
    },
    "sync.portable_players": {
        "route": "sync.portable_players", "parent": "sync",
        "title": "Reproductores portátiles", "breadcrumb_title": "Portátiles",
        "source": "../pages/sync/PortablePlayersPlaceholderPage.qml",
        "icon": "portable_player", "order": 20, "sidebar_visible": True,
        "sidebar_group": "sync", "expandable": False,
        "status": "planned",
        "capability": "sync",
        "aliases": [],
        "keywords": ["portátiles", "portable", "fiio", "hiby", "usb", "mtp", "reproductor"],
        "placeholder_state": "planned",
        "params": None, "category": "experimental",
    },
    "sync.plans": {
        "route": "sync.plans", "parent": "sync",
        "title": "Planes de sincronización", "breadcrumb_title": "Planes",
        "source": "../pages/sync/SyncPlansPlaceholderPage.qml",
        "icon": "sync_plans", "order": 30, "sidebar_visible": True,
        "sidebar_group": "sync", "expandable": False,
        "status": "planned",
        "capability": "sync",
        "aliases": ["devices.profile_editor"],
        "keywords": ["planes", "plans", "sincronización", "reglas", "conversión"],
        "placeholder_state": "planned",
        "params": None, "category": "experimental",
    },
    "sync.history": {
        "route": "sync.history", "parent": "sync",
        "title": "Historial", "breadcrumb_title": "Historial",
        "source": "../pages/sync/SyncHistoryPlaceholderPage.qml",
        "icon": "sync_history", "order": 40, "sidebar_visible": True,
        "sidebar_group": "sync", "expandable": False,
        "status": "planned",
        "capability": "sync",
        "aliases": [],
        "keywords": ["historial", "history", "transferencias", "errores"],
        "placeholder_state": "planned",
        "params": None, "category": "experimental",
    },

    # ═══════════════════════════════════════════════════════════════════
    # GLOBAL / UTILITY ROUTES (not in main sidebar)
    # ═══════════════════════════════════════════════════════════════════
    "search": {
        "route": "search", "parent": None, "title": "Búsqueda",
        "breadcrumb_title": "Búsqueda",
        "source": "../pages/search/GlobalSearchPage.qml",
        "icon": "search", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": ["buscar", "search", "búsqueda global"],
        "placeholder_state": None,
        "params": None, "category": "core",
    },
    "queue": {
        "route": "queue", "parent": None, "title": "Cola",
        "breadcrumb_title": "Cola",
        "source": "../pages/queue/QueuePage.qml",
        "icon": "queue", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": ["cola", "queue", "reproducción"],
        "placeholder_state": None,
        "params": None, "category": "core",
    },
    "history": {
        "route": "history", "parent": None, "title": "Historial",
        "breadcrumb_title": "Historial",
        "source": "../pages/history/HistoryPage.qml",
        "icon": "history", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": ["historial", "history", "reproducción"],
        "placeholder_state": None,
        "params": None, "category": "core",
    },
    "jobs": {
        "route": "jobs", "parent": None, "title": "Trabajos",
        "breadcrumb_title": "Trabajos",
        "source": "../pages/jobs/JobsPage.qml",
        "icon": "settings", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": ["jobs", "trabajos", "tareas", "procesos"],
        "placeholder_state": None,
        "params": None, "category": "tools",
    },
    "nowplaying": {
        "route": "nowplaying", "parent": None, "title": "Reproduciendo",
        "breadcrumb_title": "Reproduciendo",
        "source": "../pages/nowplaying/NowPlayingPage.qml",
        "icon": "home", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "core",
    },
    "playback": {
        "route": "playback", "parent": None, "title": "Reproducción",
        "breadcrumb_title": "Reproducción",
        "source": "../pages/PlaybackPage.qml",
        "icon": "home", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "core",
    },
    "lyrics": {
        "route": "lyrics", "parent": None, "title": "Letra",
        "breadcrumb_title": "Letra",
        "source": "../pages/lyrics/LyricsPage.qml",
        "icon": "home", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "tools",
    },
    "tagging": {
        "route": "tagging", "parent": None, "title": "Smart Tagging",
        "breadcrumb_title": "Smart Tagging",
        "source": "../pages/SmartTaggingPage.qml",
        "icon": "analysis", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": ["smart_tagging"],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "tools",
    },
    "diagnostics": {
        "route": "diagnostics", "parent": None, "title": "Diagnóstico",
        "breadcrumb_title": "Diagnóstico",
        "source": "../pages/DiagnosticsPage.qml",
        "icon": "settings", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "tools",
    },

    # ═══════════════════════════════════════════════════════════════════
    # SETTINGS (fixed bottom sidebar entry)
    # ═══════════════════════════════════════════════════════════════════
    "eq": {
        "route": "eq", "parent": None,
        "title": "Ecualizador", "breadcrumb_title": "Ecualizador",
        "source": "../pages/equalizer/EqualizerPage.qml",
        "icon": "eq", "order": 65, "sidebar_visible": True,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": "eq",
        "aliases": ["equalizer"],
        "keywords": ["ecualizador", "eq", "dsp", "bandas", "presets"],
        "placeholder_state": None,
        "params": None, "category": "tools",
    },
    "settings": {
        "route": "settings", "parent": None, "title": "Ajustes",
        "breadcrumb_title": "Ajustes",
        "source": "../pages/SettingsPage.qml",
        "icon": "settings", "order": 1000, "sidebar_visible": True,
        "sidebar_group": "fixed_bottom", "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": ["ajustes", "settings", "configuración", "preferencias"],
        "placeholder_state": None,
        "params": None, "category": "settings",
    },
    "settings.general": {
        "route": "settings.general", "parent": "settings",
        "title": "Ajustes generales", "breadcrumb_title": "General",
        "source": "../pages/settings/SettingsGeneralPage.qml",
        "icon": "settings", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "settings",
    },
    "settings.appearance": {
        "route": "settings.appearance", "parent": "settings",
        "title": "Apariencia", "breadcrumb_title": "Apariencia",
        "source": "../pages/settings/SettingsAppearancePage.qml",
        "icon": "settings", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "settings",
    },
    "settings.playback": {
        "route": "settings.playback", "parent": "settings",
        "title": "Reproducción", "breadcrumb_title": "Playback",
        "source": "../pages/settings/SettingsPlaybackPage.qml",
        "icon": "settings", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "settings",
    },
    "settings.library": {
        "route": "settings.library", "parent": "settings",
        "title": "Biblioteca", "breadcrumb_title": "Biblioteca",
        "source": "../pages/settings/SettingsLibraryPage.qml",
        "icon": "settings", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "settings",
    },
    "settings.accessibility": {
        "route": "settings.accessibility", "parent": "settings",
        "title": "Accesibilidad", "breadcrumb_title": "Accesibilidad",
        "source": "../pages/settings/SettingsAccessibilityPage.qml",
        "icon": "settings", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "settings",
    },
    "settings.audio": {
        "route": "settings.audio", "parent": "settings",
        "title": "Audio", "breadcrumb_title": "Audio",
        "source": "../pages/settings/SettingsAudioPage.qml",
        "icon": "settings", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "settings",
    },
    "settings.about": {
        "route": "settings.about", "parent": "settings",
        "title": "Acerca de", "breadcrumb_title": "Acerca de",
        "source": "../pages/settings/SettingsAboutPage.qml",
        "icon": "settings", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "settings",
    },

    # Legacy compat routes
    "ecosystem": {
        "route": "ecosystem", "parent": None, "title": "Ecosistema Michi",
        "breadcrumb_title": "Ecosistema",
        "source": "../pages/home/EcosystemCard.qml",
        "icon": "connections", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "core",
    },
    "devices.detail": {
        "route": "devices.detail", "parent": "sync",
        "title": "Dispositivo", "breadcrumb_title": "Dispositivo",
        "source": "../pages/devices/DeviceDetailPage.qml",
        "icon": "mobile", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": None,
        "aliases": ["device_detail"],
        "keywords": [],
        "placeholder_state": None,
        "params": {"device_id": {"required": True, "type": "string"}},
        "category": "detail",
    },
    "placeholder": {
        "route": "placeholder", "parent": None, "title": "Sección en migración",
        "breadcrumb_title": "Migración",
        "source": "../pages/PlaceholderPage.qml",
        "icon": "home", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "deprecated", "capability": None,
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "tools",
    },

    # Audio Lab — rutas directas a páginas herramienta (hubs eliminados)
    "audio_lab.diagnostics": {
        "route": "audio_lab.diagnostics", "parent": "audio_lab",
        "title": "Diagnóstico de Audio", "breadcrumb_title": "Diagnóstico Audio",
        "source": "../pages/audio_lab/AudioAnalysisPage.qml",
        "icon": "analysis", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": "audio_lab",
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "tools",
    },
    "audio_lab.identifier": {
        "route": "audio_lab.identifier", "parent": "audio_lab",
        "title": "Identificador", "breadcrumb_title": "Identificador",
        "source": "../pages/metadata/MetadataInspectorPage.qml",
        "icon": "analysis", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": "metadata",
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "tools",
    },
    "audio_lab.backup": {
        "route": "audio_lab.backup", "parent": "audio_lab",
        "title": "Respaldar", "breadcrumb_title": "Respaldar",
        "source": "../pages/audio_lab/AudioBackupPage.qml",
        "icon": "audio_lab", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": "audio_lab",
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "tools",
    },
    "audio_lab.output_profiles": {
        "route": "audio_lab.output_profiles", "parent": "audio_lab",
        "title": "Perfiles de Salida", "breadcrumb_title": "Perfiles",
        "source": "../pages/outputs/OutputProfilesPage.qml",
        "icon": "processing", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": "output_profiles",
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "tools",
    },
    "audio_lab.local_intelligence": {
        "route": "audio_lab.local_intelligence", "parent": "audio_lab",
        "title": "Inteligencia Local", "breadcrumb_title": "Inteligencia Local",
        "source": "../pages/mix/MixHubPage.qml",
        "icon": "analysis", "order": 0, "sidebar_visible": False,
        "sidebar_group": None, "expandable": False,
        "status": "functional", "capability": "mix",
        "aliases": [],
        "keywords": [],
        "placeholder_state": None,
        "params": None, "category": "tools",
    },
}


# ═══════════════════════════════════════════════════════════════════
# ROUTE ALIASES — legacy route → canonical route
# Aliases are resolved BEFORE page loading.
# History stores canonical route.
# Header shows canonical title.
# Sidebar activates correct parent.
# ═══════════════════════════════════════════════════════════════════
def _build_alias_map() -> dict[str, str]:
    """Build a flat legacy → canonical mapping from route aliases."""
    result: dict[str, str] = {}
    for canonical, spec in ROUTES.items():
        for alias in spec.get("aliases", []):
            if alias not in result:
                result[alias] = canonical
    return result


ROUTE_ALIASES: dict[str, str] = _build_alias_map()


def resolve_route(route: str) -> str:
    """Resolve a route through the alias chain to its canonical form.

    Returns the canonical route if found, or the original route if not.
    Prevents alias cycles (max 10 hops).
    """
    seen: set[str] = set()
    current = route
    for _ in range(10):
        if current in ROUTES:
            return current
        if current in ROUTE_ALIASES:
            canonical = ROUTE_ALIASES[current]
            if canonical in seen:
                return current
            seen.add(current)
            current = canonical
        else:
            break
    return current


# ═══════════════════════════════════════════════════════════════════
# SIDEBAR ORDER — defines the display order of top-level sections
# ═══════════════════════════════════════════════════════════════════
SIDEBAR_ORDER: list[str] = [
    "home",        # 1. Inicio
    "library",     # 2. Biblioteca (expandable: songs, albums, artists, folders)
    "mix",         # 3. Mix
    "streaming",   # 4. Streaming (expandable: radio, podcasts)
    "playlists",   # 5. Playlists
    "connections", # 6. Conexiones (expandable: micro, big, navidrome, jellyfin, ha)
    "audio_lab",   # 7. Audio Lab (expandable: analysis, processing, metadata, capture, health)
    "home_audio",  # 8. Home Audio (expandable: stream, rooms, distribution, chain planner)
    "michi_ai",    # 9. Michi AI
    "sync",        # 10. Michi Sync Suite (expandable: mobile, portable, plans, history)
]

SIDEBAR_FIXED_BOTTOM: list[str] = [
    "settings",
]


def get_sidebar_sections() -> list[dict]:
    """Return the hierarchical sidebar structure for QML consumption.

    Returns a list of section dicts with structure:
    {
        "route": str, "title": str, "icon": str, "expandable": bool,
        "order": int, "status": str,
        "children": [{..."route"..., "title"..., "icon"..., "active": False}]
    }
    """
    sections = []
    for route in SIDEBAR_ORDER:
        spec = ROUTES.get(route)
        if not spec or not spec.get("sidebar_visible"):
            continue
        section = {
            "route": spec["route"],
            "title": spec["title"],
            "icon": spec.get("icon", ""),
            "expandable": spec.get("expandable", False),
            "order": spec.get("order", 0),
            "status": spec.get("status", "functional"),
            "children": [],
        }
        if section["expandable"]:
            children = sorted(
                [r for r in ROUTES.values()
                 if r.get("parent") == route and r.get("sidebar_visible") and r.get("sidebar_group")],
                key=lambda r: r.get("order", 0),
            )
            section["children"] = [
                {
                    "route": c["route"],
                    "title": c["title"],
                    "icon": c.get("icon", ""),
                    "status": c.get("status", "functional"),
                    "order": c.get("order", 0),
                }
                for c in children
            ]
        sections.append(section)

    # Fixed bottom items
    fixed = []
    for route in SIDEBAR_FIXED_BOTTOM:
        spec = ROUTES.get(route)
        if not spec:
            continue
        fixed.append({
            "route": spec["route"],
            "title": spec["title"],
            "icon": spec.get("icon", ""),
            "expandable": False,
            "order": spec.get("order", 0),
            "status": spec.get("status", "functional"),
            "children": [],
        })
    return sections, fixed


def get_breadcrumb(route: str) -> list[dict]:
    """Build breadcrumb trail for a route.

    Returns list of {route, title} from root to leaf.
    """
    trail = []
    canonical = resolve_route(route)
    current = canonical
    while current:
        spec = ROUTES.get(current)
        if not spec:
            break
        trail.insert(0, {
            "route": current,
            "title": spec.get("breadcrumb_title", spec["title"]),
        })
        current = spec.get("parent")
    return trail


def get_parent_route(route: str) -> str | None:
    """Get the parent route for a canonical route."""
    canonical = resolve_route(route)
    spec = ROUTES.get(canonical)
    if spec:
        return spec.get("parent")
    return None


def is_child_active(parent_route: str, current_route: str) -> bool:
    """Check if current_route is a child (or descendant) of parent_route."""
    canonical = resolve_route(current_route)
    while canonical:
        if canonical == parent_route:
            return True
        spec = ROUTES.get(canonical)
        if not spec:
            break
        canonical = spec.get("parent")
    return False


CAPABILITY_MAP: dict[str, str] = {
    "audio_lab.*": "audio_lab",
    "metadata.*": "metadata",
    "tagging": "smart_tagging",
    "library_doctor": "library_doctor",
    "equalizer": "eq",
    "outputs": "output_profiles",
    "sync.*": "sync",
    "devices.*": "sync",
    "connections.*": "connections",
    "home_audio.*": "home_audio",
    "settings.*": "settings",
    "diagnostics.*": "diagnostics",
    "michi_ai": "ai",
    "ai.*": "ai",
    "disc_lab": "disc_lab",
    "streaming.podcasts": "podcasts",
    "connections.big_server": "big_server",
    "connections.navidrome": "navidrome",
    "connections.jellyfin": "jellyfin",
    "connections.home_assistant": "home_assistant",
}
