import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
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
    property var deviceCompatibility: ({})
    property string deviceType: "desktop"
    property string deviceIp: ""
    property int devicePort: 0
    property var transferJobs: []
    property var transferHistory: []
    property var devicesBridge: null

    signal backClicked()
    signal authorizeClicked()
    signal unauthorizeClicked()
    signal trustClicked()
    signal untrustClicked()
    signal unpairClicked()
    signal syncClicked()
    signal editProfileClicked()
    signal connectClicked()
    signal pairClicked()
    signal transferClicked(string jobId)
    signal cancelTransfer(string jobId)
    signal retryTransfer(string jobId)
    signal clearHistory()
    signal browseFiles()
    signal ejectDevice(string mountPoint)

    objectName: "devices.detailPage"

    Accessible.role: Accessible.Panel
    Accessible.name: "Detalle de dispositivo: " + root.deviceLabel

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

            Row {
                spacing: MichiTheme.spacing.sm
                width: parent.width

                MichiButton {
                    text: "< Volver"
                    variant: "ghost"
                    onClicked: root.backClicked()
                    objectName: "devices.detailPage.backBtn"
                    Accessible.name: "Volver a lista de dispositivos"
                }
            }

            GlassMaterial {
                width: parent.width
                height: headerColumn.height + MichiTheme.spacing.xl * 2
                radius: MichiTheme.radiusMd
                variant: "elevated"
                objectName: "devices.detailPage.header"

                Column {
                    id: headerColumn
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.sm

                    Row {
                        spacing: MichiTheme.spacing.md
                        width: parent.width

                        Rectangle {
                            width: 48; height: 48; radius: MichiTheme.radiusSm
                            color: MichiTheme.colors.accentSurface
                            anchors.verticalCenter: parent.verticalCenter

                            Text {
                                anchors.centerIn: parent
                                text: {
                                    var t = root.deviceType.toLowerCase()
                                    if (t === "android" || t === "iphone") return "\u260E"
                                    if (t === "tablet") return "\u2328"
                                    if (t === "dedicated" || t === "hiby" || t === "fiio") return "\u266B"
                                    if (t === "sandisk") return "\uD83D\uDCFD"
                                    return "\uD83D\uDDA5"
                                }
                                font.pixelSize: 22
                            }
                        }

                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: MichiTheme.spacing.xs

                            Text {
                                text: root.deviceLabel || "Dispositivo"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.pageTitleSize
                                font.weight: MichiTheme.typography.weightBold
                                elide: Text.ElideRight
                                width: parent.width
                            }

                            Text {
                                text: root.deviceVendor + " " + root.deviceModel
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.bodySize
                                visible: root.deviceVendor !== "" || root.deviceModel !== ""
                            }
                        }
                    }

                    Text {
                        text: "Protocolo: " + (root.deviceProtocol || "Desconocido")
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.metaSize
                    }

                    Text {
                        text: "IP: " + root.deviceIp + ":" + root.devicePort
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        visible: root.deviceIp !== ""
                    }

                    Row {
                        spacing: MichiTheme.spacing.sm
                        StatusBadge { text: root.deviceAuthorized ? "Autorizado" : "No autorizado"; kind: root.deviceAuthorized ? "success" : "disconnected" }
                        StatusBadge { text: root.deviceTrusted ? "Confiado" : "No confiado"; kind: root.deviceTrusted ? "success" : "disconnected" }
                        StatusBadge { text: root.deviceMountPoint !== "" ? "Montado" : "No montado"; kind: root.deviceMountPoint !== "" ? "active" : "disconnected" }
                    }
                }
            }

            DeviceStoragePanel {
                id: storagePanel
                width: parent.width
                mountPoint: root.deviceMountPoint
                storageInfo: root.deviceStorage
                compatibilityInfo: root.deviceCompatibility
                onEjectRequested: root.ejectDevice(mountPoint)
            }

            DeviceSyncProfileEditor {
                id: profileEditor
                width: parent.width
                deviceKey: root.deviceKey
            }

            Row {
                spacing: MichiTheme.spacing.sm
                width: parent.width
                wrapMode: Text.WordWrap
                objectName: "devices.detailPage.actions"

                MichiButton {
                    text: "Sincronizar"
                    variant: "primary"
                    onClicked: root.syncClicked()
                    objectName: "devices.detailPage.syncBtn"
                    Accessible.name: "Iniciar sincronización con el dispositivo"
                }

                MichiButton {
                    text: root.deviceAuthorized ? "Desautorizar" : "Autorizar"
                    variant: "secondary"
                    onClicked: root.deviceAuthorized ? root.unauthorizeClicked() : root.authorizeClicked()
                    objectName: "devices.detailPage.authorizeBtn"
                    Accessible.name: root.deviceAuthorized ? "Desautorizar dispositivo" : "Autorizar dispositivo"
                }

                MichiButton {
                    text: root.deviceTrusted ? "No confiar" : "Confiar"
                    variant: "ghost"
                    onClicked: root.deviceTrusted ? root.untrustClicked() : root.trustClicked()
                    objectName: "devices.detailPage.trustBtn"
                    Accessible.name: root.deviceTrusted ? "Revocar confianza del dispositivo" : "Confiar en el dispositivo"
                }

                MichiButton {
                    text: "Editar perfil"
                    variant: "ghost"
                    onClicked: root.editProfileClicked()
                    objectName: "devices.detailPage.editProfileBtn"
                    Accessible.name: "Editar perfil de sincronización"
                }

                MichiButton {
                    text: "Desvincular"
                    variant: "danger"
                    onClicked: root.unpairClicked()
                    objectName: "devices.detailPage.unpairBtn"
                    Accessible.name: "Desvincular dispositivo"
                    Accessible.description: "Elimina la vinculación con este dispositivo"
                }
            }

            DeviceTransferPanel {
                id: transferPanel
                width: parent.width
                bridge: root.devicesBridge
                transferJobs: root.transferJobs
                transferHistory: root.transferHistory
                onCancelTransfer: root.cancelTransfer(jobId)
                onRetryTransfer: root.retryTransfer(jobId)
                onClearHistory: root.clearHistory()
            }

            DeviceSyncHistory {
                id: syncHistory
                width: parent.width
                deviceKey: root.deviceKey
                historyEntries: root.transferHistory
                onClearHistoryClicked: root.clearHistory()
            }

            Text {
                text: "Nota: La transferencia de video no está soportada. Solo se admiten archivos de audio."
                color: MichiTheme.colors.warning
                font.pixelSize: MichiTheme.typography.captionSize
                width: parent.width
                wrapMode: Text.WordWrap
                leftPadding: MichiTheme.spacing.md
                objectName: "devices.detailPage.audioOnlyNotice"
                Accessible.role: Accessible.Alert
                Accessible.name: "Solo audio"
                Accessible.description: "Este dispositivo solo soporta transferencia de archivos de audio. El video no está disponible."
            }
        }
    }
}
