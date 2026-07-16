import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Device Transfer"
    objectName: "deviceTransferPanel"
    focus: true
    id: root

    property string deviceKey: ""
    property var transferJobs: []
    property var dv: typeof devicesBridge !== "undefined" ? devicesBridge : null

    signal startTransferClicked()
    signal cancelTransferClicked()
    signal retryTransferClicked(string jobId)

    implicitHeight: childrenRect.height


    GlassMaterial {
        width: parent.width
        height: column.height + MichiTheme.spacing.xl * 2
        radius: MichiTheme.radiusMd
        variant: "base"

        Column {
            id: column
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.sm

            Text {
                text: "Transferencias"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: "Estado: " + (root.dv ? (root.dv.transferActive ? "Activo" : "Inactivo") : "No disponible")
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.metaSize
                visible: root.deviceKey !== ""
            }

            Repeater {
                model: root.transferJobs

                Item {
                    id: jobItem
                    width: parent.width
                    implicitHeight: 80

                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.xs
                        color: MichiTheme.colors.surface
                        radius: MichiTheme.radiusSm
                        border.color: MichiTheme.colors.border
                        border.width: MichiTheme.borderWidth

                        Row {
                            anchors.fill: parent
                            anchors.margins: MichiTheme.spacing.md
                            spacing: MichiTheme.spacing.md

                            Column {
                                anchors.verticalCenter: parent.verticalCenter
                                width: parent.width - 200
                                spacing: MichiTheme.spacing.xs

                                Text {
                                    text: modelData.file_name || modelData.name || "Archivo"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                    font.weight: MichiTheme.typography.weightMedium
                                    elide: Text.ElideRight
                                    width: parent.width
                                }

                                Text {
                                    text: formatBytes(modelData.transferred_bytes || modelData.transferredBytes || 0)
                                          + " / " + formatBytes(modelData.total_bytes || modelData.totalBytes || 0)
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.metaSize
                                }

                                MichiProgressBar {
                                    width: parent.width
                                    height: 4
                                    value: (modelData.total_bytes || modelData.totalBytes || 1) > 0
                                           ? (modelData.transferred_bytes || modelData.transferredBytes || 0)
                                             / (modelData.total_bytes || modelData.totalBytes || 1)
                                           : 0
                                    accessibleName: "Progreso de transferencia"
                                }

                                Text {
                                    text: formatEstimate(modelData.estimated_seconds || modelData.estimatedSeconds || 0)
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                    visible: (modelData.estimated_seconds || modelData.estimatedSeconds || 0) > 0
                                }
                            }

                            Row {
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: MichiTheme.spacing.xs

                                StatusBadge {
                                    text: {
                                        var s = modelData.status || modelData.state || "queued"
                                        switch (s) {
                                            case "transferring": return "Transfiriendo"
                                            case "completed": return "Completado"
                                            case "failed": return "Falló"
                                            case "cancelled": return "Cancelado"
                                            default: return "En cola"
                                        }
                                    }
                                    kind: {
                                        var s = modelData.status || modelData.state || "queued"
                                        switch (s) {
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
                                    visible: {
                                        var s = modelData.status || modelData.state || ""
                                        return s === "queued" || s === "transferring"
                                    }
                                    onClicked: {
                                        if (root.dv && typeof root.dv.cancelTransfer === "function") {
                                            root.dv.cancelTransfer(modelData.job_id || "")
                                        }
                                        root.cancelTransferClicked()
                                    }
                                }

                                MichiButton {
                                    text: "Reintentar"
                                    variant: "ghost"
                                    visible: {
                                        var s = modelData.status || modelData.state || ""
                                        return s === "failed" || s === "cancelled"
                                    }
                                    onClicked: {
                                        root.retryTransferClicked(modelData.job_id || "")
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Text {
                text: root.transferJobs.length === 0 ? "No hay transferencias activas." : ""
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize
                visible: root.transferJobs.length === 0
            }

            Row {
                spacing: MichiTheme.spacing.sm
                visible: root.deviceKey !== ""

                MichiButton {
                    text: "Iniciar transferencia"
                    variant: "primary"
                    onClicked: root.startTransferClicked()
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                }

                MichiButton {
                    text: "Cancelar todo"
                    variant: "ghost"
                    visible: root.transferJobs.length > 0
                    onClicked: root.cancelTransferClicked()
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                }
            }
        }
    }

    function formatBytes(bytes) {
        if (!bytes || bytes < 1) return "0 B"
        if (bytes < 1024) return bytes + " B"
        if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB"
        if (bytes < 1073741824) return (bytes / 1048576).toFixed(1) + " MB"
        return (bytes / 1073741824).toFixed(2) + " GB"
    }

    function formatEstimate(seconds) {
        if (seconds <= 0) return ""
        if (seconds < 60) return Math.ceil(seconds) + "s restantes"
        if (seconds < 3600) return Math.ceil(seconds / 60) + "min restantes"
        return (seconds / 3600).toFixed(1) + "h restantes"
    }
}
