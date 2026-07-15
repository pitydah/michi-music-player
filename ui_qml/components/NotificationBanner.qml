import QtQuick
import "../theme"
import "../components"

Item {
    id: root

    property string kind: "info"
    property string title: ""
    property string message: ""
    property string actionText: ""
    property bool compact: false
    property bool dismissible: true
    property string objectName: "notificationBanner"

    signal actionClicked()
    signal dismissed()

    implicitHeight: compact ? 40 : column.implicitHeight + MichiTheme.spacing.lg * 2

    Accessible.role: Accessible.Alert
    Accessible.name: root.title
    Accessible.description: root.message

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radiusMd
        color: {
            switch (root.kind) {
                case "success": return Qt.rgba(0.29, 0.87, 0.50, 0.10)
                case "warning": return Qt.rgba(1.0, 0.75, 0.14, 0.10)
                case "error": return Qt.rgba(1.0, 0.44, 0.44, 0.10)
                default: return Qt.rgba(0.561, 0.718, 1.0, 0.08)
            }
        }
        border.width: MichiTheme.borderWidth
        border.color: {
            switch (root.kind) {
                case "success": return Qt.rgba(0.29, 0.87, 0.50, 0.25)
                case "warning": return Qt.rgba(1.0, 0.75, 0.14, 0.25)
                case "error": return Qt.rgba(1.0, 0.44, 0.44, 0.25)
                default: return Qt.rgba(0.561, 0.718, 1.0, 0.20)
            }
        }

        Row {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.sm

            Text {
                text: {
                    switch (root.kind) {
                        case "success": return "✓"
                        case "warning": return "!"
                        case "error": return "✕"
                        default: return "i"
                    }
                }
                color: {
                    switch (root.kind) {
                        case "success": return MichiTheme.colors.success
                        case "warning": return MichiTheme.colors.warning
                        case "error": return MichiTheme.colors.error
                        default: return MichiTheme.colors.accentBlue
                    }
                }
                font.pixelSize: MichiTheme.typography.cardTitleSize
                font.weight: MichiTheme.typography.weightBold
                anchors.verticalCenter: parent.verticalCenter
            }

            Column {
                id: column
                width: root.dismissible ? parent.width - dismissBtn.width - MichiTheme.spacing.sm * 2 : parent.width
                spacing: MichiTheme.spacing.xs
                anchors.verticalCenter: parent.verticalCenter

                Text {
                    text: root.title
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightMedium
                    visible: root.title !== "" && !root.compact
                    elide: Text.ElideRight
                    width: parent.width
                }

                Text {
                    text: root.message
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: root.compact ? MichiTheme.typography.captionSize : MichiTheme.typography.bodySize
                    wrapMode: Text.WordWrap
                    width: parent.width
                    elide: root.compact ? Text.ElideRight : Text.ElideNone
                    maximumLineCount: root.compact ? 1 : 3
                    visible: text !== ""
                }

                Text {
                    text: root.actionText
                    color: MichiTheme.colors.accentBlue
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: MichiTheme.typography.weightMedium
                    visible: root.actionText !== ""
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.actionClicked()
                    }
                    Accessible.role: Accessible.Button
                    Accessible.name: root.actionText
                }
            }

            Text {
                id: dismissBtn
                text: "✕"
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize
                anchors.verticalCenter: parent.verticalCenter
                visible: root.dismissible

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.dismissed()
                }

                Accessible.role: Accessible.Button
                Accessible.name: "Descartar"
            }
        }
    }
}
