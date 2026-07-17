import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Sidebar Item"
    objectName: "sidebarItem"
    focus: true
    id: root

    property string iconSource: ""
    property string label: ""
    property bool active: false
    property bool sidebarHovered: false
    property bool collapsed: false

    signal clicked()

    implicitHeight: 40
    implicitWidth: 200

    Rectangle {
        anchors.fill: parent
        anchors.leftMargin: MichiTheme.spacing.sm
        anchors.rightMargin: MichiTheme.spacing.sm
        radius: MichiTheme.radius.sm
        color: {
            if (root.active) return MichiTheme.colors.accentSelection
            if (root.sidebarHovered) return Qt.rgba(1.0, 1.0, 1.0, 0.04)
            return "transparent"
        }

        Behavior on color {
            ColorAnimation { duration: MichiTheme.motion.fast; easing.type: MichiTheme.motion.easing.standard }
        }

        Rectangle {
            visible: root.active
            width: 3
            height: 20
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            radius: 2
            color: MichiTheme.colors.accentBlue
        }

        Row {
            anchors.left: parent.left
            anchors.leftMargin: MichiTheme.spacing.lg
            anchors.verticalCenter: parent.verticalCenter
            spacing: 12

            Rectangle {
                width: 28
                height: 28
                radius: MichiTheme.radius.xs
                color: root.active ? MichiTheme.colors.accentSurface : "transparent"
                anchors.verticalCenter: parent.verticalCenter
                visible: root.iconSource !== ""

                Image {
                    anchors.centerIn: parent
                    width: 18
                    height: 18
                    source: root.iconSource
                    sourceSize.width: 18
                    sourceSize.height: 18
                    fillMode: Image.PreserveAspectFit
                }
            }

            Text {
                text: root.label
                color: root.active ? MichiTheme.colors.textPrimary : MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: root.active ? MichiTheme.typography.weightMedium : MichiTheme.typography.weightNormal
                anchors.verticalCenter: parent.verticalCenter
                visible: !root.collapsed
            }
        }

        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onEntered: root.sidebarHovered = true
            onExited: root.sidebarHovered = false
            onClicked: root.clicked()
        }
    }
}
