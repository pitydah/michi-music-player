import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"
import "../materials"
import "devices"

Item {
    id: root

    property var devicesBridge: typeof devicesBridge !== "undefined" ? devicesBridge : null

    Component.onCompleted: {
        if (root.devicesBridge && typeof root.devicesBridge.refresh !== "undefined")
            root.devicesBridge.refresh()
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true; boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column; width: parent.width; spacing: MichiTheme.spacing.lg

            Text {
                text: "Dispositivos"
                color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            SyncStatusPanel {
                width: parent.width
                serverActive: root.devicesBridge ? root.devicesBridge.serverActive : false
                serverPort: root.devicesBridge ? root.devicesBridge.serverPort : 53318
                peerCount: root.devicesBridge ? root.devicesBridge.peers.length : 0
                onStartServer: { if (root.devicesBridge) root.devicesBridge.startServer() }
                onStopServer: { if (root.devicesBridge) root.devicesBridge.stopServer() }
            }

            SectionHeader { text: "Dispositivos vinculados"; width: parent.width }

            Repeater {
                model: root.devicesBridge ? root.devicesBridge.pairedDevices : []

                DeviceCard {
                    width: parent.width
                    deviceAlias: modelData.alias || ""
                    deviceType: modelData.device || "desktop"
                    paired: true
                }
            }

            Text {
                text: "No hay dispositivos vinculados. Inicia el servidor y usa la app Android para conectar."
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                width: parent.width; wrapMode: Text.WordWrap
                visible: root.devicesBridge && root.devicesBridge.pairedDevices.length === 0
            }

            SectionHeader { text: "Detectados en la red"; width: parent.width }

            Repeater {
                model: root.devicesBridge ? root.devicesBridge.peers : []

                DeviceCard {
                    width: parent.width
                    deviceAlias: modelData.alias || ""
                    deviceType: modelData.device || "desktop"
                    deviceIp: modelData.ip || ""
                    devicePort: modelData.port || 0
                    paired: false
                }
            }

            Text {
                text: "No se encontraron dispositivos en la red."
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                width: parent.width
                visible: root.devicesBridge && root.devicesBridge.peers.length === 0
            }
        }
    }
}
