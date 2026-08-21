pragma Singleton
import QtQuick

QtObject {
    readonly property real subtleOpacity: 0.18
    readonly property real standardOpacity: 0.26
    readonly property real elevatedOpacity: 0.34
    readonly property real modalOpacity: 0.42
    readonly property int subtleBlur: 16
    readonly property int standardBlur: 24
    readonly property int elevatedBlur: 32
    readonly property int modalBlur: 40
    readonly property int shadowNearSpread: 2
    readonly property int shadowFarSpread: 7
    readonly property int shadowVerticalOffset: 4
}
