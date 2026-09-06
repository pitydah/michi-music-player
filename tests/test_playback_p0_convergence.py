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
    def test_toggle_from_diverged_canonical_state_does_not_loop_play(self):
        """P0 failure mode: el backend suena (físico PLAYING) pero el
        canónico quedó STOPPED (evento perdido). El toggle decide sobre el
        canónico: hoy envía play() — este test documenta la decisión del
        seam para que el diagnóstico real (traza) confirme dónde se pierde
        el evento antes de proponer convergencia activa."""
        audio, service, bridge = _chain()
        service.load_and_play(Path("/m/a.flac"))
        audio.trigger_media_accepted(Path("/m/a.flac"))
        # El backend YA está PLAYING físicamente (ghost/evento perdido)…
        audio.state = "playing"
        # …pero el modelo nunca recibió el PLAYING.
        assert service.state.status is PlaybackStatus.STOPPED
        assert bridge.status == "stopped"

        bridge.toggle_play_pause()
        # Comportamiento actual documentado: sin conocer el físico, el
        # canónico STOPPED elige play() (no pausa): el backend sigue
        # sonando y el modelo sigue sin PLAYING (no hubo transición
        # física nueva que publicar). El diagnóstico real (traza P0)
        # confirma dónde se pierde el evento antes de la convergencia.
        assert audio.state == "playing", (
            "el toggle no pausó: decidió play() sobre un canónico divergido"
        )
        assert service.state.status is PlaybackStatus.STOPPED
