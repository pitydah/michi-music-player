import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    id: root

    property var bridge: null
    property var transferJobs: []
    property var transferHistory: []

    signal cancelTransfer(string jobId)
    signal retryTransfer(string jobId)
    signal clearHistory()

    implicitHeight: childrenRect.height

    objectName: "devices.transferPanel"

    GlassMaterial {
        width: parent.width
        height: column.height + MichiTheme.spacing.xl * 2
        radius: MichiTheme.radiusMd
        variant: "base"

        Column {
            id: column
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.md

            Text {
                text: "Transferencias activas"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                objectName: "devices.transferPanel.title"
                Accessible.role: Accessible.Heading
                Accessible.name: text
            }

            Repeater {
                id: activeRepeater
                model: root.transferJobs
                objectName: "devices.transferPanel.activeRepeater"

                Item {
                    width: parent.width
                    height: 72
                    objectName: "devices.transferPanel.job." + (modelData.job_id || index)

                    Rectangle {
                        anchors.fill: parent
                        color: MichiTheme.colors.surface
                        radius: MichiTheme.radiusSm
                        border.color: MichiTheme.colors.border
                        border.width: 1

                        Row {
                            anchors.fill: parent
                            anchors.margins: MichiTheme.spacing.md
                            spacing: MichiTheme.spacing.md

                            Column {
                                anchors.verticalCenter: parent.verticalCenter
                                width: parent.width - 200
                                spacing: MichiTheme.spacing.xs

                                Text {
                                    width: parent.width
                                    text: modelData.source_path ? bridge.fileName(modelData.source_path) : "Archivo"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                    font.weight: MichiTheme.typography.weightMedium
                                    elide: Text.ElideRight
                                }

                                Text {
                                    text: {
                                        var tb = modelData.total_bytes || 0
                                        var tfb = modelData.transferred_bytes || 0
                                        return formatBytes(tfb) + " / " + formatBytes(tb)
                                    }
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.metaSize
                                }

                                MichiProgressBar {
                                    width: parent.width
                                    height: 4
                                    value: modelData.total_bytes > 0 ? (modelData.transferred_bytes || 0) / modelData.total_bytes : 0
                                    accessibleName: "Progreso de transferencia"
                                    accessibleDescription: (modelData.transferred_bytes || 0) + " de " + (modelData.total_bytes || 0) + " bytes"
                                }
                            }

                            Row {
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: MichiTheme.spacing.xs

                                StatusBadge {
                                    text: {
                                        switch (modelData.status || "queued") {
                                            case "transferring": return "Transfiriendo"
                                            case "completed": return "Completado"
                                            case "failed": return "Falló"
                                            case "cancelled": return "Cancelado"
                                            default: return "En cola"
                                        }
                                    }
                                    kind: {
                                        switch (modelData.status || "queued") {
                                            case "transferring": return "info"
                                            case "completed": return "success"
                                            case "failed": return "error"
                                            case "cancelled": return "disconnected"
                                            default: return "active"
                                        }
                                    }
                                }

                                MichiButton {
                                    text: "Cancelar"
                                    variant: "ghost"
                                    visible: modelData.status === "queued" || modelData.status === "transferring"
                                    onClicked: root.cancelTransfer(modelData.job_id || "")
                                    objectName: "devices.transferPanel.cancelBtn." + (modelData.job_id || index)
                                    Accessible.name: "Cancelar transferencia " + (modelData.source_path || "")
                                    Accessible.description: "Detiene la transferencia en curso"
                                }

                                MichiButton {
                                    text: "Reintentar"
                                    variant: "ghost"
                                    visible: modelData.status === "failed" || modelData.status === "cancelled"
                                    onClicked: root.retryTransfer(modelData.job_id || "")
                                    objectName: "devices.transferPanel.retryBtn." + (modelData.job_id || index)
                                    Accessible.name: "Reintentar transferencia " + (modelData.source_path || "")
                                    Accessible.description: "Vuelve a intentar la transferencia fallida"
                                }
                            }
                        }
                    }

                    Accessible.role: Accessible.ListItem
                    Accessible.name: (modelData.source_path ? bridge.fileName(modelData.source_path) : "Transferencia") + " - " + (modelData.status || "queued")
                }
            }

            Text {
                text: root.transferJobs.length === 0 ? "No hay transferencias activas." : ""
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize
                visible: root.transferJobs.length === 0
                objectName: "devices.transferPanel.noActive"
            }

            SectionHeader {
                text: "Historial de transferencias"
                width: parent.width
                objectName: "devices.transferPanel.historyHeader"
            }

            Repeater {
                id: historyRepeater
                model: root.transferHistory
                objectName: "devices.transferPanel.historyRepeater"

                Rectangle {
                    width: parent.width
                    height: 48
                    color: index % 2 === 0 ? MichiTheme.colors.surface : "transparent"
                    radius: MichiTheme.radiusSm
                    objectName: "devices.transferPanel.historyItem." + index

                    Row {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.md
                        spacing: MichiTheme.spacing.sm

                        Text {
                            width: parent.width - 180
                            text: modelData.source_path ? bridge.fileName(modelData.source_path) : (modelData.job_id || "")
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            font.weight: MichiTheme.typography.weightMedium
                            elide: Text.ElideRight
                        }

                        StatusBadge {
                            text: {
                                switch (modelData.status || "") {
                                    case "completed": return "Completado"
                                    case "failed": return "Falló"
                                    case "cancelled": return "Cancelado"
                                    default: return (modelData.status || "Desconocido")
                                }
                            }
                            kind: {
                                switch (modelData.status || "") {
                                    case "completed": return "success"
                                    case "failed": return "error"
                                    case "cancelled": return "disconnected"
                                    default: return "info"
                                }
                            }
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Text {
                            text: modelData.direction === "to_device" ? "→ Disp." : "← Disp."
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    Accessible.role: Accessible.ListItem
                    Accessible.name: (modelData.source_path ? bridge.fileName(modelData.source_path) : "Historial") + " - " + (modelData.status || "")
                }
            }

            Text {
                text: root.transferHistory.length === 0 ? "No hay historial de transferencias." : ""
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize
                visible: root.transferHistory.length === 0
                objectName: "devices.transferPanel.noHistory"
            }

            MichiButton {
                text: "Limpiar historial"
                variant: "ghost"
                visible: root.transferHistory.length > 0
                onClicked: root.clearHistory()
                objectName: "devices.transferPanel.clearHistoryBtn"
                Accessible.name: "Limpiar historial de transferencias"
                Accessible.description: "Elimina todo el historial de transferencias"
            }
        }
    }

    function formatBytes(bytes) {
        if (!bytes || bytes < 1024) return (bytes || 0) + " B"
        if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB"
        if (bytes < 1073741824) return (bytes / 1048576).toFixed(1) + " MB"
        return (bytes / 1073741824).toFixed(2) + " GB"
    }
}
