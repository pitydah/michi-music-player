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
                text: "Conversión de audio"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: "Formatos: FLAC, WAV, AIFF, MP3, AAC/M4A, Opus, Ogg Vorbis, ALAC. Solo audio, sin video."
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
            }

            AudioInputSelection {}

            AudioSelectionSummary { width: parent.width }

            SectionHeader { text: "Perfil de conversión"; width: parent.width }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "accent"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    Text { text: "Formato destino: FLAC"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; font.weight: MichiTheme.typography.weightMedium }
                    Text { text: "Codec: flac | Calidad: lossless | Sample rate: 44100 Hz | Bit depth: 16 | Canales: stereo"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize }
                }
            }

            MichiButton {
                text: "Editar perfil"; variant: "secondary"
                onClicked: { if (root.nav) root.nav.navigate("audio_lab_profiles") }
            }

            SectionHeader { text: "Opciones de salida"; width: parent.width }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    Text { text: "Carpeta: Misma que origen"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize }
                    Text { text: "Naming: {artist} - {title}"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize }
                    Text { text: "Colisiones: Preguntar"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize }
                }
            }

            SectionHeader { text: "Previsualización"; width: parent.width }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "status"
                Text {
                    anchors.centerIn: parent
                    text: "Selecciona archivo y perfil para previsualizar"
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                }
                height: 80
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton { text: "Previsualizar"; variant: "secondary" }
                MichiButton { text: "Convertir"; variant: "primary"; enabled: false }
                MichiButton { text: "Volver"; variant: "ghost"; onClicked: { if (root.nav) root.nav.back() } }
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "status"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    StatusBadge { text: "Requiere ffmpeg"; kind: "info" }
                    StatusBadge { text: "Experimental — sin daemon de conversión en segundo plano"; kind: "experimental" }
                }
            }
        }
    }
}
