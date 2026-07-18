import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../library"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Recent"
    objectName: "recentPage"
    focus: true
    id: root

    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null

    function reload() {
        if (root.lib && root.lib.trackModel) {
            root.lib.trackModel.refreshForSort("date_added", false)
        }
    }

    Component.onCompleted: reload()

    ColumnLayout {
        anchors.fill: parent; spacing: 0

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 40
            color: MichiTheme.colors.surfaceCard

            RowLayout {
                anchors.fill: parent; anchors.leftMargin: MichiTheme.spacing.md

                Text {
                    text: qsTr("Añadidos recientemente")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }
                Item { Layout.fillWidth: true }
                MichiButton { text: qsTr("Refrescar"); variant: "ghost"; onClicked: root.reload() }
            }
        }

        LibraryTrackTable {
            Layout.fillWidth: true; Layout.fillHeight: true
            trackModel: root.lib ? root.lib.trackModel : null
            bridge: root.lib
        }
    }
}
