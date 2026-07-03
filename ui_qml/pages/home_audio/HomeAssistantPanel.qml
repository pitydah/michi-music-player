import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property string state: "not_configured"

    signal configureClicked()
    signal openDiagnostics()

    implicitHeight: 240

    Column {
        anchors.fill: parent
        spacing: MichiTheme.spacing.lg

        GlassMaterial {
            width: parent.width
            height: 200
            variant: "base"
            radius: MichiTheme.radiusMd

            Column {
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.lg
                spacing: MichiTheme.spacing.md

                Text {
                    text: "Home Assistant"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Text {
                    text: root.state === "not_configured"
                        ? "Home Assistant no está configurado. Conéctalo para controlar la reproducción en tu hogar."
                        : "Home Assistant conectado y operativo."
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    width: parent.width
                    wrapMode: Text.WordWrap
                }

                Row {
                    spacing: MichiTheme.spacing.sm
                    MichiButton {
                        text: root.state === "not_configured" ? "Configurar Home Assistant" : "Abrir Home Assistant"
                        variant: "primary"
                        onClicked: root.configureClicked()
                    }
                    MichiButton {
                        text: "Diagnóstico"
                        variant: "ghost"
                        onClicked: root.openDiagnostics()
                    }
                }

                StatusBadge {
                    text: root.state === "not_configured" ? "No configurado" : "Conectado"
                    kind: root.state === "not_configured" ? "disconnected" : "success"
                }
            }
        }
    }
}
