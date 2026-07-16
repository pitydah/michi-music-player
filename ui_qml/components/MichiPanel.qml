import QtQuick
import "../theme"

Item {
    id: root

    objectName: "michiPanel"

    property string accessibleName: ""
    property string accessibleDescription: ""

    default property alias content: contentArea.children

    implicitWidth: 200
    implicitHeight: 120

    Accessible.role: Accessible.Pane
    Accessible.name: root.accessibleName
    Accessible.description: root.accessibleDescription

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radius.md
        color: MichiTheme.colors.surfaceCard
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderCard
    }

    Item {
        id: contentArea
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.lg
        clip: true
    }
}
