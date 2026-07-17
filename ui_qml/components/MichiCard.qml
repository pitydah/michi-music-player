import QtQuick
import "../theme"

Item {
    id: root

    property string controlObjectName: ""
    objectName: controlObjectName

    property bool hovered: false
    property bool interactive: true
    property bool elevated: false
    property string accessibleName: ""
    property string accessibleDescription: ""

    default property alias content: contentArea.children

    signal clicked()

    implicitWidth: 200
    implicitHeight: 120

    Accessible.role: root.interactive ? Accessible.Button : Accessible.Pane
    Accessible.name: root.accessibleName
    Accessible.description: root.accessibleDescription

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radius.md
        color: root.hovered ? MichiTheme.colors.surfaceCardHover : MichiTheme.colors.surfaceCard
        border.width: MichiTheme.borderWidth
        border.color: root.hovered ? MichiTheme.colors.borderHover : MichiTheme.colors.borderCard

        Behavior on color { ColorAnimation { duration: MichiTheme.motion.fast } }
        Behavior on border.color { ColorAnimation { duration: MichiTheme.motion.fast } }

        layer.enabled: root.elevated
        layer.effect: DropShadow {
            transparentBorder: true
            radius: 12
            samples: 24
            color: MichiTheme.colors.shadowSoft
            verticalOffset: 2
        }
    }

    Item {
        id: contentArea
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.lg
        clip: true
    }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: root.interactive
        enabled: root.interactive
        cursorShape: root.interactive ? Qt.PointingHandCursor : Qt.ArrowCursor
        onEntered: root.hovered = true
        onExited: root.hovered = false
        onClicked: root.clicked()
    }
}
