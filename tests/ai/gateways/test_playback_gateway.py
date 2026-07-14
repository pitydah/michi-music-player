from __future__ import annotations

from core.assistant_gateways import ProductionPlaybackGateway


class FakePlayer:
    def __init__(self) -> None:
        self._state = "stopped"
        self._volume = 80
        self._repeat = "none"
        self._shuffle = False
        self.current_title = ""
        self.current_artist = ""
        self.current_album = ""

    @property
    def state(self) -> str:
        return self._state

    @property
    def current(self) -> str:
        return self.current_title

    @property
    def duration(self) -> float:
        return 0.0

    def play(self, filepath: str) -> None:
        self._state = "playing"

    def pause(self) -> None:
        if self._state == "playing":
            self._state = "paused"

    def resume(self) -> None:
        if self._state == "paused":
            self._state = "playing"

    def stop(self) -> None:
        self._state = "stopped"

    def play_next(self) -> None:
        pass

    def play_prev(self) -> None:
        pass

    def seek(self, seconds: float) -> None:
        pass

    def set_volume(self, vol: int) -> None:
        self._volume = vol

    def get_volume(self) -> int:
        return self._volume

    def set_repeat(self, mode: str) -> None:
        self._repeat = mode

    def get_repeat(self) -> str:
        return self._repeat

    def toggle_shuffle(self) -> bool:
        self._shuffle = not self._shuffle
        return self._shuffle

    def get_shuffle(self) -> bool:
        return self._shuffle


class TestProductionPlaybackGateway:
    def setup_method(self) -> None:
        self.player = FakePlayer()
        self.gw = ProductionPlaybackGateway(self.player)

    def test_play_track(self) -> None:
        r = self.gw.play_track("1")
        assert r["ok"] is True

    def test_pause_resume(self) -> None:
        self.gw.play_track("1")
        r = self.gw.pause()
        assert r["ok"] is True
        r = self.gw.resume()
        assert r["ok"] is True

    def test_pause_not_playing(self) -> None:
        r = self.gw.pause()
        assert r["ok"] is False
        assert "NOT_PLAYING" in str(r.get("error", ""))

    def test_stop(self) -> None:
        self.gw.play_track("1")
        r = self.gw.stop()
        assert r["ok"] is True

    def test_volume_valid(self) -> None:
        r = self.gw.set_volume(50)
        assert r["ok"] is True
        assert r["volume"] == 50

    def test_volume_invalid(self) -> None:
        r = self.gw.set_volume(200)
        assert r["ok"] is False

    def test_volume_idempotent(self) -> None:
        self.gw.set_volume(80)
        r = self.gw.set_volume(80)
        assert r["ok"] is True
        assert r.get("idempotent") is True

    def test_repeat_valid(self) -> None:
        r = self.gw.set_repeat("all")
        assert r["ok"] is True

    def test_repeat_invalid(self) -> None:
        r = self.gw.set_repeat("invalid")
        assert r["ok"] is False

    def test_repeat_idempotent(self) -> None:
        r = self.gw.set_repeat("none")
        assert r["ok"] is True
        assert r.get("idempotent") is True

    def test_shuffle_enable(self) -> None:
        r = self.gw.set_shuffle(True)
        assert r["ok"] is True
        assert self.player._shuffle is True

    def test_shuffle_idempotent(self) -> None:
        self.gw.set_shuffle(True)
        r = self.gw.set_shuffle(True)
        assert r["ok"] is True
        assert r.get("idempotent") is True

    def test_seek_not_playing(self) -> None:
        r = self.gw.seek(10.0)
        assert r["ok"] is False

    def test_get_state_playing(self) -> None:
        self.player._state = "playing"
        r = self.gw.get_state()
        assert r["ok"] is True

    def test_unavailable(self) -> None:
        gw = ProductionPlaybackGateway(None)
        r = gw.play_track("1")
        assert r["ok"] is False
