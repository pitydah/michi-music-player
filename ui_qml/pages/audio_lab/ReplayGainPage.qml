import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var labService: typeof audioLabBridge !== "undefined" ? audioLabBridge : null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null

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
                text: "ReplayGain"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: "Análisis track, análisis album, preview, loudness, peak, clipping prevention, escribir etiquetas, eliminar etiquetas, batch, cancelar, resultados, errores por archivo."
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
            }

            AudioInputSelection {}
            AudioSelectionSummary { width: parent.width }

            SectionHeader { text: "Modo de análisis"; width: parent.width }

            Row {
                spacing: MichiTheme.spacing.md
                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2; height: 70
                    title: "Track"
                    subtitle: "Ganancia por pista"
                    variant: "accent"
                }
                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2; height: 70
                    title: "Album"
                    subtitle: "Ganancia uniforme por álbum"
                    variant: "accent"
                }
            }

            SectionHeader { text: "Acciones"; width: parent.width }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton { text: "Analizar"; variant: "primary" }
                MichiButton { text: "Escribir etiquetas"; variant: "secondary" }
                MichiButton { text: "Eliminar etiquetas"; variant: "danger" }
            }

            SectionHeader { text: "Resultados"; width: parent.width }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "status"
                Text {
                    anchors.centerIn: parent
                    text: "Selecciona archivos para analizar ReplayGain"
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                }
                height: 80
            }

            MichiButton { text: "Volver"; variant: "ghost"; onClicked: { if (root.nav) root.nav.back() } }
        }
    }
}
