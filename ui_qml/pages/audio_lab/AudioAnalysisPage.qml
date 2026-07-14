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
                text: "Análisis técnico"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
            }
            Text {
                text: "Formato, codec, contenedor, duración, tamaño, bitrate, sample rate, bit depth, canales, channel layout, encoder, tags, artwork, ReplayGain, peak, loudness, clipping, silencios, checksum, decode status, corrupción, inconsistencias."
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
            }

            AudioInputSelection {}

            AudioSelectionSummary { width: parent.width }

            SectionHeader { text: "Resultado del análisis"; width: parent.width }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
                Text {
                    anchors.centerIn: parent
                    text: "Selecciona archivos para analizar"
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                }
                height: 120
            }

            AudioTechnicalReport { width: parent.width }

            AudioWaveformSummary { width: parent.width }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton { text: "Analizar selección"; variant: "primary"; enabled: root.labService && root.labService.backendInfo && root.labService.backendInfo.available }
                MichiButton { text: "Volver"; variant: "ghost"; onClicked: { if (root.nav) root.nav.back() } }
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "status"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    StatusBadge { text: "UNSUPPORTED"; kind: "danger" }
                    Text { text: "Si no hay backend disponible, se mostrará UNSUPPORTED con explicación. No se inventan datos."; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap }
                }
            }
        }
    }
}
