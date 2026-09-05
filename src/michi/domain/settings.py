"""Domain layer — application settings. No Qt/infrastructure."""

import json
from dataclasses import dataclass, field

from michi.domain.audio_engine import AudioEngineId


@dataclass(frozen=True)
class WindowGeometry:
    """Restorable window placement. Pure — no Qt/QRect.

    Negative x/y are legitimate (multi-monitor layouts); width/height are
    always positive in a valid geometry.
    """

    x: int | None = None
    y: int | None = None
    width: int = 1100
    height: int = 700
    maximized: bool = False


@dataclass(frozen=True)
class GalleryViewPreferences:
    artwork_size: str = "medium"
    spacing: str = "balanced"
    metadata_level: str = "standard"
    precision_metadata: bool = False
    quick_actions: bool = True
    inspector: bool = True


@dataclass(frozen=True)
class AlbumFlowPreferences:
    cover_size: str = "standard"
    visible_albums: str = "auto"
    depth: str = "standard"
    ambient_color: bool = True
    metadata_level: str = "standard"


@dataclass(frozen=True)
class ListeningWallPreferences:
    sleeve_size: str = "standard"
    spacing: str = "standard"
    reveal: str = "standard"
    metadata_level: str = "standard"
    artwork_label: bool = True
    inspector: bool = True


@dataclass(frozen=True)
class ChronologyPreferences:
    grouping: str = "decade"
    direction: str = "newest"
    density: str = "standard"
    metadata_level: str = "standard"
    show_period_density: bool = False


@dataclass(frozen=True)
class EditorialPreferences:
    hero_visible: bool = True
    information_richness: str = "standard"
    cached_enrichment_visible: bool = True
    archive_layout: str = "list"


@dataclass(frozen=True)
class StudioListPreferences:
    density: str = "standard"
    artwork_size: str = "small"
    metadata_level: str = "standard"
    precision_metadata: bool = True
    inspector: bool = True
    artist_column: bool = True
    year_column: bool = True
    tracks_column: bool = True
    duration_column: bool = True
    format_column: bool = True


# LIB-A P1-A: estado de columnas de la tabla de tracks, tipado en el
# domain (nunca dicts arbitrarios). Title es estructural: title_visible
# no puede deserializar a False. Widths se clampean al parsear (bounds
# idénticos a los del resize interactivo).
_TRACK_TABLE_MIN_WIDTHS = {
    "artwork": 30,
    "title": 220,
    "artist": 120,
    "album": 140,
    "format": 68,
    "sampleRate": 84,
    "bitDepth": 70,
    "dsdRate": 74,
    "bitrate": 74,
    "channels": 70,
    "fileSize": 74,
    "genre": 100,
    "composer": 120,
    "year": 58,
    "duration": 76,
}
_TRACK_TABLE_MAX_WIDTH = 720  # todas las resizables salvo artwork
_TRACK_TABLE_ARTWORK_MAX = 52
_TRACK_TABLE_VISIBLE_COLUMNS = (
    "artwork",
    "title",
    "artist",
    "album",
    "format",
    "sampleRate",
    "bitDepth",
    "dsdRate",
    "bitrate",
    "channels",
    "fileSize",
    "genre",
    "composer",
    "year",
    "duration",
    "actions",
)
_TRACK_TABLE_PRESETS = frozenset({"essential", "audiophile", "metadata", "minimal", ""})
_TRACK_TABLE_DEFAULT_VISIBLE = {
    "artwork": True,
    "title": True,
    "artist": True,
    "album": True,
    "format": True,
    "sampleRate": False,
    "bitDepth": False,
    "dsdRate": False,
    "bitrate": False,
    "channels": False,
    "fileSize": False,
    "genre": False,
    "composer": False,
    "year": False,
    "duration": True,
    "actions": True,
}
_TRACK_TABLE_DEFAULT_WIDTHS = {
    "artwork": 44,
    "title": 300,
    "artist": 190,
    "album": 230,
    "format": 88,
    "sampleRate": 100,
    "bitDepth": 82,
    "dsdRate": 92,
    "bitrate": 90,
    "channels": 82,
    "fileSize": 90,
    "genre": 150,
    "composer": 180,
    "year": 68,
    "duration": 80,
}


_TRACK_TABLE_FIELD = {
    "sampleRate": "sample_rate",
    "bitDepth": "bit_depth",
    "dsdRate": "dsd_rate",
    "fileSize": "file_size",
}


def _track_table_field(column: str) -> str:
    return _TRACK_TABLE_FIELD.get(column, column)


def _clamp_track_table_width(column: str, value: float) -> int:
    """Único validador de anchos persistidos (bounds del resize)."""
    if column == "artwork":
        return int(
            max(
                _TRACK_TABLE_MIN_WIDTHS["artwork"], min(_TRACK_TABLE_ARTWORK_MAX, value)
            )
        )
    minimum = _TRACK_TABLE_MIN_WIDTHS.get(column, 68)
    return int(max(minimum, min(_TRACK_TABLE_MAX_WIDTH, value)))


@dataclass(frozen=True)
class LibraryTrackTablePreferences:
    """Preferencias de columnas de la tabla de tracks (LIB-A P1-A)."""

    preset: str = "essential"
    artwork_visible: bool = True
    title_visible: bool = True
    artist_visible: bool = True
    album_visible: bool = True
    format_visible: bool = True
    sample_rate_visible: bool = False
    bit_depth_visible: bool = False
    dsd_rate_visible: bool = False
    bitrate_visible: bool = False
    channels_visible: bool = False
    file_size_visible: bool = False
    genre_visible: bool = False
    composer_visible: bool = False
    year_visible: bool = False
    duration_visible: bool = True
    actions_visible: bool = True
    artwork_width: int = 44
    title_width: int = 300
    artist_width: int = 190
    album_width: int = 230
    format_width: int = 88
    sample_rate_width: int = 100
    bit_depth_width: int = 82
    dsd_rate_width: int = 92
    bitrate_width: int = 90
    channels_width: int = 82
    file_size_width: int = 90
    genre_width: int = 150
    composer_width: int = 180
    year_width: int = 68
    duration_width: int = 80

    @classmethod
    def _default_visible(cls, column: str) -> bool:
        return _TRACK_TABLE_DEFAULT_VISIBLE.get(column, False)

    @classmethod
    def _default_width(cls, column: str) -> int:
        return _TRACK_TABLE_DEFAULT_WIDTHS.get(column, 80)


@dataclass(frozen=True)
class LibraryViewPreferences:
    active_mode: str = "grid"
    sort_mode: str = "title"
    sort_descending: bool = False
    filter_mode: str = "all"
    gallery: GalleryViewPreferences = field(default_factory=GalleryViewPreferences)
    flow: AlbumFlowPreferences = field(default_factory=AlbumFlowPreferences)
    vinyl: ListeningWallPreferences = field(default_factory=ListeningWallPreferences)
    chronology: ChronologyPreferences = field(default_factory=ChronologyPreferences)
    editorial: EditorialPreferences = field(default_factory=EditorialPreferences)
    studio_list: StudioListPreferences = field(default_factory=StudioListPreferences)
    # LIB-A P1-A: estado de columnas de la tabla de tracks (persistido).
    track_table: LibraryTrackTablePreferences = field(
        default_factory=LibraryTrackTablePreferences
    )


@dataclass
class SettingsState:
    volume: int = 80  # 0-100
    muted: bool = False
    last_directory: str = ""
    recent_files: list[str] = field(default_factory=list)
    theme: str = "dark"
    window_geometry: WindowGeometry = WindowGeometry()
    online_enrichment: bool = False  # M6.9 privacy: network DEFAULT OFF
    # M11.3F: persisted user engine preference (SELECTED intent — never the
    # ACTIVE engine). Missing/malformed preference falls back to Qt.
    audio_engine_id: AudioEngineId = AudioEngineId.QT_MULTIMEDIA
    library_views: LibraryViewPreferences = field(
        default_factory=LibraryViewPreferences
    )


def library_view_preferences_to_json(preferences: LibraryViewPreferences) -> str:
    """Serialize the complete Library view contract using stable QML keys."""
    return json.dumps(
        {
            "activeMode": preferences.active_mode,
            "sortMode": preferences.sort_mode,
            "sortDescending": preferences.sort_descending,
            "filterMode": preferences.filter_mode,
            "gallery": {
                "artworkSize": preferences.gallery.artwork_size,
                "spacing": preferences.gallery.spacing,
                "metadataLevel": preferences.gallery.metadata_level,
                "precisionMetadata": preferences.gallery.precision_metadata,
                "quickActions": preferences.gallery.quick_actions,
                "inspector": preferences.gallery.inspector,
            },
            "flow": {
                "coverSize": preferences.flow.cover_size,
                "visibleAlbums": preferences.flow.visible_albums,
                "depth": preferences.flow.depth,
                "ambientColor": preferences.flow.ambient_color,
                "metadataLevel": preferences.flow.metadata_level,
            },
            "vinyl": {
                "sleeveSize": preferences.vinyl.sleeve_size,
                "spacing": preferences.vinyl.spacing,
                "reveal": preferences.vinyl.reveal,
                "metadataLevel": preferences.vinyl.metadata_level,
                "artworkLabel": preferences.vinyl.artwork_label,
                "inspector": preferences.vinyl.inspector,
            },
            "chronology": {
                "grouping": preferences.chronology.grouping,
                "direction": preferences.chronology.direction,
                "density": preferences.chronology.density,
                "metadataLevel": preferences.chronology.metadata_level,
                "showPeriodDensity": preferences.chronology.show_period_density,
            },
            "editorial": {
                "heroVisible": preferences.editorial.hero_visible,
                "informationRichness": preferences.editorial.information_richness,
                "cachedEnrichmentVisible": (
                    preferences.editorial.cached_enrichment_visible
                ),
                "archiveLayout": preferences.editorial.archive_layout,
            },
            "studioList": {
                "density": preferences.studio_list.density,
                "artworkSize": preferences.studio_list.artwork_size,
                "metadataLevel": preferences.studio_list.metadata_level,
                "precisionMetadata": preferences.studio_list.precision_metadata,
                "inspector": preferences.studio_list.inspector,
                "artistColumn": preferences.studio_list.artist_column,
                "yearColumn": preferences.studio_list.year_column,
                "tracksColumn": preferences.studio_list.tracks_column,
                "durationColumn": preferences.studio_list.duration_column,
                "formatColumn": preferences.studio_list.format_column,
            },
            # LIB-A P1-A: estado de la tabla de tracks (preset + visibles
            # + widths) — el dominio lo tipa, nunca dicts arbitrarios.
            "trackTable": {
                "preset": preferences.track_table.preset,
                "visible": {
                    column: getattr(
                        preferences.track_table,
                        f"{_track_table_field(column)}_visible",
                    )
                    for column in _TRACK_TABLE_VISIBLE_COLUMNS
                },
                "widths": {
                    column: getattr(
                        preferences.track_table,
                        f"{_track_table_field(column)}_width",
                    )
                    for column in _TRACK_TABLE_VISIBLE_COLUMNS
                    if column != "actions"
                },
            },
        },
        separators=(",", ":"),
        sort_keys=True,
    )


def library_view_preferences_from_json(
    raw: object,
) -> tuple[LibraryViewPreferences, bool]:
    """Strict, field-isolated decode of persisted Library view preferences."""
    if not isinstance(raw, str):
        return LibraryViewPreferences(), True
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return LibraryViewPreferences(), True
    if not isinstance(parsed, dict):
        return LibraryViewPreferences(), True

    malformed = False

    def section(name: str) -> dict:
        nonlocal malformed
        value = parsed.get(name, {})
        if isinstance(value, dict):
            return value
        malformed = True
        return {}

    def choice(obj: dict, key: str, default: str, allowed: set[str]) -> str:
        nonlocal malformed
        value = obj.get(key, default)
        if isinstance(value, str) and value in allowed:
            return value
        malformed = True
        return default

    def flag(obj: dict, key: str, default: bool) -> bool:
        nonlocal malformed
        value = obj.get(key, default)
        if isinstance(value, bool):
            return value
        malformed = True
        return default

    gallery = section("gallery")
    flow = section("flow")
    vinyl = section("vinyl")
    chronology = section("chronology")
    editorial = section("editorial")
    studio = section("studioList")
    metadata = {"minimal", "standard", "detailed"}
    preferences = LibraryViewPreferences(
        active_mode=choice(
            parsed,
            "activeMode",
            "grid",
            {"grid", "cover", "vinyl", "timeline", "magazine", "list"},
        ),
        sort_mode=choice(
            parsed,
            "sortMode",
            "title",
            {"title", "artist", "year", "tracks", "duration"},
        ),
        sort_descending=flag(parsed, "sortDescending", False),
        filter_mode=choice(
            parsed,
            "filterMode",
            "all",
            {"all", "artwork", "missingArtwork", "dated", "undated", "hires"},
        ),
        gallery=GalleryViewPreferences(
            artwork_size=choice(
                gallery, "artworkSize", "medium", {"small", "medium", "large"}
            ),
            spacing=choice(
                gallery, "spacing", "balanced", {"tight", "balanced", "airy"}
            ),
            metadata_level=choice(gallery, "metadataLevel", "standard", metadata),
            precision_metadata=flag(gallery, "precisionMetadata", False),
            quick_actions=flag(gallery, "quickActions", True),
            inspector=flag(gallery, "inspector", True),
        ),
        flow=AlbumFlowPreferences(
            cover_size=choice(
                flow, "coverSize", "standard", {"small", "standard", "large"}
            ),
            visible_albums=choice(
                flow, "visibleAlbums", "auto", {"auto", "5", "7", "9"}
            ),
            depth=choice(
                flow, "depth", "standard", {"subtle", "standard", "immersive"}
            ),
            ambient_color=flag(flow, "ambientColor", True),
            metadata_level=choice(flow, "metadataLevel", "standard", metadata),
        ),
        vinyl=ListeningWallPreferences(
            sleeve_size=choice(
                vinyl, "sleeveSize", "standard", {"small", "standard", "large"}
            ),
            spacing=choice(
                vinyl, "spacing", "standard", {"tight", "standard", "gallery"}
            ),
            reveal=choice(
                vinyl, "reveal", "standard", {"subtle", "standard", "pronounced"}
            ),
            metadata_level=choice(vinyl, "metadataLevel", "standard", metadata),
            artwork_label=flag(vinyl, "artworkLabel", True),
            inspector=flag(vinyl, "inspector", True),
        ),
        chronology=ChronologyPreferences(
            grouping=choice(chronology, "grouping", "decade", {"decade", "year"}),
            direction=choice(chronology, "direction", "newest", {"newest", "oldest"}),
            density=choice(
                chronology, "density", "standard", {"compact", "standard", "expanded"}
            ),
            metadata_level=choice(chronology, "metadataLevel", "standard", metadata),
            show_period_density=flag(chronology, "showPeriodDensity", False),
        ),
        editorial=EditorialPreferences(
            hero_visible=flag(editorial, "heroVisible", True),
            information_richness=choice(
                editorial,
                "informationRichness",
                "standard",
                {"minimal", "standard", "rich"},
            ),
            cached_enrichment_visible=flag(editorial, "cachedEnrichmentVisible", True),
            archive_layout=choice(
                editorial, "archiveLayout", "list", {"list", "compactGrid"}
            ),
        ),
        studio_list=StudioListPreferences(
            density=choice(
                studio, "density", "standard", {"compact", "standard", "comfortable"}
            ),
            artwork_size=choice(
                studio, "artworkSize", "small", {"none", "small", "standard"}
            ),
            metadata_level=choice(studio, "metadataLevel", "standard", metadata),
            precision_metadata=flag(studio, "precisionMetadata", True),
            inspector=flag(studio, "inspector", True),
            artist_column=flag(studio, "artistColumn", True),
            year_column=flag(studio, "yearColumn", True),
            tracks_column=flag(studio, "tracksColumn", True),
            duration_column=flag(studio, "durationColumn", True),
            format_column=flag(studio, "formatColumn", True),
        ),
        track_table=_decode_track_table(parsed.get("trackTable")),
    )
    return preferences, malformed


def _decode_track_table(raw: object) -> LibraryTrackTablePreferences:
    """Field-isolated decode del estado de la tabla (LIB-A P1-A).

    - sin trackTable → defaults seguros;
    - campo ausente → default SOLO para ese campo;
    - bool/width malformado → default SOLO para ese campo;
    - claves futuras desconocidas ignoradas;
    - Title NUNCA deserializa oculto (estructural);
    - widths clampeados con el mismo rango del resize interactivo."""
    if not isinstance(raw, dict):
        return LibraryTrackTablePreferences()

    visible_raw = raw.get("visible", {})
    widths_raw = raw.get("widths", {})
    if not isinstance(visible_raw, dict):
        visible_raw = {}
    if not isinstance(widths_raw, dict):
        widths_raw = {}

    preset = raw.get("preset", "essential")
    if not isinstance(preset, str) or preset not in _TRACK_TABLE_PRESETS:
        preset = "essential"

    kwargs: dict[str, object] = {"preset": preset}
    for column in _TRACK_TABLE_VISIBLE_COLUMNS:
        field = _track_table_field(column)
        if column == "title":
            # Estructural: nunca oculto.
            kwargs["title_visible"] = True
            continue
        default = LibraryTrackTablePreferences._default_visible(column)
        value = visible_raw.get(column, default)
        if isinstance(value, bool):
            kwargs[f"{field}_visible"] = value
        else:
            kwargs[f"{field}_visible"] = default
    for column in _TRACK_TABLE_VISIBLE_COLUMNS:
        field = _track_table_field(column)
        if column == "actions":
            continue  # ancho estructural (diseño actual: fijo)
        default = LibraryTrackTablePreferences._default_width(column)
        value = widths_raw.get(column, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            value = default
        kwargs[f"{field}_width"] = _clamp_track_table_width(column, float(value))
    return LibraryTrackTablePreferences(**kwargs)


def window_geometry_to_json(geometry: WindowGeometry) -> str:
    """Strict JSON serialization of a WindowGeometry (canonical key order)."""
    return json.dumps(
        {
            "x": geometry.x,
            "y": geometry.y,
            "width": geometry.width,
            "height": geometry.height,
            "maximized": geometry.maximized,
        }
    )


def window_geometry_from_json(raw: object) -> tuple[WindowGeometry, bool]:
    """Decode a persisted window_geometry value into (geometry, malformed).

    M11.2C field fallback rules: a missing row is not this function's
    concern (callers default silently); a present row must be strict JSON
    whose width/height keys exist and are positive integers. x/y may be
    null or any integer (negative is legitimate), and default to None when
    missing; maximized defaults to False and must be a boolean when
    present. Any violation falls back to the default WindowGeometry with
    malformed=True.
    """
    if not isinstance(raw, str):
        return WindowGeometry(), True
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return WindowGeometry(), True
    if not isinstance(parsed, dict):
        return WindowGeometry(), True

    def _is_int(value: object) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)

    width = parsed.get("width")
    height = parsed.get("height")
    if not _is_int(width) or not _is_int(height) or width <= 0 or height <= 0:
        return WindowGeometry(), True

    x = parsed.get("x")
    y = parsed.get("y")
    if x is not None and not _is_int(x):
        return WindowGeometry(), True
    if y is not None and not _is_int(y):
        return WindowGeometry(), True

    maximized = parsed.get("maximized", False)
    if not isinstance(maximized, bool):
        return WindowGeometry(), True

    return (
        WindowGeometry(x=x, y=y, width=width, height=height, maximized=maximized),
        False,
    )
