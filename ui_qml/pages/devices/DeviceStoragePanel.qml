import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    id: root

    property string mountPoint: ""
    property var storageInfo: ({})
    property var compatibilityInfo: ({})

    signal ejectRequested(string mountPoint)

    implicitHeight: childrenRect.height

    objectName: "devices.storagePanel"

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
                objectName: "devices.storagePanel.title"
                Accessible.role: Accessible.Heading
                Accessible.name: text
            }

            Text {
                text: root.mountPoint ? "Montado en: " + root.mountPoint : "Sin dispositivo montado"
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
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
            }

            Grid {
                width: parent.width
                columns: 2
                columnSpacing: MichiTheme.spacing.md
                rowSpacing: MichiTheme.spacing.xs

                Text { text: "Total:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                Text {
                    text: root.storageInfo.total_bytes > 0 ? formatBytes(root.storageInfo.total_bytes) : "-"
                    color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                }
                Text { text: "Libre:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                Text {
                    text: root.storageInfo.free_bytes > 0 ? formatBytes(root.storageInfo.free_bytes) : "-"
                    color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                }
                Text { text: "Usado:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                Text {
                    text: root.storageInfo.used_bytes > 0 ? formatBytes(root.storageInfo.used_bytes) : "-"
                    color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                }
            }

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
                width: parent.width
                spacing: MichiTheme.spacing.xs
                visible: root.compatibilityInfo.supported_formats && root.compatibilityInfo.supported_formats.length > 0
                objectName: "devices.storagePanel.formatBadges"

                Repeater {
                    model: root.compatibilityInfo.supported_formats || []
                    delegate: StatusBadge {
                        text: modelData
                        kind: "success"
                    }
                }
            }

            Text {
                text: "Información de compatibilidad no disponible"
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.captionSize
                visible: !root.compatibilityInfo.supported_formats || root.compatibilityInfo.supported_formats.length === 0
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
