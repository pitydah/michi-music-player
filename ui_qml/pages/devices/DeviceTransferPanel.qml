import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    id: root

<<<<<<< Updated upstream
<<<<<<< Updated upstream
    property string deviceKey: ""
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    property var bridge: null
>>>>>>> Stashed changes
    property var transferJobs: []
    property var dv: typeof devicesBridge !== "undefined" ? devicesBridge : null

    signal startTransferClicked()
    signal cancelTransferClicked()
    signal retryTransferClicked(string jobId)

    implicitHeight: childrenRect.height

<<<<<<< Updated upstream
    objectName: "DeviceTransferPanel"
    Accessible.role: Accessible.Pane
    Accessible.name: "Panel de transferencia"
=======
    objectName: "devices.transferPanel"
=======
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
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

    GlassMaterial {
        width: parent.width
        height: column.height + MichiTheme.spacing.xl * 2
        radius: MichiTheme.radiusMd
        variant: "base"

        Column {
            id: column
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
<<<<<<< Updated upstream
<<<<<<< Updated upstream
            spacing: MichiTheme.spacing.sm
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
            spacing: MichiTheme.spacing.md
>>>>>>> Stashed changes

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
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                        anchors.margins: MichiTheme.spacing.xs
=======
=======
>>>>>>> Stashed changes
=======
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
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                                    text: modelData.file_name || modelData.name || "Archivo"
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                                    width: parent.width
                                    text: modelData.source_path ? bridge.fileName(modelData.source_path) : "Archivo"
=======
                                    text: modelData.file_name || modelData.name || "Archivo"
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                    font.weight: MichiTheme.typography.weightMedium
                                    elide: Text.ElideRight
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                                    width: parent.width
                                }

                                Text {
                                    text: formatBytes(modelData.transferred_bytes || modelData.transferredBytes || 0)
                                          + " / " + formatBytes(modelData.total_bytes || modelData.totalBytes || 0)
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                                }

                                Text {
                                    text: {
                                        var tb = modelData.total_bytes || 0
                                        var tfb = modelData.transferred_bytes || 0
                                        return formatBytes(tfb) + " / " + formatBytes(tb)
                                    }
=======
                                    width: parent.width
                                }

                                Text {
                                    text: formatBytes(modelData.transferred_bytes || modelData.transferredBytes || 0)
                                          + " / " + formatBytes(modelData.total_bytes || modelData.totalBytes || 0)
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.metaSize
                                }

                                MichiProgressBar {
                                    width: parent.width
                                    height: 4
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                                    value: (modelData.total_bytes || modelData.totalBytes || 1) > 0
                                           ? (modelData.transferred_bytes || modelData.transferredBytes || 0)
                                             / (modelData.total_bytes || modelData.totalBytes || 1)
                                           : 0
                                    accessibleName: "Progreso de transferencia"
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                                    value: modelData.total_bytes > 0 ? (modelData.transferred_bytes || 0) / modelData.total_bytes : 0
                                    accessibleName: "Progreso de transferencia"
                                    accessibleDescription: (modelData.transferred_bytes || 0) + " de " + (modelData.total_bytes || 0) + " bytes"
=======
                                    value: (modelData.total_bytes || modelData.totalBytes || 1) > 0
                                           ? (modelData.transferred_bytes || modelData.transferredBytes || 0)
                                             / (modelData.total_bytes || modelData.totalBytes || 1)
                                           : 0
                                    accessibleName: "Progreso de transferencia"
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                                }

                                Text {
                                    text: formatEstimate(modelData.estimated_seconds || modelData.estimatedSeconds || 0)
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                    visible: (modelData.estimated_seconds || modelData.estimatedSeconds || 0) > 0
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
                                }
                            }

                            Row {
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: MichiTheme.spacing.xs

                                StatusBadge {
                                    text: {
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                                        var s = modelData.status || modelData.state || "queued"
                                        switch (s) {
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                                        switch (modelData.status || "queued") {
=======
                                        var s = modelData.status || modelData.state || "queued"
                                        switch (s) {
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                                            case "transferring": return "Transfiriendo"
                                            case "completed": return "Completado"
                                            case "failed": return "Falló"
                                            case "cancelled": return "Cancelado"
                                            default: return "En cola"
                                        }
                                    }
                                    kind: {
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                                        var s = modelData.status || modelData.state || "queued"
                                        switch (s) {
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                                        switch (modelData.status || "queued") {
=======
                                        var s = modelData.status || modelData.state || "queued"
                                        switch (s) {
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                                            case "transferring": return "info"
                                            case "completed": return "success"
                                            case "failed": return "error"
                                            case "cancelled": return "disconnected"
                                            default: return "active"
                                        }
                                    }
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                                    objectName: "transferJobStatus_" + index
                                    Accessible.name: text
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
=======
                                    objectName: "transferJobStatus_" + index
                                    Accessible.name: text
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                                }

                                MichiButton {
                                    text: "Cancelar"
                                    variant: "ghost"
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                                    visible: modelData.status === "queued" || modelData.status === "transferring"
                                    onClicked: root.cancelTransfer(modelData.job_id || "")
                                    objectName: "devices.transferPanel.cancelBtn." + (modelData.job_id || index)
                                    Accessible.name: "Cancelar transferencia " + (modelData.source_path || "")
                                    Accessible.description: "Detiene la transferencia en curso"
=======
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
                                }

                                MichiButton {
                                    text: "Reintentar"
                                    variant: "ghost"
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                                    visible: modelData.status === "failed" || modelData.status === "cancelled"
                                    onClicked: root.retryTransfer(modelData.job_id || "")
                                    objectName: "devices.transferPanel.retryBtn." + (modelData.job_id || index)
                                    Accessible.name: "Reintentar transferencia " + (modelData.source_path || "")
                                    Accessible.description: "Vuelve a intentar la transferencia fallida"
=======
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                                    visible: {
                                        var s = modelData.status || modelData.state || ""
                                        return s === "failed" || s === "cancelled"
                                    }
                                    onClicked: {
                                        root.retryTransferClicked(modelData.job_id || "")
                                    }
                                    objectName: "retryTransferButton_" + index
                                    Accessible.name: "Reintentar transferencia"
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
                                }
                            }
                        }
                    }
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD

                    Accessible.role: Accessible.ListItem
                    Accessible.name: (modelData.source_path ? bridge.fileName(modelData.source_path) : "Transferencia") + " - " + (modelData.status || "queued")
=======
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                }
            }

            Text {
                text: root.transferJobs.length === 0 ? "No hay transferencias activas." : ""
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize
                visible: root.transferJobs.length === 0
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                Accessible.name: "No hay transferencias activas"
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                objectName: "devices.transferPanel.noActive"
>>>>>>> Stashed changes
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

<<<<<<< Updated upstream
=======
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
=======
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

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
            }
        }
    }

    function formatBytes(bytes) {
<<<<<<< Updated upstream
<<<<<<< Updated upstream
        if (!bytes || bytes < 1) return "0 B"
        if (bytes < 1024) return bytes + " B"
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
        if (!bytes || bytes < 1024) return (bytes || 0) + " B"
=======
        if (!bytes || bytes < 1) return "0 B"
        if (bytes < 1024) return bytes + " B"
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
        if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB"
        if (bytes < 1073741824) return (bytes / 1048576).toFixed(1) + " MB"
        return (bytes / 1073741824).toFixed(2) + " GB"
    }
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
<<<<<<< HEAD
=======
>>>>>>> Stashed changes
=======
<<<<<<< HEAD
=======
>>>>>>> Stashed changes

    function formatEstimate(seconds) {
        if (seconds <= 0) return ""
        if (seconds < 60) return Math.ceil(seconds) + "s restantes"
        if (seconds < 3600) return Math.ceil(seconds / 60) + "min restantes"
        return (seconds / 3600).toFixed(1) + "h restantes"
    }
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
}
