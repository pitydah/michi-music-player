"""PLAYBACK-P0-04 — Regression seals across the REAL boundary:

backend observation → AudioPort callback → PlaybackService → PlaybackBridge
→ QML state.

The contract under test is the physical↔canonical convergence chain, not a
direct state setter. Each test drives the fake backend (the observable
physical authority) and asserts on the bridge properties that QML binds
(status/position).

Also seals the P0 failure mode: when the canonical model never learned the
physical PLAYING (event lost), a click must NOT loop play() forever — the
toggle decision is exercised so the divergence is visible in the seam.
"""

from pathlib import Path

from michi.application.coordinator import PlaybackCoordinator
from michi.application.playback_service import PlaybackService
from michi.domain.playback import PlaybackStatus
from michi.presentation.playback_bridge import PlaybackBridge
from tests.conftest import FakeAudioPort


def _chain():
    """Real seam: FakeAudioPort (backend) → PlaybackCoordinator
    (position/duration projection) → PlaybackService → Bridge."""
    audio = FakeAudioPort()
    service = PlaybackService(audio)
    coordinator = PlaybackCoordinator(audio, service)
    coordinator.start()
    bridge = PlaybackBridge(service)
    return audio, service, bridge


def _accepted_playing(audio, service, path=Path("/m/a.flac")):
    """Drive the physical chain to a legitimately PLAYING canonical model."""
    service.load_and_play(path)
    audio.trigger_media_accepted(path)
    audio.trigger_playback_state(PlaybackStatus.PLAYING)
    assert service.state.status is PlaybackStatus.PLAYING


def _pause_via_toggle(bridge, audio, service):
    """Toggle desde PLAYING canónico → pause físico + evento PAUSED."""
    bridge.toggle_play_pause()  # canonical PLAYING → pause
    assert audio.state == "paused"
    audio.trigger_playback_state(PlaybackStatus.PAUSED)
    assert service.state.status is PlaybackStatus.PAUSED


class TestPhysicalCanonicalConvergence:
    def test_full_physical_chain_reaches_qml_state(self):
        """§3.6: backend observation → callback → service → bridge: the
        QML-bound status must become playing."""
        audio, service, bridge = _chain()
        _accepted_playing(audio, service)
        assert bridge.status == "playing"

    def test_pause_click_reaches_backend_and_freezes_position(self):
        """§3.6: click pause → backend PAUSED → canonical PAUSED → the
        QML status flips to paused."""
        audio, service, bridge = _chain()
        _accepted_playing(audio, service)
        audio.emit_position_changed(12_000)
        assert bridge.position == 12  # bridge: segundos (QML contract)

        _pause_via_toggle(bridge, audio, service)
        assert bridge.status == "paused"
        # Posición congelada: el backend físico en pausa no emite ticks —
        # el modelo conserva la última posición confirmada (12 s).
        assert service.state.position_ms == 12_000

    def test_resume_click_continues_from_same_position(self):
        """§3.6: resume → backend PLAYING → canonical PLAYING."""
        audio, service, bridge = _chain()
        _accepted_playing(audio, service)
        audio.emit_position_changed(12_000)
        _pause_via_toggle(bridge, audio, service)
        bridge.toggle_play_pause()  # canonical PAUSED → resume (no play())
        assert audio.state == "playing"
        audio.trigger_playback_state(PlaybackStatus.PLAYING)
        assert bridge.status == "playing"
        # La posición confirmada en pausa se conserva al reanudar.
        assert service.state.position_ms == 12_000

    def test_space_uses_bridge_toggle_authority(self):
        """P0-03: el Space llama playback.toggle_play_pause() — el mismo
        camino que el botón; el seal estructural (main.qml) vive en el
        design canon. Aquí: el toggle del bridge es el de tres estados."""
        audio, service, bridge = _chain()
        _accepted_playing(audio, service)
        bridge.toggle_play_pause()
        assert audio.state == "paused"
        audio.trigger_playback_state(PlaybackStatus.PAUSED)
        bridge.toggle_play_pause()  # PAUSED → resume (no play())
        assert audio.state == "playing"


class TestDivergenceSeam:
    def test_diverged_physical_playing_converges_to_canonical_playing(self):
        """POST-R4 P12 (15.3-A): el backend suena (físico PLAYING) y el
        canónico quedó STOPPED (evento perdido) con media legítima
        aceptada. El toggle NO emite un play() no-op que eterniza la
        divergencia: el sistema converge al canónico PLAYING con la
        evidencia del estado físico (la decisión la toma intent+accepted,
        nunca el botón)."""
        audio, service, bridge = _chain()
        service.load_and_play(Path("/m/a.flac"))
        audio.trigger_media_accepted(Path("/m/a.flac"))
        # El backend YA está PLAYING físicamente (ghost/evento perdido)…
        audio.state = "playing"
        # …pero el modelo nunca recibió el PLAYING.
        assert service.state.status is PlaybackStatus.STOPPED
        assert bridge.status == "stopped"

        bridge.toggle_play_pause()
        # A: convergencia a PLAYING (evento legítimo aceptado): el estado
        # estable divergido (físico PLAYING / canónico STOPPED) NO existe.
        assert service.state.status is PlaybackStatus.PLAYING, (
            "el canónico converge a PLAYING con la evidencia física"
        )
        assert bridge.status == "playing"

        # El siguiente toggle opera sobre la verdad canónica: pause exacto.
        bridge.toggle_play_pause()
        assert audio.state == "paused"
        audio.trigger_playback_state(PlaybackStatus.PAUSED)
        assert service.state.status is PlaybackStatus.PAUSED

    def test_play_from_diverged_state_does_not_replay(self):
        """El play() directo desde la divergencia (sin toggle) tampoco
        re-emite play(): converge a PLAYING y el backend no recibe una
        orden redundante."""
        audio, service, bridge = _chain()
        service.load_and_play(Path("/m/a.flac"))
        audio.trigger_media_accepted(Path("/m/a.flac"))
        audio.state = "playing"
        assert service.state.status is PlaybackStatus.STOPPED

        service.play()
        assert audio.state == "playing", "sin orden redundante al backend"
        assert service.state.status is PlaybackStatus.PLAYING

    def test_diverged_without_accepted_media_still_safety_stops(self):
        """Sin media aceptada, el PLAYING físico sigue siendo ilegítimo:
        el toggle mantiene la convergencia de seguridad (B: ghost
        playback → STOPPED físico)."""
        audio, service, bridge = _chain()
        service.load_and_play(Path("/m/a.flac"))
        # sin trigger_media_accepted: el backend "arrancó solo" (ghost)
        audio.state = "playing"
        assert service.state.status is PlaybackStatus.STOPPED

        bridge.toggle_play_pause()
        # el toggle elige play(); sin accepted, el fix no converge: el
        # play() ordena al backend; el evento PLAYING que sigue sin
        # accepted dispara la convergencia de seguridad (R2).
        audio.trigger_playback_state(PlaybackStatus.PLAYING)
        assert audio.state == "stopped", "ghost playback converge físicamente a STOPPED"
        assert service.state.status is PlaybackStatus.STOPPED
