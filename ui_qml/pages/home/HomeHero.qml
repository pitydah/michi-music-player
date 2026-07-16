import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Home Hero"
    objectName: "homeHero"
    focus: true
    id: root

    implicitHeight: 200

    HeroMaterial {
        anchors.fill: parent
        radius: MichiTheme.radiusLg
        showGlow: true

        Row {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            spacing: MichiTheme.spacing.xl

            Column {
                width: parent.width * 0.60
                anchors.verticalCenter: parent.verticalCenter
                spacing: MichiTheme.spacing.md

                Text {
                    text: "Centro Michi"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.heroTitleSize
                    font.weight: MichiTheme.typography.weightBold
                }

                Text {
                    text: "Tu ecosistema musical. Biblioteca, servidores, Home Audio y asistente en un solo lugar."
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    width: parent.width
                    wrapMode: Text.WordWrap
                    lineHeight: 1.5
                }

                Row {
                    spacing: MichiTheme.spacing.sm

                    MichiButton {
                        text: "Continuar escuchando"
                        variant: "primary"
                        onClicked: {
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("playback")
                        }
                    }

                    MichiButton {
                        text: "Explorar"
                        variant: "ghost"
                        onClicked: {
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("library")
                        }
                    }
                }
            }

            Item {
                width: parent.width * 0.35
                height: parent.height
                anchors.verticalCenter: parent.verticalCenter

                Rectangle {
                    anchors.centerIn: parent
                    width: 100
                    height: 100
                    radius: 50
                    color: MichiTheme.colors.accentSurface
                    border.color: MichiTheme.colors.borderFocus
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "MM"
                        color: MichiTheme.colors.accentBlue
                        font.pixelSize: 28
                        font.weight: MichiTheme.typography.weightBold
                        font.letterSpacing: 2.0
                        opacity: 0.50
                    }
                }
            }
        }
    }
}
