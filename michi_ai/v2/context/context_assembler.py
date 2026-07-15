from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Protocol, runtime_checkable

from michi_ai.v2.core.models import ContextSnapshot, PrivacyLevel, SanitizedContext

logger = logging.getLogger(__name__)

_MAX_CONTEXT_SIZE = 500
_SENSITIVE_KEYS: frozenset[str] = frozenset({
    "token", "password", "api_key", "secret", "cookie", "credentials",
    "auth", "authorization", "bearer", "jwt", "session_token",
    "refresh_token", "access_key", "private_key",
})


@runtime_checkable
class ContextProvider(Protocol):
    def get_context(self) -> dict[str, Any]: ...


@dataclass
class ContextProviderRegistration:
    name: str
    provider: ContextProvider | Callable[[], dict[str, Any]]
    required: bool = False
    timeout: float = 5.0


class ContextAssembler:
    def __init__(self, max_context_size: int = _MAX_CONTEXT_SIZE) -> None:
        self._providers: dict[str, ContextProviderRegistration] = {}
        self._max_context_size = max_context_size
        self._lock = threading.Lock()

    def register(self, name: str, provider: ContextProvider | Callable[[], dict[str, Any]], required: bool = False, timeout: float = 5.0) -> None:
        self._providers[name] = ContextProviderRegistration(
            name=name, provider=provider, required=required, timeout=timeout,
        )

    def unregister(self, name: str) -> None:
        self._providers.pop(name, None)

    def _get_provider_data(self, reg: ContextProviderRegistration) -> dict[str, Any]:
        if isinstance(reg.provider, ContextProvider):
            return reg.provider.get_context()
        return reg.provider()

    def assemble(self, session_id: str = "", privacy_level: PrivacyLevel = PrivacyLevel.STANDARD) -> ContextSnapshot:
        sections: dict[str, dict[str, Any]] = {}
        warnings: list[str] = []

        def _fetch_provider(reg: ContextProviderRegistration, container: list[dict[str, Any] | Exception], evt: threading.Event) -> None:
            try:
                data = reg.provider.get_context() if isinstance(reg.provider, ContextProvider) else reg.provider()
                container.append(data if isinstance(data, dict) else {})
            except Exception as e:
                container.append(e)
            finally:
                evt.set()

        for name, reg in self._providers.items():
            event = threading.Event()
            result_container: list[dict[str, Any] | Exception] = []

            t = threading.Thread(target=_fetch_provider, args=(reg, result_container, event), daemon=True)
            t.start()
            timed_out = not event.wait(timeout=reg.timeout)

            if timed_out or not result_container:
                msg = f"timed out after {reg.timeout}s" if timed_out else "no response"
                if reg.required:
                    warnings.append(f"Required context provider '{name}' {msg}")
                    sections[name] = {}
                else:
                    logger.debug("Optional context provider '%s' %s", name, msg)
                    sections[name] = {}
            elif isinstance(result_container[0], Exception):
                exc = result_container[0]
                if reg.required:
                    warnings.append(f"Required context provider '{name}' failed: {exc}")
                    sections[name] = {}
                else:
                    logger.debug("Optional context provider '%s' failed: %s", name, exc)
                    sections[name] = {}
            else:
                sections[name] = result_container[0]

        snapshot = ContextSnapshot(
            timestamp=datetime.now(timezone.utc),
            session_id=session_id,
            active_section=sections.get("navigation", {}).get("current_section", ""),
            active_entity=sections.get("navigation", {}).get("active_entity", {}),
            selection=sections.get("selection", {}),
            playback=sections.get("playback", {}),
            queue=sections.get("queue", {}),
            library=sections.get("library", {}),
            devices=sections.get("devices", {}),
            servers=sections.get("servers", {}),
            settings=sections.get("settings", {}),
            jobs=sections.get("jobs", {}),
            capabilities=sections.get("capabilities", {}),
            recent_actions=tuple(sections.get("recent_actions", {}).get("actions", [])),
            warnings=tuple(warnings),
        )
        return snapshot

    def assemble_sanitized(self, session_id: str = "", privacy_level: PrivacyLevel = PrivacyLevel.STANDARD) -> SanitizedContext:
        snapshot = self.assemble(session_id=session_id, privacy_level=privacy_level)
        policy = ContextPrivacyPolicy(privacy_level)
        sanitized, removed = policy.apply(snapshot)
        return SanitizedContext(
            snapshot=sanitized,
            sanitized_at=datetime.now(timezone.utc),
            removed_fields=tuple(removed),
            privacy_level=privacy_level,
        )

    def clear(self) -> None:
        self._providers.clear()


_SENSITIVE_KEYS: frozenset[str] = frozenset({
    "token", "password", "api_key", "secret", "cookie", "credentials",
    "auth", "authorization", "bearer", "jwt", "session_token",
    "refresh_token", "access_key", "private_key",
})


class ContextPrivacyPolicy:
    def __init__(self, level: PrivacyLevel = PrivacyLevel.STANDARD) -> None:
        self.level = level

    def apply(self, snapshot: ContextSnapshot) -> tuple[ContextSnapshot, list[str]]:
        removed: list[str] = []

        if self.level == PrivacyLevel.MINIMAL:
            return self._apply_minimal(snapshot, removed)
        elif self.level == PrivacyLevel.STANDARD:
            return self._apply_standard(snapshot, removed)
        elif self.level == PrivacyLevel.DIAGNOSTIC:
            return self._apply_diagnostic(snapshot, removed)
        elif self.level == PrivacyLevel.LOCAL_FULL:
            return self._apply_local_full(snapshot, removed)
        return snapshot, removed

    def _apply_minimal(self, snapshot: ContextSnapshot, removed: list[str]) -> tuple[ContextSnapshot, list[str]]:
        removed.append("playback")
        removed.append("queue")
        removed.append("devices")
        removed.append("servers")
        removed.append("settings")
        removed.append("jobs")
        removed.append("recent_actions")
        return ContextSnapshot(
            timestamp=snapshot.timestamp,
            session_id=self._mask_id(snapshot.session_id),
            active_section=snapshot.active_section,
            active_entity={},
            selection={},
            playback={},
            queue={},
            library=self._sanitize_library_minimal(snapshot.library),
            devices={},
            servers={},
            settings={},
            jobs={},
            capabilities={},
            recent_actions=(),
            warnings=snapshot.warnings,
        ), removed

    def _apply_standard(self, snapshot: ContextSnapshot, removed: list[str]) -> tuple[ContextSnapshot, list[str]]:
        return self._strip_sensitive(snapshot, removed)

    def _apply_diagnostic(self, snapshot: ContextSnapshot, removed: list[str]) -> tuple[ContextSnapshot, list[str]]:
        return self._strip_sensitive(snapshot, removed)

    def _apply_local_full(self, snapshot: ContextSnapshot, removed: list[str]) -> tuple[ContextSnapshot, list[str]]:
        return snapshot, removed

    def _strip_sensitive(self, snapshot: ContextSnapshot, removed: list[str]) -> tuple[ContextSnapshot, list[str]]:
        def _clean_dict(d: dict[str, Any], path: str = "") -> dict[str, Any]:
            result: dict[str, Any] = {}
            for k, v in d.items():
                current_path = f"{path}.{k}" if path else k
                if k.lower() in _SENSITIVE_KEYS:
                    removed.append(current_path)
                    continue
                if isinstance(v, dict):
                    result[k] = _clean_dict(v, current_path)
                elif isinstance(v, str) and self._is_path(v):
                    if self.level == PrivacyLevel.DIAGNOSTIC:
                        result[k] = self._truncate_path(v)
                    else:
                        removed.append(current_path)
                else:
                    result[k] = v
            return result

        return ContextSnapshot(
            timestamp=snapshot.timestamp,
            session_id=snapshot.session_id,
            active_section=snapshot.active_section,
            active_entity=_clean_dict(snapshot.active_entity),
            selection=_clean_dict(snapshot.selection),
            playback=_clean_dict(snapshot.playback),
            queue=_clean_dict(snapshot.queue),
            library=_clean_dict(snapshot.library),
            devices=_clean_dict(snapshot.devices),
            servers=_clean_dict(snapshot.servers),
            settings=_clean_dict(snapshot.settings),
            jobs=_clean_dict(snapshot.jobs),
            capabilities=snapshot.capabilities,
            recent_actions=snapshot.recent_actions,
            warnings=snapshot.warnings,
        ), removed

    def _sanitize_library_minimal(self, library: dict[str, Any]) -> dict[str, Any]:
        safe_keys = {"track_count", "album_count", "artist_count", "genre_count"}
        return {k: v for k, v in library.items() if k in safe_keys}

    def _mask_id(self, session_id: str) -> str:
        if len(session_id) <= 8:
            return session_id
        return session_id[:4] + "..." + session_id[-4:]

    def _is_path(self, value: str) -> bool:
        return value.startswith("/") or value.startswith("~") or "\\" in value

    def _truncate_path(self, path: str) -> str:
        parts = path.strip("/").split("/")
        if len(parts) <= 2:
            return path
        return "/" + parts[0] + "/.../" + parts[-1]
