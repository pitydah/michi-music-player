import QtQuick
import "../../theme"
import "../../materials"
import "../../components"

Item {
    id: root

    property string microServerState: "not_configured"
    property bool localServer: false

    signal openConnections()
    signal openHomeAudio()

    implicitHeight: 210

    GlassMaterial {
        anchors.fill: parent
        hovered: mouseArea.containsMouse
        interactive: true
        radius: MichiTheme.radiusMd

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
        }

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.md

            Text {
                text: "Ecosistema Michi"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Row {
                spacing: MichiTheme.spacing.sm
                StatusBadge {
                    text: {
                        switch (root.microServerState) {
                            case "connected": return "Conectado"
                            case "detected": return "Detectado"
                            default: return "No configurado"
                        }
                    }
                    kind: {
                        switch (root.microServerState) {
                            case "connected": return "success"
                            case "detected": return "info"
                            default: return "disconnected"
                        }
                    }
                }
                StatusBadge { text: "Experimental"; kind: "experimental" }
            }

            Text {
                text: "Michi Micro Server — Servidor musical doméstico del ecosistema Michi"
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                width: parent.width
                wrapMode: Text.WordWrap
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: "Ver servidores"
                    variant: "primary"
                    onClicked: root.openConnections()
                }
                MichiButton {
                    text: "Home Audio"
                    variant: "secondary"
                    onClicked: root.openHomeAudio()
                }
            }
        }
    }
}
