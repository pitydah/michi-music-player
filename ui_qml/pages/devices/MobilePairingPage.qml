import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Emparejar dispositivo")
    objectName: "mobilePairingPage"
    focus: true
    id: root

    property var msb: typeof mobileSyncBridge !== "undefined" ? mobileSyncBridge : null
    property int _timeLeft: 300
    property bool _timerRunning: false

    function refresh() {
        if (root.msb) {
            if (root.msb.pairingState === "idle" || root.msb.pairingState === "") {
                root.msb.startPairing()
            }
        }
    }

    Component.onCompleted: root.refresh()

    Timer {
        id: timer
        interval: 1000
        repeat: true
        onTriggered: {
            root._timeLeft -= 1
            if (root._timeLeft <= 0) {
                timer.stop()
                if (root.msb) root.msb.cancelPairing()
            }
        }
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Text {
                text: qsTr("Emparejar dispositivo móvil")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: qsTr("Escanea el código QR con la aplicación Michi en tu teléfono, o ingresa el código manualmente.")
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize
                width: parent.width
                wrapMode: Text.WordWrap
                visible: root.msb && root.msb.pairingState === "waiting"
            }

            // QR Code display
            GlassMaterial {
                width: Math.min(parent.width, 280)
                height: width + 80
                radius: MichiTheme.radius.md
                anchors.horizontalCenter: parent.horizontalCenter
                visible: root.msb && root.msb.pairingState === "waiting"

                Column {
                    anchors.centerIn: parent
                    spacing: MichiTheme.spacing.md

                    Rectangle {
                        width: 200; height: 200
                        radius: MichiTheme.radius.sm
                        anchors.horizontalCenter: parent.horizontalCenter
                        color: "white"
                        visible: root.msb && root.msb.qrDataUrl !== ""

                        Image {
                            anchors.centerIn: parent
                            width: 180; height: 180
                            source: root.msb ? root.msb.qrDataUrl : ""
                            fillMode: Image.PreserveAspectFit
                        }
                    }

                    Text {
                        text: root.msb ? root.msb.pairingCode : ""
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: 28
                        font.weight: MichiTheme.typography.weightBold
                        anchors.horizontalCenter: parent.horizontalCenter
                        font.letterSpacing: 6
                    }
                }
            }

            // Time remaining
            Text {
                text: root._timerRunning ? qsTr("Tiempo restante: %1:%2").arg(Math.floor(root._timeLeft / 60)).arg(root._timeLeft % 60) : ""
                color: root._timeLeft < 30 ? MichiTheme.colors.error : MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                anchors.horizontalCenter: parent.horizontalCenter
                visible: root.msb && root.msb.pairingState === "waiting"
            }

            // Manual code entry
            GlassMaterial {
                width: parent.width
                radius: MichiTheme.radius.md
                visible: root.msb && root.msb.pairingState === "waiting"

                Column {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: qsTr("O ingresa el código manualmente")
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                    }

                    Row {
                        spacing: MichiTheme.spacing.sm

                        TextField {
                            id: codeInput
                            placeholderText: qsTr("Código de 6 dígitos")
                            font.pixelSize: MichiTheme.typography.bodySize
                            maximumLength: 6
                            validator: RegularExpressionValidator { regularExpression: /[0-9]{6}/ }
                            Accessible.role: Accessible.EditableText
                            Accessible.name: qsTr("Código de verificación")
                        }

                        MichiButton {
                            text: qsTr("Verificar")
                            enabled: codeInput.text.length === 6
                            onClicked: {
                                if (root.msb) {
                                    var r = root.msb.verifyPairing(codeInput.text)
                                    if (r && r.ok) {
                                        root._timerRunning = false
                                        timer.stop()
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Verification status
            StatusBadge {
                visible: root.msb && root.msb.pairingState === "verified"
                text: qsTr("Dispositivo conectado correctamente")
                kind: "success"
                anchors.horizontalCenter: parent.horizontalCenter
            }

            // Paired devices list
            SectionHeader { text: qsTr("Dispositivos pareados"); width: parent.width }
            Repeater {
                model: root.msb ? root.msb.pairedDevices : []

                GlassMaterial {
                    width: parent.width
                    height: 48
                    radius: MichiTheme.radius.sm
                    variant: "base"

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.sm
                        spacing: MichiTheme.spacing.sm

                        Text {
                            text: modelData.name || qsTr("Dispositivo")
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }

                        StatusBadge {
                            text: modelData.trusted ? qsTr("Confiado") : qsTr("No confiado")
                            kind: modelData.trusted ? "success" : "warning"
                        }

                        MichiButton {
                            text: qsTr("Olvidar")
                            variant: "ghost"
                            implicitWidth: 60
                            implicitHeight: 28
                            onClicked: {
                                if (root.msb) root.msb.unpairDevice(modelData.id)
                            }
                        }
                    }
                }
            }

            // Empty state
            Text {
                text: qsTr("No hay dispositivos pareados")
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize
                visible: root.msb && root.msb.pairedDevices.length === 0
                anchors.horizontalCenter: parent.horizontalCenter
            }

            // Start pairing button
            MichiButton {
                text: root.msb && root.msb.pairingState === "waiting" ? qsTr("Generar nuevo código") : qsTr("Iniciar emparejamiento")
                variant: "primary"
                anchors.horizontalCenter: parent.horizontalCenter
                onClicked: {
                    root._timeLeft = 300
                    root._timerRunning = true
                    timer.start()
                    if (root.msb) root.msb.startPairing()
                }
            }
        }
    }
}
