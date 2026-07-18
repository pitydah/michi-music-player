import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Device Transfer Queue"
    focus: true
    id: root

    property var transferJobs: []

    implicitHeight: childrenRect.height

    objectName: "DeviceTransferQueue"

    GlassMaterial {
        width: parent.width
        height: column.height + MichiTheme.spacing.xl * 2
        radius: MichiTheme.radius.md
        variant: "base"

        Column {
            id: column
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.sm

            Text {
                text: qsTr("Cola de transferencia")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Repeater {
                model: root.transferJobs

                DeviceTransferJob {
                    width: parent.width
                    jobId: modelData.job_id || ""
                    fileName: modelData.file_name || "Archivo"
                    progress: modelData.progress || 0
                    status: modelData.status || "queued"
                    totalBytes: modelData.total_bytes || 0
                    transferredBytes: modelData.transferred_bytes || 0
                }
            }

            Text {
                text: root.transferJobs.length === 0 ? "No hay transferencias activas." : ""
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize
                visible: root.transferJobs.length === 0
            }
        }
    }
}
