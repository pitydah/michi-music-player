import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../library"

LibrarySectionPage {
    objectName: "mostPlayedPage"
    focus: true
    id: root
    sectionTitle: qsTr("Más reproducidas")
    sectionSubtitle: qsTr("Las canciones que más escuchas")
    sectionIcon: "songs"
    navigationIndex: 6

    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null

    function reload() {
        if (root.lib && root.lib.trackModel) {
            root.lib.trackModel.refreshForSort("play_count", false)
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
                    text: qsTr("Más reproducidos")
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
