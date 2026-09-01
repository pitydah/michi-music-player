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
    )
    return preferences, malformed


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
