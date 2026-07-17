import QtQuick
import QtQuick.Controls as QQC2
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Pairing"
    objectName: "pairingDialog"
    id: root
    focus: true

    property string pairingCode: ""
    property string pairingStatus: "waiting"
    property string errorMessage: ""
    property bool open: false

    signal pairConfirmed()
    signal pairRejected()
    signal retryRequested()


    Accessible.description: "Código de vinculación para conectar el servidor"

    visible: open
    enabled: visible

    Keys.onEscapePressed: {
        root.open = false
        root.pairRejected()
    }

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.overlayDark
        z: 9990

        MouseArea {
            anchors.fill: parent
            onClicked: {
                root.open = false
                root.pairRejected()
            }
        }
    }

    FocusScope {
        id: dialogContent
        anchors.centerIn: parent
        width: Math.min(400, parent.width * 0.9)
        height: contentColumn.implicitHeight + MichiTheme.spacing.xl * 2
        z: 9991
        focus: root.visible

        GlassMaterial {
            anchors.fill: parent
            radius: MichiTheme.radius.lg
            variant: "elevated"

            Column {
                id: contentColumn
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.xl
                spacing: MichiTheme.spacing.lg

                Text {
                    text: "Vincular servidor"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                StatusBadge {
                    text: root.pairingStatus === "waiting" ? "Esperando código..."
                        : root.pairingStatus === "paired" ? "Vinculado"
                        : root.pairingStatus === "failed" ? "Error de vinculación"
                        : "Desconocido"
                    kind: root.pairingStatus === "paired" ? "success"
                        : root.pairingStatus === "failed" ? "error"
                        : "warning"
                }

                Rectangle {
                    width: parent.width
                    height: 80
                    radius: MichiTheme.radius.md
                    color: MichiTheme.colors.surfaceInput
                    border.color: MichiTheme.colors.borderCard
                    border.width: MichiTheme.borderWidth
                    visible: root.pairingCode !== ""

                    Text {
                        anchors.centerIn: parent
                        text: root.pairingCode
                        color: MichiTheme.colors.accentBlue
                        font.pixelSize: MichiTheme.typography.displaySize
                        font.weight: MichiTheme.typography.weightBold
                        font.letterSpacing: 2
                    }
                }

                Text {
                    text: root.pairingStatus === "waiting" ? "Introduce este código en el servidor para completar la vinculación."
                        : root.pairingStatus === "paired" ? "El servidor ha sido vinculado correctamente."
                        : "No se pudo completar la vinculación. Intenta de nuevo."
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    wrapMode: Text.WordWrap
                    width: parent.width
                }

                Text {
                    text: root.errorMessage
                    color: MichiTheme.colors.error
                    font.pixelSize: MichiTheme.typography.captionSize
                    visible: root.errorMessage !== ""
                }

                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: MichiTheme.spacing.sm

                    MichiButton {
                        id: confirmBtn
                        text: root.pairingStatus === "paired" ? "Cerrar" : "Confirmar"
                        variant: "primary"
                        onClicked: {
                            root.open = false
                            if (root.pairingStatus === "paired") {
                                root.pairConfirmed()
                            } else {
                                root.pairConfirmed()
                                root.pairingStatus = "paired"
                            }
                        }
                        focus: true
                        KeyNavigation.tab: rejectBtn
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                    }

                    MichiButton {
                        id: rejectBtn
                        text: "Cancelar"
                        variant: "ghost"
                        onClicked: {
                            root.open = false
                            root.pairRejected()
                        }
                        KeyNavigation.tab: retryBtn
                        KeyNavigation.backtab: confirmBtn
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                        Keys.onEscapePressed: {
                            root.open = false
                            root.pairRejected()
                        }
                    }

                    MichiButton {
                        id: retryBtn
                        text: "Reintentar"
                        variant: "secondary"
                        visible: root.pairingStatus === "failed"
                        onClicked: {
                            root.pairingStatus = "waiting"
                            root.errorMessage = ""
                            root.retryRequested()
                        }
                        KeyNavigation.backtab: rejectBtn
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                    }
                }
            }
        }

        FocusScope {
            focus: root.visible
        }
    }
}
