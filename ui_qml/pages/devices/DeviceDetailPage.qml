import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property string deviceKey: ""
    property string deviceLabel: ""
    property string deviceVendor: ""
    property string deviceModel: ""
    property string deviceProtocol: ""
    property string deviceMountPoint: ""
    property bool deviceAuthorized: false
    property bool deviceTrusted: false
    property string deviceLastContact: ""
    property var deviceStorage: ({})

    signal backClicked()
    signal authorizeClicked()
    signal unauthorizeClicked()
    signal trustClicked()
    signal untrustClicked()
    signal unpairClicked()
    signal syncClicked()
    signal editProfileClicked()

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

            MichiButton {
                text: "< Volver"
                variant: "ghost"
                onClicked: root.backClicked()
            }

            GlassMaterial {
                width: parent.width
                height: 200
                radius: MichiTheme.radiusMd
                variant: "elevated"

                Column {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.sm

                    Text {
                        text: root.deviceLabel
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.pageTitleSize
                        font.weight: MichiTheme.typography.weightBold
                    }

                    Text { text: root.deviceVendor + " " + root.deviceModel; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                    Text { text: "Protocolo: " + root.deviceProtocol; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize }
                    Text { text: "Punto de montaje: " + root.deviceMountPoint; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; visible: root.deviceMountPoint !== "" }

                    Row {
                        spacing: MichiTheme.spacing.sm
                        StatusBadge { text: root.deviceAuthorized ? "Autorizado" : "No autorizado"; kind: root.deviceAuthorized ? "success" : "disconnected" }
                        StatusBadge { text: root.deviceTrusted ? "Confiado" : "No confiado"; kind: root.deviceTrusted ? "success" : "disconnected" }
                    }
                }
            }

            DeviceStorageView {
                id: storageView
                width: parent.width
                mountPoint: root.deviceMountPoint
                storageInfo: root.deviceStorage
            }

            DeviceCompatibilityView {
                id: compatView
                width: parent.width
                protocol: root.deviceProtocol
            }

            DeviceSyncProfileEditor {
                id: profileEditor
                width: parent.width
                deviceKey: root.deviceKey
            }

            Row {
                spacing: MichiTheme.spacing.sm

                MichiButton { text: "Sincronizar"; variant: "primary"; onClicked: root.syncClicked() }
                MichiButton { text: root.deviceAuthorized ? "Desautorizar" : "Autorizar"; variant: "secondary"; onClicked: root.deviceAuthorized ? root.unauthorizeClicked() : root.authorizeClicked() }
                MichiButton { text: root.deviceTrusted ? "No confiar" : "Confiar"; variant: "ghost"; onClicked: root.deviceTrusted ? root.untrustClicked() : root.trustClicked() }
                MichiButton { text: "Editar perfil"; variant: "ghost"; onClicked: root.editProfileClicked() }
                MichiButton { text: "Desvincular"; variant: "danger"; onClicked: root.unpairClicked() }
            }

            DeviceSyncHistory {
                id: syncHistory
                width: parent.width
                deviceKey: root.deviceKey
            }
        }
    }
}
