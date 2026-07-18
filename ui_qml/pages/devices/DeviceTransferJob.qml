import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Device Transfer Job"
    objectName: "deviceTransferJob"
    focus: true
    id: root

    property string jobId: ""
    property string fileName: "Archivo"
    property real progress: 0.0
    property string status: "queued"
    property int totalBytes: 0
    property int transferredBytes: 0

    signal cancelClicked(string jobId)
    signal retryClicked(string jobId)

    implicitHeight: 70


    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.surface
        radius: MichiTheme.radius.sm
        border.color: MichiTheme.colors.border
        border.width: MichiTheme.borderWidth

        Row {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.md

            Column {
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width - 160
                spacing: MichiTheme.spacing.xs

                Text {
                    text: root.fileName
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: MichiTheme.typography.weightMedium
                    elide: Text.ElideRight
                    width: parent.width
                }

                Text {
                    text: formatBytes(root.transferredBytes) + " / " + formatBytes(root.totalBytes)
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                }

                MichiProgressBar {
                    Accessible.role: Accessible.ProgressBar
                    width: parent.width
                    height: 4
                    value: root.totalBytes > 0 ? root.transferredBytes / root.totalBytes : 0
                    accessibleName: "Progreso de " + root.fileName
                }
            }

            Row {
                anchors.verticalCenter: parent.verticalCenter
                spacing: MichiTheme.spacing.xs

                StatusBadge {
                    text: {
                        switch (root.status) {
                            case "transferring": return "Transfiriendo"
                            case "completed": return "Completado"
                            case "failed": return "Falló"
                            case "cancelled": return "Cancelado"
                            default: return "En cola"
                        }
                    }
                    kind: {
                        switch (root.status) {
                            case "transferring": return "info"
                            case "completed": return "success"
                            case "failed": return "error"
                            case "cancelled": return "disconnected"
                            default: return "active"
                        }
                    }
                }

                MichiButton {
                    text: qsTr("Cancelar")
                    variant: "ghost"
                    visible: root.status === "queued" || root.status === "transferring"
                    onClicked: root.cancelClicked(root.jobId)
                }

                MichiButton {
                    text: qsTr("Reintentar")
                    variant: "ghost"
                    visible: root.status === "failed" || root.status === "cancelled"
                    onClicked: root.retryClicked(root.jobId)
                }
            }
        }
    }

    function formatBytes(bytes) {
        if (bytes < 1024) return bytes + " B"
        if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB"
        if (bytes < 1073741824) return (bytes / 1048576).toFixed(1) + " MB"
        return (bytes / 1073741824).toFixed(2) + " GB"
    }
}
