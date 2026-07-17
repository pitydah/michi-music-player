import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Chat Bubble"
    objectName: "chatBubble"
    focus: true
    id: root

    property string messageText: ""
    property string role: "assistant"
    property bool hovered: false

    implicitHeight: bubbleColumn.height + MichiTheme.spacing.md * 2
    width: parent ? parent.width : 400

    GlassMaterial {
        radius: MichiTheme.radius.md
        variant: root.role === "user" ? "accent" : "base"
        hovered: root.hovered

        Column {
            id: bubbleColumn
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.xs

            Text {
                text: root.role === "user" ? "Tú" : "Michi AI"
                color: root.role === "user" ? MichiTheme.colors.accentBlue : MichiTheme.colors.experimental
                font.pixelSize: MichiTheme.typography.metaSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: root.messageText
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
                width: parent.width
                lineHeight: 1.4
            }
        }

        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            onEntered: root.hovered = true
            onExited: root.hovered = false
        }
    }
}
