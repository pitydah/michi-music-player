import QtQuick
import "../theme"

Rectangle {
    id: root

    property string message: ""
    property string kind: "info"
    property bool dismissible: true
    property string actionText: ""
    property bool busy: false

    signal dismissed()
    signal actionClicked()

    Accessible.role: Accessible.AlertMessage
    Accessible.name: root.message

    implicitHeight: contentRow.height + MichiTheme.spacing.md * 2
    radius: MichiTheme.radius.md
    visible: root.message !== ""

    color: {
        if (root.kind === "success") return Qt.rgba(0.29, 0.87, 0.50, 0.12)
        if (root.kind === "error") return Qt.rgba(1, 0.44, 0.44, 0.12)
        if (root.kind === "warning") return Qt.rgba(1, 0.75, 0.14, 0.12)
        return Qt.rgba(0.561, 0.718, 1.0, 0.10)
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
                if (!root.busy) return ""
                if (root.kind === "success") return "✓"
                if (root.kind === "error") return "✕"
                return "i"
            }
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: MichiTheme.typography.weightBold
            visible: root.busy
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - (root.actionText !== "" ? actionBtn.width + MichiTheme.spacing.sm : 0) - (root.dismissible ? 28 : 0) - MichiTheme.spacing.sm * 2
            text: root.message
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
            wrapMode: Text.WordWrap
        }

        MichiButton {
            id: actionBtn
            anchors.verticalCenter: parent.verticalCenter
            text: root.actionText
            variant: "ghost"
            visible: root.actionText !== ""
            onClicked: root.actionClicked()
        }

        MouseArea {
            anchors.verticalCenter: parent.verticalCenter
            width: 24
            height: 24
            visible: root.dismissible
            onClicked: root.dismissed()

            Text {
                anchors.centerIn: parent
                text: "✕"
                color: MichiTheme.colors.textSecondary
                font.pixelSize: 12
            }
        }
    }
}
