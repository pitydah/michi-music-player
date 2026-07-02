"""Podcast models — data classes for podcasts, episodes, downloads, and history."""

from __future__ import annotations

import dataclasses
from typing import Any


@dataclasses.dataclass
class PodcastShow:
    id: int = 0
    title: str = ""
    feed_url: str = ""
    website: str = ""
    author: str = ""
    description: str = ""
    image_url: str = ""
    image_path: str = ""
    language: str = ""
    categories: list[str] = dataclasses.field(default_factory=list)
    last_updated: str = ""
    episode_count: int = 0
    unread_count: int = 0
    favorite: bool = False
    created_at: str = ""
    updated_at: str = ""


@dataclasses.dataclass
class PodcastEpisode:
    id: int = 0
    podcast_id: int = 0
    guid: str = ""
    title: str = ""
    description: str = ""
    audio_url: str = ""
    episode_url: str = ""
    image_url: str = ""
    image_path: str = ""
    published_at: str = ""
    duration_seconds: int = 0
    position_seconds: int = 0
    played: bool = False
    completed: bool = False
    favorite: bool = False
    downloaded: bool = False
    local_path: str = ""
    file_size: int = 0
    mime_type: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclasses.dataclass
class PodcastDownload:
    episode_id: int = 0
    status: str = ""  # queued | downloading | completed | error
    progress: float = 0.0
    local_path: str = ""
    file_size: int = 0
    error: str = ""
    started_at: str = ""
    completed_at: str = ""


@dataclasses.dataclass
class BroadcastHistoryItem:
    id: int = 0
    entry_type: str = "radio"  # radio | podcast
    ref_id: str = ""
    title: str = ""
    subtitle: str = ""
    started_at: str = ""
    ended_at: str = ""
    duration_seconds: int = 0
    position_seconds: int = 0
    completed: bool = False
    extra: dict[str, Any] = dataclasses.field(default_factory=dict)
