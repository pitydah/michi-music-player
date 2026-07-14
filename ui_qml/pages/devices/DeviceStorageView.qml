import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    id: root

    property string mountPoint: ""
    property var storageInfo: ({})

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
                text: "Almacenamiento"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: root.mountPoint ? "Punto de montaje: " + root.mountPoint : "Sin dispositivo montado"
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
            }

            Grid {
                width: parent.width
                columns: 2
                columnSpacing: MichiTheme.spacing.md
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
                    color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
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
