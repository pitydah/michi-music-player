from core.audio_lab.audio_lab_profile_service import AudioLabProfileService, BUILTIN_PROFILES


class TestAudioLabProfileService:
    def test_create(self):
        svc = AudioLabProfileService()
        assert svc is not None

    def test_builtin_profiles(self):
        assert len(BUILTIN_PROFILES) >= 5
