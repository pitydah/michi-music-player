pragma Singleton
import QtQuick

QtObject {
    property bool reduceMotion: false
    property string highContrast: "false"
    property real fontScaleFactor: 1.0
    property real fontScale: 1.0

    readonly property int motionDurationFast: reduceMotion ? 0 : 120
    readonly property int motionDurationNormal: reduceMotion ? 0 : 200

    readonly property color textPrimary: highContrast === "true" ? "#FFFFFF" : "#E0E0E0"
    readonly property color textMuted: highContrast === "true" ? "#CCCCCC" : "#808080"

    function updateFromBridge(bridge) {
        if (bridge) {
            reduceMotion = bridge.reduceMotion
            highContrast = String(bridge.highContrast)
            fontScaleFactor = bridge.fontScale === "large" ? 1.25 : bridge.fontScale === "small" ? 0.85 : 1.0
            fontScale = fontScaleFactor
        }
    }
}
