import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"
import "../materials"

Item {
    id: root

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

            Text {
                text: "Ecualizador"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            HeroMaterial {
                width: parent.width; height: 200; radius: MichiTheme.radiusLg; showGlow: true
                Column {
                    anchors.centerIn: parent
                    spacing: MichiTheme.spacing.md
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "EQ"
                        color: MichiTheme.colors.accentBlue
                        font.pixelSize: 48; font.weight: MichiTheme.typography.weightBold
                    }
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Ecualizador paramétrico y gráfico"
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                    }
                }
            }

            GlassCard {
                width: parent.width; height: 80
                title: "Modo gráfico"
                subtitle: "Control visual de bandas de frecuencia"
                variant: "base"
                onClicked: {
                    if (typeof navigationBridge !== "undefined" && navigationBridge)
                        navigationBridge.navigate("settings")
                }
            }

            GlassCard {
                width: parent.width; height: 80
                title: "Modo paramétrico"
                subtitle: "Control preciso con Q, frecuencia y ganancia"
                variant: "base"
            }

            GlassCard {
                width: parent.width; height: 80
                title: "Preamplificador"
                subtitle: "Ajuste de ganancia general antes del EQ"
                variant: "base"
            }

            GlassCard {
                width: parent.width; height: 80
                title: "Presets"
                subtitle: "Rock, Pop, Jazz, Clásica, Vocal, Bass Boost..."
                variant: "accent"
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "status"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    StatusBadge { text: "Interfaz clásica disponible"; kind: "info" }
                    StatusBadge { text: "Experimental"; kind: "experimental" }
                }
            }
        }
    }
}
