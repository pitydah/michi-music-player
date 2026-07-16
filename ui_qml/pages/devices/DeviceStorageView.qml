import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Device Storage View"
    objectName: "deviceStorageView"
    focus: true
    id: root

    property string mountPoint: ""
    property var storageInfo: ({})

    implicitHeight: childrenRect.height

    objectName: "DeviceStorageView"
    Accessible.role: Accessible.Pane
    Accessible.name: "Almacenamiento"

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
                Accessible.name: "Almacenamiento"
            }

            Text {
                text: root.mountPoint ? "Punto de montaje: " + root.mountPoint : "Sin dispositivo montado"
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                Accessible.name: text
            }

            Grid {
                width: parent.width
                columns: 2
                columnSpacing: MichiTheme.spacing.md
                rowSpacing: MichiTheme.spacing.sm

                Text { text: "Total:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; objectName: "storageTotalLabel" }
                Text {
                    text: root.storageInfo.totalBytes ? formatBytes(root.storageInfo.totalBytes) : "-"
                    color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                    objectName: "storageTotalValue"
                }

                Text { text: "Libre:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; objectName: "storageFreeLabel" }
                Text {
                    text: root.storageInfo.freeBytes ? formatBytes(root.storageInfo.freeBytes) : "-"
                    color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                    objectName: "storageFreeValue"
                }

                Text { text: "Usado:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; objectName: "storageUsedLabel" }
                Text {
                    text: root.storageInfo.usedBytes ? formatBytes(root.storageInfo.usedBytes) : "-"
                    color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                    objectName: "storageUsedValue"
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
