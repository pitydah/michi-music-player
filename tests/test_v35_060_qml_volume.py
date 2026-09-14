"""DAC-V35-060 static QML ownership gates."""

from __future__ import annotations

from pathlib import Path

QML = Path("src/michi/presentation/qml")


def test_v60_21_settings_has_no_duplicate_generic_volume_commands() -> None:
    settings = (QML / "views" / "SettingsView.qml").read_text(encoding="utf-8")

    assert "playback.set_volume" not in settings
    assert "playback.set_muted" not in settings


def test_v60_22_player_uses_authority_aware_dac_volume_control() -> None:
    player = (QML / "player" / "NowPlayingBar.qml").read_text(encoding="utf-8")

    assert "DacVolumeControl" in player
    assert "volumeAdjustable: root.volumeAdjustable" in player
    assert "volumeModeLabel: root.volumeModeLabel" in player


def test_v60_23_dac_volume_control_disables_only_gain_not_mute() -> None:
    control = (QML / "components" / "DacVolumeControl.qml").read_text(encoding="utf-8")

    assert "enabled: root.volumeAdjustable" in control
    assert "onClicked: root.muteToggleRequested" in control
    assert "text: root.volumeAdjustable" in control
    assert 'qsTr("Fixed / Unity")' in control


def test_v60_24_app_shell_binds_canonical_output_policy_projection() -> None:
    shell = (QML / "shell" / "AppShell.qml").read_text(encoding="utf-8")

    assert "volumeAdjustable: audioOutput.volumeAdjustable" in shell
    assert "volumeModeLabel: audioOutput.volumeLabel" in shell
