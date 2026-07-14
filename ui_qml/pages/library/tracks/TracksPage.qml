import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../theme"
import "../../../components"
import "../"

Item {
    id: root

    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null

    LibraryTrackTable {
        anchors.fill: parent
        trackModel: root.lib ? root.lib.trackModel : null
        bridge: root.lib
    }
}
