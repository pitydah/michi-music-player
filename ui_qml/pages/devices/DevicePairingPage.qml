import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../materials"
import "../../components"

Item {
    id: root

    property var devicesBridge: null
    property var discoveredPeers: []
    property string qrCodeData: ""

    signal backRequested()
    signal pairWithPeer(string alias, string ip, int port)
    signal pairManually(string ip, int port, string alias)
    signal cancelPairing()

    objectName: "devices.pairingPage"

    Accessible.role: Accessible.Panel
    Accessible.name: "Vinculación de dispositivos"

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
                    onClicked: root.backRequested()
                    objectName: "devices.pairingPage.backBtn"
                    Accessible.name: "Volver a dispositivos"
                }
            }

            Text {
                text: "Vincular dispositivo"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                objectName: "devices.pairingPage.title"
                Accessible.role: Accessible.Heading
                Accessible.name: text
            }

            GlassMaterial {
                width: parent.width
                height: column2.height + MichiTheme.spacing.xl * 2
                radius: MichiTheme.radiusMd
                variant: "elevated"

                Column {
                    id: column2
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Dispositivos detectados en la red"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                        objectName: "devices.pairingPage.discoveredTitle"
                        Accessible.role: Accessible.Heading
                        Accessible.name: text
                    }

                    Repeater {
                        model: root.discoveredPeers
                        objectName: "devices.pairingPage.peerList"

                        GlassCard {
                            width: parent.width
                            height: 72
                            title: modelData.alias || "Dispositivo"
                            subtitle: (modelData.ip || "") + ":" + (modelData.port || 0)
                            interactive: true
                            objectName: "devices.pairingPage.peer." + index

                            Accessible.role: Accessible.Button
                            Accessible.name: "Vincular con " + (modelData.alias || "dispositivo")

                            MouseArea {
                                anchors.fill: parent
                                onClicked: root.pairWithPeer(modelData.alias || "", modelData.ip || "", modelData.port || 0)
                                cursorShape: Qt.PointingHandCursor
                            }

                            Row {
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.rightMargin: MichiTheme.spacing.md
                                spacing: MichiTheme.spacing.xs

                                StatusBadge {
                                    text: "Vincular"
                                    kind: "info"
                                }
                            }
                        }
                    }

                    Text {
                        text: "No se detectaron dispositivos en la red."
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.bodySize
                        visible: root.discoveredPeers.length === 0
                        objectName: "devices.pairingPage.noPeers"
                    }
                }
            }

            GlassMaterial {
                width: parent.width
                height: manualColumn.height + MichiTheme.spacing.xl * 2
                radius: MichiTheme.radiusMd
                variant: "base"

                Column {
                    id: manualColumn
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Conexión manual"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                        objectName: "devices.pairingPage.manualTitle"
                        Accessible.role: Accessible.Heading
                        Accessible.name: text
                    }

                    TextField {
                        id: manualIpField
                        width: parent.width
                        placeholderText: "Dirección IP"
                        objectName: "devices.pairingPage.manualIpField"
                        Accessible.name: "Dirección IP del dispositivo"
                        Accessible.role: Accessible.EditableText
                    }

                    TextField {
                        id: manualPortField
                        width: parent.width
                        placeholderText: "Puerto (53318)"
                        inputMethodHints: Qt.ImhDigitsOnly
                        objectName: "devices.pairingPage.manualPortField"
                        Accessible.name: "Puerto del dispositivo"
                        Accessible.role: Accessible.EditableText
                    }

                    TextField {
                        id: manualAliasField
                        width: parent.width
                        placeholderText: "Alias (opcional)"
                        objectName: "devices.pairingPage.manualAliasField"
                        Accessible.name: "Alias del dispositivo"
                        Accessible.role: Accessible.EditableText
                    }

                    MichiButton {
                        text: "Conectar manualmente"
                        variant: "primary"
                        enabled: manualIpField.text !== ""
                        onClicked: {
                            var port = parseInt(manualPortField.text) || 53318
                            root.pairManually(manualIpField.text, port, manualAliasField.text)
                        }
                        objectName: "devices.pairingPage.manualConnectBtn"
                        Accessible.name: "Conectar manualmente al dispositivo"
                        Accessible.description: "Establece conexión usando dirección IP y puerto"
                    }
                }
            }

            GlassMaterial {
                width: parent.width
                height: qrColumn.height + MichiTheme.spacing.xl * 2
                radius: MichiTheme.radiusMd
                variant: "base"

                Column {
                    id: qrColumn
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Código QR de emparejamiento"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                        objectName: "devices.pairingPage.qrTitle"
                        Accessible.role: Accessible.Heading
                        Accessible.name: text
                    }

                    Rectangle {
                        width: 160; height: 160
                        radius: MichiTheme.radiusSm
                        color: MichiTheme.colors.textOnError
                        anchors.horizontalCenter: parent.horizontalCenter
                        visible: root.qrCodeData !== ""
                        objectName: "devices.pairingPage.qrCode"

                        Text {
                            anchors.centerIn: parent
                            text: "QR"
                            color: "black"
                            font.pixelSize: MichiTheme.typography.heroTitleSize
                            font.bold: true
                        }

                        Accessible.role: Accessible.Graphic
                        Accessible.name: "Código QR para emparejamiento"
                        Accessible.description: root.qrCodeData
                    }

                    Text {
                        text: root.qrCodeData || "Genera un código QR para emparejar dispositivos."
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        horizontalAlignment: Text.AlignHCenter
                        width: parent.width
                        wrapMode: Text.WordWrap
                    }

                    MichiButton {
                        text: "Generar código QR"
                        variant: "primary"
                        anchors.horizontalCenter: parent.horizontalCenter
                        onClicked: {
                            if (root.devicesBridge && root.devicesBridge.generateQRCode)
                                root.qrCodeData = root.devicesBridge.generateQRCode()
                        }
                        objectName: "devices.pairingPage.generateQrBtn"
                        Accessible.name: "Generar código QR de emparejamiento"
                    }
                }
            }
        }
    }
}
