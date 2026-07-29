"""Tests for the Home Audio QML meta-object contract."""

from ui_qml_bridge.home_audio_bridge import HomeAudioBridge


def test_home_audio_bridge_exposes_qml_signal_and_slot_names() -> None:
    bridge = HomeAudioBridge()
    meta_object = bridge.metaObject()
    method_names = {
        bytes(meta_object.method(index).name()).decode("utf-8")
        for index in range(meta_object.methodOffset(), meta_object.methodCount())
    }

    assert {
        "stateChanged",
        "operationFinished",
        "groupZones",
        "setZoneVolume",
    } <= method_names
