import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    id: root

    property string state: "not_configured"
    property string objectName: "connections.microServerHero"

    signal scanClicked()
    signal manualAddClicked()

    implicitHeight: 220

    Accessible.role: Accessible.Panel
    Accessible.name: "Micro Servidor"
    Accessible.description: "Estado: " + root.state

    HeroMaterial {
        anchors.fill: parent
        radius: MichiTheme.radiusLg
        showGlow: true

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            spacing: MichiTheme.spacing.md

            Text {
                text: "Michi Micro Server"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.heroTitleSize
                font.weight: MichiTheme.typography.weightBold
                objectName: root.objectName + ".title"
            }

            Text {
                text: "Servidor musical doméstico del ecosistema Michi."
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                width: parent.width * 0.60
                wrapMode: Text.WordWrap
            }

            Row {
                spacing: MichiTheme.spacing.sm
                StatusBadge { text: "Ecosistema Michi"; kind: "info" }
                StatusBadge { text: "Rust - Streaming - Biblioteca central"; kind: "info" }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                StatusBadge {
                    id: stateBadge
                    text: {
                        switch (root.state) {
                            case "connected": return "Conectado"
                            case "detected": return "Detectado"
                            default: return "No configurado"
                        }
                    }
                    kind: {
                        switch (root.state) {
                            case "connected": return "success"
                            case "detected": return "info"
                            default: return "disconnected"
                        }
                    }
                    objectName: root.objectName + ".stateBadge"
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    id: scanBtn
                    text: "Buscar Michi Micro Server"
                    variant: "primary"
                    onClicked: root.scanClicked()
                    objectName: root.objectName + ".scanButton"
                    Accessible.name: "Buscar servidores en la red"
                }
                MichiButton {
                    id: manualBtn
                    text: "Agregar manualmente"
                    variant: "ghost"
                    onClicked: root.manualAddClicked()
                    objectName: root.objectName + ".manualButton"
                    Accessible.name: "Agregar servidor manualmente"
                }
            }
        }
    }
}
