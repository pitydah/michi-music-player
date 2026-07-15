from __future__ import annotations

from core.protocols import (
    JobServiceProtocol,
    ActionRegistryProtocol,
    ConfirmationServiceProtocol,
    NavigationProtocol,
    PlaybackServiceProtocol,
    QueueServiceProtocol,
    DeviceSyncServiceProtocol,
    AudioLabServiceProtocol,
    MixServiceProtocol,
    GlobalSearchServiceProtocol,
    NotificationServiceProtocol,
    MichiAIServiceProtocol,
)


def _all_protocols() -> list:
    return [
        JobServiceProtocol,
        ActionRegistryProtocol,
        ConfirmationServiceProtocol,
        NavigationProtocol,
        PlaybackServiceProtocol,
        QueueServiceProtocol,
        DeviceSyncServiceProtocol,
        AudioLabServiceProtocol,
        MixServiceProtocol,
        GlobalSearchServiceProtocol,
        NotificationServiceProtocol,
        MichiAIServiceProtocol,
    ]


class TestProtocolsExist:
    def test_all_defined(self):
        assert len(_all_protocols()) >= 12

    def test_each_is_protocol(self):
        for p in _all_protocols():
            assert isinstance(p, type)

    def test_job_service_has_submit(self):
        assert hasattr(JobServiceProtocol, "submit")

    def test_job_service_has_cancel(self):
        assert hasattr(JobServiceProtocol, "cancel")

    def test_job_service_has_status(self):
        assert hasattr(JobServiceProtocol, "status")

    def test_action_registry_has_register(self):
        assert hasattr(ActionRegistryProtocol, "register")

    def test_confirmation_service_has_request(self):
        assert hasattr(ConfirmationServiceProtocol, "request")

    def test_confirmation_service_has_approve(self):
        assert hasattr(ConfirmationServiceProtocol, "approve")

    def test_navigation_has_navigate(self):
        assert hasattr(NavigationProtocol, "navigate")

    def test_playback_has_play(self):
        assert hasattr(PlaybackServiceProtocol, "play")

    def test_queue_has_get_items(self):
        assert hasattr(QueueServiceProtocol, "get_items")

    def test_device_sync_has_discover(self):
        assert hasattr(DeviceSyncServiceProtocol, "discover")

    def test_audio_lab_has_setup(self):
        assert hasattr(AudioLabServiceProtocol, "setup")

    def test_mix_has_favorites(self):
        assert hasattr(MixServiceProtocol, "favorites")

    def test_global_search_has_search(self):
        assert hasattr(GlobalSearchServiceProtocol, "search")

    def test_notification_has_notify(self):
        assert hasattr(NotificationServiceProtocol, "notify")

    def test_michi_ai_has_process_message(self):
        assert hasattr(MichiAIServiceProtocol, "process_message")
