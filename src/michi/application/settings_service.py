"""Settings use case — owns persisted preference lifecycle.

Depends on SettingsRepository port. No SQLite/infrastructure dependency.
Does NOT own runtime Playback/Queue/Library state.
"""

from michi.application.persistence import SettingsRepository
from michi.domain.audio_engine import AudioEngineId
from michi.domain.settings import LibraryViewPreferences, SettingsState, WindowGeometry


class SettingsService:
    """Authority over persisted SettingsState. Coordinates load/save lifecycle."""

    def __init__(self, repository: SettingsRepository) -> None:
        self._repo = repository
        self._state: SettingsState | None = None

    @property
    def state(self) -> SettingsState:
        if self._state is None:
            self._state = self._repo.load()
        return self._state

    def load(self) -> SettingsState:
        self._state = self._repo.load()
        return self._state

    def save(self) -> None:
        self._repo.save(self.state)

    def set_playback_preferences(self, volume: int, muted: bool) -> None:
        s = self.state
        s.volume = max(0, min(100, volume))
        s.muted = muted

    def set_last_directory(self, path: str) -> None:
        self.state.last_directory = path

    def set_recent_files(self, files: list[str]) -> None:
        self.state.recent_files = list(files)

    def set_theme(self, theme: str) -> None:
        self.state.theme = theme
        self.save()

    def set_window_geometry(self, geometry: WindowGeometry) -> None:
        self.state.window_geometry = geometry
        self.save()

    def set_audio_engine(self, engine_id: AudioEngineId) -> None:
        """Persist the SELECTED engine preference (M11.3F).

        Durable save BEFORE any destructive engine-switch boundary: if the
        persistence write fails, the in-memory preference is restored to its
        previous value and the ORIGINAL persistence error re-raised — no
        half-mutated preference survives a failed save.
        """
        previous = self.state.audio_engine_id
        if previous == engine_id:
            return
        self.state.audio_engine_id = engine_id
        try:
            self.save()
        except Exception:
            self.state.audio_engine_id = previous
            raise

    def set_dsd_pcm_conversion_consent(self, enabled: bool) -> None:
        """Persist explicit DSD→PCM conversion consent transactionally.

        Absence is the safe default. Every accepted change advances the
        monotonic policy revision consumed by plans and pre-COMMIT checks.
        Revoking conversion also revokes DSP consent on the same route.
        """
        enabled = bool(enabled)
        previous = (
            self.state.dsd_pcm_conversion_consent,
            self.state.dsd_pcm_dsp_consent,
            self.state.dsd_pcm_policy_revision,
        )
        if previous[0] == enabled:
            return
        self.state.dsd_pcm_conversion_consent = enabled
        if not enabled:
            self.state.dsd_pcm_dsp_consent = False
        self.state.dsd_pcm_policy_revision += 1
        try:
            self.save()
        except Exception:
            (
                self.state.dsd_pcm_conversion_consent,
                self.state.dsd_pcm_dsp_consent,
                self.state.dsd_pcm_policy_revision,
            ) = previous
            raise

    def set_dsd_pcm_dsp_consent(self, enabled: bool) -> None:
        """Persist DSP consent separately; requires conversion consent."""
        enabled = bool(enabled)
        if enabled and not self.state.dsd_pcm_conversion_consent:
            raise ValueError("DSD_PCM_DSP_CONSENT_REQUIRES_CONVERSION")
        previous = (
            self.state.dsd_pcm_dsp_consent,
            self.state.dsd_pcm_policy_revision,
        )
        if previous[0] == enabled:
            return
        self.state.dsd_pcm_dsp_consent = enabled
        self.state.dsd_pcm_policy_revision += 1
        try:
            self.save()
        except Exception:
            (
                self.state.dsd_pcm_dsp_consent,
                self.state.dsd_pcm_policy_revision,
            ) = previous
            raise

    def set_dsd_pcm_quality_profile(self, quality_profile: str) -> None:
        allowed = ("FAST", "BALANCED", "HIGH", "REFERENCE")
        if quality_profile not in allowed:
            raise ValueError("DSD_PCM_QUALITY_PROFILE_UNKNOWN")
        previous = (
            self.state.dsd_pcm_quality_profile,
            self.state.dsd_pcm_policy_revision,
        )
        if previous[0] == quality_profile:
            return
        self.state.dsd_pcm_quality_profile = quality_profile
        self.state.dsd_pcm_policy_revision += 1
        try:
            self.save()
        except Exception:
            (
                self.state.dsd_pcm_quality_profile,
                self.state.dsd_pcm_policy_revision,
            ) = previous
            raise

    def set_album_artwork_source(self, album_key: str, source: str) -> None:
        """POST-R4 E2 (12.4): persiste la fuente de artwork elegida por
        el usuario para un álbum ("local"/"external"/"" = quitar la
        elección). Misma verdad transaccional que set_audio_engine: un
        save fallido restaura el estado anterior."""
        album_key = (album_key or "").strip()
        source = (source or "").strip()
        if source not in ("local", "external", ""):
            return
        previous = dict(self.state.album_artwork_source)
        if source:
            self.state.album_artwork_source[album_key] = source
        else:
            self.state.album_artwork_source.pop(album_key, None)
        if self.state.album_artwork_source == previous:
            return
        try:
            self.save()
        except Exception:
            self.state.album_artwork_source = previous
            raise

    def album_artwork_source(self, album_key: str) -> str:
        return self.state.album_artwork_source.get(album_key, "")

    def set_online_enrichment(self, enabled: bool) -> None:
        """Persist the Online Library Enrichment policy (M6.9 Presentation).

        Same transactional truth as ``set_audio_engine``: on save failure the
        in-memory state is rolled back and the original error re-raised — no
        half-mutated policy survives a failed save.
        """
        previous = self.state.online_enrichment
        if previous == enabled:
            return
        self.state.online_enrichment = enabled
        try:
            self.save()
        except Exception:
            self.state.online_enrichment = previous
            raise

    def set_library_view_preferences(self, preferences: LibraryViewPreferences) -> None:
        """Persist Library presentation preferences transactionally."""
        previous = self.state.library_views
        if previous == preferences:
            return
        self.state.library_views = preferences
        try:
            self.save()
        except Exception:
            self.state.library_views = previous
            raise
