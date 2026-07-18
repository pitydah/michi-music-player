import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Device Storage"
    objectName: "deviceStoragePanel"
    focus: true
    id: root

    property string mountPoint: ""
    property var storageInfo: ({})
    property var dv: typeof devicesBridge !== "undefined" ? devicesBridge : null

    signal ejectClicked()

    implicitHeight: childrenRect.height


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
                text: qsTr("Almacenamiento")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: root.mountPoint ? "Punto de montaje: qsTr(" + root.mountPoint : ")Sin dispositivo montado"
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
            }

            Grid {
                width: parent.width
                columns: 2
                columnSpacing: MichiTheme.spacing.md
                rowSpacing: MichiTheme.spacing.sm

                Text { text: qsTr("Total:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                Text {
                    text: root.storageInfo.totalBytes ? formatBytes(root.storageInfo.totalBytes) : qsTr("-")
                    color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                }

                Text { text: qsTr("Libre:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                Text {
                    text: root.storageInfo.freeBytes ? formatBytes(root.storageInfo.freeBytes) : qsTr("-")
                    color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                }

                Text { text: qsTr("Usado:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                Text {
                    text: root.storageInfo.usedBytes ? formatBytes(root.storageInfo.usedBytes) : qsTr("-")
                    color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                }
            }

            Rectangle {
                width: parent.width
                height: 8
                radius: MichiTheme.radius.pill
                color: MichiTheme.colors.controlTrack
                visible: root.storageInfo.totalBytes && root.storageInfo.totalBytes > 0

                Rectangle {
                    width: Math.min(parent.width, (root.storageInfo.usedBytes || 0) / Math.max(1, root.storageInfo.totalBytes || 1) * parent.width)
                    height: parent.height
                    radius: MichiTheme.radius.pill
                    color: {
                        var ratio = (root.storageInfo.usedBytes || 0) / Math.max(1, root.storageInfo.totalBytes || 1)
                        if (ratio > 0.9) return MichiTheme.colors.error
                        if (ratio > 0.75) return MichiTheme.colors.warning
                        return MichiTheme.colors.accentBlue
                    }
                }
            }

            Text {
                text: qsTr("Formatos compatibles")
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
                    }
                }
            }

            Text {
                text: qsTr("Formatos de video no soportados (solo audio)")
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.captionSize
                visible: true

            }

            MichiButton {
                Accessible.role: Accessible.Button

                text: qsTr("Expulsar dispositivo")
                variant: "secondary"
                visible: root.mountPoint !== ""
                onClicked: {
                    if (root.dv && typeof root.dv.ejectDevice === "function")
                        root.dv.ejectDevice(root.mountPoint)
                    root.ejectClicked()
                }
                activeFocusOnTab: true
                Keys.onReturnPressed: clicked()
                Keys.onSpacePressed: clicked()
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
}
