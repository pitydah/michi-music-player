import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "."

Item {
    id: root

    property var devicesBridge: typeof devicesBridge !== "undefined" ? devicesBridge : null
    property var deviceSyncService: typeof deviceSyncService !== "undefined" ? deviceSyncService : null

    Component.onCompleted: {
        if (root.devicesBridge && typeof root.devicesBridge.refresh !== "undefined")
            root.devicesBridge.refresh()
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Text {
                text: "Dispositivos y sincronización"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            SyncStatusPanel {
                id: syncStatus
                width: parent.width
                serverActive: root.devicesBridge ? root.devicesBridge.serverActive : false
                serverPort: root.devicesBridge ? root.devicesBridge.serverPort : 53318
                peerCount: root.devicesBridge ? root.devicesBridge.peers.length : 0
                onStartServer: { if (root.devicesBridge) root.devicesBridge.startServer() }
                onStopServer: { if (root.devicesBridge) root.devicesBridge.stopServer() }
            }

            SectionHeader { text: "Dispositivos emparejados"; width: parent.width }

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
                text: "No hay dispositivos emparejados."
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                width: parent.width
                visible: root.devicesBridge && root.devicesBridge.pairedDevices.length === 0
            }

            SectionHeader { text: "Pares detectados en red"; width: parent.width }

            Repeater {
                model: root.devicesBridge ? root.devicesBridge.peers : []

                DeviceCard {
                    width: parent.width
                    deviceAlias: modelData.alias || ""
                    deviceIp: modelData.ip || ""
                    devicePort: modelData.port || 0
                    deviceType: modelData.device || "desktop"
                    paired: false
                }
            }

            Text {
                text: "No se detectaron pares en la red."
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                width: parent.width
                visible: root.devicesBridge && root.devicesBridge.peers.length === 0
            }

            DevicePairingDialog {
                id: pairingDialog
                width: parent.width
                visible: false
            }

            DeviceStorageView {
                id: storageView
                width: parent.width
            }

            DeviceTransferQueue {
                id: transferQueue
                width: parent.width
            }
        }
    }
}
