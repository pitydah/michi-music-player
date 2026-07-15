import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    id: root

    property string notificationId: ""
    property string kind: "info"
    property string title: ""
    property string message: ""
    property real timestamp: 0
    property bool persistent: false
    property int progress: -1
    property string jobId: ""
    property string action: ""
    property string objectName: "notificationItem"

    signal dismissRequested(string id)
    signal actionRequested(string id)
    signal retryRequested(string id)
    signal cancelRequested(string id)

    implicitHeight: 72
    Accessible.role: Accessible.ListItem
    Accessible.name: root.title !== "" ? root.title : root.message
    Accessible.description: root.message + ". " + root.kind

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radiusSm
        color: MichiTheme.colors.surfaceCard
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderCard

        Rectangle {
            width: 3
            height: parent.height
            radius: 1.5
            color: {
                switch (root.kind) {
                    case "success": return MichiTheme.colors.success
                    case "warning": return MichiTheme.colors.warning
                    case "error": return MichiTheme.colors.error
                    default: return MichiTheme.colors.accentBlue
                }
            }
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
        }

        Row {
            anchors.fill: parent
            anchors.leftMargin: MichiTheme.spacing.lg
            anchors.rightMargin: MichiTheme.spacing.sm
            anchors.topMargin: MichiTheme.spacing.sm
            anchors.bottomMargin: MichiTheme.spacing.sm
            spacing: MichiTheme.spacing.md

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
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width - 80
                spacing: MichiTheme.spacing.xs

                Text {
                    text: root.title
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightMedium
                    elide: Text.ElideRight
                    width: parent.width
                    visible: root.title !== ""
                }

                Text {
                    text: root.message
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    elide: Text.ElideRight
                    width: parent.width
                    maximumLineCount: 1
                    visible: root.message !== ""
                }

                Row {
                    spacing: MichiTheme.spacing.sm
                    width: parent.width
                    visible: root.progress >= 0

                    MichiProgressBar {
                        width: parent.width * 0.6
                        value: root.progress
                        indeterminate: root.progress === 0
                    }

                    Text {
                        text: root.progress + "%"
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.captionSize
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }

                Row {
                    spacing: MichiTheme.spacing.sm
                    visible: root.action !== "" || root.persistent

                    MichiButton {
                        text: root.action === "retry" ? "Reintentar" : root.action === "cancelJob" ? "Cancelar" : root.action === "openJob" ? "Abrir" : "Ver"
                        variant: "ghost"
                        visible: root.action !== ""
                        onClicked: root.actionRequested(root.notificationId)
                    }

                    MichiButton {
                        text: "Descartar"
                        variant: "ghost"
                        onClicked: root.dismissRequested(root.notificationId)
                    }
                }
            }

            Text {
                text: formatTime(root.timestamp)
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: parent.right
                anchors.rightMargin: MichiTheme.spacing.sm

                function formatTime(ts) {
                    if (!ts) return ""
                    var d = new Date(ts * 1000)
                    var h = d.getHours().toString().padStart(2, "0")
                    var m = d.getMinutes().toString().padStart(2, "0")
                    return h + ":" + m
                }
            }
        }
    }

    Keys.onReturnPressed: {
        root.actionRequested(root.notificationId)
    }
}
