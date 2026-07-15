import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    id: root

    property string mountPoint: ""
    property var storageInfo: ({})
<<<<<<< Updated upstream
    property var dv: typeof devicesBridge !== "undefined" ? devicesBridge : null
=======
<<<<<<< HEAD
    property var compatibilityInfo: ({})
>>>>>>> Stashed changes

    signal ejectClicked()

    implicitHeight: childrenRect.height

<<<<<<< Updated upstream
    objectName: "DeviceStoragePanel"
    Accessible.role: Accessible.Pane
    Accessible.name: "Almacenamiento del dispositivo"
=======
    objectName: "devices.storagePanel"
=======
    property var dv: typeof devicesBridge !== "undefined" ? devicesBridge : null

    signal ejectClicked()

    implicitHeight: childrenRect.height

    objectName: "DeviceStoragePanel"
    Accessible.role: Accessible.Pane
    Accessible.name: "Almacenamiento del dispositivo"
>>>>>>> origin/michi-qml-functional-wave
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
            spacing: MichiTheme.spacing.sm

            Text {
                text: "Almacenamiento"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
<<<<<<< Updated upstream
                Accessible.name: "Almacenamiento"
=======
<<<<<<< HEAD
                objectName: "devices.storagePanel.title"
                Accessible.role: Accessible.Heading
                Accessible.name: text
>>>>>>> Stashed changes
            }

            Text {
                text: root.mountPoint ? "Punto de montaje: " + root.mountPoint : "Sin dispositivo montado"
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
<<<<<<< Updated upstream
                Accessible.name: text
=======
                visible: root.mountPoint !== ""
                objectName: "devices.storagePanel.mountPoint"
            }

            Rectangle {
                width: parent.width
                height: 24
                radius: MichiTheme.radiusPill
                color: MichiTheme.colors.controlTrack
                visible: root.storageInfo.total_bytes > 0
                objectName: "devices.storagePanel.bar"

                Rectangle {
                    width: {
                        var ratio = root.storageInfo.total_bytes > 0
                            ? (root.storageInfo.used_bytes || 0) / root.storageInfo.total_bytes : 0
                        return Math.min(parent.width, parent.width * ratio)
                    }
                    height: parent.height
                    radius: MichiTheme.radiusPill
                    color: {
                        var ratio = root.storageInfo.total_bytes > 0
                            ? (root.storageInfo.used_bytes || 0) / root.storageInfo.total_bytes : 0
                        if (ratio > 0.9) return MichiTheme.colors.error
                        if (ratio > 0.7) return MichiTheme.colors.warning
                        return MichiTheme.colors.accentBlue
                    }
                }

                Accessible.role: Accessible.ProgressBar
                Accessible.name: "Uso de almacenamiento"
                Accessible.description: {
                    var used = formatBytes(root.storageInfo.used_bytes || 0)
                    var total = formatBytes(root.storageInfo.total_bytes || 0)
                    return used + " usado de " + total
                }
=======
                Accessible.name: "Almacenamiento"
            }

            Text {
                text: root.mountPoint ? "Punto de montaje: " + root.mountPoint : "Sin dispositivo montado"
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                Accessible.name: text
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
            }

            Grid {
                width: parent.width
                columns: 2
                columnSpacing: MichiTheme.spacing.md
<<<<<<< Updated upstream
                rowSpacing: MichiTheme.spacing.sm
=======
<<<<<<< HEAD
                rowSpacing: MichiTheme.spacing.xs
>>>>>>> Stashed changes

                Text { text: "Total:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                Text {
                    text: root.storageInfo.totalBytes ? formatBytes(root.storageInfo.totalBytes) : "-"
                    color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                }

                Text { text: "Libre:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                Text {
                    text: root.storageInfo.freeBytes ? formatBytes(root.storageInfo.freeBytes) : "-"
                    color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                }

                Text { text: "Usado:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                Text {
<<<<<<< Updated upstream
                    text: root.storageInfo.usedBytes ? formatBytes(root.storageInfo.usedBytes) : "-"
=======
                    text: root.storageInfo.used_bytes > 0 ? formatBytes(root.storageInfo.used_bytes) : "-"
=======
                rowSpacing: MichiTheme.spacing.sm

                Text { text: "Total:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                Text {
                    text: root.storageInfo.totalBytes ? formatBytes(root.storageInfo.totalBytes) : "-"
                    color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                }

                Text { text: "Libre:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                Text {
                    text: root.storageInfo.freeBytes ? formatBytes(root.storageInfo.freeBytes) : "-"
                    color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                }

                Text { text: "Usado:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                Text {
                    text: root.storageInfo.usedBytes ? formatBytes(root.storageInfo.usedBytes) : "-"
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
                    color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                }
            }

<<<<<<< Updated upstream
            Rectangle {
=======
<<<<<<< HEAD
            Row {
                spacing: MichiTheme.spacing.sm
                visible: root.mountPoint !== ""

                MichiButton {
                    text: "Expulsar"
                    variant: "secondary"
                    onClicked: root.ejectRequested(root.mountPoint)
                    objectName: "devices.storagePanel.ejectBtn"
                    Accessible.name: "Expulsar dispositivo"
                    Accessible.description: "Desmonta de forma segura el dispositivo de almacenamiento"
                }
            }

            Text {
                text: "Formatos soportados"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.cardTitleSize
                font.weight: MichiTheme.typography.weightMedium
                visible: root.compatibilityInfo.supported_formats && root.compatibilityInfo.supported_formats.length > 0
                topPadding: MichiTheme.spacing.md
                objectName: "devices.storagePanel.formatsTitle"
            }

            Flow {
>>>>>>> Stashed changes
                width: parent.width
                height: 8
                radius: MichiTheme.radiusPill
                color: MichiTheme.colors.controlTrack
                visible: root.storageInfo.totalBytes && root.storageInfo.totalBytes > 0

<<<<<<< Updated upstream
=======
                Repeater {
                    model: root.compatibilityInfo.supported_formats || []
                    delegate: StatusBadge {
                        text: modelData
                        kind: "success"
=======
            Rectangle {
                width: parent.width
                height: 8
                radius: MichiTheme.radiusPill
                color: MichiTheme.colors.controlTrack
                visible: root.storageInfo.totalBytes && root.storageInfo.totalBytes > 0

>>>>>>> Stashed changes
                Rectangle {
                    width: Math.min(parent.width, (root.storageInfo.usedBytes || 0) / Math.max(1, root.storageInfo.totalBytes || 1) * parent.width)
                    height: parent.height
                    radius: MichiTheme.radiusPill
                    color: {
                        var ratio = (root.storageInfo.usedBytes || 0) / Math.max(1, root.storageInfo.totalBytes || 1)
                        if (ratio > 0.9) return MichiTheme.colors.error
                        if (ratio > 0.75) return MichiTheme.colors.warning
                        return MichiTheme.colors.accentBlue
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
                    }
                }
            }

            Text {
<<<<<<< Updated upstream
                text: "Formatos compatibles"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.cardTitleSize
                font.weight: MichiTheme.typography.weightMedium
                visible: root.storageInfo.supportedFormats
            }

            Flow {
                width: parent.width
                spacing: MichiTheme.spacing.xs
                visible: root.storageInfo.supportedFormats

                Repeater {
                    model: root.storageInfo.supportedFormats || []

                    StatusBadge {
                        text: modelData
                        kind: "success"
                        objectName: "supportedFormatBadge_" + index
                        Accessible.name: "Formato soportado: " + modelData
                    }
                }
            }

            Text {
                text: "Formatos de video no soportados (solo audio)"
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.captionSize
=======
<<<<<<< HEAD
                text: "Información de compatibilidad no disponible"
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.captionSize
                visible: !root.compatibilityInfo.supported_formats || root.compatibilityInfo.supported_formats.length === 0
=======
                text: "Formatos compatibles"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.cardTitleSize
                font.weight: MichiTheme.typography.weightMedium
                visible: root.storageInfo.supportedFormats
            }

            Flow {
                width: parent.width
                spacing: MichiTheme.spacing.xs
                visible: root.storageInfo.supportedFormats

                Repeater {
                    model: root.storageInfo.supportedFormats || []

                    StatusBadge {
                        text: modelData
                        kind: "success"
                        objectName: "supportedFormatBadge_" + index
                        Accessible.name: "Formato soportado: " + modelData
                    }
                }
            }

            Text {
                text: "Formatos de video no soportados (solo audio)"
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.captionSize
>>>>>>> Stashed changes
                visible: true

                Accessible.name: "Solo se admiten formatos de audio"
            }

            MichiButton {
                text: "Expulsar dispositivo"
                variant: "secondary"
                visible: root.mountPoint !== ""
                onClicked: {
                    if (root.dv && typeof root.dv.ejectDevice === "function")
                        root.dv.ejectDevice(root.mountPoint)
                    root.ejectClicked()
                }
                objectName: "ejectDeviceButton"
                Accessible.name: "Expulsar dispositivo de forma segura"
                activeFocusOnTab: true
                Keys.onReturnPressed: clicked()
                Keys.onSpacePressed: clicked()
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
            }
        }
    }

    function formatBytes(bytes) {
<<<<<<< Updated upstream
        if (!bytes || bytes < 1) return "0 B"
        if (bytes < 1024) return bytes + " B"
=======
<<<<<<< HEAD
        if (!bytes || bytes < 1024) return (bytes || 0) + " B"
=======
        if (!bytes || bytes < 1) return "0 B"
        if (bytes < 1024) return bytes + " B"
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
        if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB"
        if (bytes < 1073741824) return (bytes / 1048576).toFixed(1) + " MB"
        return (bytes / 1073741824).toFixed(2) + " GB"
    }
}
