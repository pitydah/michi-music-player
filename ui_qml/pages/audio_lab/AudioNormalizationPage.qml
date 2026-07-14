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
                text: "Normalización"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: "ReplayGain metadata (no destructivo) / Player-side gain (en memoria) / Normalización destructiva (requiere confirmación explícita)"
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
            }

            AudioInputSelection {}
            AudioSelectionSummary { width: parent.width }

            SectionHeader { text: "Tipo de normalización"; width: parent.width }

            GlassCard {
                width: parent.width; height: 70
                title: "ReplayGain metadata"
                subtitle: "Escribe etiquetas de ganancia — no destructivo"
                variant: "accent"
            }
            GlassCard {
                width: parent.width; height: 70
                title: "Player-side gain"
                subtitle: "Aplicar ganancia en reproducción — no destructivo"
                variant: "base"
            }
            GlassCard {
                width: parent.width; height: 70
                title: "Normalización destructiva"
                subtitle: "Sobrescribe archivo — requiere confirmación explícita"
                variant: "danger"
            }

            SectionHeader { text: "Resultados"; width: parent.width }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "status"
                Text {
                    anchors.centerIn: parent
                    text: "Selecciona archivos y tipo para analizar"
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                }
                height: 80
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton { text: "Medir loudness"; variant: "primary" }
                MichiButton { text: "Aplicar"; variant: "primary"; enabled: false }
                MichiButton { text: "Volver"; variant: "ghost"; onClicked: { if (root.nav) root.nav.back() } }
            }
        }
    }
}
