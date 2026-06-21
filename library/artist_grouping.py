"""Artist grouping — intelligent album/track grouping by artist."""
from dataclasses import dataclass, field
from collections import defaultdict

from library.library_db import MediaItem


@dataclass
class ArtistAlbumGroup:
    key: str
    title: str
    artist: str
    albumartist: str
    year: int
    tracks: list
    cover_path: str
    total_duration: float
    disc_count: int
    track_count: int
    formats: list[str]
    genres: list[str]
    album_type: str = ""  # album, ep, single, compilation, appearance


@dataclass
class ArtistGroup:
    key: str
    display_name: str
    sort_name: str
    albums: list[ArtistAlbumGroup] = field(default_factory=list)
    loose_tracks: list[MediaItem] = field(default_factory=list)
    all_tracks: list[MediaItem] = field(default_factory=list)
    genres: list[str] = field(default_factory=list)
    years: list[int] = field(default_factory=list)
    cover_paths: list[str] = field(default_factory=list)
    total_duration: float = 0.0
    track_count: int = 0
    album_count: int = 0
    # External enrichment
    external_id: str = ""
    mbid: str = ""
    bio: str = ""
    genre: str = ""
    thumb_url: str = ""
    banner_url: str = ""
    logo_url: str = ""
    fanart_urls: list[str] = field(default_factory=list)
    thumb_path: str = ""
    banner_path: str = ""
    logo_path: str = ""
    fanart_paths: list[str] = field(default_factory=list)
    country: str = ""
    formed_year: str = ""
    style: str = ""
    mood: str = ""
    website: str = ""
    last_enriched_at: str = ""
    enrichment_status: str = ""  # "loaded", "not_found", "error"


_VARIOUS_NAMES = {"various artists", "varios artistas", "va", "various", "varios",
                   "compilation", "compilacion", "compilación", "soundtrack",
                   "banda sonora", "bso", "ost"}


def normalize_artist_name(name: str) -> str:
    """Normalize artist name for grouping (not for display)."""
    n = str(name or "").strip()
    n = " ".join(n.split())
    if n.lower().startswith("the "):
        n = n[4:].strip()
    return n.lower()


def _artist_key(item: MediaItem) -> str:
    """Get the grouping key for an item's artist. Prefers MusicBrainz ID."""
    mb_raw = getattr(item, "mb_albumartist_id", None)  # noqa: B009
    if mb_raw and isinstance(mb_raw, str) and mb_raw.strip():
        return "mb:" + mb_raw.strip()
    ai = str(getattr(item, "albumartist", "") or "")
    ar = str(item.artist or "")
    return normalize_artist_name(ai or ar) or "artista desconocido"


def _artist_display(item: MediaItem) -> str:
    """Get the display name for an item's artist."""
    ai = str(getattr(item, "albumartist", "") or "")
    ar = str(item.artist or "")
    return ai or ar or "Artista desconocido"


def _album_key(item: MediaItem) -> str:
    """Get the grouping key for an album."""
    al = str(item.album or "")
    return normalize_artist_name(str(getattr(item, "albumartist", "") or item.artist or "")) + "||" + al.lower().strip()


def build_artist_albums(items: list[MediaItem]) -> dict[str, tuple[list[ArtistAlbumGroup], list[MediaItem]]]:
    """Group items by artist, then by album within each artist.
    Returns dict[artist_key -> (albums, loose_tracks)]."""
    by_artist: dict[str, list[MediaItem]] = defaultdict(list)
    unknown_artist: list[MediaItem] = []

    for item in items:
        akey = _artist_key(item)
        if not akey or akey == "artista desconocido":
            unknown_artist.append(item)
        else:
            by_artist[akey].append(item)

    # Build album groups per artist
    result: dict[str, tuple[list[ArtistAlbumGroup], list[MediaItem]]] = {}

    for akey, atracks in by_artist.items():
        # Split tracks with album from those without
        album_tracks = [t for t in atracks if str(t.album or "").strip()]
        loose = [t for t in atracks if not str(t.album or "").strip()]

        # Group by album
        album_map: dict[str, list[MediaItem]] = defaultdict(list)
        for t in album_tracks:
            ak = _album_key(t)
            album_map[ak].append(t)

        album_groups = []
        for _, atracks_album in album_map.items():
            atracks_album.sort(key=lambda t: (getattr(t, "disc_number", 0) or 0,
                                               getattr(t, "track_number", 0) or 0,
                                               t.filename))
            first = atracks_album[0]
            title = first.album or "Sin álbum"
            dur = sum(getattr(t, "duration", 0) or 0 for t in atracks_album)
            discs = set(getattr(t, "disc_number", 0) or 0 for t in atracks_album)
            exts = sorted(set((getattr(t, "ext", "") or "").upper().lstrip(".") for t in atracks_album))
            gens = sorted(set(t.genre for t in atracks_album if t.genre))
            year = first.year or 0

            # Best cover path
            cover = ""
            for t in atracks_album:
                from library.album_art import find_cover_in_dir
                d = getattr(t, "directory", "") or ""
                c = find_cover_in_dir(d) if d else ""
                if c:
                    cover = c
                    break
            if not cover and atracks_album:
                cover = atracks_album[0].filepath

            album_groups.append(ArtistAlbumGroup(
                key=title.lower(),
                title=title,
                artist=_artist_display(first),
                albumartist=getattr(first, "albumartist", "") or "",
                year=year,
                tracks=atracks_album,
                cover_path=cover,
                total_duration=dur,
                disc_count=max(len(discs), 1),
                track_count=len(atracks_album),
                formats=exts,
                genres=gens,
            ))

        # Sort albums by year then title
        album_groups.sort(key=lambda a: (a.year or 9999, a.title.lower()))
        result[akey] = (album_groups, loose)

    # Unknown artist
    if unknown_artist:
        result["artista desconocido"] = ([], unknown_artist)

    return result


def build_artist_groups(items: list[MediaItem]) -> list[ArtistGroup]:
    """Build the full artist hierarchy from flat item list."""
    artist_data = build_artist_albums(items)
    artist_names: dict[str, str] = {}

    for item in items:
        akey = _artist_key(item)
        if akey not in artist_names:
            artist_names[akey] = _artist_display(item)
        # Keep the longest/most complete name
        d = _artist_display(item)
        if len(d) > len(artist_names[akey]):
            artist_names[akey] = d

    groups = []
    for akey, (albums, loose_from_artist) in artist_data.items():
        display = artist_names.get(akey, akey.title())

        all_tracks = []
        cover_paths = []
        genres = set()
        years = set()
        total_dur = 0.0

        for album in albums:
            all_tracks.extend(album.tracks)
            total_dur += album.total_duration
            for g in album.genres:
                genres.add(g)
            if album.year:
                years.add(album.year)
            if album.cover_path and album.cover_path not in cover_paths:
                cover_paths.append(album.cover_path)

        # Loose tracks from the album grouping
        for t in loose_from_artist:
            all_tracks.append(t)
            total_dur += getattr(t, "duration", 0) or 0

        track_count = len(all_tracks)

        groups.append(ArtistGroup(
            key=akey,
            display_name=display,
            sort_name=normalize_artist_name(display) or display.lower(),
            albums=albums,
            loose_tracks=loose_from_artist,
            all_tracks=all_tracks,
            genres=sorted(genres),
            years=sorted(years),
            cover_paths=cover_paths,
            total_duration=total_dur,
            track_count=track_count,
            album_count=sum(1 for a in albums if a.title != "Sin álbum"),
        ))

    groups.sort(key=lambda g: g.sort_name)
    return groups
