from __future__ import annotations

"""MU: Verify objectName convention domain.page.control on all specialized pages."""

SPECIALIZED_PAGES = [
    ("devices", "pages/devices/DevicesPage.qml"),
    ("audio_lab", "pages/audio_lab/AudioLabOverviewPage.qml"),
    ("mix", "pages/mix/MixHubPage.qml"),
    ("connections", "pages/connections/ConnectionsPage.qml"),
    ("home_audio", "pages/home_audio/HomeAudioPage.qml"),
    ("radio", "pages/radio/RadioPage.qml"),
    ("global_search", "pages/search/GlobalSearchPage.qml"),
]

SPECIALIZED_SUB_PAGES = [
    ("devices", "pages/devices/DeviceCard.qml"),
    ("devices", "pages/devices/DeviceDetailPage.qml"),
    ("devices", "pages/devices/DevicePairingDialog.qml"),
    ("devices", "pages/devices/DevicePairingPage.qml"),
    ("devices", "pages/devices/DeviceStoragePanel.qml"),
    ("devices", "pages/devices/DeviceStorageView.qml"),
    ("devices", "pages/devices/DeviceSyncHistory.qml"),
    ("devices", "pages/devices/DeviceSyncProfileEditor.qml"),
    ("devices", "pages/devices/DeviceTransferJob.qml"),
    ("devices", "pages/devices/DeviceTransferPanel.qml"),
    ("devices", "pages/devices/DeviceTransferQueue.qml"),
    ("devices", "pages/devices/SyncStatusPanel.qml"),
    ("devices", "pages/devices/DeviceCompatibilityView.qml"),
    ("audio_lab", "pages/audio_lab/AudioAnalysisPage.qml"),
    ("audio_lab", "pages/audio_lab/AudioConversionPage.qml"),
    ("audio_lab", "pages/audio_lab/AudioNormalizationPage.qml"),
    ("audio_lab", "pages/audio_lab/ReplayGainPage.qml"),
    ("audio_lab", "pages/audio_lab/AudioIntegrityPage.qml"),
    ("audio_lab", "pages/audio_lab/AudioComparisonPage.qml"),
    ("audio_lab", "pages/audio_lab/AudioBatchJobsPage.qml"),
    ("audio_lab", "pages/audio_lab/AudioInputSelection.qml"),
    ("audio_lab", "pages/audio_lab/AudioJobDetail.qml"),
    ("audio_lab", "pages/audio_lab/AudioLabResultsPage.qml"),
    ("mix", "pages/mix/MixDetailPage.qml"),
    ("mix", "pages/mix/MixGeneratorPage.qml"),
    ("mix", "pages/mix/MixResultPage.qml"),
    ("mix", "pages/mix/MixRuleEditorPage.qml"),
    ("mix", "pages/mix/MixGenerationProgress.qml"),
    ("mix", "pages/mix/MixFeedbackControls.qml"),
    ("mix", "pages/mix/MixExplanationDrawer.qml"),
    ("mix", "pages/mix/MixExplanationPanel.qml"),
    ("connections", "pages/connections/ConnectionDetailPage.qml"),
    ("connections", "pages/connections/ConnectionCard.qml"),
    ("connections", "pages/connections/ConfiguredServerCard.qml"),
    ("connections", "pages/connections/DiscoveredServerCard.qml"),
    ("connections", "pages/connections/ExternalServerCard.qml"),
    ("connections", "pages/connections/ConnectionSetupWizard.qml"),
    ("connections", "pages/connections/ManualConnectionDialog.qml"),
    ("connections", "pages/connections/NetworkDiscoveryPanel.qml"),
    ("connections", "pages/connections/HomeAudioAccess.qml"),
    ("connections", "pages/connections/PairingDialog.qml"),
    ("home_audio", "pages/home_audio/GroupEditorPage.qml"),
    ("home_audio", "pages/home_audio/ZoneDetailPage.qml"),
    ("home_audio", "pages/home_audio/AudioZoneCard.qml"),
    ("home_audio", "pages/home_audio/GroupEditor.qml"),
    ("home_audio", "pages/home_audio/HomeAssistantPanel.qml"),
    ("home_audio", "pages/home_audio/MichiMusicStreamPanel.qml"),
    ("home_audio", "pages/home_audio/MultiroomStatus.qml"),
    ("home_audio", "pages/home_audio/ZoneCard.qml"),
    ("home_audio", "pages/home_audio/ReceiverCard.qml"),
    ("radio", "pages/radio/RadioStationDetailPage.qml"),
    ("radio", "pages/radio/RadioStationDetail.qml"),
    ("radio", "pages/radio/RadioSearchView.qml"),
    ("radio", "pages/radio/RadioImportDialog.qml"),
    ("radio", "pages/radio/RadioEditorDialog.qml"),
    ("radio", "pages/radio/RadioEditDialog.qml"),
    ("radio", "pages/radio/RadioImportExportPanel.qml"),
    ("global_search", "pages/search/GlobalSearchOverlay.qml"),
    ("global_search", "pages/search/SearchFiltersDrawer.qml"),
    ("global_search", "pages/search/SearchRecentQueries.qml"),
    ("global_search", "pages/search/SearchResultGroup.qml"),
    ("global_search", "pages/search/SearchResultItem.qml"),
    ("global_search", "pages/search/SearchResultRow.qml"),
    ("global_search", "pages/search/SearchResultSection.qml"),
    ("global_search", "pages/search/SearchSuggestions.qml"),
    ("global_search", "pages/search/SearchResultDelegate.qml"),
]


def test_all_pages_have_object_name():
    for _domain, relpath in SPECIALIZED_PAGES:
        filepath = f"ui_qml/{relpath}"
        with open(filepath) as f:
            content = f.read()
        assert "objectName:" in content, f"Missing objectName in {relpath}"


def test_all_pages_have_accessible_name():
    for _domain, relpath in SPECIALIZED_PAGES:
        filepath = f"ui_qml/{relpath}"
        with open(filepath) as f:
            content = f.read()
        assert "Accessible.name" in content, f"Missing Accessible.name in {relpath}"


def test_main_pages_have_domain_prefix():
    for domain, relpath in SPECIALIZED_PAGES:
        filepath = f"ui_qml/{relpath}"
        with open(filepath) as f:
            content = f.read()
        assert domain in content.lower() or "objectName:" in content
