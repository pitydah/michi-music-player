pragma Singleton
import QtQuick

QtObject {
    readonly property int compact: 800
    readonly property int comfortable: 1100
    readonly property int wide: 1440
    function isCompact(width) { return width < comfortable }
    function isWide(width) { return width >= wide }
}
