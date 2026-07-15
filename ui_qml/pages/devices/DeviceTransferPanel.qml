import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    id: root

    property string deviceKey: ""
    property var bridge: null
    property var transferJobs: []
    property var dv: typeof devicesBridge !== "undefined" ? devicesBridge : null

    signal startTransferClicked()
    signal cancelTransferClicked()
    signal retryTransferClicked(string jobId)

    implicitHeight: childrenRect.height

    objectName: "DeviceTransferPanel"
    Accessible.role: Accessible.Pane
    Accessible.name: "Panel de transferencia"
    objectName: "devices.transferPanel"
    property string deviceKey: ""
    property var transferJobs: []
    property var dv: typeof devicesBridge !== "undefined" ? devicesBridge : null

    signal startTransferClicked()
    signal cancelTransferClicked()
    signal retryTransferClicked(string jobId)

    implicitHeight: childrenRect.height

    objectName: "DeviceTransferPanel"
    Accessible.role: Accessible.Pane
    Accessible.name: "Panel de transferencia"

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
            spacing: MichiTheme.spacing.md

            Text {
                text: "Transferencias"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                Accessible.name: "Transferencias"
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
                    objectName: "transferJob_" + index
                    Accessible.name: "Transferencia: " + (modelData.file_name || modelData.name || "Archivo")

                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.xs
            spacing: MichiTheme.spacing.sm

            Text {
                text: "Transferencias"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                Accessible.name: "Transferencias"
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
                    objectName: "transferJob_" + index
                    Accessible.name: "Transferencia: " + (modelData.file_name || modelData.name || "Archivo")

                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.xs
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
                                    text: modelData.file_name || modelData.name || "Archivo"
                                    width: parent.width
                                    text: modelData.source_path ? bridge.fileName(modelData.source_path) : "Archivo"
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
                                }

                                Text {
                                    text: {
                                        var tb = modelData.total_bytes || 0
                                        var tfb = modelData.transferred_bytes || 0
                                        return formatBytes(tfb) + " / " + formatBytes(tb)
                                    }
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
                                    value: modelData.total_bytes > 0 ? (modelData.transferred_bytes || 0) / modelData.total_bytes : 0
                                    accessibleName: "Progreso de transferencia"
                                    accessibleDescription: (modelData.transferred_bytes || 0) + " de " + (modelData.total_bytes || 0) + " bytes"
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
                                        switch (modelData.status || "queued") {
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
                                        switch (modelData.status || "queued") {
                                        var s = modelData.status || modelData.state || "queued"
                                        switch (s) {
                                            case "transferring": return "info"
                                            case "completed": return "success"
                                            case "failed": return "error"
                                            case "cancelled": return "disconnected"
                                            default: return "active"
                                        }
                                    }
                                    objectName: "transferJobStatus_" + index
                                    Accessible.name: text
                                    objectName: "transferJobStatus_" + index
                                    Accessible.name: text
                                }

                                MichiButton {
                                    text: "Cancelar"
                                    variant: "ghost"
                                    visible: modelData.status === "queued" || modelData.status === "transferring"
                                    onClicked: root.cancelTransfer(modelData.job_id || "")
                                    objectName: "devices.transferPanel.cancelBtn." + (modelData.job_id || index)
                                    Accessible.name: "Cancelar transferencia " + (modelData.source_path || "")
                                    Accessible.description: "Detiene la transferencia en curso"
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
                                    objectName: "cancelTransferButton_" + index
                                    Accessible.name: "Cancelar transferencia"
                                }

                                MichiButton {
                                    text: "Reintentar"
                                    variant: "ghost"
                                    visible: modelData.status === "failed" || modelData.status === "cancelled"
                                    onClicked: root.retryTransfer(modelData.job_id || "")
                                    objectName: "devices.transferPanel.retryBtn." + (modelData.job_id || index)
                                    Accessible.name: "Reintentar transferencia " + (modelData.source_path || "")
                                    Accessible.description: "Vuelve a intentar la transferencia fallida"
                                    visible: {
                                        var s = modelData.status || modelData.state || ""
                                        return s === "failed" || s === "cancelled"
                                    }
                                    onClicked: {
                                        root.retryTransferClicked(modelData.job_id || "")
                                    }
                                    objectName: "retryTransferButton_" + index
                                    Accessible.name: "Reintentar transferencia"
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
                Accessible.name: "No hay transferencias activas"
                objectName: "devices.transferPanel.noActive"
            }

            Row {
                spacing: MichiTheme.spacing.sm
                visible: root.deviceKey !== ""

                MichiButton {
                    text: "Iniciar transferencia"
                    variant: "primary"
                    onClicked: root.startTransferClicked()
                    objectName: "startTransferButton"
                    Accessible.name: "Iniciar nueva transferencia"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
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
                Accessible.name: "No hay transferencias activas"
            }

            Row {
                spacing: MichiTheme.spacing.sm
                visible: root.deviceKey !== ""

                MichiButton {
                    text: "Iniciar transferencia"
                    variant: "primary"
                    onClicked: root.startTransferClicked()
                    objectName: "startTransferButton"
                    Accessible.name: "Iniciar nueva transferencia"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                }

                MichiButton {
                    text: "Cancelar todo"
                    variant: "ghost"
                    visible: root.transferJobs.length > 0
                    onClicked: root.cancelTransferClicked()
                    objectName: "cancelAllTransfersButton"
                    Accessible.name: "Cancelar todas las transferencias"
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
        if (!bytes || bytes < 1024) return (bytes || 0) + " B"
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
