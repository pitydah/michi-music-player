import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    id: root

    property string iconText: ""
    property string label: ""
    property bool active: false
    property bool sidebarHovered: false

    signal clicked()

    implicitHeight: 40
    implicitWidth: 200

    Rectangle {
        anchors.fill: parent
        anchors.leftMargin: MichiTheme.spacing.sm
        anchors.rightMargin: MichiTheme.spacing.sm
        radius: MichiTheme.radiusSm
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
            anchors.leftMargin: 16
            anchors.verticalCenter: parent.verticalCenter
            spacing: 12

            Rectangle {
                width: 28
                height: 28
                radius: MichiTheme.radiusXs
                color: root.active ? MichiTheme.colors.accentSurface : "transparent"
                anchors.verticalCenter: parent.verticalCenter
                visible: root.iconText !== ""

                Text {
                    anchors.centerIn: parent
                    text: root.iconText
                    color: root.active ? MichiTheme.colors.accentBlue : MichiTheme.colors.textMuted
                    font.pixelSize: 12
                    font.weight: MichiTheme.typography.weightSemiBold
                    font.letterSpacing: 1.2
                }
            }

            Text {
                text: root.label
                color: root.active ? MichiTheme.colors.textPrimary : MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: root.active ? MichiTheme.typography.weightMedium : MichiTheme.typography.weightNormal
                anchors.verticalCenter: parent.verticalCenter
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
