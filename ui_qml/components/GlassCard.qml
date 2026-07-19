import QtQuick
import QtQuick.Controls
import "../theme"
import "../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Glass Card"
    objectName: "glassCard"
    focus: true
    id: root

    property string title: ""
    property string subtitle: ""
    property string iconName: ""
    property string variant: "base"
    property bool hovered: false
    property bool interactive: true
    property alias cardRadius: glass.radius

    signal clicked()

    Keys.onReturnPressed: if (root.interactive) root.clicked()
    Keys.onSpacePressed: if (root.interactive) root.clicked()
    Accessible.onPressAction: if (root.interactive) root.clicked()

    GlassMaterial {
        id: glass
        anchors.fill: parent
        variant: root.variant
        hovered: root.hovered || root.activeFocus
        interactive: root.interactive
        radius: MichiTheme.radius.md

        MouseArea {
            id: pointerArea
            anchors.fill: parent
            enabled: root.interactive
            hoverEnabled: root.interactive
            cursorShape: root.interactive ? Qt.PointingHandCursor : Qt.ArrowCursor
            onEntered: root.hovered = true
            onExited: root.hovered = false
            onClicked: root.clicked()
        }

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.xs

            Text {
                text: root.title
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.cardTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                elide: Text.ElideRight
                width: parent.width
                visible: text !== ""
            }

            Text {
                text: root.subtitle
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                elide: Text.ElideRight
                width: parent.width
                visible: text !== ""
            }
        }

        Rectangle {
            anchors.fill: parent
            anchors.margins: 2
            radius: Math.max(0, glass.radius - 2)
            color: "transparent"
            border.width: root.activeFocus ? MichiTheme.focusWidth : 0
            border.color: MichiTheme.colors.borderFocus
            visible: root.activeFocus
        }
    }
}
