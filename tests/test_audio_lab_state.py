from core.audio_lab.audio_lab_state import AudioLabState


class TestAudioLabState:
    def test_create(self):
        state = AudioLabState()
        assert state._inputs == []

    def test_empty_inputs(self):
        state = AudioLabState()
        assert state.inputs == []
