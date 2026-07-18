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

    implicitHeight: Math.max(160, MichiTheme.typography.heroTitleSize * 6)

    HeroMaterial {
        anchors.fill: parent
        radius: MichiTheme.radius.lg
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
                    text: qsTr("Centro Michi")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.heroTitleSize
                    font.weight: MichiTheme.typography.weightBold
                }

                Text {
                    text: qsTr("Tu ecosistema musical. Biblioteca, servidores, Home Audio y asistente en un solo lugar.")
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    width: parent.width
                    wrapMode: Text.WordWrap
                    lineHeight: 1.5
                }

                Row {
                    spacing: MichiTheme.spacing.sm

                    MichiButton {
                        Accessible.role: Accessible.Button
                        text: qsTr("Continuar escuchando")
                        variant: "primary"
                        onClicked: {
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("playback")
                        }
                    }

                    MichiButton {
                        text: qsTr("Explorar")
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
                    radius: width / 2
                    color: MichiTheme.colors.accentSurface
                    border.color: MichiTheme.colors.borderFocus
                    border.width: MichiTheme.borderWidth

                    Image {
                        anchors.centerIn: parent
                        width: 48
                        height: 48
                        source: "../../../icons/app_icon.svg"
                        sourceSize.width: 48
                        sourceSize.height: 48
                        fillMode: Image.PreserveAspectFit
                    }
                }
            }
        }
    }
}
