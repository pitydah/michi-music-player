import QtQuick
import QtQuick.Controls as QQC2
import "../theme"

Item {
    id: root

    property string message: ""
    property string kind: "info"
    property int duration: 4000
    property bool showIcon: true

    signal dismissed()

    Accessible.role: Accessible.AlertMessage
    Accessible.name: root.message

    implicitWidth: Math.min(400, parent ? parent.width * 0.8 : 400)
    implicitHeight: bg.height

    Rectangle {
        id: bg
        width: parent.width
        height: contentRow.height + MichiTheme.spacing.md * 2
        radius: MichiTheme.radius.md
        color: {
            if (root.kind === "success") return Qt.rgba(0.29, 0.87, 0.50, 0.15)
            if (root.kind === "error") return Qt.rgba(1, 0.44, 0.44, 0.15)
            if (root.kind === "warning") return Qt.rgba(1, 0.75, 0.14, 0.15)
            return Qt.rgba(0.561, 0.718, 1.0, 0.12)
        }
        border.width: 1
        border.color: {
            if (root.kind === "success") return Qt.rgba(0.29, 0.87, 0.50, 0.25)
            if (root.kind === "error") return Qt.rgba(1, 0.44, 0.44, 0.25)
            if (root.kind === "warning") return Qt.rgba(1, 0.75, 0.14, 0.25)
            return Qt.rgba(0.561, 0.718, 1.0, 0.20)
        }

        Row {
            id: contentRow
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: MichiTheme.spacing.md
            anchors.rightMargin: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.sm

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: {
                    if (!root.showIcon) return ""
                    if (root.kind === "success") return "✓"
                    if (root.kind === "error") return "✕"
                    if (root.kind === "warning") return "⚠"
                    return "i"
                }
                color: {
                    if (root.kind === "success") return MichiTheme.colors.success
                    if (root.kind === "error") return MichiTheme.colors.error
                    if (root.kind === "warning") return MichiTheme.colors.warning
                    return MichiTheme.colors.accentPrimary
                }
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: MichiTheme.typography.weightBold
                visible: root.showIcon
            }

            Text {
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width - closeBtn.width - (root.showIcon ? 24 : 0) - MichiTheme.spacing.sm * 3
                text: root.message
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
            }

            QQC2.Button {
                id: closeBtn
                anchors.verticalCenter: parent.verticalCenter
                text: qsTr("✕")
                flat: true
                font.pixelSize: 12
                implicitWidth: 24
                implicitHeight: 24
                onClicked: root.dismissed()
                Accessible.name: "Cerrar notificación"
            }
        }
    }
}
