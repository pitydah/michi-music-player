import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Search Recent Queries"
    objectName: "searchRecentQueries"
    focus: true
    id: root

    property var recentQueries: []
    property var bridge: null

    signal queryClicked(string text)
    signal clearRecent()

    implicitHeight: childrenRect.height

    Column {
        width: parent.width; spacing: MichiTheme.spacing.sm

        Row {
            width: parent.width
            SectionHeader { text: "Búsquedas recientes"; width: parent.width - 80 }
            MichiButton { text: "Limpiar"; variant: "ghost"; onClicked: root.clearRecent() }
        }

        Repeater {
            model: root.recentQueries

            Rectangle {
                width: parent.width; height: 32; color: "transparent"; radius: MichiTheme.radius.sm
                Text {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm
                    text: modelData; color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize; verticalAlignment: Text.AlignVCenter
                }
                MouseArea {
                    anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                    onClicked: root.queryClicked(modelData)
                }
            }
        }
    }
}
