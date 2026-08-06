from __future__ import annotations

from typing import Any, Mapping, Protocol


class MixServiceProtocol(Protocol):
    """Catalog-query contract consumed by the mix facade and QML bridge."""

    @property
    def available(self) -> bool: ...

    def fetch_tracks(
        self,
        sql: str,
        params: list,
        limit: int = 50,
    ) -> list[dict[str, Any]]: ...

    def favorites(self, limit: int = 50) -> list[dict[str, Any]]: ...
    def recent(self, limit: int = 50) -> list[dict[str, Any]]: ...
    def most_played(self, limit: int = 50) -> list[dict[str, Any]]: ...
    def unplayed(self, limit: int = 50) -> list[dict[str, Any]]: ...

    def rediscovery(
        self,
        limit: int = 30,
        older_than_days: int = 180,
    ) -> list[dict[str, Any]]: ...

    def genre(
        self,
        genre: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]: ...

    def by_field(
        self,
        field: str,
        value: str = "",
        limit: int = 30,
    ) -> list[dict[str, Any]]: ...

    def by_album(
        self,
        album: str = "",
        limit: int = 30,
    ) -> list[dict[str, Any]]: ...

    def by_decade(
        self,
        decade: int = 0,
        limit: int = 30,
    ) -> list[dict[str, Any]]: ...

    def by_year(
        self,
        year: int = 0,
        limit: int = 30,
    ) -> list[dict[str, Any]]: ...

    def high_quality(
        self,
        min_bitrate: int = 320,
        limit: int = 30,
        *,
        lossless: bool = False,
    ) -> list[dict[str, Any]]: ...

    def custom(
        self,
        filters: Mapping[str, Any] | None = None,
        limit: int = 30,
    ) -> list[dict[str, Any]]: ...
