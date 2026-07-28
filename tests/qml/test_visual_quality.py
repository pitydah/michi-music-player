from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine


QML_DIR = Path(__file__).resolve().parents[2] / "ui_qml"


def test_visual_quality_singleton_defaults(qapp):
    engine = QQmlEngine(qapp)
    component = QQmlComponent(engine)
    source = b"""
        import QtQuick
        import "theme"

        QtObject {
            property string qualityProfile: MichiVisualQuality.profile
            property bool textureEnabled: MichiVisualQuality.textureEnabled
            property bool glowEnabled: MichiVisualQuality.glowEnabled
            property bool blurEnabled: MichiVisualQuality.blurEnabled
            property real animationScale: MichiVisualQuality.animationScale
            property string requestedProfile: ""

            onRequestedProfileChanged: MichiVisualQuality.setProfile(requestedProfile)
        }
    """
    component.setData(source, QUrl.fromLocalFile(str(QML_DIR / "VisualQualityTest.qml")))

    assert component.isReady(), [error.toString() for error in component.errors()]
    instance = component.create()
    assert instance is not None
    assert instance.property("qualityProfile") == "balanced"
    assert instance.property("textureEnabled") is True
    assert instance.property("glowEnabled") is False
    assert instance.property("blurEnabled") is False
    assert instance.property("animationScale") == 1.0

    instance.setProperty("requestedProfile", "low")
    assert instance.property("qualityProfile") == "low"
    assert instance.property("textureEnabled") is False
    assert instance.property("glowEnabled") is False
    assert instance.property("animationScale") == 0.5

    instance.setProperty("requestedProfile", "premium")
    assert instance.property("qualityProfile") == "premium"
    assert instance.property("textureEnabled") is True
    assert instance.property("glowEnabled") is True
    assert instance.property("animationScale") == 1.0

    instance.setProperty("requestedProfile", "unsupported")
    assert instance.property("qualityProfile") == "premium"
    instance.deleteLater()
    engine.deleteLater()
