import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Breadcrumbs"
    objectName: "breadcrumbs"
    focus: true
    id: root

    property var routeHistory: []
    property color textColor: MichiTheme.colors.textMuted
    property color activeColor: MichiTheme.colors.textPrimary
    property color separatorColor: MichiTheme.colors.textMeta

    signal breadcrumbClicked(string route)

    implicitHeight: 24

    Row {
        anchors.fill: parent
        spacing: MichiTheme.spacing.xs
        clip: true

        Repeater {
            model: root.routeHistory

            delegate: Row {
                spacing: MichiTheme.spacing.xs

                Text {
                    text: index < root.routeHistory.length - 1 ? modelData + " /" : modelData
                    color: index < root.routeHistory.length - 1 ? root.textColor : root.activeColor
                    font.pixelSize: MichiTheme.typography.captionSize
                    font.weight: index < root.routeHistory.length - 1 ? MichiTheme.typography.weightNormal : MichiTheme.typography.weightMedium
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    enabled: index < root.routeHistory.length - 1
                    onClicked: root.breadcrumbClicked(modelData)
                }
            }
        }
    }
}
