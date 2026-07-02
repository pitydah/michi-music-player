"""PodcastFeedParser — parse RSS/Atom podcast feeds using xml.etree.ElementTree."""

from __future__ import annotations

import datetime
import logging
import re
import xml.etree.ElementTree as ET
from urllib.request import urlopen, Request

from streaming.podcast_models import PodcastEpisode, PodcastShow

logger = logging.getLogger("michi.podcast.feed")


class ParseResult:
    def __init__(self):
        self.ok: bool = False
        self.show: PodcastShow | None = None
        self.episodes: list[PodcastEpisode] = []
        self.warnings: list[str] = []
        self.errors: list[str] = []


def parse_feed(feed_url: str, timeout: int = 30) -> ParseResult:
    """Parse a podcast RSS feed and return shows + episodes."""
    result = ParseResult()

    if not feed_url.startswith(("http://", "https://")):
        result.errors.append("La URL debe comenzar con http:// o https://")
        return result

    try:
        req = Request(feed_url, headers={"User-Agent": "MichiMusicPlayer/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except Exception as e:
        result.errors.append(f"No se pudo acceder al feed: {e}")
        return result

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        result.errors.append(f"XML invalido: {e}")
        return result

    # Detect RSS 2.0 or Atom
    is_rss = root.tag == "rss"
    is_atom = root.tag in ("feed", "{http://www.w3.org/2005/Atom}feed")

    if not is_rss and not is_atom:
        result.errors.append("Formato de feed no soportado (se esperaba RSS 2.0 o Atom)")
        return result

    if is_rss:
        _parse_rss(root, result)
    else:
        _parse_atom(root, result)

    if result.show is None:
        result.errors.append("No se pudo extraer informacion del canal")
        return result

    result.ok = True
    return result


def _parse_rss(root: ET.Element, result: ParseResult):
    channel = root.find("channel")
    if channel is None:
        result.errors.append("No se encontro <channel> en el RSS")
        return

    show = PodcastShow()
    show.feed_url = _tag_text(channel, "title") or ""
    show.title = _tag_text(channel, "title") or ""
    show.website = _tag_text(channel, "link") or ""
    show.description = _tag_text(channel, "description") or ""
    show.author = _itunes_text(channel, "author") or _tag_text(channel, "managingEditor") or ""

    # Image
    img = channel.find("image")
    if img is not None:
        show.image_url = _tag_text(img, "url") or ""
    itunes_img = channel.find("{http://www.itunes.com/dtds/podcast-1.0.dtd}image")
    if itunes_img is not None and not show.image_url:
        show.image_url = itunes_img.get("href", "")

    show.language = _tag_text(channel, "language") or ""
    last_build = _tag_text(channel, "lastBuildDate") or _tag_text(channel, "pubDate") or ""
    if last_build:
        show.last_updated = _normalize_date(last_build)

    # Categories
    for cat in channel.findall("category"):
        text = cat.text
        if text and text.strip():
            show.categories.append(text.strip())
    for cat in channel.findall("{http://www.itunes.com/dtds/podcast-1.0.dtd}category"):
        text = cat.get("text", "")
        if text:
            show.categories.append(text)

    result.show = show

    # Items/episodes
    for item in channel.findall("item"):
        ep = PodcastEpisode()
        ep.guid = _guid(item)
        ep.title = _tag_text(item, "title") or "(sin titulo)"
        ep.description = _tag_text(item, "description") or ""
        ep.episode_url = _tag_text(item, "link") or ""

        # Enclosure
        enc = item.find("enclosure")
        if enc is not None:
            ep.audio_url = enc.get("url", "")
            ep.mime_type = enc.get("type", "")
            try:
                ep.file_size = int(enc.get("length", 0))
            except (ValueError, TypeError):
                ep.file_size = 0

        if not ep.audio_url:
            continue  # skip non-audio items

        ep.image_url = _itunes_text(item, "image") or show.image_url
        pub = _tag_text(item, "pubDate") or ""
        if pub:
            ep.published_at = _normalize_date(pub)
        ep.duration_seconds = _parse_duration(
            _itunes_text(item, "duration") or _tag_text(item, "duration") or "0"
        )
        result.episodes.append(ep)

    if not result.episodes:
        result.warnings.append("No se encontraron episodios con audio en este feed")


def _parse_atom(root: ET.Element, result: ParseResult):
    ns = "{http://www.w3.org/2005/Atom}"
    show = PodcastShow()
    show.feed_url = _tag_text(root, f"{ns}title") or ""
    show.title = _tag_text(root, f"{ns}title") or ""
    link_el = root.find(f"{ns}link[@rel='alternate']") or root.find(f"{ns}link")
    if link_el is not None:
        show.website = link_el.get("href", "")
    show.description = _tag_text(root, f"{ns}subtitle") or ""

    result.show = show

    for entry in root.findall(f"{ns}entry"):
        ep = PodcastEpisode()
        ep.guid = _atom_id(entry, ns)
        ep.title = _tag_text(entry, f"{ns}title") or "(sin titulo)"
        ep.description = _tag_text(entry, f"{ns}summary") or ""
        link_el = entry.find(f"{ns}link[@rel='alternate']") or entry.find(f"{ns}link")
        if link_el is not None:
            ep.episode_url = link_el.get("href", "")
        ep.audio_url = _atom_enclosure_url(entry, ns)
        if not ep.audio_url:
            continue
        pub = _tag_text(entry, f"{ns}published") or _tag_text(entry, f"{ns}updated") or ""
        if pub:
            ep.published_at = pub[:10]
        result.episodes.append(ep)

    if not result.episodes:
        result.warnings.append("No se encontraron episodios con audio en este feed")


def _tag_text(parent: ET.Element, tag: str) -> str:
    el = parent.find(tag)
    return el.text.strip() if el is not None and el.text else ""


def _itunes_text(parent: ET.Element, tag: str) -> str:
    ns = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
    el = parent.find(f"{ns}{tag}")
    if el is not None:
        return el.text.strip() if el.text else el.get("href", "")
    return ""


def _guid(item: ET.Element) -> str:
    guid_el = item.find("guid")
    if guid_el is not None and guid_el.text:
        return guid_el.text.strip()
    link = _tag_text(item, "link")
    if link:
        return link
    enc = item.find("enclosure")
    if enc is not None:
        return enc.get("url", "")
    import hashlib
    return hashlib.md5((_tag_text(item, "title") or "").encode()).hexdigest()


def _atom_id(entry: ET.Element, ns: str) -> str:
    id_el = entry.find(f"{ns}id")
    if id_el is not None and id_el.text:
        return id_el.text.strip()
    link = entry.find(f"{ns}link")
    if link is not None:
        return link.get("href", "")
    import hashlib
    return hashlib.md5((_tag_text(entry, f"{ns}title") or "").encode()).hexdigest()


def _atom_enclosure_url(entry: ET.Element, ns: str) -> str:
    for link in entry.findall(f"{ns}link"):
        rel = link.get("rel", "")
        if rel == "enclosure" or link.get("type", "").startswith("audio/"):
            return link.get("href", "")
    return ""


def _parse_duration(text: str) -> int:
    if not text:
        return 0
    text = text.strip()
    # HH:MM:SS
    m = re.match(r"(\d+):(\d+):(\d+)", text)
    if m:
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
    # MM:SS
    m = re.match(r"(\d+):(\d+)", text)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    # Plain seconds
    try:
        return int(float(text))
    except (ValueError, TypeError):
        return 0


def _normalize_date(date_str: str) -> str:
    """Try to parse a date string and return ISO YYYY-MM-DD."""
    if not date_str:
        return ""
    # Common RSS formats
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str[:10]
