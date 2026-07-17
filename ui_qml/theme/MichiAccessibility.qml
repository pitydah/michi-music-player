pragma Singleton
import QtQuick

QtObject {
    property bool reduceMotion: false
    property real fontScale: 1.0
    property bool highContrast: false

    readonly property int animationDuration: reduceMotion ? 0 : 200
    readonly property int animationFast: reduceMotion ? 0 : 120
    readonly property int animationSlow: reduceMotion ? 0 : 300
}
