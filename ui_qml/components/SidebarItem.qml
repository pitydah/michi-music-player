import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    Accessible.role: Accessible.Button
    Accessible.name: root.text || root.label || "Sidebar Item"
    objectName: "sidebarItem"
    activeFocusOnTab: true
    focus: true
    id: root

    property string iconSource: ""
    property string label: ""
    property string text: ""
    property string route: ""
    property string currentRoute: ""
    property bool active: route !== "" && currentRoute === route
    property bool sidebarHovered: false
    property bool collapsed: false

    signal clicked()

    Keys.onReturnPressed: root.clicked()
    Keys.onSpacePressed: root.clicked()

    implicitHeight: 40
    implicitWidth: 200

    Rectangle {
        anchors.fill: parent
        anchors.leftMargin: root.collapsed ? 6 : MichiTheme.spacing.sm
        anchors.rightMargin: root.collapsed ? 6 : MichiTheme.spacing.sm
        radius: MichiTheme.radius.sm
        color: {
            if (root.active) return MichiTheme.colors.accentSelection
            if (root.sidebarHovered) return MichiTheme.colors.surfaceSubtle
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
            radius: MichiTheme.radius.xs
            color: MichiTheme.colors.accentBlue
        }

        Row {
            anchors.left: parent.left
            anchors.leftMargin: root.collapsed ? Math.round((parent.width - 20) / 2) : MichiTheme.spacing.md
            anchors.verticalCenter: parent.verticalCenter
            spacing: MichiTheme.spacing.md

            Item {
                width: 20
                height: 20
                anchors.verticalCenter: parent.verticalCenter
                visible: root.iconSource !== ""

                Image {
                    id: navIcon
                    objectName: "sidebarIcon_" + root.route
                    property int loadStatus: status
                    anchors.centerIn: parent
                    width: 20
                    height: 20
                    source: root.iconSource
                    sourceSize.width: 20
                    sourceSize.height: 20
                    fillMode: Image.PreserveAspectFit
                    opacity: root.active ? 1.0 : 0.82
                }
            }

            Text {
                text: root.text || root.label
                color: root.active ? MichiTheme.colors.textPrimary : MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: root.active ? MichiTheme.typography.weightMedium : MichiTheme.typography.weightNormal
                anchors.verticalCenter: parent.verticalCenter
                visible: !root.collapsed
                width: Math.max(0, parent.parent.width - 56)
                elide: Text.ElideRight
            }
        }

        ToolTip {
            visible: root.collapsed && ma.containsMouse
            text: root.text || root.label
            delay: 600
        }

        MouseArea {
            id: ma
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onEntered: root.sidebarHovered = true
            onExited: root.sidebarHovered = false
            onClicked: root.clicked()
        }
    }
}
